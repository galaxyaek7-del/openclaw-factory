import urllib.request, ssl, re
ctx = ssl.create_default_context()
req = urllib.request.Request("https://aekraft.gumroad.com/l/fetmu", headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8", "replace")
hrefs = re.findall(r'href="([^"]{0,120})"', html)
print("total hrefs:", len(hrefs))
seen = set()
for h in hrefs:
    if h not in seen:
        seen.add(h)
        print(" -", h[:110])
