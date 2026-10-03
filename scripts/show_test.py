src = open('tests/test_affiliate_signals.py', encoding='utf-8').read()
i = src.find('def test_active_cap_enforced')
print(src[max(0, i-600):i+1600].encode('ascii', 'replace').decode())
