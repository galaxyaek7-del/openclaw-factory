import urllib.request, ssl, re
ctx = ssl.create_default_context()
req = urllib.request.Request("https://aekraft.gumroad.com/l/fetmu", headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8", "replace")
print("page bytes:", len(html))
for pat in ["I want this", "Add to cart", "sold out", "unavailable", "checkout", "Buy now"]:
    print("contains:", pat, "->", pat.lower() in html.lower())
