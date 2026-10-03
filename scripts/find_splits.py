import re
src = open('server.js', encoding='utf-8').read()
pat = re.compile(r"\.split\(['\"]\\n['\"]\)")
ms = list(pat.finditer(src))
print('split-newline occurrences:', len(ms))
for m in ms:
    line = src[:m.start()].count('\n') + 1
    ctx = src[max(0, m.start()-50):m.start()+60].replace('\n', ' ')
    print(' line', line, ':', ctx)
