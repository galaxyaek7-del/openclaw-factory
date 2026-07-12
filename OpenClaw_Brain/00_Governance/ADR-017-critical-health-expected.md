# ADR-017 — Critical Health = Expected When No Live Publish Yet

**التاريخ:** 2026-07-12
**الحالة:** معتمَد، توثيقي فقط (لا كود مُعدَّل).

## القرار

`verdict: "CRITICAL"` في `/health` (مصدره `reality.py`، لا `factory_loop.js`) هو **إشارة صحيحة متوقَّعة**، لا عطل، طالما `total_published: 0` — أي طالما لا `GUMROAD_ACCESS_TOKEN` ولا `FACTORY_LIVE_PUBLISH=true` (القاعدة الحرجة #1، `CLOSING_NOTE.md` §3). السبب المسجَّل حالياً حرفياً: "Zero products published on any channel... The factory produces inventory nobody can buy" — صحيح تماماً، وليس فشلاً بنيوياً في الأذرع أو `factory_loop.js`.

**لا تُفزَّع من هذا الـverdict ولا تُحقِّق فيه كعطل** حتى يتغيّر أحد الشرطين أعلاه فعلياً؛ حينها فقط CRITICAL المستمر يصبح إشارة حقيقية تستحق تحقيقاً.

## الأثر

لا كود مُعدَّل. توثيق فقط — يمنع تحقيقاً مستقبلياً مكرراً في نفس الاستنتاج (تحقَّق منه فعلياً 2026-07-12 عبر `curl /api/reality`).
