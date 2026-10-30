# Automation health audit (productized service, demonstration)

Status: **demonstration only**; no customer, no inquiry, nothing published. Demo input is synthetic.

Reproduce: `python services/automation_health/audit.py services/automation_health/demo_input.json`

## The problem

An automation that stops working rarely announces it. The factory's own n8n ran every company
workflow into "access to env vars denied" for twelve days (2026-10-10..22) while its health
check said OK, because the n8n port still answered (OBSERVED, `scripts/n8n_workflow_health.py`).
The same failure class (a schedule that silently stops, a run that errors, a workflow nobody
switched back on) is the offer.

## Offer

For an owner of a small n8n instance: a one-off report listing every workflow as OK, FAILING,
STALE, UNKNOWN or INACTIVE, with the reason, and a short list of what needs attention.

## Input requirements

- A **read-only** n8n API key (created and revocable by the customer) and the instance URL, or
  the two JSON exports `GET /api/v1/workflows` and `GET /api/v1/executions` (without `includeData`).
- The customer's statement of how often each workflow should run.

## Processing

`audit.assess()` joins workflows to executions and applies the verdict rules in its docstring
(same rules as the factory's internal tool). Output: JSON report plus a short written summary.

## Quality checks and error handling

- A workflow is never OK without a successful, fresh execution and a declared schedule.
- Missing schedule -> UNKNOWN with the reason, not OK.
- Malformed timestamps count as no evidence.
- 8 unit tests (`tests/test_automation_health_audit.py`), including the demo result.

## Security boundaries

- No database access, no credential access, no execution payloads (they can hold customer data).
- No write to the customer's n8n. The customer deletes the API key after the audit.
- Nothing is stored after delivery except the report sent to the customer.

## Human review and effort

Every report is read by the founder before delivery, and the business meaning of a successful
run (did the CRM row really arrive?) is a question for the customer, not the audit. Effort:
about 30-60 minutes per instance of up to ~30 workflows (INFERRED; never measured on a customer).

## Scope and exclusions

Included: status and timing per workflow, the attention list, one follow-up question round.
Excluded: fixing workflows, credentials, data-content checks, other automation platforms
(Zapier/Make need their own adapter), uptime monitoring.

## Price hypothesis (UNKNOWN until a buyer answers)

$49 per audit (one instance, up to ~30 workflows). Comparable offers read on 2026-10-30 (OBSERVED):
- Fiverr, "fix one n8n error": [$98.45 incl. fees](https://www.fiverr.com/automateowned/build-an-n8n-automation-with-ai-agents-error-handling-and-documentation),
  [$24.60](https://www.fiverr.com/novatechs/troubleshoot-enhance-and-optimize-n8n-automation-workflows) (past orders listed at $50 to $200), [$14.05](https://www.fiverr.com/techautomate247/create-n8n-automation-ai-agents-and-api-integrations).
- Upwork catalogue, "n8n workflow reliability audit & fix": [$149 to $599](https://www.upwork.com/services/product/development-it-fix-stabilize-your-n8n-workflow-errors-credentials-silent-failures-2002132381087128397).
- n8n community forum, Jobs category: a [$25 written audit of one workflow export](https://community.n8n.io/t/for-hire-fixed-price-n8n-micro-automations-audits-instant-usdc-payment-no-platform-fees/306934)
  (this also shows the forum hosts "[FOR HIRE]" posts; its rules are still to be read before experiment D4).

Difference: those fix one workflow; this audits every workflow on the instance from the read-only API and
names the silent ones (stale schedules, inactive or never-run workflows), without fixing anything.

## Cheapest test

The factory's existing "silent failures" guide (`customer_site/edu/silent-failures-automation-monitoring.html`)
with a call to action for a free first audit, once a recorded public intake exists. Continue at
3 requests in 60 days; stop at 0.
