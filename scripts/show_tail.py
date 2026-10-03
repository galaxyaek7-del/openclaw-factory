src = open('failfast_out.txt', encoding='utf-8', errors='replace').read()
tail = src[-1500:]
print(tail.encode('ascii', 'replace').decode())
