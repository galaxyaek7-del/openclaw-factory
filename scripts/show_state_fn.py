import re
src = open('ai_capability/observatory.py', encoding='utf-8', errors='replace').read()
i = src.find('CURRENT')
# find the state function
m = re.search(r'def \w*(?:obsolescen|model_state|classify_model)\w*', src)
print('func:', m.group(0) if m else 'NOT FOUND by that pattern')
for pat in ['def model_state', 'def obsolescence', 'CURRENT', 'currently_used']:
    idxs = [mm.start() for mm in re.finditer(re.escape(pat), src)][:5]
    print(pat, '->', idxs)
