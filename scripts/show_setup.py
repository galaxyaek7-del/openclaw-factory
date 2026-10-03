src = open('tests/test_affiliate_signals.py', encoding='utf-8').read()
i = src.find('def setUp')
print(src[i:i+1200].encode('ascii', 'replace').decode())
print('=======')
import re
m = re.search(r'ACTIVE_CAP|MAX_ACTIVE|cap', open('affiliate_signals.py', encoding='utf-8').read()) if __import__('os').path.exists('affiliate_signals.py') else None
import glob
print('signal module candidates:', glob.glob('*signal*.py'), glob.glob('affiliate/*signal*.py'))
