# ADR-013 — هل `channels/base_arm.py` يفترض أن المنتج كتاب؟ (اقتراح، لا تنفيذ)

**التاريخ:** 2026-07-11
**الحالة:** اقتراح للمراجعة. لم يُنفَّذ أي سطر كود بموجب هذا الـADR.
**السبب:** استجابة لطلب "المرحلة 3" من `PRODUCT_VISION.md` — راجع `channels/base_arm.py`، هل يفترض ضمنياً أن المنتج كتاب؟

---

## الجواب الصادق: العقد نفسه محايد نسبياً. المشكلة في التنفيذ، لا في العقد.

هذا يستحق التوضيح لأنه ليس الجواب المتوقَّع بالضرورة — **`BaseArm` (الـABC) لا يحتوي فعلياً أي افتراض "كتاب" مباشر.** ثلاث دوال فقط:

```python
# channels/base_arm.py:37-51
def status(self) -> ArmStatus: ...
def supports(self, product) -> bool: ...
def publish(self, product, dry_run: bool = True) -> PublishResult: ...
```
لا "pages"، لا "cover"، لا أي حقل كتاب في التوقيعات نفسها. `product` معامل عام، `PublishResult` عام (`ok`, `platform`, `product_id`, `url`, `error`, `dry_run`) — لا شيء هنا يمنع بنيوياً ذراعاً لقالب أو صوتي أو حتى SaaS من تطبيق نفس العقد.

**المشكلة الحقيقية:** الذراع الوحيدة المُنفَّذة فعلياً (`GumroadArm`) تفترض حقلين محدَّدين من `Product` بشكل ضمني وغير محمي:

## الأدلة (كل سطر حقيقي)

### 1. `supports()` يفترض "ملف واحد + سعر رقمي واحد"

`channels/gumroad_arm.py:36-44`:
```python
def supports(self, product) -> bool:
    if not product.file_path:
        return False
    if product.price_usd is None or product.needs_pricing:
        return False
    return True
```
هذا **يصلح فعلياً** لكل خطوط الإنتاج التي هي "ملف رقمي واحد يُشترى مرة واحدة" — كتب، قوالب، مطبوعات، أصول إبداعية، صوتيات (المراحل 1، 2، 4 من `PRODUCT_VISION.md`). **لا يصلح** لـSaaS (لا `file_path` أصلاً — المنتج وصول لخدمة) ولا لقوالب مرخَّصة إن احتاجت حزمة ملفات متعددة بدل ملف واحد.

### 2. `publish()` يحوّل `price_usd` كرقم واحد مباشرة لسنتات

`channels/gumroad_arm.py:71`:
```python
"price_cents": round(product.price_usd * 100),
```
مبني بالكامل على افتراض "دفعة واحدة نهائية". اشتراك SaaS شهري لا "سعر واحد يتحوّل لسنتات" — يحتاج مساراً مختلفاً كلياً في `gumroad_publisher.py` نفسها (أو ذراع منفصلة، Gumroad تدعم Membership products عبر API مختلف عن `create_product`).

### 3. `registry.py` و`distributor.py` — محايدان فعلاً، لا حاجة لتعديل

فحصت `channels/registry.py` و`distributor.py` أيضاً (خارج نطاق الطلب المباشر لكن ذو صلة): كلاهما يتعاملان مع `Product`/`BaseArm` بشكل عام تماماً — `distributor.py`'s `distribute()` تستدعي `arm.supports(product)` ثم `arm.publish(product, dry_run)` دون أي افتراض عن شكل `product`. **لا تغيير مقترَح لهذين الملفين.**

---

## الاقتراح (تصميم، لا كود يُطبَّق الآن)

### أ. لا تغيير على `BaseArm` نفسه — العقد الحالي كافٍ

التوقيعات الثلاثة (`status`, `supports`, `publish`) تبقى كما هي. أي إضافة هنا (مثل دالة رابعة `supports_pricing_model()`) تُضاف يوماً ما **فقط عند بناء أول ذراع تحتاجها فعلياً** — إضافة تجريدية اليوم بلا حالة استخدام حقيقية تخالف مبدأ YAGNI الذي يحكم هذا المشروع بأكمله (`OCTOPUS_ARCHITECTURE.md` §8).

