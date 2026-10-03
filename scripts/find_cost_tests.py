import glob, re
for f in sorted(glob.glob('tests/test_*.py')):
    try:
        src = open(f, encoding='utf-8', errors='replace').read()
    except Exception:
        continue
    if re.search(r'GROQ_PRICING|llama-3\.1|cost_usd|_log_ai_cost', src):
        print(f)
