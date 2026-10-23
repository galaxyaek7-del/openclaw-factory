# -*- coding: utf-8 -*-
"""Galaxy Forge -- minimal, independent .xlsx formula evaluator (2026-10-22).

WHY THIS EXISTS
---------------
file_testing_engine.py proves a workbook opens and contains formulas; it
cannot prove the formulas compute the right numbers. No native engine is
available here: LibreOffice is not installed, pycel does not run on
Python 3.14 (ast.Str removed), and `formulas` needs a scipy DLL that this
machine's application-control policy blocks.

This module evaluates the subset of Excel the factory's tool workbooks
actually use, with Excel's semantics for blanks, text and errors:

  literals: numbers, "text" (with "" escapes), TRUE/FALSE
  references: A1, $A$1, A1:B9, Sheet!A1, 'Sheet name'!A1:B9
  operators: + - * / & = <> < > <= >=, unary -, parentheses
  functions: IF (lazy), AND, OR, NOT, SUM, COUNTIF (equality criterion),
             MAX, MIN, ROUND, ABS, IFERROR
  dates: date cells become Excel day serials, so D2+30 and G2-F2 work

Anything else raises Unsupported, so a caller reports the cell as
UNVERIFIED instead of guessing. Pure Python + openpyxl; no network.
"""
from __future__ import annotations

import datetime as _dt
import re

import openpyxl
from openpyxl.utils import column_index_from_string, get_column_letter


class Unsupported(Exception):
    """A formula uses syntax or a function outside the supported subset."""


class XLError:
    def __init__(self, code):
        self.code = code

    def __eq__(self, other):
        return isinstance(other, XLError) and other.code == self.code

    def __repr__(self):
        return self.code


VALUE = XLError("#VALUE!")
DIV0 = XLError("#DIV/0!")
BLANK = object()  # an empty cell (distinct from the empty string a formula returns)

_TOKEN = re.compile(r"""
    (?P<ws>\s+)
  | (?P<str>"(?:[^"]|"")*")
  | (?P<ref>(?:'(?:[^']|'')+'!|[A-Za-z_][A-Za-z0-9_ .]*!)?\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?)
  | (?P<num>\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)
  | (?P<func>[A-Z][A-Z0-9.]*(?=\())
  | (?P<bool>TRUE|FALSE)\b
  | (?P<op><>|<=|>=|[-+*/&=<>(),])
""", re.X)


def _tokens(src):
    pos, out = 0, []
    while pos < len(src):
        m = _TOKEN.match(src, pos)
        if not m:
            raise Unsupported(f"cannot parse at {src[pos:pos + 20]!r}")
        pos = m.end()
        kind = m.lastgroup
        if kind != "ws":
            out.append((kind, m.group()))
    return out


class _Parser:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def take(self, value=None):
        tok = self.peek()
        if value is not None and tok[1] != value:
            raise Unsupported(f"expected {value!r}, got {tok[1]!r}")
        self.i += 1
        return tok

    def parse(self):
        node = self.comparison()
        if self.i != len(self.t):
            raise Unsupported(f"trailing tokens {self.t[self.i:]}")
        return node

    def comparison(self):
        node = self.concat()
        while self.peek()[1] in ("=", "<>", "<", ">", "<=", ">="):
            op = self.take()[1]
            node = ("cmp", op, node, self.concat())
        return node

    def concat(self):
        node = self.additive()
        while self.peek()[1] == "&":
            self.take()
            node = ("cat", node, self.additive())
        return node

    def additive(self):
        node = self.term()
        while self.peek()[1] in ("+", "-"):
            op = self.take()[1]
            node = ("arith", op, node, self.term())
        return node

    def term(self):
        node = self.unary()
        while self.peek()[1] in ("*", "/"):
            op = self.take()[1]
            node = ("arith", op, node, self.unary())
        return node

    def unary(self):
        if self.peek()[1] == "-":
            self.take()
            return ("neg", self.unary())
        if self.peek()[1] == "+":
            self.take()
            return self.unary()
        return self.primary()

    def primary(self):
        kind, val = self.take()
        if kind == "num":
            return ("lit", float(val))
        if kind == "str":
            return ("lit", val[1:-1].replace('""', '"'))
        if kind == "bool":
            return ("lit", val == "TRUE")
        if kind == "ref":
            return ("ref", val)
        if kind == "func":
            self.take("(")
            args = []
            if self.peek()[1] != ")":
                args.append(self.comparison())
                while self.peek()[1] == ",":
                    self.take()
                    args.append(self.comparison())
            self.take(")")
            return ("call", val.upper(), args)
        if val == "(":
            node = self.comparison()
            self.take(")")
            return node
        raise Unsupported(f"unexpected token {val!r}")


