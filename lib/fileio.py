"""Galaxy Forge — deterministic file I/O (P7: one encoding policy).

read_text(): tries utf-8-sig, utf-16 (BOM), utf-8; returns (text, encoding).
write_text(): explicit encoding required, default utf-8; utf-16 always
writes BOM (matches repo convention for dashboard/index.html files).
Any genuine decode failure raises with a clear recovery message instead
of triggering blind retries upstream.
"""
import os

_ORDER = ("utf-8-sig", "utf-16", "utf-8")


class DecodeError(ValueError):
    """No known encoding decoded the file — inspect bytes manually."""


def read_text(path):
    """Return (text, encoding_used). Raises DecodeError or OSError."""
    with open(path, "rb") as fh:
        raw = fh.read()
    for enc in _ORDER:
        try:
            return raw.decode(enc), enc
        except (UnicodeDecodeError, ValueError):
            continue
    raise DecodeError("undecodable with %s: %s (inspect bytes, do not retry blindly)"
                      % ("/".join(_ORDER), path))


def write_text(path, text, encoding="utf-8"):
    """Write with explicit encoding. Creates parent dirs. Returns encoding."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding=encoding, newline="") as fh:
        fh.write(text)
    return encoding
