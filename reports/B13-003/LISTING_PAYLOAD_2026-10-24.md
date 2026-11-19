# B13-003 Listing Payload (2026-10-24)

**State:** `LOCAL_READY__AWAITS_FOUNDER_PRICE_DECISION_AND_LISTING_AUTHORIZATION`

- Published: **no**
- Gumroad call made: **no**
- Price: **$16.99** (planning target; not founder-approved)
- Digital net: **$15.29** against a **$2.50** floor
- Premium net: **$15.29** against a **$25.00** floor
- Gate: **APPROVED** (100/100/70)
- Guide: **30 pages**, **10,378 gate words**
- Workbook: **162 formulas**, **6 validations**, **0 Excel errors**
- Independent value check: **PASS**, 24 fields compared, 0 mismatches
- Local listing audit: **LOCAL_CHECKS_PASS__AWAITING_PRICE_AND_PUBLICATION_DECISION**, 0 problems
- Copy claims: **8/8** verified against the workbook and guide
- Observed competitor range: **$4.99-$29.00** from 6 sourced offers

## Why this is not live
No founder price decision and no listing/publication authorization exist. The
read-only gate check returned **DENY**. The Gumroad auth state was fresh and
verified, but the live-publish flag was false and no scope was supplied. This
payload is local evidence, not a publication.

## Files
- `books/batch13/B13-003_caregiver_command_kit.xlsx` - 32,518 bytes
- `books/batch13/B13-003_caregiver_command_kit_guide.pdf` - 55,506 bytes
- `reports/B13-003/B13-003.png` - 1280x720

## Listing copy
Full copy: `drafts/b13_003_listing_copy.txt`

Caregiver Command Kit: Emergency, Medication, Appointments

When the phone rings at 2 a.m., you do not need another app. You need the facts in one place.

This kit is a 14-sheet Excel workbook plus a 30-page PDF guide for the family caregiver who is holding medication schedules, appointment notes, emergency contacts, insurance details, and document locations in their head. It is built for the handoff: the aide on Monday, the sibling on the weekend, the triage nurse at midnight.

Inside the 14-sheet Excel workbook (162 live formulas, no macros):

- Start Here - the color key, the privacy rule, and the order to fill the file
- Care Profile - stable facts: legal and preferred name, diagnoses, allergies, mobility, baseline, clinicians, contacts, and care wishes
- Emergency One-Pager - a printable page for the refrigerator or go-bag, with the current medication list and what the ER should know
- Medications - name, dose, purpose, prescriber, schedule, pharmacy, refill date, status, last reconciled, and days to refill
- Appointments - date, provider, purpose, questions to ask, transport, after-visit notes, next step, and follow-up
- Care Team - the people and organizations a fill-in helper may need to call, with role, phone, portal, and preferred contact method
- Daily Log - a short daily record of mood, appetite, sleep, mobility, pain, hydration, what changed, and caregiver initials
- Hospital & Discharge - a go-bag checklist and an admission-to-discharge task list with owners and status
- Documents & Access - where each important document lives, who holds it, and when it was last reviewed (locations, not passwords or account numbers)
- Insurance & Benefits - plan, customer service, card location, renewal date, prior authorization notes, status, and days to renewal
- Expenses & Mileage - dated costs, category, paid to, amount, reimbursable flag, miles, mileage value, and notes
- Respite & Backup - who can cover what, when, and with how much notice
- Questions & Decisions - the decision log: question, options, who decides, decision, review date, status, and days to review
- Summary - one page with twelve integrity checks that counts what is current and flags missing doses, missing prescribers, missing providers, missing owners, missing allergies, stale documents, stale decisions, and past-due refills

The workbook ships with one worked example: an older adult with mild cognitive impairment and several chronic conditions, five active medications, a family and neighbor support network, a clinic visit, a refill review, an eye exam, and a short daily log. Every name, date, contact, and amount is illustrative. Replace the yellow rows with your own facts, keep the blue formula rows, and delete the examples you do not need.

Also included: a 30-page PDF guide. It covers the first 20 minutes, the emergency page, medication reconciliation, appointment preparation, the care-team directory, the daily log, hospital admission and discharge, document locations, insurance calls, expenses and mileage, respite and backup coverage, family decisions, cognitive changes and falls, privacy, legal boundaries, and the weekly reset. The guide includes a worked example, a one-page care plan, a family meeting agenda, a clinician call script, a hospital go-bag list, and a first-week checklist.

Built for Excel. The workbook uses standard formulas only, no macros and no add-ins. LibreOffice Calc and Google Sheets have not been tested by me, so if anything misbehaves, reply to your receipt and I will fix it.

This is an organizing and handoff tool, not medical, legal, or financial advice. It does not replace a clinician, a pharmacist, an attorney, or the official advance directive. In an emergency, call 911. Confirm medication and care decisions with a qualified professional.

New product from Galaxy Forge: no sales recorded yet, no reviews. Support: reply to your Gumroad receipt email.


## Honest gaps
- No payment proof exists for this niche in this factory; the market layer relies on six sourced offers and a price below every direct-page comparable.
- Two Etsy prices are search-index evidence because direct page loads returned HTTP 403; four prices were read from directly fetched product pages.
- The cover is the only preview image produced. Additional preview images are an explicit gap before a final visual review.
- LibreOffice Calc and Google Sheets are untested.
- No sale, review, or revenue is claimed. The guide and workbook are not medical, legal, or financial advice.
