# ADR-025 — أذرع Payhip وEtsy الجديدة (dry-run) — تجاوز واعٍ لـADR-8

**التاريخ:** 2026-07-12
**الحالة:** معتمَد، منفَّذ (dry-run فقط، لا نشر حي على أي منهما).
**يتجاوز:** `OCTOPUS_ARCHITECTURE.md`'s ADR-8 (تأجيل Payhip/Etsy/Redbubble حتى يبيع Gumroad دولاراً حقيقياً) — **بطلب صريح من الرئيس اليوم**، بعد أن أُبلِغ مباشرة بالتعارض مع ADR-8 وأكَّد المضي رغم ذلك. هذا تجاوز واعٍ موثَّق، لا تجاهل صامت.

---

## القرار

بناء ذراعين جديدتين (`channels/payhip_arm.py`, `channels/etsy_arm.py`) بنفس نمط `channels/gumroad_arm.py` تماماً — عقد `BaseArm` نفسه، فصل publisher/arm نفسه. **كلاهما dry-run فقط اليوم** — لا توكن حقيقي، لا نشر حي، بلا استثناء.

## بحث حقيقي أُجري قبل البناء (لا افتراض)

بحث ويب مباشر اليوم (لا تخمين) كشف حدَّين واقعيَّين يجب توثيقهما بصراحة قبل أي استخدام مستقبلي:

**Payhip:** API العام الموثَّق رسمياً (`help.payhip.com/article/347-public-api`, `payhip.com/api-reference`) **يغطي الكوبونات ومفاتيح التراخيص فقط — لا يوجد endpoint لإنشاء منتج برمجياً اليوم.** ملف `config/channels.json` الموجود مسبقاً (غير مرتبط بهذه الجلسة) يصف Payhip بـ`"api_available": true` بشكل عام — لا يتعارض هذا مع الاكتشاف أعلاه لأن API فعلاً "متاحة"، لكن **ليس لإنشاء منتجات**. النتيجة: `PayhipArm.publish(dry_run=False)` **لا يحاول استدعاء شبكة أبداً** — يُعيد خطأً واضحاً وصادقاً بدل محاولة استدعاء endpoint غير موجود.

**Etsy:** عكس Payhip تماماً تقنياً — Etsy Open API v3 **يدعم فعلياً** إنشاء قوائم رقمية برمجياً (`POST /v3/application/shops/{shop_id}/listings`, نوع `"download"`)، لكن يحتاج تدفق OAuth2 كامل (لا توكن ثابت بسيط كـGumroad) **و**تسجيل تطبيق مطوِّر جديد — وهو موثَّق بكثرة كعملية غير موثوقة/مقيَّدة فعلياً منذ 2024 (رفض تطبيقات، فئات كاملة "لا تُوافَق حالياً" حسب Etsy نفسها). `config/channels.json` الموجود مسبقاً يصف هذا بدقة أكبر ("closed to new apps since 2024") — مؤكَّد اتجاهياً، لا مبالَغاً فيه.

## القرارات التصميمية

**ADR-25.1 — لا تدفق OAuth2 يُبنى اليوم.** الحصول على `ETSY_ACCESS_TOKEN` عملية بشرية منفصلة (تسجيل تطبيق + موافقة Etsy + تفويض مستخدم) — تماماً كحصول `GUMROAD_ACCESS_TOKEN` نفسه، غير مُنفَّذة هنا. `EtsyArm` تفترض التوكن موجوداً في `.env` إن وُجد لاحقاً، ولا تبنيه.

**ADR-25.2 — `PayhipArm.publish(dry_run=False)` يفشل بصدق دائماً، لا يحاول endpoint وهمي.** أمانة معمارية: لا شيء في هذا المصنع يدّعي قدرة لا يملكها فعلاً (نفس فلسفة `economics.py`'s `EconomicsConfigError`, `ledger.py`'s سجل صادق).

**ADR-25.3 — التسجيل في `distributor.py`.** `import channels.payhip_arm` و`import channels.etsy_arm` تُضافان بجانب `import channels.gumroad_arm` — تسجيل ذاتي، لا تعديل على `registry.py`/`distribute()` نفسها (Open/Closed، مبدأ #3).

## الأثر

- ملفات جديدة: `channels/payhip_publisher.py`, `channels/payhip_arm.py`, `channels/etsy_publisher.py`, `channels/etsy_arm.py`.
- ملف مُعدَّل: `distributor.py` (سطرا `import` إضافيان فقط).
- ملف مُعدَّل: `tests/test_base_arm.py` أو ملف اختبار جديد لتغطية الذراعين الجديدتين.
- `channels/gumroad_arm.py`, `channels/base_arm.py`, `channels/registry.py`: **بلا أي تعديل**.
- لا توكن حقيقي أُضيف لأي منصة. لا نشر حي حدث أو سيحدث بموجب هذا القرار وحده.
