# Lesson: The Paginated API That Lied (Gumroad /v2/products)

**Mistake:** trusted `/v2/products?page=N` pagination at face value across three sessions of findings ("150 live products", "300", "1000+", "2000 products").

**Consequence:** every catalog-size claim was a duplication artifact; real reconciliation attempts failed mysteriously (known-live URLs "missing" from thousand-row lists).

**How found:** cycle-65 full sweep fetched 200 pages / 2000 rows, then deduped by URL: **10 unique products**. The endpoint repeats the same slice regardless of `page`.

**Fix:** inventory via stable IDs (sales_ledger product_ids + get_product per ID). All 50 claimed products resolved live with this method.

**Generalizable lesson:** any paginated external API gets a dedup-count check before its totals are cited anywhere. Totals from raw row counts are fabrication-adjacent until deduplicated.
