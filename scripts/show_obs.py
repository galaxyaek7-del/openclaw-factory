src = open('C:/openclaw-ci-repro2/tests/test_ai_observatory.py', encoding='utf-8').read()
i = src.find('def test_governance_category_is_registered_at_recommend_level')
print(src[max(0, i-1500):i+800])
