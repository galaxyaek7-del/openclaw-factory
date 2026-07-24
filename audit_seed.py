"""Galaxy Forge — Seed Quality Auditor

Reads a seed DOCX, extracts one chapter, sends it to Groq for
honest critique. Writes a markdown report. Zero factory impact.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

from docx import Document

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
SEEDS_DIR = os.path.join(FACTORY_DIR, "seeds")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

_CHAPTER_RE = re.compile(r"chapter\s*\d+", re.IGNORECASE)


def _get_groq_key():
    key = os.environ.get("GROQ_KEY")
    if key:
        return key
    env_path = os.path.join(FACTORY_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GROQ_KEY"):
                    return line.split("=", 1)[1].strip()
    return None


def read_docx(path):
    doc = Document(path)

    title = ""
    introduction = ""
    conclusion = ""
    chapters = []

    section = None  # None | "intro" | "chapter" | "conclusion"
    current_chapter = None
    intro_parts = []
    conclusion_parts = []

    for p in doc.paragraphs:
        style = p.style.name if p.style else ""
        text = p.text.strip()

        if style == "Heading 1":
            title = text
            section = None
            continue

        if style == "Heading 2":
            if current_chapter is not None:
                current_chapter["body"] = "\n\n".join(current_chapter["_parts"]).strip()
                del current_chapter["_parts"]
                chapters.append(current_chapter)
                current_chapter = None

            if _CHAPTER_RE.search(text):
                section = "chapter"
                current_chapter = {"heading": text, "_parts": []}
            elif text.lower() == "introduction":
                section = "intro"
            elif text.lower() == "conclusion":
                section = "conclusion"
            else:
                section = None
            continue

        if not text:
            continue

        if section == "intro":
            intro_parts.append(text)
        elif section == "chapter" and current_chapter is not None:
            current_chapter["_parts"].append(text)
        elif section == "conclusion":
            conclusion_parts.append(text)

    if current_chapter is not None:
        current_chapter["body"] = "\n\n".join(current_chapter["_parts"]).strip()
        del current_chapter["_parts"]
        chapters.append(current_chapter)

    introduction = "\n\n".join(intro_parts).strip()
    conclusion = "\n\n".join(conclusion_parts).strip()

    return {
        "title": title,
        "introduction": introduction,
        "chapters": chapters,
        "conclusion": conclusion,
    }


def build_critique_prompt(chapter_body, target_price=6.99):
    system = "You are a harsh book editor. No flattery. No hedging."
    user = f"""Below is one chapter from a self-help ebook targeted at remote workers, priced at ${target_price:.2f}.

Grade it honestly on:
1. Substance (does it teach something concrete?)
2. Voice (does it sound human or AI-generic?)
3. Value-per-word (would a reader feel cheated?)
4. Publishability (would you buy this?)

For each: score 1-10 and cite one specific line as evidence.

Then: 3 concrete rewrites you would make. No general advice.

Chapter:
{chapter_body}"""
    return system, user


def call_groq(prompt, model="llama-3.1-8b-instant", max_tokens=2048, timeout=60):
    system, user = prompt
    key = _get_groq_key()
    if not key:
        raise RuntimeError("GROQ_KEY not found in environment or .env — cannot call Groq")

    payload = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "User-Agent": "Mozilla/5.0 (Galaxy-Forge-SeedAuditor)",
        "Accept": "application/json",
    }

    last_error = None
    for attempt in (1, 2):  # one retry on network error
        try:
            req = urllib.request.Request(GROQ_API_URL, data=payload, method="POST", headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                result = json.loads(r.read().decode("utf-8"))
            text = result["choices"][0]["message"]["content"]
            tokens = None
            usage = result.get("usage") or {}
            if isinstance(usage, dict) and "total_tokens" in usage:
                tokens = usage["total_tokens"]
            return text, tokens
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code in (400, 401, 403):
                break
        except Exception as e:
            last_error = e
        if attempt == 1:
            time.sleep(1)

    raise RuntimeError(f"Groq call failed after retry: {last_error}")


def main():
    parser = argparse.ArgumentParser(description="Audit one chapter of a seed DOCX via Groq critique.")
    parser.add_argument("--docx", required=True)
    parser.add_argument("--chapter", type=int, default=1)
    parser.add_argument("--price", type=float, default=6.99)
    args = parser.parse_args()

    stage = "setup"
    try:
        stage = "read_docx"
        if not os.path.exists(args.docx):
            raise FileNotFoundError(f"DOCX not found: {args.docx}")
        book = read_docx(args.docx)

        stage = "extract_chapter"
        idx = args.chapter - 1
        if idx < 0 or idx >= len(book["chapters"]):
            raise ValueError(
                f"chapter {args.chapter} requested, but only {len(book['chapters'])} chapter(s) found"
            )
        chapter = book["chapters"][idx]
        wordcount = len(chapter["body"].split())
        if wordcount < 50:
            print(f"WARNING: chapter {args.chapter} ('{chapter['heading']}') is only {wordcount} words — continuing anyway.")

        stage = "build_prompt"
        prompt = build_critique_prompt(chapter["body"], target_price=args.price)

        stage = "call_groq"
        model = "llama-3.1-8b-instant"
        critique, tokens_used = call_groq(prompt, model=model)

        stage = "write_report"
        os.makedirs(SEEDS_DIR, exist_ok=True)
        report_path = os.path.join(SEEDS_DIR, "quality_report.md")
        timestamp = datetime.now(timezone.utc).isoformat()
        report = f"""# Quality Audit — {book['title']}

**Chapter audited:** {args.chapter} — {chapter['heading']}
**Wordcount:** {wordcount}
**Model:** {model}
**Tokens used:** {tokens_used}

---

{critique}

---

*Generated: {timestamp}*
"""
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(report)
        print(f"\n[report written to: {report_path}]")

    except Exception as e:
        print(f"FAILED at stage '{stage}': {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
