import re
src = open('affiliate/opportunities.py', encoding='utf-8').read()
i = src.find('def add_opportunity')
print(src[i:i+2500].encode('ascii', 'replace').decode())
