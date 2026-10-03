import re
src = open('autonomous_operations.py', encoding='utf-8', errors='replace').read()
i = src.find('ACTION_CATEGORY_AUTONOMY')
print(src[i:i+2500].encode('ascii', 'replace').decode())
