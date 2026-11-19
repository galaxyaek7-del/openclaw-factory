#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notion Affiliate Content Pipeline — AI Brokerage Arm

Generates DRAFT content for Notion affiliate marketing using GROQ (existing pipeline).
All content is DRAFT — AWAITING FOUNDER REVIEW, never auto-published.

Reuses: ai_capability/orchestrator.py (GROQ), product data from local_store.json
Outputs: notion_affiliate_agent/drafts/<slug>.md
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
_DRAFTS_DIR = Path(__file__).resolve().parent / "drafts"
_LOCAL_STORE = Path(__file__).resolve().parent / "local_store.json"
_TEMPLATES_DIR = Path(__file__).resolve().parent / "content_templates"

DISCLOSURE_LINE = "This content contains affiliate links. We may earn a commission if you purchase through these links, at no extra cost to you."

# Map content types to prompt templates
CONTENT_TYPE_PROMPTS = {
    "Review": "You are a thoughtful product reviewer. Write a detailed, honest review of {product} for {audience}. Include: what it is, key features, genuine pros (at least 2), genuine cons/drawbacks (at least 2), who it's best for, pricing, and a balanced verdict. Do not exaggerate. Keep tone helpful and personal, but mark every section that would benefit from the Founder's firsthand experience with: NEEDS FOUNDER PERSONAL INPUT: [specific spot]. End with disclosure: 'This content contains affiliate links.' Product data: {product_data}",
    "Comparison": "You are a comparison writer. Write a detailed, fair comparison: Notion vs {competitor} for {audience}. Structure: overview of each, head-to-head on 4-5 criteria (flexibility, learning curve, pricing, integrations, offline access), genuine pros/cons for each, verdict with clear recommendation for different use cases. Do not exaggerate Notion. Mark: NEEDS FOUNDER PERSONAL INPUT: [specific spot] where firsthand comparison would help. End with disclosure. Product data: {product_data}",
    "Guide": "You are a practical guide writer. Write a step-by-step setup guide: How to set up {product} for {audience}. Include: prerequisites, 5-7 clear steps with brief explanations, tips for common pitfalls, and a short troubleshooting note. Mark: NEEDS FOUNDER PERSONAL INPUT: [specific spot] where personal workflow would help. End with disclosure. Product data: {product_data}",
    "Template": "You are a Notion template designer and copywriter. Describe a free Notion template for {audience}: template purpose, included databases/views (3-4), how to use it (3 steps), who it's best for, and customization tips. Include 2 genuine limitations of the template. Mark: NEEDS FOUNDER PERSONAL INPUT: [specific spot] where personal template would help. End with disclosure. Product data: {product_data}"
}

def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return slug[:60]

def _load_products():
    with open(_LOCAL_STORE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("product_tracker", [])

def _call_groq(prompt: str) -> str:
    """Call GROQ via existing ai_capability orchestrator, fallback to template if GROQ unavailable."""
    try:
        from ai_capability.orchestrator import generate as groq_generate
        # Use existing GROQ pipeline — same as book_generator.py would
        result = groq_generate(prompt, task_type="writing")
        if isinstance(result, dict):
            return result.get("content") or result.get("text") or str(result)
        return str(result)
    except Exception as e:
        # Fallback: return prompt with note, so pipeline never crashes — still DRAFT
        return f"[GROQ unavailable: {e}]\n\n[DRAFT TEMPLATE — GROQ call failed, using prompt as placeholder]\n\n{prompt}\n\n---\n\n{DISCLOSURE_LINE}\n\nNEEDS FOUNDER PERSONAL INPUT: entire draft needs Founder voice and firsthand experience."

def generate_draft(product_name: str, content_type: str, audience: str, competitor: str = "Asana") -> dict:
    """
    Generate a DRAFT content piece.

    Returns: {title, content_type, audience, product, content, disclosure, status, flags}
    """
    products = _load_products()
    product = next((p for p in products if p["Name"].lower() == product_name.lower()), None)
    if not product:
        raise ValueError(f"Product '{product_name}' not found in product_tracker. Available: {[p['Name'] for p in products]}")

    if content_type not in CONTENT_TYPE_PROMPTS:
        raise ValueError(f"Unknown content_type '{content_type}'. Available: {list(CONTENT_TYPE_PROMPTS.keys())}")

    prompt = CONTENT_TYPE_PROMPTS[content_type].format(
        product=product_name,
        audience=audience,
        competitor=competitor,
        product_data=json.dumps(product, ensure_ascii=False)
    )

    content = _call_groq(prompt)

    # Ensure disclosure is present
    if "affiliate links" not in content.lower():
        content += f"\n\n{DISCLOSURE_LINE}"

    # Ensure at least one NEEDS FOUNDER PERSONAL INPUT flag
    if "NEEDS FOUNDER PERSONAL INPUT" not in content:
        content = f"NEEDS FOUNDER PERSONAL INPUT: add your personal experience with {product_name} for {audience} — what worked, what didn't, specific example\n\n" + content

    title = f"{content_type}: {product_name} for {audience}"
    slug = _slugify(title)

    return {
        "title": title,
        "content_type": content_type,
        "audience": audience,
        "product": product_name,
        "competitor": competitor if content_type == "Comparison" else None,
        "content": content,
        "disclosure": DISCLOSURE_LINE,
        "status": "DRAFT — AWAITING FOUNDER REVIEW",
        "flags": ["NEEDS FOUNDER PERSONAL INPUT" in content, "affiliate links" in content.lower()],
        "slug": slug,
        "created_at": datetime.now().isoformat(),
    }

def save_draft(draft: dict) -> Path:
    """Save draft to notion_affiliate_agent/drafts/<slug>.md"""
    _DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    path = _DRAFTS_DIR / f"{draft['slug']}.md"
    content = f"# {draft['title']}\n\n"
    content += f"**Status:** {draft['status']}\n\n"
    content += f"**Content Type:** {draft['content_type']} | **Audience:** {draft['audience']} | **Product:** {draft['product']}\n\n"
    if draft.get("competitor"):
        content += f"**Competitor:** {draft['competitor']}\n\n"
    content += f"**Created:** {draft['created_at']}\n\n"
    content += "---\n\n"
    content += draft["content"]
    content += "\n\n---\n\n"
    content += f"*{draft['disclosure']}*\n"
    path.write_text(content, encoding="utf-8")
    return path

def generate_batch(specs: list) -> list:
    """
    Generate a batch of drafts.

    specs: list of {product_name, content_type, audience, competitor?}
    Returns: list of {draft, path}
    """
    results = []
    for spec in specs:
        draft = generate_draft(
            product_name=spec["product_name"],
            content_type=spec["content_type"],
            audience=spec["audience"],
            competitor=spec.get("competitor", "Asana"),
        )
        path = save_draft(draft)
        results.append({"draft": draft, "path": str(path)})
    return results

if __name__ == "__main__":
    # Demo: generate one of each type for Notion, for different audiences
    demo_specs = [
        {"product_name": "Notion", "content_type": "Review", "audience": "small teams"},
        {"product_name": "Notion", "content_type": "Comparison", "audience": "small teams", "competitor": "Asana"},
        {"product_name": "Notion AI", "content_type": "Guide", "audience": "freelancers"},
        {"product_name": "Notion", "content_type": "Template", "audience": "students"},
    ]
    results = generate_batch(demo_specs)
    for r in results:
        print(f"Draft: {r['draft']['title']} -> {r['path']}")
