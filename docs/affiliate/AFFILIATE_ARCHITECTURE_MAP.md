# Affiliate architecture map (as implemented)

```mermaid
flowchart LR
  DISC[affiliate_discovery.py<br/>research] --> OPP[(data/commission_opportunities.jsonl)]
  OPP --> REG[affiliate/registry.py<br/>status read model]
  EV[(data/affiliate_algeria_evidence.json)] --> ELIG[affiliate/eligibility_matrix.py<br/>eligibility + payout]
  OPP --> ELIG
  APPR[(data/affiliate_program_approvals.jsonl)<br/>NEW 2026-10-23] --> REG
  REG --> CONTENT[affiliate_content_factory.py / prepare_content<br/>drafts]
  CONTENT --> QA[affiliate/content_qa.py]
  QA --> GATE[channels/write_gate.py<br/>publish / message switches]
  GATE -.->|only with authorization| CH[(channels)]
  LINKS[affiliate/links.py<br/>registry + validate_destination NEW] --> SITE[customer_site pages]
  SITE --> CLICK[/api/affiliate/click/:id<br/>server.js/]
  CLICK --> CT[click_tracking.py] --> CLK[(data/affiliate_clicks.jsonl)]
  CLICK --> AMZ[Amazon product URL<br/>tag only if configured]
  NET[network statement / email] -.->|manual, with evidence| LED[commission_ledger.py<br/>record_commission + record_status_change NEW]
  LED --> SUM[real_commission_summary<br/>latest state, per currency]
  SUM --> FIRST[first_real_dollar_status]
  FW[affiliate/ledger_firewall.py] --> FIN[(finance_data.json)]
```

## Lifecycle

```mermaid
sequenceDiagram
  participant R as Registry
  participant F as Founder
  participant N as Network
  participant S as Site
  participant V as Visitor
  participant L as Commission ledger
  R->>F: program QUALIFIED, eligibility/payout evidence
  F->>N: applies (founder action; not automated)
  N-->>F: approval email
  F->>R: record_approval(APPROVED, evidence)
  F->>S: link configured (tag / affiliate URL)
  V->>S: visits (UNMEASURED on Pages)
  V->>S: clicks -> /api/affiliate/click (local server only today)
  N-->>F: conversion on network dashboard
  F->>L: record_commission(REAL, PENDING, evidence, tx id)
  N-->>F: approved / reversed / paid
  F->>L: record_status_change(...)
  L-->>R: first real dollar when CONFIRMED/PAID in USD
```

## Stages that do not exist

- No automated import of network reports or postbacks: every real conversion is entered by hand with evidence (by design, but it is the only path).
- No public click receiver: the site is static on GitHub Pages; `/api/affiliate/click` exists only on the local server.
- No payout ledger beyond commission statuses (no bank/PayPal receipt reconciliation).
