# Factory decisions approved by the founder (2026-11-06)

The founder approved executing decisions **1 (measure first)** and **5 (kill criteria written in advance)**. The other recommendations stay proposals.

## Status
| # | Decision | State |
|---|---|---|
| 1 | Measure before anything else | Partly built. UTM on every outbound Gumroad link from the site (done), funnel report (`scripts/funnel_report.py`, in the doctor round), hosted-counter hook in `customer_site/assets/gf-pageview.js` (disabled until a code is set). **Visit counting still needs the founder's one-time step below.** |
| 5 | Kill criteria written in advance | Done: `config/kill_criteria.json`, judged by the funnel report and surfaced in the doctor round. Thresholds are decisions, not forecasts. "Not measured" is never counted as a miss. |

## Kill criteria (config/kill_criteria.json)
| Checkpoint | Date | Needs | If missed |
|---|---|---|---|
| C1 | 2026-11-27 | at least 5 measured pin outbound clicks | review pins, concentrate on the 5 strongest tools, check that clicks are measured |
| C2 | 2026-12-11 | at least 25 clicks OR 1 sale | change positioning/price of top tools one change at a time; put the service path first |
| C3 | 2027-01-08 | at least 1 sale | founder decision: stop adding tools, keep measured channels, move effort to the service arm |

## One-time founder step: real visit counts (about 2 minutes, free, no card)
The static site on GitHub Pages cannot receive the old beacon, so visits are NOT MEASURED. The agent cannot create accounts.
1. Create a free site at https://www.goatcounter.com (privacy-friendly, no cookies). You choose a site code, for example `galaxyforge`.
2. Tell the agent the code. It sets `GF_COUNTER_CODE` once in `customer_site/assets/gf-pageview.js`, runs the tests and publishes; every page that loads that file starts counting.
3. The funnel report then gets a visits line (read from your GoatCounter dashboard or its export, entered by the doctor session; the factory loop cannot call it).
Alternatives with the same shape: Cloudflare Web Analytics. Anything that needs a card or a paid plan is out of scope.
