# مهام التشغيل الذاتي (TASKS.md)

علامة `[ ]` = غير منفَّذة، `[x]` = منفَّذة ومُثبَتة ومُرتَّبة.

آخر تحديث للحالة: 2026-11-25.

## البند 1 — التشغيل التلقائي مع Windows
[x] `scripts/install_factory_autostart.ps1` (متتبَّع في Git) يُسجِّل المهمة `GalaxyForge-Factory-Autostart` عند تسجيل الدخول، التي تُشغِّل `scripts/start_factory_supervised.ps1` (serve + loop تحت المشرف، مع حارس منع النسخة الثانية). نسخة قديمة غير متتبَّعة بنفس الاسم (`install_autostart.ps1`) موجودة على القرص؛ المعتمد هو المتتبَّع.
[x] الإلغاء موثّق في رأس السكربت: `Unregister-ScheduledTask -TaskName 'GalaxyForge-Factory-Autostart' -Confirm:$false`.
[x] التحقق: `Get-ScheduledTask` يعرض المهمة. كانت حالتها `Disabled` وفُعِّلت إلى `Ready` في 2026-11-25.
[ ] التحقق بإعادة تشغيل Windows حقيقية — إجراء مؤسس (FOUNDER_ACTIONS #5)؛ لم يُنفَّذ بعد.

## البند 2 — تقوية المشرف
[x] إعادة تشغيل `server.js` و`factory_loop.js` عند التعطل مع backoff (`SUPERVISOR_BACKOFF_MS`) وcooldown (`SUPERVISOR_COOLDOWN_MS`) وحارس حلقة تعطل (`SUPERVISOR_MAX_RESTARTS`/`SUPERVISOR_WINDOW_MS`) — `scripts/supervisor.js`.
[x] فحص صحة حقيقي على `/health`: `diagnose()` في `factory_loop.js` يستعلم `/health` كل دورة ويسجّل لقطات حقيقية عبر `lib/health_trend.js`.
[x] تدوير السجلات: `rotateLoopLog()` للحلقة (اختبار `tests/test_factory_loop_log_rotation.js`) و`rotateLog()` للمشرف (جديد 2026-11-25؛ اختبار `tests/test_supervisor_stop_rotation.js`).

## البند 3 — حلقة العمل الذاتية
**BLOCKED — يحتاج ADR من المؤسس (2026-11-18):** هذا البند يعيد فتح "التنفيذ التلقائي المستمر" الذي رُفض ست مرات (ADR-107/110/115/142/147/157) ويمنعه `CLAUDE.md` صراحة. لا يُبنى `autopilot.ps1` قبل قرار مؤسس صريح يعدّل ADR-157. التفاصيل: `docs/claude_md/08_governance_precedence.md` (C3).
[ ] scripts/autopilot.ps1 تُنفِّذ دورة OpenCode واحدة جديدة غير تفاعلية كل N دقائق.
[ ] ملف قفل يمنع دورتين متداخلتين.
[ ] منهلة زمنية لكل دورة.
[ ] أقصى دورات في اليوم.
[ ] إيقاف تلقائي إذا Failed نفس المهمة 3 دورات متتالية (تُعرَف BLOCKED مع الخطأ الحقيقي).
[ ] جلسة جديدة لكل دورة (لا تعبئة للسياق).

## البند 4 — نبض القلب والتنبيهات
[x] كتابة `data/heartbeat.json` في كل دورة: `writeHeartbeat()` في `factory_loop.js` عند بداية كل tick ونهايته (الحقول: `at`, `pid`, `interval_ms`, `phase`)؛ اختبار `tests/test_factory_heartbeat_stop.js`.
[ ] تنبيه Telegram (الوضع التجريبي أولاً) عند: حلقة تعطل، مهمة معطلة، انقطاع النبض 2 ساعات، ملخص يومي قصير. **لم يُفعَّل:** لا إرسال حقيقي حتى تأكيد المؤسس في `FOUNDER_ACTIONS.md`. (تنبيهات التعطل/الاستسلام الموجودة مسبقاً في المشرف تبقى كما هي.)

## البند 5 — مفتاح الإيقاف
[x] ملف `STOP` في جذر المستودع يوقف كل شيء بشكل نظيف: `factory_loop.js` لا يبدأ أي دورة ويخرج بالرمز 0، و`scripts/supervisor.js` يراقب الملف كل 5 ثوانٍ ويوقف الطفل. اختبارات: `tests/test_factory_heartbeat_stop.js` و`tests/test_supervisor_stop_rotation.js`.
[x] التوثيق في هذا الملف وفي تعليقات الكود.

## البند 6 — لوحة العدادات
[ ] البيانات متاحة عبر `/health` و`gf_readonly_factory_status` (حالة الحلقة، آخر checkpoint، المهام المعلّقة، أحداث المشرف)، لكن عرض "مدة التشغيل" في واجهة الـdashboard نفسها لم يُتحقَّق منه بعد.

## البند 7 — أدلة 72 ساعة
[ ] بعد التثبيت، جمع مدة التشغيل وسجلات الدورات. لم يمضِ 72 ساعة على تفعيل المهمة بعد.
