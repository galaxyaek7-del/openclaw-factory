import re
src = open('affiliate/signals.py', encoding='utf-8').read()
for m in re.finditer(r'[Cc][Aa][Pp]', src):
    s = max(0, m.start()-300)
    print(src[s:m.start()+200].encode('ascii', 'replace').decode())
    print('======')
