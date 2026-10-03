import re
src = open('failfast_out.txt', encoding='utf-8', errors='replace').read()
print('total chars:', len(src))
# show first error block
i = src.find('ERROR')
j = src.find('FAIL:')
k = min([x for x in [i, j] if x >= 0])
print(src[max(0, k-200):k+1200].encode('ascii', 'replace').decode())
