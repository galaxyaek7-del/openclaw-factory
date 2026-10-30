# Research sample: European Accessibility Act penalties: what the statutes say vs. what is quoted

Date: 2026-10-29. Status: SAMPLE (not offered, not legal advice).
Dataset: `data_products/releases/eaa-penalty-register/2026-10-30/` (data card PASS; the 2026-10-29 release is kept unchanged).

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
- **Austria (VERIFIED 2026-10-30, official text):**
  - BaFG s. 36 sets up to EUR 80,000 for s. 36(1) offences, EUR 40,000 for s. 36(2) and EUR 16,000 for s. 36(3).
  - Lower ceilings apply to micro, small and medium enterprises: EUR 50,000 under (1) and EUR 25,000 under (2).
  - The penalty authority is the Sozialministeriumservice.
  - Source: [RIS](https://ris.bka.gv.at/eli/bgbl/i/2023/76/P36/NOR40254396). This one matches the secondary table.
- **Netherlands (VERIFIED 2026-10-30, official gazette):**
  - The implementing act ([Staatsblad 2024, 87](https://zoek.officielebekendmakingen.nl/stb-2024-87.html)) sets the maximum administrative fine at the 5th fine category of Criminal Code art. 23, both for products (Warenwet) and for services (Wet handhaving consumentenbescherming).
  - That category's euro value is indexed and was not re-read. The secondary table's EUR 103,000 matches an earlier year's value.
- **France (VERIFIED in part, 2026-10-30):**
  - Code de la consommation art. R.451-4 I (created by Décret 2023-931) punishes listed product breaches with the fine of a 5th-class contravention: CE marking, conformity assessment, and manufacturer, importer and distributor duties.
  - The amount is set by the Code pénal, not re-read for this release. Whether service breaches fall under this article is UNKNOWN.
  - Source: [Légifrance](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000048180406/).
  - A contravention is far below the EUR 300,000 one secondary table gives (another gives EUR 50,000–75,000). Where those figures come from is UNKNOWN.
- **Spain (VERIFIED, 2026-10-30):**
  - Ley 11/2023 art. 30 sends breaches to the sectoral legislation. Where that is silent, Title III of RDL 1/2013 applies.
  - Its art. 83 sets EUR 301 to EUR 1,000,000: minor up to EUR 30,000, serious up to EUR 90,000.
  - The secondary table's EUR 1,000,000 is this fallback ceiling.
  - Sources: [Ley 11/2023](https://www.boe.es/buscar/act.php?id=BOE-A-2023-11022), [RDL 1/2013](https://www.boe.es/buscar/act.php?id=BOE-A-2013-12632).
- **Coverage:** all six countries in this sample are tied to their own legal text. FR and NL each have one figure not re-read (the contravention amount; the indexed category value).

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
