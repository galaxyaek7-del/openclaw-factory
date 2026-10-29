# Before / after (synthetic demonstration data)

| Before (as exported) | After |
|---|---|
| supplier /  ab-1001  / Ceramic mug 350ml / $8.50 / 03/15/2026 / 40 | |
| supplier / AB-1002 / Ceramic mug 500ml / $9.75 / 03/15/2026 / 25 | |
| supplier / ab-1003 / Tea towel, linen /  6.20  / 03/16/2026 /  | |
| supplier / AB-1004 / Coaster set (4) / $12.00 / 13/03/2026 / 18 | |
| shop_eu / AB-1001 / Ceramic mug 350ml / €8,50 / 15-03-2026 / 40 | |
| shop_eu / ab-1005  / Bread board, oak / €24,90 / 16-03-2026 / 6 | |
| shop_eu / AB-1006 / Candle, beeswax / €11,40 / 2026.03.17 / 30 | |
| shop_eu / AB-1007 / Napkin rings (6) / €7,00 / 03-04-2026 / 12 | |
| shop_us / AB-1002 / Ceramic mug 500ml / 9.75 / 2026-03-15 / 25 | |
| shop_us / AB-1008 / Salt cellar / $14.00 / 04/05/2026 / 9 | |
| shop_us / AB-1009 / Pepper grinder / $19.50 / 2026-02-30 / 7 | |
| shop_us / AB-1010 / Butter dish /  / 04/18/2026 / 11 | |
| shop_us /   ab-1002 / Ceramic mug 500ml / $9.75 / 03/15/2026 / 25 | |

Cleaned rows:

| source | sku | name | price | date | qty |
|---|---|---|---|---|---|
| supplier | AB-1001 | Ceramic mug 350ml | 8.5 | 2026-03-15 | 40 |
| supplier | AB-1002 | Ceramic mug 500ml | 9.75 | 2026-03-15 | 25 |
| supplier | AB-1003 | Tea towel, linen | 6.2 | 2026-03-16 |  |
| supplier | AB-1004 | Coaster set (4) | 12.0 | 2026-03-13 | 18 |
| shop_eu | AB-1001 | Ceramic mug 350ml | 8.5 | 2026-03-15 | 40 |
| shop_eu | AB-1005 | Bread board, oak | 24.9 | 2026-03-16 | 6 |
| shop_eu | AB-1006 | Candle, beeswax | 11.4 | 2026-03-17 | 30 |
| shop_eu | AB-1007 | Napkin rings (6) | 7.0 | 03-04-2026 | 12 |
| shop_us | AB-1002 | Ceramic mug 500ml | 9.75 | 2026-03-15 | 25 |
| shop_us | AB-1008 | Salt cellar | 14.0 | 04/05/2026 | 9 |
| shop_us | AB-1009 | Pepper grinder | 19.5 | 2026-02-30 | 7 |
| shop_us | AB-1010 | Butter dish |  | 2026-04-18 | 11 |

What the QA report says:

- input rows 13, output rows 12, duplicates removed 1
- dates converted 9; ambiguous dates kept as written for review 2 ['03-04-2026', '04/05/2026']; impossible dates kept and flagged 1 ['2026-02-30']
- rows with a missing value 2
- SKUs appearing in more than one row (reported, not merged): ['AB-1001', 'AB-1002']
- columns mixing currencies (amounts made numeric, currencies differ): ['price'] {'price': ['$', '€']}
