import re
src = open('tests/test_ai_observatory.py', encoding='utf-8').read()
for m in re.finditer(r'^(?:import|from)\s+.*', src, re.M):
    print(m.group(0))
