import re
src = open('affiliate/opportunities.py', encoding='utf-8').read()
m = re.search(r'MAX_ACTIVE\s*=\s*\d+', src)
print('MAX_ACTIVE:', m.group(0) if m else 'NOT FOUND')
i = src.find('def evidence_gate_check')
print(src[i:i+1200].encode('ascii', 'replace').decode())
