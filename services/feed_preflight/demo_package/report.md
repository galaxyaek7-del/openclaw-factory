# Feed preflight report (demonstration, synthetic store)

Rows checked: 12. Rows clean: 4. Rows with errors: 8. Errors: 10. Warnings: 3.

| Row | id | Field | Severity | What to fix |
|---|---|---|---|---|
| 3 | NC-002 | price | error | '24,00 USD': a comma is not accepted as the decimal point; use a number, a point for decimals and an ISO 4217 code, e.g. 15.00 USD |
| 4 | NC-003 | gtin | error | GTIN check digit is wrong; do not guess a code, ask the manufacturer |
| 5 | NC-004 | availability | warning | 'In Stock' is a spelling variant; the specification lists in_stock, use it exactly |
| 6 | NC-005 | gtin | warning | no GTIN and no brand+MPN pair; if the product truly has none, set identifier_exists to no |
| 8 | NC-007 | id | error | id is used by 2 rows; each product needs its own |
| 8 | NC-007 | link | error | must start with http:// or https:// |
| 9 | NC-007 | id | error | id is used by 2 rows; each product needs its own |
| 10 | NC-009 | gtin | error | GTIN is in a restricted GS1 range (02, 04, 2); do not guess a code, ask the manufacturer |
| 11 | NC-010 | title | error | longer than 150 characters (166) |
| 12 | NC-011 | image_link | error | required value is empty |
| 12 | NC-011 | sale_price | warning | sale price is not below the price |
| 13 | NC-012 | price | error | a price of 0 is not accepted (except phones sold with a contract) |
| 13 | NC-012 | identifier_exists | error | set to 'no' while a GTIN is given; the product may be disapproved |

Not checked by this preflight (Google decides these at review):

- whether feed price and availability match the landing page and checkout
- image content and policy compliance
- category-specific required attributes
- account-level settings (shipping, returns, tax)

Rules from: https://support.google.com/merchants/answer/7052112, https://support.google.com/merchants/answer/6324461
