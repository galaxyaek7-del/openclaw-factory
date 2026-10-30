# Research sample: European Accessibility Act penalties: what the statutes say vs. what is quoted

Date: 2026-10-29. Status: SAMPLE (not offered, not legal advice).
Dataset: `data_products/releases/eaa-penalty-register/2026-10-29/` (data card PASS).

## Question
An online seller serving EU consumers asks: "What can a fine be under the EAA?"

## Finding
- **Comparisons disagree:** published comparisons disagree, and at least one widely read table does not match the statute it cites.
- **Germany (VERIFIED, official text):**
  - BFSG s. 37(2) sets a maximum fine of EUR 100,000 for the offences in s. 37(1) Nos 1, 7, 8, 9 and 10. No 8 is offering or providing a non-compliant service.
  - The other offences (Nos 2–6: information, marking, documentation) carry up to EUR 10,000.
  - Source: [gesetze-im-internet.de](https://www.gesetze-im-internet.de/bfsg/__37.html).
- **Ireland (VERIFIED, official text):**
  - S.I. No. 636/2023 Reg. 32: on indictment, up to EUR 60,000 or 18 months, or both; on summary conviction, a class A fine or up to 6 months.
  - The CCPC is the market surveillance authority for products. Several bodies can prosecute within their functions (Reg. 35).
  - Source: [irishstatutebook.ie](https://www.irishstatutebook.ie/eli/2023/si/636/made/en/print).
- **The conflict:**
  - Deque's country table gives Germany "up to EUR 500,000", citing the BFSG together with its implementing regulation and the Medienstaatsvertrag.
  - BFSG s. 37 alone gives EUR 100,000. Which provision produces EUR 500,000 is UNKNOWN; the media-law route is a plausible but unverified explanation.
  - Vendor blogs also quote EUR 100,000+ and EUR 500,000 without statutes.
- **Not verified:** France, Netherlands, Austria and Spain are carried in the dataset as SECONDARY_UNVERIFIED (Deque figures). France has another secondary source at EUR 50,000–75,000.

## Why this could be a product
- **Who:** sellers and their advisers get conflicting numbers from vendors who also sell remediation. A neutral, statute-cited register with a verification status per figure does not appear to exist (INFERRED from the searches; not exhaustive).
- **Shape:**
  - a quarterly-maintained register;
  - a one-page brief per country;
  - change alerts when a transposition is amended.

## What it is not
- It is not a prediction of fines actually imposed: statutory maximums say nothing about enforcement practice.
- It is not legal advice.

## Effort and risks
- **Effort:** about 1–2 hours per country to read the national text and record provisions (DERIVED from DE and IE this session). 27 countries is roughly 30–50 hours initially.
- **Language:** several texts are not in English, and machine translation must be checked.
- **Legal-advice boundary:** the product must stay factual.

## Pricing hypothesis (UNKNOWN)
- Free sample of 2 countries.
- Full register with change alerts: $49 per year.
- A per-country brief: $15.
- No buyer has been asked.

## $0 validation
- **Offer:** a free sample: the DE and IE rows plus this brief.
- **Signal:** count requests for the full register through the inquiry queue once a receiver exists.
- **Continue:** at least 5 requests from sellers or advisers in 60 days.
- **Stop:** fewer than 2.

## Sources
- [BFSG s. 37](https://www.gesetze-im-internet.de/bfsg/__37.html)
- [S.I. No. 636/2023](https://www.irishstatutebook.ie/eli/2023/si/636/made/en/print)
- [Deque EAA country data](https://www.deque.com/european-accessibility-act-eaa-compliance/country-compliance-data/)
- [Level Access on enforcement](https://www.levelaccess.com/blog/eaa-compliance-in-2026-how-enforcement-has-evolved-and-what-to-expect-next/)