### ب. الذراع الجديدة تفحص `product.pricing_model` بنفسها، لا العقد يفرضه

إن أُضيف حقل `pricing_model` إلى `Product` (مقترَح `ADR-012`)، كل ذراع (بما فيها `GumroadArm` مستقبلاً) تتحقق منه داخل `supports()` الخاصة بها:
```python
def supports(self, product) -> bool:
    if product.pricing_model == "subscription":
        return False  # Gumroad's create_product() doesn't handle this yet
    if not product.file_path:
        return False
    ...
```
هذا **إضافي بحت** — لا يكسر `GumroadArm` الحالية، فقط يجعلها ترفض بأمان (`supports() -> False`) بدل قبول منتج لا تعرف كيف تتعامل معه.

### ج. ذراع بلا ملف (SaaS) — تحتاج تفسيراً مختلفاً لـ`file_path`، لا حقلاً جديداً بالضرورة

بما أن `BaseArm.publish(product, ...)` عام أصلاً، ذراع SaaS مستقبلية (لتفعيل اشتراك بدل رفع ملف) يمكن أن تُطبَّق العقد **دون أي تعديل على `BaseArm`** — فقط تتجاهل `product.file_path` وتستخدم حقولاً أخرى (مثلاً `product.description` كوصف الخدمة). العقد يبقى صالحاً كما هو؛ هذا يُثبت أن التصميم الحالي **لا يمنع** SaaS بنيوياً على مستوى العقد، فقط الذراع الملموسة الوحيدة (Gumroad) غير مصمَّمة له اليوم — وهذا متوقَّع وصحيح (Gumroad نفسها منصة ملفات رقمية بالدرجة الأولى).

### د. `PublishResult` قد يحتاج حقلاً اختيارياً للاشتراكات مستقبلاً

```python
@dataclass
class PublishResult:
    # ... الحقول الستة الحالية بلا تغيير ...
    subscription_id: str | None = None  # فقط عند pricing_model == "subscription"
```
إضافي، افتراض آمن `None` — لا كسر لأي كود حالي يبني `PublishResult(...)` بالترتيب الموضعي الحالي (يجب الانتباه: `PublishResult` اليوم **ليس** لها قيم افتراضية على حقولها الستة — أي إضافة حقل جديد يجب أن تكون في النهاية بقيمة افتراضية، تماماً كما فُعل مع `Product.product_type` سابقاً، وإلا تكسر كل استدعاء موضعي حالي في `gumroad_arm.py`, `distributor.py`, وملفات الاختبار).

---

## الخلاصة المقارنة

| الطبقة | تفترض "كتاب"؟ | يحتاج تعديلاً؟ |
|---|---|---|
| `BaseArm` (العقد) | لا | لا — يبقى كما هو |
| `registry.py` / `distributor.py` | لا | لا |
| `GumroadArm` (تنفيذ) | نعم، ضمنياً (ملف + سعر واحد) — لكنه صحيح لخطوط 1-2-3-4-8 من `PRODUCT_VISION.md`، لا لكل شيء | يُضاف فحص `pricing_model` عند الحاجة الفعلية، لا اليوم |
| `Product` (المصدر الحقيقي للافتراض) | نعم، عبر `price_usd` كرقم واحد وغياب `pricing_model` | نعم — انظر `ADR-012` |

**الخلاصة الصادقة الأهم:** الحفرة ليست في `base_arm.py` كما قد يُفترَض من عنوان السؤال — هي في `Product` (`ADR-012`)، وتنعكس بشكل طبيعي في أول ذراع تستهلكه. عقد الأذرع نفسه صُمِّم بعمومية كافية منذ البداية (`OCTOPUS_ARCHITECTURE.md` §3، ADR-3 "العقد قبل التنفيذ") ليستوعب هذا التوسّع دون تعديل.

## ما هذا الاقتراح لا يفعله

- لا يعدّل `channels/base_arm.py`.
- لا يعدّل `channels/gumroad_arm.py`.
- لا يبني أي ذراع SaaS أو أي ذراع جديدة.
