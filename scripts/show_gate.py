import re
src = open('affiliate/opportunities.py', encoding='utf-8').read()
i = src.find('def _real_evidence')
print(src[i:i+700].encode('ascii', 'replace').decode())
i2 = src.find('def read_queue')
print(src[i2:i2+600].encode('ascii', 'replace').decode())