def _num(v):
    if v is BLANK:
        return 0.0
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, XLError):
        return v
    try:
        return float(v)
    except (TypeError, ValueError):
        return VALUE


def _cmp(op, a, b):
    if isinstance(a, XLError):
        return a
    if isinstance(b, XLError):
        return b
    # Excel: a blank cell equals "" and equals 0.
    if a is BLANK:
        a = "" if isinstance(b, str) else (False if isinstance(b, bool) else 0.0)
    if b is BLANK:
        b = "" if isinstance(a, str) else (False if isinstance(a, bool) else 0.0)
    rank = lambda v: 2 if isinstance(v, bool) else (1 if isinstance(v, str) else 0)  # noqa: E731
    if rank(a) != rank(b):
        ra, rb = rank(a), rank(b)
        return {"=": False, "<>": True, "<": ra < rb, ">": ra > rb, "<=": ra < rb, ">=": ra > rb}[op]
    if isinstance(a, str):
        a, b = a.lower(), b.lower()
    return {"=": a == b, "<>": a != b, "<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b}[op]


class Workbook:
    """Evaluate cells of a saved .xlsx. evaluate('Sheet!A1') -> value."""

    def __init__(self, path):
        self.wb = openpyxl.load_workbook(path, data_only=False)
        self.cache = {}

    def _split(self, ref, sheet):
        if "!" in ref:
            s, r = ref.rsplit("!", 1)
            sheet = s[1:-1].replace("''", "'") if s.startswith("'") else s
            ref = r
        return sheet, ref.replace("$", "")

    def cell(self, sheet, coord):
        key = (sheet, coord)
        if key in self.cache:
            v = self.cache[key]
            if v is _IN_PROGRESS:
                raise Unsupported(f"circular reference at {sheet}!{coord}")
            return v
        if sheet not in self.wb.sheetnames:
            raise Unsupported(f"unknown sheet {sheet!r}")
        raw = self.wb[sheet][coord].value
        if isinstance(raw, (_dt.datetime, _dt.date)):
            raw = excel_serial(raw)  # Excel stores dates as day serials
        if raw is None:
            val = BLANK
        elif isinstance(raw, str) and raw.startswith("="):
            self.cache[key] = _IN_PROGRESS
            val = self._eval(_Parser(_tokens(raw[1:])).parse(), sheet)
        else:
            val = raw
        self.cache[key] = val
        return val

    def _range(self, ref, sheet):
        sheet, r = self._split(ref, sheet)
        a, b = r.split(":")
        ca, ra = re.match(r"([A-Z]+)(\d+)", a).groups()
        cb, rb = re.match(r"([A-Z]+)(\d+)", b).groups()
        out = []
        for col in range(column_index_from_string(ca), column_index_from_string(cb) + 1):
            for row in range(int(ra), int(rb) + 1):
                out.append(self.cell(sheet, f"{get_column_letter(col)}{row}"))
        return out

    def _values(self, node, sheet):
        if node[0] == "ref" and ":" in node[1]:
            return self._range(node[1], sheet), True
        return [self._eval(node, sheet)], False

    def _eval(self, node, sheet):
        kind = node[0]
        if kind == "lit":
            return node[1]
        if kind == "ref":
            if ":" in node[1]:
                raise Unsupported("range used outside a function")
            return self.cell(*self._split(node[1], sheet))
        if kind == "neg":
            v = _num(self._eval(node[1], sheet))
            return v if isinstance(v, XLError) else -v
        if kind == "arith":
            a, b = _num(self._eval(node[2], sheet)), _num(self._eval(node[3], sheet))
            for v in (a, b):
                if isinstance(v, XLError):
                    return v
            op = node[1]
            if op == "/":
                return DIV0 if b == 0 else a / b
            return a + b if op == "+" else a - b if op == "-" else a * b
        if kind == "cat":
            a, b = self._eval(node[1], sheet), self._eval(node[2], sheet)
            for v in (a, b):
                if isinstance(v, XLError):
                    return v
            text = lambda v: "" if v is BLANK else (("TRUE" if v else "FALSE") if isinstance(v, bool) else  # noqa: E731
                                                     (f"{v:g}" if isinstance(v, float) else str(v)))
            return text(a) + text(b)
        if kind == "cmp":
            return _cmp(node[1], self._eval(node[2], sheet), self._eval(node[3], sheet))
        if kind == "call":
            return self._call(node[1], node[2], sheet)
        raise Unsupported(f"node {kind}")

    def _truth(self, v):
        if isinstance(v, XLError):
            return v
        if v is BLANK:
            return False
        if isinstance(v, str):
            if v.upper() in ("TRUE", "FALSE"):
                return v.upper() == "TRUE"
            return VALUE
        return bool(v)

    def _call(self, name, args, sheet):
        if name == "IF":
            cond = self._truth(self._eval(args[0], sheet))
            if isinstance(cond, XLError):
                return cond
            if cond:
                return self._eval(args[1], sheet) if len(args) > 1 else True
            return self._eval(args[2], sheet) if len(args) > 2 else False
        if name == "IFERROR":
            v = self._eval(args[0], sheet)
            return self._eval(args[1], sheet) if isinstance(v, XLError) else v
        if name in ("AND", "OR"):
            vals = []
            for a in args:
                for v in self._values(a, sheet)[0]:
                    t = self._truth(v)
                    if isinstance(t, XLError):
                        return t
                    vals.append(t)
            return all(vals) if name == "AND" else any(vals)
        if name == "NOT":
            t = self._truth(self._eval(args[0], sheet))
            return t if isinstance(t, XLError) else not t
        if name in ("SUM", "MAX", "MIN"):
            nums = []
            for a in args:
                vals, is_range = self._values(a, sheet)
                for v in vals:
                    if isinstance(v, XLError):
                        return v
                    if is_range and (v is BLANK or isinstance(v, (str, bool))):
                        continue  # ranges skip text, blanks and booleans
                    n = _num(v)
                    if isinstance(n, XLError):
                        return n
                    nums.append(n)
            if name == "SUM":
                return sum(nums)
            return (max(nums) if name == "MAX" else min(nums)) if nums else 0.0
        if name == "COUNTIF":
            vals, _ = self._values(args[0], sheet)
            crit = self._eval(args[1], sheet)
            if isinstance(crit, str) and crit[:1] in "<>=":
                raise Unsupported("COUNTIF with an operator criterion")
            return float(sum(1 for v in vals if v is not BLANK and _cmp("=", v, crit) is True))
        if name == "ROUND":
            v, d = _num(self._eval(args[0], sheet)), _num(self._eval(args[1], sheet))
            return v if isinstance(v, XLError) else round(v, int(d))
        if name == "ABS":
            v = _num(self._eval(args[0], sheet))
            return v if isinstance(v, XLError) else abs(v)
        raise Unsupported(f"function {name}")

    def evaluate(self, ref):
        sheet, coord = ref.rsplit("!", 1)
        v = self.cell(sheet.strip("'"), coord.replace("$", ""))
        return "" if v is BLANK else v


_IN_PROGRESS = object()
_EPOCH = _dt.datetime(1899, 12, 30)


def excel_serial(d):
    """Excel's 1900 date system serial (valid for dates after 1900-03-01)."""
    if not isinstance(d, _dt.datetime):
        d = _dt.datetime(d.year, d.month, d.day)
    delta = d - _EPOCH
    return delta.days + delta.seconds / 86400.0
