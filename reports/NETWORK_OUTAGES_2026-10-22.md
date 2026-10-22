# Network outages on the factory host (2026-10-15 → 2026-10-22)

Source: the `network` health check in `factory_loop.log`, which HEAD-requests
api.groq.com, api.telegram.org and github.com every tick. 711 ticks since
2026-10-15; 123 reported every target unreachable at once.

## Verdict: real outages, not a monitoring bug

Failures come in contiguous blocks, with all targets failing together. That
is the shape of the host losing connectivity, not of one service misbehaving.

| Window (UTC) | Ticks | ≈ Duration |
|---|---|---|
| 10-17 14:34 → 17:14 | 17 | 2.8 h |
| 10-18 16:02 → 17:02 | 7 | 1.2 h |
| 10-19 13:51 → 16:01 | 14 | 2.3 h |
| **10-20 04:10 → 12:00** | **48** | **8.0 h** |
| 10-21 14:25 → 15:55 | 10 | 1.7 h |
| **10-22 02:55 → 06:15** | **21** | **3.5 h** |
| plus 6 isolated single or double ticks | | |

## What it explains (correlation, not proof)

- Openclaw_Sensing_Engine failed with "connection cannot be established" at
  10-20 07:00. That is inside the 8-hour outage of 10-20.
- Its other failure of that kind, at 10-16 07:00, falls in **no** outage window.
  A stray newline at the end of the Trends URL is a plausible cause. It was
  removed in the 2026-10-22 workflow fix.

## Implications

- Scheduled jobs that run during an outage fail through no fault of their
  own. Sensing runs once a day at 07:00 UTC (08:00 Algiers), which is close
  to the morning outage pattern. A failed daily run loses a whole day of
  trend data.
- Since 2026-10-22, network failures are classified retryable
  (`channels/error_classification.py`), so a publish attempt that hits an
  outage is queued for a later retry rather than lost.
- The cause is outside the code: power, ISP, Wi-Fi or a laptop sleep policy
  that keeps the process alive but drops the network. That is UNKNOWN from
  here, and it is the founder's to check.
