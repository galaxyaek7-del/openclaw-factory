import urllib.request, ssl, re
ctx = ssl.create_default_context()
req = urllib.request.Request("https://aekraft.gumroad.com/l/fetmu", headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8", "replace")
for m in re.finditer(r"[Bb]uy now", html):
    s = max(0, m.start()-200)
    print("---- context ----")
    print(html[s:m.start()+120].replace("\n", " "))
    print()
