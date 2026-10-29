# DEMONSTRATION, NOT A CUSTOMER RESULT

This walk-through uses invented data. No shop, customer, saving or result below is real.

## The situation (invented)

A small shop selling kitchen goods merges three files before a price update: its supplier's
price list (US dates, dollars), its EU shop export (EU dates, euros with a decimal comma)
and its US shop export (mixed). Thirteen rows, as in `input_messy.csv`.

## What a quick spreadsheet clean-up would have done

Converted every date it could parse, including `03-04-2026`, which might be 3 April or
4 March, and stripped the currency symbols so that `$8.50` and `€8,50` read as the same 8.5.

## What the service returns

`output_clean.csv` and `qa_report.json`:

- 12 rows (one exact duplicate removed);
- 9 dates converted, 2 ambiguous dates left exactly as written, 1 impossible date
  (`2026-02-30`) flagged rather than invented;
- AB-1001 and AB-1002 listed as repeated across sources, for the owner to resolve;
- the price column flagged as mixing dollars and euros.

## What the owner still decides

Which of the repeated rows is current, what the two ambiguous dates are, and whether the
euro prices need converting. The service does not make those decisions.
