import re
src = open('factory_loop.js', encoding='utf-8', errors='replace').read()
n = 0
for m in re.finditer(r'x_queue|check_publish_allowed', src):
    s = max(0, m.start()-120)
    txt = src[s:m.start()+150].replace(chr(10), ' ')
    print('...', txt[:280].encode('ascii', 'replace').decode())
    print('---')
    n += 1
    if n >= 8:
        break
print('matches shown:', n)
