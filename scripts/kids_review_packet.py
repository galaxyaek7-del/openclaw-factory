#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One Arabic review sheet per children's episode (2026-11-05), so the founder's two reviews take minutes.

Reads kids_studio/publishing/episodes.json, the episode's subtitles, its verification record and its video digest, and
writes kids_studio/review/REVIEW_<episode>.md: every subtitle cue with its time (tick the ones read aloud), the exact
title/description/tags that will be published, the child-safety and Arabic checklist, and the approval command.

It approves NOTHING and writes no approval: the approval is the founder's statement that the reviews were done.

    python scripts/kids_review_packet.py
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "kids_studio" / "publishing" / "episodes.json"
OUT = ROOT / "kids_studio" / "review"

SAFETY = [
    "لا مشاهد مخيفة ولا مطاردات ولا خطر",
    "لا سلوك يمكن لطفل أن يقلّده بشكل غير آمن (القفز، التسلّق، لمس المكسور، اللعب قرب ماء عميق)",
    "المواقف الخطرة تُحَلّ بالتوقّف وإخبار شخص بالغ",
    "لا سخرية ولا إقصاء ولا إهانة ولا عنف بين الشخصيات",
    "لا علامات تجارية ولا إعلانات ولا روابط ولا دعوات للشراء",
    "لا وميض سريع (أقل من 3 ومضات في الثانية)",
]
ARABIC = [
    "كل جملة فصحى سليمة نحواً وإملاءً ومناسبة لعمر 4 إلى 8 سنوات",
    "التشكيل صحيح في كل الجمل",
    "النص يُقرأ جهراً بسلاسة وفي زمن الظهور المحدّد",
    "الدرس واضح من الأحداث لا من الجمل وحدها",
    "العنوان والوصف خاليان من الأخطاء",
]


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cues(srt_text):
    out = []
    for block in re.split(r"\n\s*\n", srt_text.strip()):
        lines = block.strip().splitlines()
        if len(lines) >= 3 and "-->" in lines[1]:
            out.append((lines[1].split(" --> ")[0][:8], " ".join(lines[2:])))
    return out


def sheet(ep, root=ROOT):
    video = root / ep["video"]
    digest = sha256(video) if video.exists() else "(video file missing)"
    ver = {}
    try:
        ver = json.loads((root / ep["verify"]).read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError):
        pass
    try:
        rows = cues((root / ep["subtitles"]).read_text(encoding="utf-8"))
    except OSError:
        rows = []
    dur = ver.get("container_duration_s")
    L = [f"# ورقة مراجعة: {ep['episode']}", "",
         f"- الملف: `{ep['video']}`" + (f"، المدة {float(dur):.0f} ثانية" if dur else ""),
         f"- البصمة (sha256): `{digest}`",
         f"- الوصف الداخلي: {ep.get('label', '')}",
         f"- فحوص التحقق الآلية: {sum(1 for v in (ver.get('checks') or {}).values() if v)}/{len(ver.get('checks') or {})} ناجحة",
         "- هذه الحلقة بلا أصوات: الحوار في مسار الترجمة العربية فقط.", "",
         "## 1. ما سيُنشر بالضبط", f"**العنوان:** {ep.get('title', '')}", "", f"**الوصف:** {ep.get('description', '')}", "",
         "**الوسوم:** " + "، ".join(ep.get("tags", [])), "",
         "## 2. الترجمة العربية (اقرأها جهراً مع الفيديو)", "", "| ☐ | الزمن | الجملة |", "|---|---|---|"]
    L += [f"| ☐ | {t} | {txt} |" for t, txt in rows]
    L += ["", "## 3. سلامة الطفل (شاهد الفيديو كاملاً)", ""] + [f"- ☐ {x}" for x in SAFETY]
    L += ["", "## 4. اللغة العربية", ""] + [f"- ☐ {x}" for x in ARABIC]
    L += ["", "## 5. الموافقة (بعد إنهاء 3 و4 فقط)", "",
          "```", f"python scripts/approve_kids_episode.py --episode {ep['episode']} --privacy unlisted --child-safety-reviewed --arabic-reviewed", "```",
          "الموافقة مربوطة ببصمة الملف أعلاه وتنتهي بعد 14 يوماً. إن أُعيد بناء الفيديو تلزم موافقة جديدة.",
          "الأمر يعني أنك أنت راجعت. لا يكتبه الوكيل عنك.", ""]
    return "\n".join(L)


def main():
    reg = json.loads(REG.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for ep in reg["episodes"]:
        p = OUT / f"REVIEW_{ep['episode']}.md"
        p.write_text(sheet(ep), encoding="utf-8")
        made.append(str(p.relative_to(ROOT)))
    sys.stdout.write(json.dumps({"written": made}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
