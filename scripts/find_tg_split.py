import re
src = open('lib/telegram_commands.js', encoding='utf-8').read()
for m in re.finditer(r"split\(", src):
    s = max(0, m.start()-250)
    seg = src[s:m.start()+150].replace('\n', ' ')
    print('...', seg.encode('ascii', 'replace').decode())
    print('---')
