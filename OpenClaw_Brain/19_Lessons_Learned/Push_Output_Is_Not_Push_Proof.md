# Lesson: Push Output Is Not Push Proof (PowerShell + git)

**Mistake:** treated `To https://... HEAD -> main` console lines as proof of successful pushes across an entire session of cycles.

**Consequence:** remote sat at an old commit while outputs implied advancement; discovered only by direct `git log origin/main` comparison. No data lost (working tree + local history were complete), but hours of "pushed" status claims were unverified.

**How found:** a range anomaly (`bbbb4cf..7183f00` spanning far more than one cycle) prompted `git fetch` + `git log origin/main` + reflog archaeology.

**Fix:** a push counts ONLY when `git log origin/main` shows the commit. Codified in queue procedure. PowerShell stderr/stdout interleave (RemoteException rendering) was the specific confounder.

**Generalizable lesson:** never trust command-output text for state-changing operations; re-read the resulting state from the authority (remote ref, API record, filesystem) every time.
