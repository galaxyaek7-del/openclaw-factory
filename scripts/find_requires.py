import re
src = open('lib/telegram_commands.js', encoding='utf-8').read()
for m in re.finditer(r'require\([^)]*\)', src):
    print(src[max(0, m.start()-20):m.end()].replace('\n', ' '))
