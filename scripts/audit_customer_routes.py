import re
src = open('server.js', encoding='utf-8').read()
pat = re.compile(r"app\.(?:post|get)\('(/api/customer/[^']+)'")
for m in pat.finditer(src):
    seg = src[m.end():m.end()+3000]
    em = re.search(r'(execFile\(|spawn\(|runPythonService\w*\()', seg)
    print(m.group(1), '->', em.group(1) if em else 'NO-PYTHON-CALL')
