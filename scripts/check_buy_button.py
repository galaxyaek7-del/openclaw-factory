import urllib.request, ssl, re
ctx = ssl.create_default_context()
req = urllib.request.Request("https://aekraft.gumroad.com/l/fetmu", headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8", "replace")
for pat in ["gumroad.com/checkout", "data-gumroad", "cart-link", "$79", "product-price", "purchase", "overlay", "stay-on-site"]:
    print("contains:", pat, "->", pat in html)
m = re.search(r"<title>(.*?)</title>", html)
print("title:", m.group(1) if m else "?")
