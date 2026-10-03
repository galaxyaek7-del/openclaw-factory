import json
#LAST gpt-oss-20b usage in real cost log
try:
    lines = [l for l in open('data/ai_cost_log.jsonl', encoding='utf-8') if l.strip()]
    print('log lines:', len(lines))
    last = None
    for l in lines:
        r = json.loads(l)
        if r.get('model') == 'openai/gpt-oss-20b':
            last = r.get('timestamp')
    print('last gpt-oss-20b call:', last)
except Exception as e:
    print('ERR', e)
# staleness rule in observatory
src = open('ai_capability/observatory.py', encoding='utf-8', errors='replace').read()
import re
i = src.find('WATCH')
print(src[max(0, i-800):i+400].encode('ascii', 'replace').decode())
