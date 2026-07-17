# ADR-062 — سجل تدقيق الاسترجاع (Recovery Audit Log): كل عملية استرجاع حقيقية تُسجَّل، لا استثناء

**التاريخ:** 2026-07-17 (مُوثَّق بأثر رجعي — القرار نُفِّذ فعلياً في Phase 10D، الالتزام `158bad7`)
**الحالة:** مُنفَّذ ومُختبَر.
**يُنفِّذ:** "Executive Directive — Phase 10D: Disaster Recovery & Business Continuity"، Objective 5 (Auditability).

---

## القرار

كل عملية استرجاع أو نشر حقيقية تُغيِّر حالة النظام (`scripts/deploy_production.js --confirm`، `scripts/restore_file_from_git.js --apply`) يجب أن تُسجِّل سجلاً حقيقياً واحداً على الأقل — نجاحاً أو فشلاً — في `data/recovery_actions.jsonl` عبر دالة مشتركة واحدة (`lib/recovery_log.js`'s `recordRecoveryAction()`)، لا نسخة ثانية من نفس المنطق في كل سكربت.

## لماذا

هذا المصنع يعتمد اتفاقية "append-only JSONL + تخطّي السطر الفاسد بأمان" في كل مكان (`data/decisions.jsonl`، `books/_generation_log.jsonl`، `data/golden_hunter_events.jsonl`). كانت هناك فجوة حقيقية: عمليات الاسترجاع/النشر نفسها — وهي أخطر العمليات لأنها تُغيِّر حالة الإنتاج فعلياً — لم يكن لها أي سجل حقيقي دائم. لو حدث استرجاع خاطئ أو نشر فاشل، لا يوجد سجل يجيب: من فعل هذا، لماذا، وماذا تأثَّر.

## ما بُني

- `lib/recovery_log.js`: `recordRecoveryAction({operator, reason, affectedSystems, result})` — يرفض التسجيل بدون كل حقل مطلوب (فشل بصوت عالٍ لا تسجيل ناقص بصمت)، `readRecoveryActions()` يقرأ السجل مع تخطّي أي سطر فاسد.
- كل استدعاء حقيقي لـ`--confirm`/`--apply` في `deploy_production.js`/`restore_file_from_git.js` يستدعي `recordRecoveryAction()` في مساري النجاح والفشل كليهما.
- مُختبَر: `tests/test_recovery_log.js` (5 اختبارات)، بالإضافة إلى سجلات حقيقية فعلية أُنتِجَت أثناء اختبار Phase 10D/12 نفسه (مثال حقيقي من `data/recovery_actions.jsonl`: `{"operator":"Dell","reason":"Phase 10E Final Production Deployment & Go-Live",...,"result":"success — new PID 1520, verified healthy"}`).

## ما لم يُبنَ عمداً

- لا قفل (lock) يمنع كتابتين متزامنتين لنفس السطر — الاعتماد على `fs.appendFileSync`'s طبيعة الكتابة الصغيرة الذرية (نفس افتراض بقية السجلات في هذا المصنع)، غير مُثبَت رسمياً تحت تزامن حقيقي (راجع `ZERO_ASSUMPTION_PRODUCTION_AUDIT.md`، القسم C، "NOT VERIFIED").
