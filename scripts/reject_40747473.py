import json, datetime
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
# Record rejection in pipeline
pipe = json.load(open('data/global_pipeline.json', encoding='utf-8'))
pipe['rejected'].append({"id": 40747473, "reason": "D-grade loop06: budget 750-1250 above policy max 250 (Excel-to-PDF formatting fits capability but over-bounds)"})
pipe['at'] = now
json.dump(pipe, open('data/global_pipeline.json', 'w', encoding='utf-8'), indent=1)
# Add to seen registry
try:
    seen = json.load(open('data/seen_opportunities.json', encoding='utf-8'))
    if isinstance(seen, list):
        seen.append(40747473)
    elif isinstance(seen, dict):
        seen.setdefault('ids', []).append(40747473)
    json.dump(seen, open('data/seen_opportunities.json', 'w', encoding='utf-8'))
    print('seen registry updated')
except Exception as e:
    print('seen update:', str(e)[:100])
print('rejected 40747473: over-bounds')
