# 🦾 ARMS ARCHITECTURE INPUT — بلا تجميل

قراءة فقط. لا تعديل كود. تاريخ الفحص: 2026-07-11.

---

## 1. شجرة المجلدات الكاملة

(مُستثنى: `node_modules/`, `.git/` — كل الباقي مذكور. `arms/` **غير موجود** كمجلد مستقل حتى الآن.)

```
.
├── .claude/settings.local.json
├── .env
├── .factory_loop.lock
├── .gitignore
├── .vscode/settings.json
├── Archive                          (ملف فارغ 0 بايت، ليس مجلداً)
├── Books.stray_empty_file.bak       (ملف فارغ 0 بايت)
├── CLAUDE.md
├── CONSTITUTION.md
├── FACTORY_AUDIT_REPORT.md
├── FACTORY_STATUS.md
├── FACTORY_WEEKLY_REPORT.md
├── Factory                          (ملف فارغ 0 بايت)
├── GOLDEN_OPPORTUNITIES.md
├── GOOD_MORNING.md
├── GROWTH_LOG.md
├── Ideas                            (ملف فارغ 0 بايت)
├── Knowledge                        (ملف فارغ 23 بايت)
├── LESSONS_LEARNED.md
├── NICHE_SAFETY_FILTER.md
├── OPENCLAW_OS_CONSTITUTION.md
├── OPPORTUNITIES.md
├── OpenClaw_Brain/
│   ├── 00_Constitution/README.md
│   ├── 01_Vision/README.md
│   ├── 02_Roadmap/README.md
│   ├── 03_Current_Mission/README.md
│   ├── 03_Current_Mission/Self_Awareness.md
│   ├── 04_Architecture/README.md
│   ├── 05_Living_Cells/README.md
│   ├── 06_Councils/README.md
│   ├── 07_Knowledge_Base/README.md
│   ├── 08_Market_Intelligence/README.md
│   ├── 09_Prompt_Library/README.md
│   ├── 10_Automation/README.md
│   ├── 11_Security/README.md
│   ├── 12_Production/README.md
│   ├── 13_Publishing/README.md
│   ├── 14_Marketing/README.md
│   ├── 15_Finance/README.md
│   ├── 16_Laboratory/README.md
│   ├── 17_Research/README.md
│   ├── 18_Daily_Logs/README.md
│   ├── 19_Lessons_Learned/README.md
│   ├── 19_Lessons_Learned/The_1299_Pricing_Trap.md
│   ├── 19_Lessons_Learned/The_Circuit_Breaker_Discovery.md
│   ├── 19_Lessons_Learned/The_Self_Awareness_Blind_Spot.md
│   ├── 19_Lessons_Learned/The_Success_True_Bug.md
│   ├── 99_Archive/README.md
│   ├── MASTER_INDEX.md
│   └── SURVIVAL_GUIDE.md
├── QUARANTINE.md
├── REJECTED_NICHES.md
├── Research                         (ملف فارغ 0 بايت)
├── THE_MOAT.md
├── __pycache__/  (ملفات .pyc مُجمَّعة تلقائياً)
├── audit_seed.py
├── backups/                         (24 نسخة احتياطية .bak لملفات مختلفة — تأريخ يدوي قبل تعديلات كبرى)
├── book_generator.py
├── books/
│   ├── _generation_log.jsonl        ← سجل توليد كل كتاب (JSONL، سطر لكل توليد)
│   ├── covers/                      ← 9 أغلفة PNG
│   └── *.pdf                        ← 10 كتب PDF فعلية
├── channels/
│   └── gumroad_publisher.py         ← **الذراع الوحيدة المكتوبة فعلياً**
├── config/
│   ├── book_hivenotes_v1.json
│   ├── channels.json                ← سجل قنوات التوزيع (توثيقي فقط، غير مقروء من أي كود JS)
│   ├── economics.json               ← اقتصاديات الوحدة (هوامش، حدود ربح)
│   └── reality.json                 ← الحقيقة الأرضية (منشورات فعلية، فارغة)
├── cookbook_cover.pdf
├── cover_designer_v2.py
├── cover_generator.py
├── cover_test.pdf
├── data/
│   └── finance.json                 ← **ملف تالف** (يبدأ بـ `{"{` مكرر — راجع القسم 6)
├── demo.pdf
├── demo_cookbook.pdf
├── diagnostics/
│   └── day09_health_report.json
├── economics.py
├── factory_loop.js
├── factory_loop.log
├── finance_data.json                ← ملف المالية الحقيقي المستخدَم فعلياً (وليس data/finance.json)
├── finance_errors.log
├── golden_opportunities.json
├── healthy_eating_120.pdf
├── hive_logbook_generator.py
├── index.html
├── inspections.log
├── inspectors.py
├── knowledge_brain.js
├── market_analyzer.py
├── market_hunter.py
├── market_hunter_runs.log
├── niche_reports/
├── niche_validator.py
├── niche_validator_v2.py
├── output.pdf
├── package-lock.json
├── package.json
├── profit_oracle.py
├── quality_doctor.py
├── reality.py
├── reports/
│   └── WEEK_2026-07-05.md
├── safety_filter.py
├── scout_runs.log
├── seed_english_book.py
├── seeds/
│   ├── hivenotes/
│   │   ├── gumroad_spec.json        ← مواصفات نشر جاهزة لكتاب HiveNotes
│   │   └── hive_logbook_v1.pdf
│   ├── morning-focus-journal-for-remote-workers-v1.docx
│   ├── morning-focus-journal-for-remote-workers-v1.json
│   └── quality_report.md
├── self_awareness.js
├── server.js
├── start_factory.bat
├── test_output.pdf
└── الطالب_الناجح.pdf                (اسم ملف بترميز مكسور في اللائحة الأصلية — pdf عربي)
```

**ملاحظة صادقة:** لا يوجد مجلد `arms/` بعد. الذراع الوحيدة الموجودة (`channels/gumroad_publisher.py`) تعيش في مجلد `channels/` وليس `arms/` — تسمية غير موحَّدة إن كانت الخطة تسمية مستقبلية `arms/`.

---

## 2. `gumroad_publisher.py` — الكود كامل

المسار: `channels/gumroad_publisher.py` (189 سطراً). فيما يلي **الكود الكامل** كما هو على القرص:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Factory — Gumroad Publisher
Uploads digital products to Gumroad via REST API.
Reads GUMROAD_ACCESS_TOKEN from .env. Never logs the token.

Standalone module. Does not import or modify any live factory file.
Loud errors only — nothing here silently falls back or swallows a
failure into a fake success.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests

FACTORY_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = FACTORY_DIR / ".env"
GUMROAD_API_BASE = "https://api.gumroad.com/v2"


class ConfigError(Exception):
    """A missing/invalid local configuration — never a Gumroad API error."""
    pass


def load_token(env_path=None):
    env_path = Path(env_path) if env_path else DEFAULT_ENV_PATH
    token = os.environ.get("GUMROAD_ACCESS_TOKEN")
    if token:
        return token
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GUMROAD_ACCESS_TOKEN"):
                    value = line.split("=", 1)[1].strip()
                    if value:
                        return value
    raise ConfigError(
        "GUMROAD_ACCESS_TOKEN not set. Get it from https://gumroad.com/settings/advanced"
    )


def list_products(token):
    try:
        r = requests.get(f"{GUMROAD_API_BASE}/products", params={"access_token": token}, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Gumroad list_products request failed: {_safe_err(e)}")
    data = r.json()
    if not data.get("success", False):
        raise RuntimeError(f"Gumroad API returned success=false: {data.get('message', 'unknown error')}")
    return data.get("products", [])


def create_product(token, product_spec):
    file_path = product_spec.get("file_path")
    if not file_path:
        raise ConfigError("product_spec missing 'file_path'")
    file_path = Path(file_path)
    if not file_path.exists():
        raise ConfigError(f"file_path not found: {file_path}")

    price_cents = product_spec.get("price_cents")
    if price_cents is None:
        raise ConfigError("product_spec missing 'price_cents'")

    title = product_spec.get("title")
    if not title:
        raise ConfigError("product_spec missing 'title'")

    data = {
        "access_token": token,
        "name": title,
        "price": price_cents,
        "description": product_spec.get("description", ""),
        "customizable_price": "false",
    }
    try:
        with open(file_path, "rb") as fh:
            files = {"file": (file_path.name, fh, "application/pdf")}
            r = requests.post(f"{GUMROAD_API_BASE}/products", data=data, files=files, timeout=120)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Gumroad create_product request failed: {_safe_err(e)}")
    result = r.json()
    if not result.get("success", False):
        raise RuntimeError(f"Gumroad create_product failed: {result.get('message', 'unknown error')}")
    return result.get("product", result)


def update_product(token, product_id, updates):
    if not product_id:
        raise ConfigError("update_product requires a product_id")
    data = dict(updates)
    data["access_token"] = token
    try:
        r = requests.put(f"{GUMROAD_API_BASE}/products/{product_id}", data=data, timeout=60)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Gumroad update_product request failed: {_safe_err(e)}")
    result = r.json()
    if not result.get("success", False):
        raise RuntimeError(f"Gumroad update_product failed: {result.get('message', 'unknown error')}")
    return result.get("product", result)


def get_sales(token, product_id=None):
    params = {"access_token": token}
    if product_id:
        params["product_id"] = product_id
    try:
        r = requests.get(f"{GUMROAD_API_BASE}/sales", params=params, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Gumroad get_sales request failed: {_safe_err(e)}")
    data = r.json()
    if not data.get("success", False):
        raise RuntimeError(f"Gumroad get_sales failed: {data.get('message', 'unknown error')}")
    return data.get("sales", [])


def _safe_err(exc):
    """Stringify a requests exception WITHOUT ever letting the access_token
    (present in the request URL/params/body) leak into an error message."""
    text = str(exc)
    token = os.environ.get("GUMROAD_ACCESS_TOKEN", "")
    if token and token in text:
        text = text.replace(token, "***REDACTED***")
    return text


def emit(obj):
    sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Gumroad publisher CLI (OpenClaw Factory)")
    parser.add_argument("--list", action="store_true", help="List existing Gumroad products")
    parser.add_argument("--create", metavar="SPEC_JSON", help="Create a product from a spec JSON file")
    parser.add_argument("--sales", action="store_true", help="List sales")
    parser.add_argument("--product-id", default=None, help="Optional product_id filter for --sales")
    args = parser.parse_args()

    try:
        token = load_token()

        if args.list:
            products = list_products(token)
            emit({"success": True, "products": products})
            return

        if args.create:
            with open(args.create, "r", encoding="utf-8") as f:
                spec = json.load(f)
            product = create_product(token, spec)
            emit({"success": True, "product": product})
            return

        if args.sales:
            sales = get_sales(token, product_id=args.product_id)
            emit({"success": True, "sales": sales})
            return

        parser.print_help()

    except ConfigError as e:
        emit({"success": False, "error": str(e)})
        sys.exit(0)
    except Exception as e:
        emit({"success": False, "error": str(e)})
        sys.exit(0)


if __name__ == "__main__":
    main()
```

### تحليل الدوال

| الدالة | مدخلاتها | مخرجاتها | تستدعي Gumroad API فعلياً؟ |
|---|---|---|---|
| `load_token(env_path=None)` | مسار `.env` اختياري | التوكن (نص) أو `ConfigError` | لا — محلي فقط |
| `list_products(token)` | التوكن | قائمة منتجات (`list[dict]`) | **نعم** — `GET /v2/products` |
| `create_product(token, product_spec)` | التوكن + `dict` بحقول `file_path`, `price_cents`, `title`, `description` (اختياري) | `dict` بيانات المنتج المُنشَأ | **نعم** — `POST /v2/products` (multipart، يرفع ملف PDF فعلياً) |
| `update_product(token, product_id, updates)` | التوكن + معرّف + `dict` تحديثات | `dict` بيانات المنتج المُحدَّث | **نعم** — `PUT /v2/products/{id}` |
| `get_sales(token, product_id=None)` | التوكن + معرّف منتج اختياري | قائمة مبيعات (`list[dict]`) | **نعم** — `GET /v2/sales` |
| `_safe_err(exc)` | استثناء `requests` | نص خطأ بلا تسريب توكن | لا — أداة مساعدة |
| `emit(obj)` | أي `dict` | يطبعه كـ JSON UTF-8 على `stdout` | لا |
| `main()` | آرغيومنتات CLI (`--list`, `--create SPEC_JSON`, `--sales`, `--product-id`) | يستدعي إحدى الدوال أعلاه ويطبع النتيجة | — |

**الخلاصة الصادقة:** هذا **ليس هيكلاً فارغاً (stub)** — الكود يستدعي Gumroad REST API الحقيقي فعلياً (4 عمليات CRUD كاملة: list, create, update, sales)، بما في ذلك رفع ملف PDF حقيقي عبر `multipart/form-data`. المشكلة الوحيدة أنه **لم يُختبر مرة واحدة** لغياب `GUMROAD_ACCESS_TOKEN` في `.env` (مؤكَّد في `FACTORY_AUDIT_REPORT.md` §1 و§5).

---

## 3. كيف يُستدعى النشر حالياً؟

**بحث كامل في `server.js` عن `gumroad`/`channels/`/`publish`:**
- **صفر استدعاء** لـ `channels/gumroad_publisher.py` من `server.js`. كل ما ظهر هو كلمة "Gumroad" كنص في:
  - سطر 213: `const FINANCE_PLATFORMS = ['KDP', 'Etsy', 'Gumroad'];` — قائمة منصات لإدخال **مبيعات يدوياً** في `/finance/add` (المستخدم يكتب رقم البيع بنفسه، لا نشر آلي).
  - أسطر 216، 266، 273، 285: حقول `totalGumroad` في حسابات المالية — تجميع أرقام مُدخَلة يدوياً، لا استدعاء API.
  - أسطر 348، 387، 402، 406: نص داخل `system prompt` لوكيلَي Scout وPublisher (استراتيجية نصية يقترحها Groq، ليست كوداً تنفيذياً).

**بحث كامل في `factory_loop.js` عن نفس الكلمات:** **صفر استدعاء أيضاً**. كل ما ظهر هو حقول `totalGumroad` في دوال حساب الإيرادات المعروضة في `good-morning`/`awareness` (نفس النمط: نص تجميعي، لا نشر آلي).

**الخلاصة المباشرة على سؤالك:**
> من server.js؟ **لا.**
> من factory_loop.js؟ **لا.**
> يدوياً؟ **نعم — الطريقة الوحيدة الموجودة فعلياً هي تشغيل السكربت يدوياً من سطر الأوامر:**
> ```bash
> python channels/gumroad_publisher.py --create seeds/hivenotes/gumroad_spec.json
> ```
> ولم يحدث هذا الاستدعاء ولو مرة واحدة (بحث كامل في كل ملفات `.log` — صفر ذِكر لـ `gumroad_publisher` أو `GUMROAD_ACCESS_TOKEN`).

لا يوجد أي كود — لا في `server.js` ولا في `factory_loop.js` ولا في أي مكان آخر بالمشروع — يستدعي `channels/gumroad_publisher.py` كـ subprocess أو كوحدة مستوردة. السكربت **مفصول بالكامل** عن خط الإنتاج الآلي.

---

## 4. بنية "المنتج الجاهز"

يوجد **شكلان مختلفان** فعلياً في المصنع، غير موحَّدَين:

### الشكل الأول — خط الإنتاج الرئيسي (`book_generator.py` عبر `/generate-book`)
لكل كتاب: **PDF + غلاف PNG منفصل + سطر JSONL واحد في سجل مشترك** (`books/_generation_log.jsonl`) يحوي كل الميتاداتا. **لا يوجد ملف ميتاداتا منفصل لكل كتاب.**

مثال حقيقي واحد كامل (آخر سطر في `books/_generation_log.jsonl`، الكتاب: "الرجل الناجح: 30 يومًا لتميزك الشخصي"):

```json
{
  "success": true,
  "file": "الرجل_الناجح_30_يوم_ا_لتميزك_الشخصي.pdf",
  "path": "C:\\openclaw-dasgboard\\books\\الرجل_الناجح_30_يوم_ا_لتميزك_الشخصي.pdf",
  "pages": 12,
  "topic": "كتاب تعليمي يُدرب القارئ على بناء شخصية ناجحة من الداخل من خلال 30 يومًا من التحفيز والتشكيك",
  "audience": "المشاغبون في الحملات الخاصة بأعمالهم و المحترفين في جميع الأصناف الذين يرغبون في التغيير والنمو الذاتي",
  "price": 49.0,
  "repriced": false,
  "ai_used": true,
  "ai_error": null,
  "quality_gate": { "passed": true, "reason": "نجحت كل فحوصات الجودة", "checks": { "...": "..." } },
  "cover": {
    "success": true,
    "file": "الرجل_الناجح__30_يوم_ا_لتميزك_الشخصي_cover.png",
    "path": "C:\\openclaw-dasgboard\\books\\covers\\الرجل_الناجح__30_يوم_ا_لتميزك_الشخصي_cover.png",
    "size": [1600, 2560],
    "theme_hex": "#2563eb"
  },
  "cover_v2_used": true,
  "published": true,
  "inspection": {
    "passed": true,
    "published": true,
    "technical": { "passed": true, "checks": [ "... 13 فحصاً تقنياً ..." ], "failures": [] },
    "commercial": {
      "passed": true,
      "checks": [
        { "name": "profit_score", "passed": true, "detail": "62/100 (الحد الأدنى: 60)" },
        { "name": "butter_price", "passed": true, "detail": "$49.00 (حد الزبدة: $30)" },
        { "name": "not_duplicate", "passed": true, "detail": "لا تكرار في سجل الإنتاج" },
        { "name": "not_previously_rejected", "passed": true, "detail": "لم يُرفض من قبل" }
      ],
      "verdict": "يستحق النشر لمشترين محترفين",
      "profit_score": 62
    },
    "timestamp": "2026-07-09T09:39:58.808249"
  },
  "timestamp": "2026-07-09T09:39:58.809270"
}
```

**ملاحظة صادقة:** هذا السجل **ليس** بصيغة قابلة للاستهلاك المباشر من `gumroad_publisher.py --create` — يحتاج تحويلاً يدوياً/برمجياً إلى الشكل الثاني (فيه `price` كرقم عشري بالدولار وليس `price_cents`، ولا `title` صريح — العنوان مأخوذ من `inspection.title`، ولا `description`).

### الشكل الثاني — مسار HiveNotes البذري (`hive_logbook_generator.py`)
لكل كتاب: **PDF + ملف ميتاداتا JSON منفصل مُعَدّ خصيصاً لصيغة Gumroad**. هذا هو الشكل الوحيد في المشروع الجاهز فعلياً لـ `gumroad_publisher.py --create` بدون أي تحويل:

`seeds/hivenotes/gumroad_spec.json` (كامل):
```json
{
  "channel": "gumroad",
  "product_type": "digital",
  "title": "The Beekeeper's Hive Inspection Logbook (Printable PDF)",
  "subtitle": "52-Week Field Record for Hobbyist Apiarists",
  "price_cents": 699,
  "price_usd": 6.99,
  "file_path": "seeds/hivenotes/hive_logbook_v1.pdf",
  "cover_image_path": null,
  "description": "A structured 140-page hive inspection logbook for hobbyist beekeepers. Print at home or use on a tablet. Includes: 52 weekly inspection sheets, year-at-a-glance tracker, pests and disease log, honey harvest records, contacts directory, and equipment inventory. Instant PDF download — print as many copies as you need.",
  "tags": ["beekeeping", "beekeeper", "logbook", "hive inspection", "apiary", "printable", "PDF"],
  "publisher": "HiveNotes Press"
}
```

**ملاحظة دقيقة:** حتى هذا الملف فيه حقول لا يقرأها `create_product()` إطلاقاً — `subtitle`, `price_usd`, `cover_image_path`, `tags`, `channel`, `product_type`, `publisher` كلها **مُتجاهَلة** من الكود؛ الدالة تقرأ فقط `file_path`, `price_cents`, `title`, `description`. الحقل `cover_image_path` تحديداً قيمته `null` — لا غلاف مرفق أصلاً حتى لو استُخدم هذا الملف الآن.

**الخلاصة:** لا يوجد شكل موحَّد واحد لـ"المنتج الجاهز" في المصنع بأكمله. خط الإنتاج الرئيسي ينتج سجل JSONL غني بالفحوصات لكن غير متوافق مباشرة مع أي ذراع نشر؛ مسار HiveNotes ينتج ملف مواصفات متوافق فعلياً لكنه مسار يدوي منفصل تماماً لا يمر بنفس فحوصات الجودة/الأمان.

---

## 5. نقاط التوسّع — أين تتصل ذراع جديدة؟

**لا يوجد أي interface أو abstract class مشترك في المشروع بالكامل.** بحث كامل عن أنماط `class.*Channel`, `def publish`, `abstract`, `interface` في كل ملفات `.py` — **صفر نتيجة**. `channels/gumroad_publisher.py` هو النمط الوحيد الموجود، وهو غير موروث من أي قاعدة مشتركة — مجرد سكربت CLI مستقل بنمط اتفاقي (convention)، لا عقد برمجي (contract) مفروض.

### النمط الاتفاقي الذي يجب أن تتبعه ذراع جديدة (مُستنتَج من `gumroad_publisher.py`، غير مفروض بالكود):
1. **الموقع:** `channels/<platform>_publisher.py` (مثال مستقبلي: `channels/payhip_publisher.py`, `channels/etsy_publisher.py`).
2. **تحميل السر:** دالة `load_token()` تقرأ متغير بيئة أولاً، ثم تقع احتياطياً على `.env` بنفس نمط `PLATFORM_ACCESS_TOKEN`، وترمي `ConfigError` صريح إن غاب — لا تسكت الفشل أبداً.
3. **دوال CRUD:** `list_products`, `create_product`, `update_product`, `get_sales` — كل واحدة ترفع `RuntimeError` واضح عند فشل HTTP، وتتحقق من حقل `success` في رد الـ API قبل اعتباره نجاحاً.
4. **حماية السر من التسريب:** دالة مثل `_safe_err()` تستبدل التوكن بـ `***REDACTED***` في أي رسالة خطأ قبل طباعتها.
5. **واجهة CLI موحَّدة:** `argparse` بخيارات `--list`, `--create SPEC_JSON`, `--sales`, تطبع دائماً JSON واحد على `stdout` عبر `emit()`، وتُنهي بـ `sys.exit(0)` حتى عند الفشل (الفشل يُعبَّر عنه بحقل `"success": false"` داخل الـ JSON، لا برمز خروج غير صفري) — هذا مهم لأن أي مستدعٍ مستقبلي (`server.js` أو `factory_loop.js`) سيحتاج تفسير الفشل من محتوى الـ JSON لا من exit code.

### نقطة الاتصال الفعلية المفقودة (هذا ما لا يوجد بعد ويجب أن يُضاف):
لا يوجد **أي** نقطة في `server.js` أو `factory_loop.js` تستدعي أي ذراع نشر حالياً (مؤكَّد في القسم 3). لإضافة ذراع جديدة ووصلها فعلياً، أقرب نمط موجود بالفعل في `server.js` يمكن تقليده هو نمط استدعاء `book_generator.py` كـ subprocess داخل `/generate-book` (حول السطر 95) — نفس النمط (spawn + stdin JSON + قراءة stdout JSON) يصلح حرفياً لاستدعاء `channels/gumroad_publisher.py --create` أو أي ذراع مستقبلية. لا يوجد اليوم أي endpoint باسم `/api/publish` أو ما شابه في قائمة الـ 20 مساراً المذكورة في `FACTORY_AUDIT_REPORT.md` §6.

### `config/channels.json` — سجل توثيقي فقط
هذا الملف **يُعرِّف** القنوات المخطَّطة (`kdp_paperback`, `gumroad`, `payhip`, `etsy_digital`) بحقول `automation`, `api_available`, `fee_percent`, إلخ — لكنه **غير مقروء من أي كود JS في المشروع** (بحث كامل عن `channels.json` أو `channels/gumroad` في كل ملفات `.js` — صفر نتيجة). إضافة قناة جديدة إلى هذا الملف اليوم **لا يفعّل أي شيء تلقائياً** — إنه مجرد توثيق بشري.

**الخلاصة الصادقة على سؤالك:** لا توجد نقطة اتصال برمجية جاهزة لذراع جديدة — لا interface، لا endpoint مُعَدّ مسبقاً، لا آلية تسجيل ديناميكي. أقرب شيء لـ"نقطة توسّع" هو نسخ نمط `gumroad_publisher.py` حرفياً لكل منصة جديدة، ثم يدوياً إضافة استدعاء subprocess جديد في `server.js` (لا يوجد بعد) يشبه استدعاء `/generate-book` لـ `book_generator.py`.

---

## 6. config — كيف تُخزَّن أسرار المنصات؟

**الأسماء فقط، لا القيم:**

| المصدر | الاسم | موجود فعلياً في `.env`؟ |
|---|---|---|
| `.env` | `GROQ_KEY` | **نعم** — المفتاح الوحيد الموجود فعلياً |
| `.env` (متوقَّع من `channels/gumroad_publisher.py`) | `GUMROAD_ACCESS_TOKEN` | **لا** — غير موجود |
| — | أي مفتاح KDP/Etsy/Payhip | **لا يوجد أي متغير بهذا الشكل في أي كود بالمشروع** |

**آلية القراءة:** `.env` هو المصدر الوحيد للأسرار في كامل المشروع. `dotenv` مُستخدَم في `server.js` (موجود في `package.json`)، و`channels/gumroad_publisher.py` يقرأ `.env` يدوياً بنفسه (سطر-بسطر، بحثاً عن بادئة `GUMROAD_ACCESS_TOKEN=`) دون استخدام أي مكتبة — لا يعتمد على أن `server.js` أو أي عملية أخرى تكون قد حمّلت البيئة أولاً.

**`config/*.json` — لا يخزّن أي سر:**
- `config/channels.json` — بيانات وصفية عامة عن كل منصة (رسوم، هل API متاح، رابط توثيق) — **لا مفاتيح ولا توكنات**.
- `config/economics.json` — أرقام اقتصادية ثابتة (هوامش، عتبات ربح) — لا أسرار.
- `config/reality.json` — سجل منشورات فعلية (فارغ حالياً) — لا أسرار.
- `config/book_hivenotes_v1.json` — إعدادات محتوى كتاب — لا أسرار.

**`.gitignore` يحمي `.env` فعلياً:** مؤكَّد — `.env` مُدرَج صراحة في `.gitignore` (إلى جانب `node_modules/`, `backups/`, `*.log`, `.factory_loop.lock`, `__pycache__/`, `*.pyc`, `*.pyo`). لا خطر تسريب `.env` عبر git بالوضع الحالي.

**ملاحظة جانبية غير مطلوبة لكن حقيقية:** `data/finance.json` (ملف منفصل عن `finance_data.json` الجذري) **تالف فعلياً** — يبدأ بـ `{"{` (قوس مفتوح مكرر) ولا يُحلَّل كـ JSON صالح. غير مذكور في أي كود قرأته حتى الآن (لم يُستدعَ اسمه في `server.js` أو `factory_loop.js`) — يبدو ملفاً يتيماً من محاولة سابقة.
