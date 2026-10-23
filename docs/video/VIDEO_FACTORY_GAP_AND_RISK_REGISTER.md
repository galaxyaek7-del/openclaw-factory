# Video factory: gaps and risks

| ID | Gap or risk | Severity | Effect | Treatment |
|---|---|---|---|---|
| V1 | Voice licence for commercial video UNRESOLVED | High | blocks publication | founder decision: licensed voice or own recording |
| V2 | Windows font licence for video UNRESOLVED | Medium | blocks publication | switch to OFL fonts (engineering, small) |
| V3 | No real YouTube transport / OAuth | High | no upload possible | founder creates OAuth client; then build transport behind existing gates |
| V4 | Narration intelligibility not measured | Medium | quality unknown to machines | human listen; optional free local recogniser later |
| V5 | Visual style is text-and-shapes ("slideshow-like") | High for growth | low retention expected; risk under YouTube's inauthentic/mass-produced monetization policy if scaled without original value | keep each video tied to a real worked example; add real screen captures of the product; never mass-produce |
| V6 | Publication approval is a recorded approval, not a single-use token | Low | weaker than upload scope | by design: write_scope refuses to scope "published"; documented |
| V7 | No Arabic voice | Medium | Arabic videos impossible locally | Arabic subtitles only, or founder narration |
| V8 | No thumbnails, music, analytics | Medium | incomplete channel package | later, after V1-V3 |
| V9 | Crash after a real upload but before the result is recorded | Low (no transport yet) | duplicate risk | handled: NEEDS_RECONCILIATION, no auto retry |
| V10 | Render depends on Windows (speech, fonts) | Low | not portable to CI | tests stub speech; renderer falls back to Pillow fonts |
| V11 | imageio-ffmpeg not in requirements | Low | render/verify tests skip on CI | state-machine tests still run on CI |
| V12 | Synthetic-media disclosure judgement | Low | mislabel | set true conservatively; YouTube's rule targets realistic content |
