import glob, os
pages = sorted(glob.glob('customer_site/*.html'))
with_beacon, without = [], []
for p in pages:
    content = open(p, encoding='utf-8', errors='replace').read()
    (with_beacon if 'page-view' in content else without).append(os.path.basename(p))
print(f'WITH beacon: {len(with_beacon)}')
print(f'WITHOUT beacon: {len(without)}')
for p in without:
    print(f'  MISSING: {p}')
