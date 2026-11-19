# The Workflow Automation Cost Check: Before You Move a Process into n8n

> **Affiliate disclosure:** This draft is intended to carry an affiliate link for n8n. If you use that link and become a paying customer, Galaxy Forge may earn a commission at no extra cost to you. No link is configured yet.
>
> **Draft status:** `LINK_BLOCKED`. This is not a published page. Do not publish, index, or send traffic to it until a real approved link and disclosure are in place.

Automation pricing pages usually show plan tiers. They rarely show the cost of the process you are automating: the exceptions, the maintenance, the failed runs, and the human time spent checking whether the automation actually worked.

This checklist is a practical way to compare the real cost of a workflow before you move it into n8n. It is not a feature list, a ranking, or a promise of savings.

## Start with the process, not the tool

Write down one workflow you are considering. Then fill in these fields:

| Field | Your answer |
|---|---|
| Trigger | What starts the workflow? |
| Inputs | Which systems and fields does it read? |
| Decisions | Where does a human currently make a judgment? |
| Outputs | What must exist when it finishes? |
| Exceptions | What are the five most common ways it breaks? |
| Volume | How many runs per day or week? |
| Owner | Who fixes it when it fails? |
| Cost of failure | What happens if it runs late or wrong? |

If you cannot answer the exception and failure-cost rows, you are not ready to automate the process. You are ready to document it.

## The cost checklist

### 1. Run volume

Count real executions, not imagined ones. A workflow that runs 20 times a day has a different cost profile from one that runs twice a month. Include retries and test runs.

### 2. Human review time

Automation often moves work from "doing" to "checking." Estimate the minutes per run spent reviewing output, correcting exceptions, and handling failures. Multiply by the real volume. That is a cost, even if it does not appear on a software invoice.

### 3. Maintenance surface

Every connected system can change its API, authentication, or data shape. List the integrations. For each one, ask:

- who owns the credential;
- what happens when the credential expires;
- whether the API has a versioning policy;
- whether the workflow can detect a schema change;
- how a failed run is retried or escalated.

### 4. Data handling

Decide where the data is allowed to go before you connect anything. Record:

- which fields are personal or sensitive;
- which systems receive them;
- how long execution logs retain them;
- whether the workflow can run without storing payloads;
- who can view the run history.

### 5. Failure behavior

A workflow that fails silently is worse than a manual process. Define:

- a failure alert with an owner;
- an idempotency rule so a retry does not duplicate an action;
- a dead-letter or manual-review path;
- a rollback step for external side effects.

### 6. Exit path

Before building, confirm you can export the workflow definition, credentials, and logs. A tool that is cheap to enter but expensive to leave is not cheap.

### 7. Total monthly cost

Add:

```text
subscription + execution overage + integration costs
+ human review time + maintenance time + failure cost
```

Do not compare a subscription price to zero. Compare it to the real current process cost.

## Where n8n fits

The current program record, last checked on 2026-10-21, states:

| Item | Recorded detail |
|---|---|
| Commission | 30% revenue share for 12 months on Starter/Pro plans |
| Application | Self-service, open to anyone with an audience |
| Network | PartnerStack |
| Minimum | EUR 100 |
| Recorded payout rail | PayPal required per n8n's FAQ; PartnerStack's directory also lists Stripe and alternative methods |
| Restriction | Paid-ads ban recorded |
| Algeria payout | `CONDITIONAL`: PayPal's Algeria receive agreement lists Algeria, but requires a linked US bank or Visa, a 30-day hold, and withdrawal-only balance use |

The 30% figure is a program term, not a customer benefit. The buyer should choose the tool because it fits the workflow, not because a publisher earns a commission.

The payout rail matters for the publisher. PayPal's Algeria receive agreement lists Algeria, but it is not a frictionless local rail: it requires a linked US bank account or Visa credit card, a 30-day hold, and withdrawal-only balance use. n8n's FAQ says PayPal is required, while PartnerStack lists alternatives; the exact rail is unconfirmed. n8n is therefore not activation-ready until the program confirms a receivable route. This draft does not claim that n8n pays in Algeria.

## What this checklist does not prove

- that n8n is cheaper than the current process;
- that a workflow will save a specific number of hours;
- that the program will approve a publisher or pay in Algeria;
- that an automation will be reliable without monitoring.

Those require real measurements and, for payout, official confirmation.

## Next step

Pick one workflow. Fill in the table. If the failure cost and owner are unclear, fix the process before automating it. If they are clear, compare the total monthly cost with and without the tool.

> **CTA (blocked):** An approved n8n affiliate link is not configured. This draft must remain `LINK_BLOCKED` until the founder supplies a real link and verifies the payout route.

---

**Sources and dates are recorded in `sources.json`. Revalidate every term at the official source before publication.**
