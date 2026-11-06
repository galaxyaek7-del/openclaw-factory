# Scout prompt evaluation (2026-11-06T15:25:05+00:00)

Offline, nothing published. A = current prompt on raw headlines; B = v2 prompt on the same headlines; C = v2 prompt on demand-grounded inputs.
PASS = parses + fits the $9-49 tool business + the chain's QA agent says PASS.

| Variant | n | PASS | DECLINED | QA_REVISE | QA_NO_ANSWER | NOT_FIT | CONTRACT_FAIL | NO_OUTPUT | pass of all | pass of answered |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 10 | 0 | 0 | 0 | 0 | 10 | 0 | 0 | 0.0 | 0.0 |
| B | 10 | 5 | 2 | 2 | 0 | 1 | 0 | 0 | 0.5 | 0.62 |
| C | 7 | 5 | 0 | 2 | 0 | 0 | 0 | 0 | 0.71 | 0.71 |

## Rows

- A1 NOT_FIT: What data am I missing to get from a MVP development company?، How can search engines craw -> إتقان SEO لتطبيقات Vue.js: من الزحف إلى الفهرسة ($49) | no tool/workbook wording
- B1 QA_REVISE: What data am I missing to get from a MVP development company?، How can search engines craw -> MVP Development & SEO ROI Calculator ($29) 
- A2 NOT_FIT: Need several references for new job. How should I check in with those I haven't talked to  -> Primavera P6 Troubleshooting & Professional Re‑Engagement Blueprint ($69) | price 69 outside $9-49
- B2 QA_REVISE: Need several references for new job. How should I check in with those I haven't talked to  -> Schedule Overrun Cost Estimator for Small Projects ($39) 
- A3 NOT_FIT: stock futures، flash flood warning، diet -> Emergency Nutrition Blueprint for Flood‑Prone Regions ($49) | no tool/workbook wording
- B3 PASS: stock futures، flash flood warning، diet -> Optimal Flood Insurance & Risk Cost Calculator for Small Businesses ($19) 
- A4 NOT_FIT: index funds، coffee shop، youth soccer -> دليل المدرب الكبار لكرة القدم الصغرى: استراتيجيات التدريب المتقدمة وتطوير اللاعبين ($59) | price 59 outside $9-49
- B4 PASS: index funds، coffee shop، youth soccer -> Coffee Shop Owner's Profit Allocation Planner: Reinvest, Invest, Sponsor ($29) 
- A5 NOT_FIT: housing development، kids soccer، What to do when puts I sold are deeply in the money? -> إتقان تطوير الإسكان الأخضر: دليل محترف من التصاريح إلى الربح ($59) | price 59 outside $9-49
- B5 PASS: housing development، kids soccer، What to do when puts I sold are deeply in the money? -> Deep ITM Put Exit Decision Calculator ($19) 
- A6 NOT_FIT: swimming competition، How can I compare different SaaS tools to find the best fit for a bu -> أسرار مربّعات السباحة: كيف تستغل أدوات SaaS لتوليد أكثر من 500$ شهريًا ($49) | no tool/workbook wording
- B6 PASS: swimming competition، How can I compare different SaaS tools to find the best fit for a bu -> SaaS Comparison & ROI Calculator ($29) 
- A7 NOT_FIT: X is opening any tweet link in a webview whether you press it or not، when is black friday -> Litigation in the Age of Social Media: Car Accident Attorneys' Guide for Black Friday 2026 ($49) | no tool/workbook wording
- B7 DECLINED: X is opening any tweet link in a webview whether you press it or not، when is black friday -> None ($None) 
- A8 NOT_FIT: Am I the kind of employee who gets praised for doing the work but never promoted?، Indexin -> الـ “بلّورة الترقية الصامتة”: خريطة الطريق للموظف الموهوب الذي يظل غير مُرتقٍ ($59) | price 59 outside $9-49
- B8 DECLINED: Am I the kind of employee who gets praised for doing the work but never promoted?، Indexin -> None ($None) 
- A9 NOT_FIT: What's your current AI agentic setup?، Who is hiring? (November 2026)، How should financia -> المنهج الذكي: كيف يُحوّل المحفظة المالية الأمان والازدهار في زمن التقلبات ($55) | price 55 outside $9-49
- B9 NOT_FIT: What's your current AI agentic setup?، Who is hiring? (November 2026)، How should financia -> Optimal Asset Allocation for Growth vs Protection ($39) | no tool/workbook wording
- A10 NOT_FIT: How can a regular person in the US check whether an advisor is a fiduciary, and what's the -> فهم الصالحة القانونية: دليل المتخصص لتحديد المستشارين الكفويين وفروق الرسوم ($49) | no tool/workbook wording
- B10 PASS: How can a regular person in the US check whether an advisor is a fiduciary, and what's the -> Advisor Cost Comparison Over Time ($39) 
- C1 QA_REVISE: Market evidence (complaining review): buyers are searching for and paying for 'EU AI Act C -> EU AI Act Compliance Cost Calculator and Decision Guide ($39) 
- C2 PASS: Market evidence (freelancer agency pricing): buyers are searching for and paying for 'AI A -> AI Agent Pricing & Profit Forecast for Small SaaS CloudOps Agencies ($29) 
- C3 QA_REVISE: Market evidence (freelancer agency pricing): buyers are searching for and paying for 'AI A -> SOC 2 Automation Cost & ROI Calculator ($39) 
- C4 PASS: Market evidence (freelancer agency pricing): buyers are searching for and paying for 'AI A -> AI Research Tool ROI Calculator for Solo Attorneys ($27) 
- C5 PASS: Market evidence (freelancer agency pricing): buyers are searching for and paying for 'AI A -> EU AI Act Compliance Audit Pricing Calculator ($29) 
- C6 PASS: Market evidence (freelancer agency pricing): buyers are searching for and paying for 'Lega -> Legal Research Pricing Calculator: Optimize Your Hourly Rate for Solo Attorneys ($39) 
- C7 PASS: Market evidence (complaining review): buyers are searching for and paying for 'Legal Case  -> Legal Research ROI Calculator for Solo Attorneys ($29) 
