# Company-Wide Commitment to Reality Mode

As part of our ongoing effort to formalize and improve our discipline, we've adopted a new reality mode across the company. This means that from now on, every report, dashboard, recommendation, forecast, opportunity, revenue estimate, and product proposal will explicitly distinguish between VERIFIED REALITY, ESTIMATED, SIMULATED, and UNKNOWN.

This decision builds on the discipline we've already informally followed, but lacked a single, named taxonomy and a computed aggregate score. Our reality mode classification is conservative, never assuming false certainty where we cannot confirm direct observation. This is reflected in the classifier's default behavior, where an unwrapped raw value with no marker defaults to ESTIMATED.

To ensure transparency and accuracy, we've also introduced a Company Reality Score. This score is built entirely from real counts, using real external-evidence sources to verify the accuracy of our assumptions. The score reports the full per-opportunity detail alongside the percentage, so the number is auditable and never a black box.

**Key Changes**

- All reports and dashboards will now include a reality level classification (VERIFIED REALITY, ESTIMATED, SIMULATED, or UNKNOWN) for every field.
- We've added a Company Reality Score, which is computed from real counts using real external-evidence sources.
- Future modules will automatically inherit the reality mode rule and construct fields using `verified()`, `estimated()`, `simulated()`, or `unknown()`.
- We've introduced a generic adapter that reads existing report shapes and classifies them onto the 4 levels without requiring the underlying module to change.

**What's Not Built**

- We're not performing a mass rewrite of existing modules' output shapes; instead, the generic adapter satisfies the directive's requirement without the risk.
- We're not continuously re-scoring the Reality Score online; instead, it's computed on-demand only.

**Next Steps**

We've written 19 new tests, along with 2 new Mission Control action tests and a real, live smoke test to confirm both `compute_company_reality_score()` and `reality_audit()` run cleanly end-to-end.

**Known Gap**

As of our adoption of this ADR, our current Company Reality Score is `0.0%` (3 real ACCEPTED opportunities, zero with any real external evidence source yet), indicating that we have no ACCEPTED opportunities currently backed by at least one real external evidence source.
