# Scout prompt evaluation (2026-11-06T17:03:45+00:00)

Offline, nothing published. A = current prompt on raw headlines; B = v2 prompt on the same headlines; C = v2 prompt on demand-grounded inputs.
PASS = parses + fits the $9-49 tool business + the chain's QA agent says PASS.

| Variant | n | PASS | DECLINED | QA_REVISE | QA_NO_ANSWER | NOT_FIT | CONTRACT_FAIL | NO_OUTPUT | pass of all | pass of answered |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 10 | 0 | 0 | 0 | 0 | 10 | 0 | 0 | 0.0 | 0.0 |
| B | 10 | 4 | 1 | 4 | 0 | 1 | 0 | 0 | 0.4 | 0.44 |
| C | 7 | 5 | 0 | 2 | 0 | 0 | 0 | 0 | 0.71 | 0.71 |

## Rows

- A1 NOT_FIT: What data am I missing to get from a MVP development company?، How can search engines craw -> دليل احترافي لتقنيات SEO المتقدمة لتطبيقات JavaScript وملفات MVP: كيف تتفادى قيود الزحف وتتحكم في ظهور موقعك ($49) | no tool/workbook wording
- B1 QA_REVISE: What data am I missing to get from a MVP development company?، How can search engines craw -> Monthly SEO & Site‑Maintenance Budget Planner for Solo SaaS Founders ($29) 
- A2 NOT_FIT: Need several references for new job. How should I check in with those I haven't talked to  -> دليل المحترفين المتكامل لإصلاح جداول Primavera P6 وبناء شبكة مهنية قوية للحصول على وظيفة جديدة ($49) | no tool/workbook wording
- B2 QA_REVISE: Need several references for new job. How should I check in with those I haven't talked to  -> Project Delay Cost Impact Calculator for Small Contractors ($29) 
- A3 NOT_FIT: stock futures، flash flood warning، diet -> الاستثمار الذكي في زمن الفيضانات: دمج تداول العقود المستقبلية للأسهم مع استراتيجيات الحمية للحد من المخاطر ($49) | no tool/workbook wording
- B3 QA_REVISE: stock futures، flash flood warning، diet -> Futures Position Sizing Calculator for Retail Traders ($29) 
- A4 NOT_FIT: index funds، coffee shop، youth soccer -> استراتيجية استثمارية للمقاهي: تحويل أرباحك اليومية إلى ثروة دائمة عبر صناديق المؤشرات ($49) | no tool/workbook wording
- B4 QA_REVISE: index funds، coffee shop، youth soccer -> Monthly Index Fund Contribution Planner for Goal‑Based Investing ($29) 
- A5 NOT_FIT: housing development، kids soccer، What to do when puts I sold are deeply in the money? -> استراتيجية المتداول المحترف لإدارة عقود البوت القصيرة ذات العائد العالي ($49) | no tool/workbook wording
- B5 PASS: housing development، kids soccer، What to do when puts I sold are deeply in the money? -> Option Put Assignment Decision Calculator: Roll, Close, or Let Assignment ($29) 
- A6 NOT_FIT: swimming competition، How can I compare different SaaS tools to find the best fit for a bu -> المنهج المتكامل لإنشاء مشروع SaaS جانبي يحقق > $500 شهريًا: اختيار الأدوات، اختبار الأداء، وإطلاق المنافسة ($49) | no tool/workbook wording
- B6 PASS: swimming competition، How can I compare different SaaS tools to find the best fit for a bu -> SaaS Subscription Cost‑Benefit Analyzer for Small Businesses ($29) 
- A7 NOT_FIT: X is opening any tweet link in a webview whether you press it or not، when is black friday -> التسويق الرقمي لمحامي حوادث السيارات: استراتيجيات جذب العملاء عبر بلاك فرايدي 2026 وتفادي مخاطر روابط تويتر ($49) | no tool/workbook wording
- B7 DECLINED: X is opening any tweet link in a webview whether you press it or not، when is black friday -> None ($None) 
- A8 NOT_FIT: Am I the kind of employee who gets praised for doing the work but never promoted?، Indexin -> الدليل المتكامل للترقي الوظيفي للموظف المتميّز: استراتيجيات الظهور، تحسين المؤشرات، واختيار التكنولوجيا الخصوصية ($49) | no tool/workbook wording
- B8 PASS: Am I the kind of employee who gets praised for doing the work but never promoted?، Indexin -> Promotion Readiness & Salary Growth Planner for Employees ($29) 
- A9 NOT_FIT: What's your current AI agentic setup?، Who is hiring? (November 2026)، How should financia -> الاستراتيجية المتكاملة للمستشار المالي في عصر الذكاء الاصطناعي وتوظيف المواهب 2026 ($49) | no tool/workbook wording
- B9 PASS: What's your current AI agentic setup?، Who is hiring? (November 2026)، How should financia -> Growth vs Protection Allocation Calculator for Financial Advisors ($39) 
- A10 NOT_FIT: How can a regular person in the US check whether an advisor is a fiduciary, and what's the -> الدليل المتقدم للتحقق من فدية المستشار المالي وإدارة مسار العمل داخل الشركة ($49) | no tool/workbook wording
- B10 NOT_FIT: How can a regular person in the US check whether an advisor is a fiduciary, and what's the -> Advisor Fee Comparator: Forecasting Lifetime Costs of Fiduciary vs Non‑Fiduciary Investment Advice ($29) | no tool/workbook wording
- C1 PASS: Market evidence (complaining review): buyers are searching for and paying for 'EU AI Act C -> EU AI Act Compliance Cost Calculator for AI SaaS Startups ($29) 
- C2 PASS: Market evidence (freelancer agency pricing): buyers are searching for and paying for 'AI A -> AI Agent Service Pricing Calculator for Small SaaS CloudOps Agencies ($29) 
- C3 PASS: Market evidence (freelancer agency pricing): buyers are searching for and paying for 'AI A -> SOC 2 Automation AI Agent ROI & Pricing Calculator for Freelance Security Consultants ($39) 
- C4 PASS: Market evidence (freelancer agency pricing): buyers are searching for and paying for 'AI A -> AI Automation ROI Calculator for Solo Attorneys ($29) 
- C5 QA_REVISE: Market evidence (freelancer agency pricing): buyers are searching for and paying for 'AI A -> EU AI Act Compliance Audit Logging Service Pricing Calculator ($39) 
- C6 QA_REVISE: Market evidence (freelancer agency pricing): buyers are searching for and paying for 'Lega -> ROI Calculator for Legal Research Automation for Solo Attorneys ($29) 
- C7 PASS: Market evidence (complaining review): buyers are searching for and paying for 'Legal Case  -> Legal Research Automation ROI Calculator for Solo Attorneys ($29) 
