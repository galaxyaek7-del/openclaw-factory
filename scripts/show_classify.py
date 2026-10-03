import re
src = open('autonomous_operations.py', encoding='utf-8', errors='replace').read()
i = src.find('def classify_action_autonomy')
print(src[i:i+1800].encode('ascii', 'replace').decode())
