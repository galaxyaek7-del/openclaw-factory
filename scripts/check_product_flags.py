import sys, json
sys.path.insert(0, '.')
import channels.gumroad_arm
from channels.registry import get
g = get('gumroad')
r = g.list_products()
pid = r['products'][0]['id']
d = g.get_product(pid)['product']
for k in sorted(d.keys()):
    print(str(k) + ': ' + str(d[k])[:80])
