# Distribution engine documents (2026-10-23)

Mandate: GF-DISTRIBUTION-ENGINE-v1.0. Nothing was posted to any platform. All publishing paths are closed by the factory switch, and no platform has a built publishing transport.

| Document | Purpose |
|---|---|
| [DISTRIBUTION_CURRENT_STATE.md](DISTRIBUTION_CURRENT_STATE.md) | Baseline before and after, with evidence |
| [DISTRIBUTION_ARCHITECTURE.md](DISTRIBUTION_ARCHITECTURE.md) | Components and how they reuse existing code |
| [DISTRIBUTION_PRODUCT_COVERAGE_MATRIX.md](DISTRIBUTION_PRODUCT_COVERAGE_MATRIX.md) | Every arm and offer type against every platform |
| [DISTRIBUTION_PLATFORM_CAPABILITY_MATRIX.md](DISTRIBUTION_PLATFORM_CAPABILITY_MATRIX.md) | What each platform allows, requires and costs |
| [DISTRIBUTION_GAP_AND_RISK_REGISTER.md](DISTRIBUTION_GAP_AND_RISK_REGISTER.md) | Gaps and risks |
| [DISTRIBUTION_CONTENT_STANDARDS.md](DISTRIBUTION_CONTENT_STANDARDS.md) | Rules every draft is checked against |
| [DISTRIBUTION_CAMPAIGN_PIPELINE.md](DISTRIBUTION_CAMPAIGN_PIPELINE.md) | Stages, states, recovery |
| [DISTRIBUTION_SIMULATION_RESULTS.md](DISTRIBUTION_SIMULATION_RESULTS.md) | The 18 offline scenarios |
| [DISTRIBUTION_REPAIR_LOG.md](DISTRIBUTION_REPAIR_LOG.md) | Defects found and fixed |
| [DISTRIBUTION_REGRESSION_TEST_REPORT.md](DISTRIBUTION_REGRESSION_TEST_REPORT.md) | Test runs |
| [DISTRIBUTION_TRACKING_AND_ATTRIBUTION.md](DISTRIBUTION_TRACKING_AND_ATTRIBUTION.md) | Links, metrics, attribution rules |
| [DISTRIBUTION_NEXT_ACTIONS.md](DISTRIBUTION_NEXT_ACTIONS.md) | Prioritized next steps |
| [DISTRIBUTION_DASHBOARD.md](DISTRIBUTION_DASHBOARD.md) | Generated dashboard (rebuilt by each cycle) |
| [PINTEREST_METRICOOL_WORKFLOW.md](PINTEREST_METRICOOL_WORKFLOW.md) | Pinterest via Metricool: payload, procedure, status |

Run a cycle: `python scripts/distribution_cycle.py --n 8 --per-arm 2`. Code: `social_distribution/`. Tests: `tests/test_social_distribution.py`.
