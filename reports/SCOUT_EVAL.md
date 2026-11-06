# Scout prompt evaluation (2026-11-06T15:32:15+00:00)

Offline, nothing published. A = current prompt on raw headlines; B = v2 prompt on the same headlines; C = v2 prompt on demand-grounded inputs.
PASS = parses + fits the $9-49 tool business + the chain's QA agent says PASS.

| Variant | n | PASS | DECLINED | QA_REVISE | QA_NO_ANSWER | NOT_FIT | CONTRACT_FAIL | NO_OUTPUT | pass of all | pass of answered |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 10 | 0 | 0 | 0 | 0 | 10 | 0 | 0 | 0.0 | 0.0 |
| B | 10 | 6 | 2 | 2 | 0 | 0 | 0 | 0 | 0.6 | 0.75 |
| C | 7 | 6 | 0 | 1 | 0 | 0 | 0 | 0 | 0.86 | 0.86 |

## Rows

- A1 NOT_FIT: What data am I missing to get from a MVP development company?، How can search engines craw -> تسويق محركات البحث لتطبيقات Vue.js: جمع البيانات، التحليل، والتحكم في ظهور GitHub Pages ($59) | price 59 outside $9-49
- B1 QA_REVISE: What data am I missing to get from a MVP development company?، How can search engines craw -> Vue.js SEO Investment Calculator: Predict Traffic & Revenue ($39) 
- A2 NOT_FIT: Need several references for new job. How should I check in with those I haven't talked to  -> المدير التنفيذي الذكي: دليل متكامل لإدارة المشاريع باستخدام Primavera P6 والتواصل المهني ($49) | no tool/workbook wording
- B2 PASS: Need several references for new job. How should I check in with those I haven't talked to  -> Primavera P6 Schedule Cost Analyzer ($29) 
- A3 NOT_FIT: stock futures، flash flood warning، diet -> الـ Stock Futures: استراتيجيات المتداول المحترف لتأمين الأرباح في أسواق المستقبل ($59) | price 59 outside $9-49
- B3 PASS: stock futures، flash flood warning، diet -> Flood Insurance Cost & Coverage Decision Tool ($29) 
- A4 NOT_FIT: index funds، coffee shop، youth soccer -> The Soccer‑Cafe Investor: Launching a Youth Soccer‑Powered Coffee Shop and Growing Your Index Fund Portfolio ($69) | price 69 outside $9-49
- B4 PASS: index funds، coffee shop، youth soccer -> Coffee Shop Owner’s Index Fund Decision Toolkit ($29) 
- A5 NOT_FIT: housing development، kids soccer، What to do when puts I sold are deeply in the money? -> استراتيجيات خروج متقدمة لخيارات البيع العميقة في المال ($55) | price 55 outside $9-49
- B5 PASS: housing development، kids soccer، What to do when puts I sold are deeply in the money? -> Deep In‑The‑Money Put Exit Strategy Planner ($29) 
- A6 NOT_FIT: swimming competition، How can I compare different SaaS tools to find the best fit for a bu -> الخطوة الأولى نحو إنشاء SaaS للسباحة: دليلك لتحقيق دخل > 500 دولار شهريًا ($49) | no tool/workbook wording
- B6 PASS: swimming competition، How can I compare different SaaS tools to find the best fit for a bu -> SaaS Tool Fit Analysis: Compute Cost‑Effectiveness and ROI to Choose the Best SaaS for Your Business ($19) 
- A7 NOT_FIT: X is opening any tweet link in a webview whether you press it or not، when is black friday -> دليل المحامي المتخصص في حوادث السيارات: استراتيجيات قانونية لاستخدام الأدلة عبر وسائل التواصل الاجتماعي وتقنيات التسويق في موسم الجمعة السوداء 2026 ($49) | no tool/workbook wording
- B7 DECLINED: X is opening any tweet link in a webview whether you press it or not، when is black friday -> None ($None) 
- A8 NOT_FIT: Am I the kind of employee who gets praised for doing the work but never promoted?، Indexin -> Career Catalyst: The Ultimate Digital Presence Playbook for Employees Seeking Promotion ($49) | no tool/workbook wording
- B8 DECLINED: Am I the kind of employee who gets praised for doing the work but never promoted?، Indexin -> None ($None) 
- A9 NOT_FIT: What's your current AI agentic setup?، Who is hiring? (November 2026)، How should financia -> الذكاء الاصطناعي في إدارة المحافظ المالية: دليلك المتخصص لتوازن النمو وحماية الأصول ($49) | no tool/workbook wording
- B9 QA_REVISE: What's your current AI agentic setup?، Who is hiring? (November 2026)، How should financia -> Client Asset Allocation Calculator: Balance Growth & Protection ($39) 
- A10 NOT_FIT: How can a regular person in the US check whether an advisor is a fiduciary, and what's the -> دليل التقييم المتقدم لمستشاري الاستثمار ($59) | price 59 outside $9-49
- B10 PASS: How can a regular person in the US check whether an advisor is a fiduciary, and what's the -> Advisor Fee Comparison Calculator ($39) 
- C1 PASS: Market evidence (complaining review): buyers are searching for and paying for 'EU AI Act C -> EU AI Act Compliance Cost & ROI Calculator ($39) 
- C2 QA_REVISE: Market evidence (freelancer agency pricing): buyers are searching for and paying for 'AI A -> AI Agent Cost–Benefit & ROI Calculator for SaaS CloudOps ($39) 
- C3 PASS: Market evidence (freelancer agency pricing): buyers are searching for and paying for 'AI A -> SOC 2 Automation Pricing & Cost Forecast Tool ($29) 
- C4 PASS: Market evidence (freelancer agency pricing): buyers are searching for and paying for 'AI A -> AI Research ROI Calculator for Solo Attorneys ($29) 
- C5 PASS: Market evidence (freelancer agency pricing): buyers are searching for and paying for 'AI A -> AI Compliance Audit Pricing Calculator: Set Your Fees for EU AI Act Audit Logging ($29) 
- C6 PASS: Market evidence (freelancer agency pricing): buyers are searching for and paying for 'Lega -> Legal Research Automation Cost vs Time Savings Calculator ($29) 
- C7 PASS: Market evidence (complaining review): buyers are searching for and paying for 'Legal Case  -> Legal Research Automation ROI & Billing Rate Calculator ($29) 
