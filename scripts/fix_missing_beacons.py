import glob, os
BEACON = '<script>\nfetch(\'/api/page-view\', { method: \'POST\', headers: {\'Content-Type\':\'application/json\'}, body: JSON.stringify({ page_id: \'%s\' }) }).catch(()=>{});\n</script>\n</body>'
fixed = []
for p in sorted(glob.glob('customer_site/*.html')):
    content = open(p, encoding='utf-8', errors='replace').read()
    if 'page-view' in content:
        continue
    page_id = os.path.basename(p).replace('.html', '')
    if '</body>' not in content:
        print(f'SKIP (no body tag): {p}')
        continue
    new = content.replace('</body>', BEACON % page_id, 1)
    open(p, 'w', encoding='utf-8').write(new)
    fixed.append(os.path.basename(p))
print(f'Fixed {len(fixed)} pages:')
for f in fixed:
    print(f'  + {f}')
