# SIMULATION: the factory's reaction to the first real demand signal

Run 2026-11-05T19:59:20+00:00. Real modules, isolated temp data, stubbed publisher: nothing real was read as demand, written or published. This proves the wiring, not that a buyer will appear.

| Scenario | Expected | Got | Result | Why |
|---|---|---|---|---|
| S0 no signal: gate | `False` | `False` | PASS | WAITING FOR REAL DATA: no sale, outside click, buyer interest or buyer-side market evidence |
| S0 no signal: publisher never goes live | `[]` | `[]` | PASS | new products frozen (GF_FREEZE_NEW_PRODUCTS=true), WAITING FOR REAL DATA: no sale, outside click, buyer intere |
| S0 no signal: loop stays frozen | `{'frozen': True, 'slots': [False, False, False]}` | `{'frozen': True, 'slots': [False, False, False]}` | PASS | frozen, and every requested production slot is refused |
| S1 test/example/simulated rows: gate | `False` | `False` | PASS | fake domains, TEST_EVENT and SIMULATION rows are ignored |
| S2 one real sale: gate opens with cap | `(True, 3)` | `(True, 3)` | PASS |  |
| S2 sale + 5 approved ready: live publications limited to the cap | `3` | `3` | PASS | published 3 ['SIM-000', 'SIM-001', 'SIM-002']; not passed 0 [] |
| S2 loop unfreezes and hands out exactly the cap in production slots | `{'frozen': False, 'slots': [True, True, True, False, False]}` | `{'frozen': False, 'slots': [True, True, True, False, False]}` | PASS |  |
| S3 real buyer email: gate opens | `True` | `True` | PASS |  |
| S4 possible-human outside click: gate opens | `True` | `True` | PASS |  |
| S5 gate unreadable: nothing published (fail-closed) | `[]` | `[]` | PASS | new products frozen (GF_FREEZE_NEW_PRODUCTS=true), demand gate not enabled: nothing is published |
| S5 gate unreadable: loop stays frozen | `{'frozen': True, 'slots': [False, False, False]}` | `{'frozen': True, 'slots': [False, False, False]}` | PASS | unparseable gate answer: frozen, every slot refused |
| S6 window full: no live call even with demand | `[]` | `[]` | PASS | 5 approved product(s) ready; Gumroad window full (10/10) |
| S7 printable Gumroad $19 + demand: covered | `True` | `True` | PASS | inside the founder's standing authorization |
| S7 same product, no demand: not covered | `False` | `False` | PASS | demand gate closed: simulated closed |
| S7 $49 product (over the $29 cap): not covered | `False` | `False` | PASS | SA-20261105-01: price 49.0 not within 0..29 |
| S7 Etsy listing: not covered | `False` | `False` | PASS | SA-20261105-01: platform 'etsy' not in scope |
| S7 non-printable type: not covered | `False` | `False` | PASS | SA-20261105-01: product type 'software' not in scope |
