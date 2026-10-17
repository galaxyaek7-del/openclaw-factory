# Gumroad listing covers — upload guide

Generated 2026-10-17 by `scripts/generate_listing_covers.py`. Audit: `reports/covers/cover_audit.json`.

## Status

- **Covers ready:** 74 at 1280×720 PNG, in `reports/covers/gumroad/`.
  - 31 show the product's existing book cover as an inset (an exact title match; every filename word appears in the title).
  - 43 use a title-only design.
- **Checks:** every image is 1280×720, and every title fits.
- **Not uploaded:** Gumroad's API has no cover upload, and uploading is your action. Nothing on Gumroad was changed.

## How to upload (about 1 minute per listing)

Button names below are approximate; they were not checked against today's Gumroad dashboard.

1. Open the listing link in the table, then click **Edit product**.
2. In **Cover**, click **Upload images or videos** and choose the file from `C:\openclaw-dasgboard\reports\covers\gumroad\`.
3. Click **Save changes**. Check the public page shows the cover.
4. When done, re-run `python scripts/gumroad_seo_audit.py`. The "No cover image" count should fall to the number you have not done yet.

**Suggested order:** table order, or start with the listings you plan to share first.

## Needs your decision first (not covered)

- **Live listing marked unavailable:** [Unavailable] AI Workflow QA & Stress Test - one agent, reviewed before you demo it to a c… (`IW58tjt2zS14fPYrWZOuxg==`). Its own title says it is unavailable, but it is still published. Unpublish it or restore it.
- **Same title live twice:** "The 5-Minute Context Reset Playbook". Two published listings share this name. Both have covers, told apart by the id suffix in the filename. Consider unpublishing one.
- **ADA Demand-Letter Response & Triage Kit:** the delivered PDF has a real defect on page 1. The title's second line is printed over the subtitle (found by `file_testing_engine`, confirmed by rendering the page). Fix the PDF before promoting this listing.

## Files

| # | Listing | Cover file | Link | Note |
|---|---|---|---|---|
| 1 | ADA Demand-Letter Response & Triage Kit | `ada-demand-letter-response-triage-kit--nLl2DJ.png` | https://aekraft.gumroad.com/l/palmdr |  |
| 2 | AI Agent Blueprint for Small SaaS CloudOps Automation | `ai-agent-blueprint-for-small-saas-cloudops-automation--Ag3pKi.png` | https://aekraft.gumroad.com/l/esnpki |  |
| 3 | Amazon FBA Reconciliation Workbook | `amazon-fba-reconciliation-workbook--ylqF8r.png` | https://aekraft.gumroad.com/l/wteork |  |
| 4 | B2B Late-Payment Collections Operating System | `b2b-late-payment-collections-operating-system--8uWrIq.png` | https://aekraft.gumroad.com/l/wsbqr |  |
| 5 | Battery & WEEE Mini-Guide for Sellers | `battery-weee-mini-guide-for-sellers--LInf08.png` | https://aekraft.gumroad.com/l/eiebdt |  |
| 6 | CCPA Compliance Action Kit for Small Business | `ccpa-compliance-action-kit-for-small-business--dyZ5uS.png` | https://aekraft.gumroad.com/l/kaooj |  |
| 7 | Clinic No-Show Reduction Kit | `clinic-no-show-reduction-kit--K5oIlu.png` | https://aekraft.gumroad.com/l/eiztlg |  |
| 8 | Commercial Lease CAM & Operating-Expense Audit Kit | `commercial-lease-cam-operating-expense-audit-kit--iTLlmV.png` | https://aekraft.gumroad.com/l/xmbxpz |  |
| 9 | Cottage Food Compliance Kit | `cottage-food-compliance-kit--to7fbH.png` | https://aekraft.gumroad.com/l/ursxh |  |
| 10 | Creator Brand-Deal Management System | `creator-brand-deal-management-system--x5CfOf.png` | https://aekraft.gumroad.com/l/vzmswo |  |
| 11 | Dental Insurance Verification Kit | `dental-insurance-verification-kit--iJOXxU.png` | https://aekraft.gumroad.com/l/diboaf |  |
| 12 | Digital-Product Refund Policy Pack | `digital-product-refund-policy-pack--f3MRQn.png` | https://aekraft.gumroad.com/l/yhnyn |  |
| 13 | Diminished Value Claim Kit | `diminished-value-claim-kit--f542PZ.png` | https://aekraft.gumroad.com/l/dyjavs |  |
| 14 | DSAR Response Kit ($59) | `dsar-response-kit-59--68zZcB.png` | https://aekraft.gumroad.com/l/uqmqnu |  |
| 15 | DTC Returns Abuse Playbook: Fair Tiered Policy with Graduated Responses | `dtc-returns-abuse-playbook-fair-tiered-policy-with-graduated-responses--MzZhoK.png` | https://aekraft.gumroad.com/l/mrecoe |  |
| 16 | Employee Offboarding & Access-Revocation System | `employee-offboarding-access-revocation-system--nwqwR1.png` | https://aekraft.gumroad.com/l/tjbly |  |
| 17 | Etsy Ads ROI Playbook + Calculator | `etsy-ads-roi-playbook-calculator--ZFXJtt.png` | https://aekraft.gumroad.com/l/hasjmp |  |
| 18 | Etsy Policy Triage: Find Your Exact Violation in 15 Minutes | `etsy-policy-triage-find-your-exact-violation-in-15-minutes--P5k2pt.png` | https://aekraft.gumroad.com/l/sjrjxq |  |
| 19 | Etsy Suspension Appeal Kit | `etsy-suspension-appeal-kit--mvuoJT.png` | https://aekraft.gumroad.com/l/fgruzn |  |
| 20 | Etsy Suspension: Triage + Appeal Bundle (Both Steps, 25+ Pages) | `etsy-suspension-triage-appeal-bundle-both-steps-25-pages--LzOV85.png` | https://aekraft.gumroad.com/l/bfhpzl | inset shows the component kit |
| 21 | EU AI Act Audit Logging Kit | `eu-ai-act-audit-logging-kit--WP6Vbq.png` | https://aekraft.gumroad.com/l/fwxmms |  |
| 22 | EU AI Act Compliance Quickstart Checklist | `eu-ai-act-compliance-quickstart-checklist--tGGL1m.png` | https://aekraft.gumroad.com/l/engiwk |  |
| 23 | EU AI Act Transparency & AI Literacy Quickstart Checklist | `eu-ai-act-transparency-ai-literacy-quickstart-checklist--AnZqjZ.png` | https://aekraft.gumroad.com/l/tmhlb |  |
| 24 | EU Cosmetics Responsible Person Guide | `eu-cosmetics-responsible-person-guide--GVqbXZ.png` | https://aekraft.gumroad.com/l/bfdgx |  |
| 25 | EU Green Claims Review Kit | `eu-green-claims-review-kit--C4xKqs.png` | https://aekraft.gumroad.com/l/uyzuu |  |
| 26 | EU Late Payment Recovery Kit | `eu-late-payment-recovery-kit--8Vlc3z.png` | https://aekraft.gumroad.com/l/ciowwm |  |
| 27 | EU Packaging EPR Action Kit | `eu-packaging-epr-action-kit--8JM3qF.png` | https://aekraft.gumroad.com/l/gfsvu |  |
| 28 | EUDR Due Diligence Starter | `eudr-due-diligence-starter--qxjGLQ.png` | https://aekraft.gumroad.com/l/brwrta |  |
| 29 | Fleet Maintenance and Damage Documentation Bundle | `fleet-maintenance-and-damage-documentation-bundle--Opfzi3.png` | https://aekraft.gumroad.com/l/oerot |  |
| 30 | Food Truck Permit Navigator | `food-truck-permit-navigator--bBfEKk.png` | https://aekraft.gumroad.com/l/cdfdcy |  |
| 31 | Food-Contact Materials Starter | `food-contact-materials-starter--tHvtBh.png` | https://aekraft.gumroad.com/l/ldrdm |  |
| 32 | Freelancer Payment Protection & Scope-Control Toolkit | `freelancer-payment-protection-scope-control-toolkit--YW18CU.png` | https://aekraft.gumroad.com/l/fwrjot |  |
| 33 | Freelancer Scope Control Kit | `freelancer-scope-control-kit--NHlV8f.png` | https://aekraft.gumroad.com/l/ziiur |  |
| 34 | Freelancer Scope-Creep Contract Kit | `freelancer-scope-creep-contract-kit--T8OiOr.png` | https://aekraft.gumroad.com/l/zjwpx |  |
| 35 | FTC Consumer Review Rule Compliance Kit | `ftc-consumer-review-rule-compliance-kit--OiBdFF.png` | https://aekraft.gumroad.com/l/ekhza |  |
| 36 | GCC Contractor Payment Command System | `gcc-contractor-payment-command-system--wJUrEK.png` | https://aekraft.gumroad.com/l/uwyfje |  |
| 37 | GCC Contractor Payment Command System (V2 Bundle) | `gcc-contractor-payment-command-system-v2-bundle--yrSExa.png` | https://aekraft.gumroad.com/l/jlxmez | inset shows the component kit |
| 38 | GPSR EU Seller Action Kit | `gpsr-eu-seller-action-kit--VPYaNk.png` | https://aekraft.gumroad.com/l/fetmu |  |
| 39 | Gulf Job-Landing ATS CV System | `gulf-job-landing-ats-cv-system--8gFbiv.png` | https://aekraft.gumroad.com/l/fccqk |  |
| 40 | Handbook Acknowledgment Tracker | `handbook-acknowledgment-tracker--3B99PV.png` | https://aekraft.gumroad.com/l/fydjid |  |
| 41 | Home-Service Quoting & Deposit Protection System | `home-service-quoting-deposit-protection-system--N9TrQZ.png` | https://aekraft.gumroad.com/l/behmhy |  |
| 42 | Homebuyer Inspection Action Kit | `homebuyer-inspection-action-kit--uUo9Qf.png` | https://aekraft.gumroad.com/l/volqjv |  |
| 43 | Landlord Move-In Inspection Pack | `landlord-move-in-inspection-pack--Mk8k3Q.png` | https://aekraft.gumroad.com/l/gzbdaz |  |
| 44 | Landlord Rent Ledger: Court-Ready Records for Self-Managing Owners | `landlord-rent-ledger-court-ready-records-for-self-managing-owners--hQgyFv.png` | https://aekraft.gumroad.com/l/odqlk |  |
| 45 | Legal Case Research Automation for Solo Attorneys | `legal-case-research-automation-for-solo-attorneys--y4nX4c.png` | https://aekraft.gumroad.com/l/uldlwa |  |
| 46 | Mechanics Lien Filing Kit for Contractors | `mechanics-lien-filing-kit-for-contractors--mx6XSG.png` | https://aekraft.gumroad.com/l/jibnyt |  |
| 47 | Mindfulness Journal for Stress Relief | `mindfulness-journal-for-stress-relief--H7Fbvl.png` | https://aekraft.gumroad.com/l/jvuelq |  |
| 48 | Newsletter Deliverability & Inbox Placement System | `newsletter-deliverability-inbox-placement-system--KzZbSt.png` | https://aekraft.gumroad.com/l/iwbcmi |  |
| 49 | PCI SAQ Readiness Kit for Small Merchants | `pci-saq-readiness-kit-for-small-merchants--F0aW62.png` | https://aekraft.gumroad.com/l/qezxe |  |
| 50 | Real Estate Transaction Deadline Kit | `real-estate-transaction-deadline-kit--2NIVAf.png` | https://aekraft.gumroad.com/l/vwlmeo |  |
| 51 | Restaurant Food Cost Control Kit | `restaurant-food-cost-control-kit--M55I0t.png` | https://aekraft.gumroad.com/l/swkgd |  |
| 52 | Restaurant Health Inspection Readiness Kit | `restaurant-health-inspection-readiness-kit--T41QMt.png` | https://aekraft.gumroad.com/l/dvfvm |  |
| 53 | SaaS Churn Email Pack | `saas-churn-email-pack--lac1Tz.png` | https://aekraft.gumroad.com/l/roxdbe |  |
| 54 | SaaS Spend & Renewal Audit System for Small Teams | `saas-spend-renewal-audit-system-for-small-teams--sjnnlS.png` | https://aekraft.gumroad.com/l/pahxdv |  |
| 55 | Sales Tax Nexus Tracker | `sales-tax-nexus-tracker--h9G1Ec.png` | https://aekraft.gumroad.com/l/uucxer |  |
| 56 | Salon Commission Pay Kit | `salon-commission-pay-kit--2HC2Ov.png` | https://aekraft.gumroad.com/l/xwacbo |  |
| 57 | Section 8 Notice Validity System (England) | `section-8-notice-validity-system-england--FbwR2V.png` | https://aekraft.gumroad.com/l/nmasnb |  |
| 58 | Security Deposit Demand Kit for Tenants | `security-deposit-demand-kit-for-tenants--0uieIt.png` | https://aekraft.gumroad.com/l/yiqba |  |
| 59 | Severance Agreement Review Checklist | `severance-agreement-review-checklist--D4JC45.png` | https://aekraft.gumroad.com/l/vunrqm |  |
| 60 | Short-Term Rental Damage Claim Evidence Kit (Airbnb & VRBO) | `short-term-rental-damage-claim-evidence-kit-airbnb-vrbo--iL2bwA.png` | https://aekraft.gumroad.com/l/xwbbb |  |
| 61 | SOC 2 Compliance Automation Guide for Startups | `soc-2-compliance-automation-guide-for-startups--M5AZWb.png` | https://aekraft.gumroad.com/l/sjmbrp |  |
| 62 | STR Direct Booking Revenue Kit | `str-direct-booking-revenue-kit--iPqoAa.png` | https://aekraft.gumroad.com/l/ppsluq |  |
| 63 | Stripe Chargeback Defense Kit for Digital Sellers | `stripe-chargeback-defense-kit-for-digital-sellers--F3Q5fU.png` | https://aekraft.gumroad.com/l/ceiwk |  |
| 64 | Subscription Renewal Compliance Kit | `subscription-renewal-compliance-kit--2ZvRp7.png` | https://aekraft.gumroad.com/l/xouyjy |  |
| 65 | Suspended Seller First-Appeal POA System | `suspended-seller-first-appeal-poa-system--66fo53.png` | https://aekraft.gumroad.com/l/zfnagp |  |
| 66 | Tech Job Offer Evaluation & Negotiation System | `tech-job-offer-evaluation-negotiation-system--q63gLi.png` | https://aekraft.gumroad.com/l/qpuagh |  |
| 67 | The 5-Minute Context Reset Playbook | `the-5-minute-context-reset-playbook--9Zq9SG.png` | https://aekraft.gumroad.com/l/vhofn | duplicate title |
| 68 | The 5-Minute Context Reset Playbook | `the-5-minute-context-reset-playbook--rMOopS.png` | https://aekraft.gumroad.com/l/akxaae | duplicate title |
| 69 | Toy Safety File Starter (EN 71 Lens) | `toy-safety-file-starter-en-71-lens--jIkPBK.png` | https://aekraft.gumroad.com/l/vyitxf |  |
| 70 | Trademark DIY Filing Action Kit | `trademark-diy-filing-action-kit--KMNGNg.png` | https://aekraft.gumroad.com/l/vkqogv |  |
| 71 | Turo Guest Dispute Toolkit | `turo-guest-dispute-toolkit--srd6CI.png` | https://aekraft.gumroad.com/l/adyvd |  |
| 72 | UK Deposit Recovery Action Pack | `uk-deposit-recovery-action-pack--A1LlQx.png` | https://aekraft.gumroad.com/l/edgiq |  |
| 73 | Vendor Onboarding & 1099-Readiness Pack for US Small Business | `vendor-onboarding-1099-readiness-pack-for-us-small-business--vQEIyR.png` | https://aekraft.gumroad.com/l/ykwdfc |  |
| 74 | Vendor Questionnaire Response Kit | `vendor-questionnaire-response-kit--J6ir7v.png` | https://aekraft.gumroad.com/l/pyzqa |  |
