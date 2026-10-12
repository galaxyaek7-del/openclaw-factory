"""Publish Legal Case Research Automation guide to Telegraph (one attempt).

Cycle 82 (urgent security + digital products): this was the one product
among the 3 chosen "best sellable" picks (see docs/CYCLE_82_*.md) with real,
cited payment evidence on file (data/market_evidence.jsonl) but, unlike the
other two (EU AI Act, SOC 2 -- see data/telegraph_euact_guide.json /
data/telegraph_soc2_1011.json), no free Telegraph guide yet. Same
zero-cost, no-login, no-spam, single-post pattern already used for every
other product in this factory (scripts/publish_telegraph_dv.py and
siblings) -- Telegraph's createAccount/createPage API is public and free.

Every pricing figure below is copied verbatim from a real, already-recorded
citation in data/market_evidence.jsonl (ADR-121 payment evidence) -- never
invented for this post.
"""
import json
import urllib.request
import urllib.parse
import ssl
import time
import datetime

ctx = ssl.create_default_context()
title = "Solo Attorney AI Research Tools Cost $104-$639/Month. Here's a Cheaper Path"

try:
    data = urllib.parse.urlencode({"short_name": "GalaxyForge", "author_name": "Galaxy Forge"}).encode()
    req = urllib.request.Request("https://api.telegra.ph/createAccount", data=data)
    token = json.loads(urllib.request.urlopen(req, timeout=15, context=ctx).read())["result"]["access_token"]
except Exception as e:
    print("ACCOUNT_FAIL:" + str(e)[:200])
    raise SystemExit(1)

time.sleep(1)

content = [
    {"tag": "p", "children": [
        "Solo attorneys doing case research by hand lose hours per case to manual search. The AI alternatives built for firms price solo practitioners out on purpose."
    ]},
    {"tag": "h2", "children": ["What the enterprise tools actually cost"]},
    {"tag": "p", "children": [
        "CoCounsel by Thomson Reuters: $104-$639 per user/month as of August 2026 "
        "(Westlaw Advantage + CoCounsel Essentials, solo attorney, All States & Federal: "
        "$639.20/user/mo on a 1-year term, or $519.35/user/mo on 3 years, per Thomson Reuters' own public configurator, checked June 2026)."
    ]},
    {"tag": "p", "children": [
        "Lexis+ AI tiers at $128/$314/$494 per month, with a $171/user/month base. Harvey requires a 20-seat minimum, commonly quoted around $288,000/year -- built for firms, not solo practice."
    ]},
    {"tag": "h2", "children": ["The real complaint behind this"]},
    {"tag": "p", "children": [
        {"tag": "em", "children": [
            "“I know, IANAL/get a lawyer but I'm a poor solo dev in the US trying to bootstrap, those overhead costs are just too much when talking to an IP attorney can go for $200+ an hour.”"
        ]},
        " — a real, public comment (Hacker News)."
    ]},
    {"tag": "h2", "children": ["A lighter alternative"]},
    {"tag": "p", "children": [
        "The Legal Case Research Automation Kit is a one-time-purchase workflow guide for solo attorneys -- structured prompts and a research-tracking system for AI-assisted case research, without a per-seat monthly contract:"
    ]},
    {"tag": "p", "children": [
        {"tag": "a", "attrs": {"href": "https://aekraft.gumroad.com/l/uldlwa?utm_source=telegraph&utm_medium=article&utm_campaign=c82_legal_research&utm_content=legal_guide"},
         "children": ["https://aekraft.gumroad.com/l/uldlwa"]}
    ]},
    {"tag": "p", "children": [
        {"tag": "em", "children": ["Disclosure: commercial link, digital product, instant delivery. Pricing figures above are cited from public sources as of the dates noted and may have changed since."]}
    ]},
]

page_data = urllib.parse.urlencode({
    "title": title, "author_name": "Galaxy Forge", "content": json.dumps(content),
    "access_token": token, "return_content": "false",
}).encode()
req = urllib.request.Request("https://api.telegra.ph/createPage", data=page_data)
page = json.loads(urllib.request.urlopen(req, timeout=20, context=ctx).read())
url = page.get("result", {}).get("url", "N/A")
print("PAGE:" + url)

rec = {
    "url": url,
    "published_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "channel": "telegraph",
    "product": "Legal Case Research Automation Kit",
    "campaign": "c82_legal_research",
    "evidence_sources": [
        "https://costbench.com/software/ai-legal-tools/cocounsel/",
        "https://owlesq.com/buyer-guides/best-ai-legal-research-tools-2026",
        "https://news.ycombinator.com/item?id=32244691",
    ],
    "note": "Auth token outside repo.",
}
open("data/telegraph_legal_research_guide.json", "w", encoding="utf-8").write(json.dumps(rec, indent=1, ensure_ascii=False))
print("saved")
