import sys
sys.path.insert(0, '.')
from notion_affiliate_agent.content_pipeline import generate_draft, save_draft, _slugify

specs = [
    {'product_name': 'Notion', 'content_type': 'Review', 'audience': 'solo law firms', 'competitor': 'Clio'},
    {'product_name': 'Notion', 'content_type': 'Comparison', 'audience': 'solo law firms', 'competitor': 'Clio'},
    {'product_name': 'Notion', 'content_type': 'Guide', 'audience': 'solo law firms', 'competitor': 'Clio'},
    {'product_name': 'Notion', 'content_type': 'Template', 'audience': 'solo law firms', 'competitor': 'Clio'},
]

titles = [
    'Review: Legal Practice Management OS for solo law firms',
    'Comparison: Notion vs Clio/MyCase for solo law firms',
    'Guide: How to set up client intake matter billing deadline workflow in Notion',
    'Template: Free client intake tracker for solo law firms'
]

for i, spec in enumerate(specs):
    draft = generate_draft(spec['product_name'], spec['content_type'], spec['audience'], spec['competitor'])
    draft['title'] = titles[i]
    draft['slug'] = _slugify(titles[i])
    path = save_draft(draft)
    print(f"Generated: {titles[i]} -> {path}")

# Update local_store content_calendar
import json
from pathlib import Path
store_path = Path("notion_affiliate_agent/local_store.json")
data = json.loads(store_path.read_text(encoding="utf-8"))
for title in titles:
    slug = _slugify(title)
    # Determine content type from title
    ct = "Review" if "Review" in title else "Comparison" if "Comparison" in title else "Guide" if "Guide" in title else "Template"
    data["content_calendar"].append({
        "Title": title,
        "Content Type": ct,
        "Platform": "Blog",
        "Publish Date": "",
        "Status": "Draft Ready",
        "Related Product": "Notion",
        "Author": "AI draft",
        "Review Notes": "NEEDS FOUNDER PERSONAL INPUT: add your personal experience with client intake pain points or small-firm operational insight at flagged spots",
        "Disclosure": "This content contains affiliate links",
        "Affiliate Links Used": "",
        "Created At": __import__("datetime").datetime.now().isoformat()
    })
store_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("Updated local_store content_calendar with 4 drafts")
