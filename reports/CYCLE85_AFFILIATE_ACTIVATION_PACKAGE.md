# CYCLE 85 — AFFILIATE ACTIVATION PACKAGE

**Prepared:** 2026-10-14 · **Cost:** $0 · **Status:** prepared, **nothing sent, nothing configured**

---

## 1. THE PRODUCT SELECTED

### **EU AI Act Compliance Toolkit — $155**
**https://aekraft.gumroad.com/l/iaiyt**
**Product ID: `pzTmMb4v8cih3nbWTj5TeA==`** — live-verified 2026-10-14, `published=true`, `price=$155`, `sales_count=0`.

> ### ⚠️ Select by ID. There are FOUR "EU AI Act" listings on this account.
>
> | Product | Price | Affiliate earns at 30% | Seller keeps at 30% |
> |---|---|---|---|
> | **EU AI Act Compliance Toolkit — Practical Templates & Implementation Guide for SMEs** | **$155** | **$46.50** | **$87.70** |
> | EU AI Act Audit Logging Kit | $29 | $8.70 | $15.76 |
> | EU AI Act Compliance Quickstart Checklist | $19 | $5.70 | $10.05 |
> | EU AI Act Transparency & AI Literacy Quickstart Checklist | $9 | $2.70 | $4.34 |

> **CORRECTION.** An earlier draft of this report claimed a 30% commission "exceeds the price" on the $9 listing. That was wrong — 30% of $9 is $2.70 and the seller still keeps $4.34. All four listings can carry 30%.
>
> The accurate reason to isolate the $155 one is commercial, not arithmetic: at $9 and $19 the affiliate earns $2.70 and $5.70, which is not worth an hour of anyone's promotion, so those listings would earn no volume while still exposing margin to low-value sales. At $155 the affiliate earns $46.50 — enough to motivate real promotion — and the seller still clears the factory's $70 elite floor at $87.70.
>
> Choosing **"All products"** would attach 30% to all four. Match on the ID, not the name.

Chosen on the three criteria, not on price alone:

| Criterion | Evidence |
|---|---|
| **Delivery quality** | 2 PDFs, byte-verified: 106,314 + 139,401 bytes, SHA-256 recorded, 3 + 31 pages, 3,266 words, real text extracted. `Not Legal Advice` is Chapter 1 in the shipped bytes. |
| **Customer benefit** | The obligation is real and dated. The toolkit states the deferred high-risk deadline (2 Dec 2027) rather than the superseded 2 Aug 2026 claim — a correction made *against* the product's own earlier sales copy. |
| **Audience clarity** | One buyer, one job: an EU SME compliance/ops owner who must produce evidence. Not a hobbyist, not a developer. |

**Why not the cheaper candidates — this is the decisive part.**

A $29 product nets **$24.46** after Gumroad and card fees. Pay a 30% affiliate and the seller keeps **$15.76**. A $59 product nets $50.59; after 30%, **$32.89**. Those numbers cannot support a serious affiliate programme, and an affiliate who earns $5.80 per sale has no reason to spend an hour on it.

The $155 product nets **$134.20**. At 30% it still keeps **$87.70** — which clears the factory's own $70 elite profit floor. It is the only listing on the account where affiliate promotion is economically coherent.

---

## 2. THE FEES ARE NOT WHAT THE CONFIG SAYS

`config/economics.json` records Gumroad as `royalty_rate 0.9, flat_fee_usd 0.0`, annotated *"Simplified"*.

Gumroad's own fee article says:

> *"For sales made on Gumroad's website, we charge a **10% + $0.50** fee per
> transaction. This does not include: **Credit card processing (2.9% + $0.30)**"*
> — https://gumroad.com/help/article/66-gumroads-fees

Real cost per direct card sale: **~12.9% + $0.80**, not 10%.

This is not a rounding detail. The fixed $0.80 is **2.8% of a $29 sale** and **0.5% of a $155 sale**. Every margin this factory has computed from that config is overstated, and the error is worst exactly where the products are cheapest.

Also worth knowing: a **Discover/marketplace sale costs a flat 30%** — nearly double a direct sale. An affiliate must be given the **direct product link**, never a Discover link.

### Real margin table (quoted rates, not estimates)

| Product | Price | Seller net before affiliate | @20% | @25% | @30% |
|---|---|---|---|---|---|
| **EU AI Act Toolkit** | $155 | **$134.20** | $103.20 | $95.45 | **$87.70** |
| Clinic No-Show | $59 | $50.59 | $38.79 | $35.84 | $32.89 |
| Turo Guest Dispute | $29 | $24.46 | $18.66 | $17.21 | $15.76 |
| CCPA Action Kit | $29 | $24.46 | $18.66 | $17.21 | $15.76 |

---

## 3. RECOMMENDED COMMISSION: **30%**

Within Gumroad's documented 1–75% range for "Your Affiliates".

Why 30% and not more:
- It leaves **$87.70** on a $155 sale — above the factory's own $70 elite floor, so the product stays profitable *after* the affiliate is paid.
- It is a round, credible number for a B2B compliance product, where the buyer is spending to avoid a regulatory penalty, not on a whim.
- Anything above ~40% starts competing with Gumroad's own pricing logic for no proven gain, and this factory has **zero** affiliate-attributed sales to justify a premium rate.

Why not Gumroad Affiliates (the self-serve 10%): that track pays a **fixed 10%** and is for people promoting *any* Discover product. It is not a negotiated rate and gives no per-product control.

---

## 4. IS THERE AN API FOR THIS? **NO.**

Per Gumroad's official API documentation:

- **Documented scopes:** `account`, `view_profile`, `view_sales`, `view_payouts`, `edit_sales`
- **Documented resources:** Products, Sales, Subscribers, License Keys, Offer Codes, Resource subscriptions (webhooks), authenticated user

**There is no affiliate scope and no affiliate endpoint.** The affiliate dashboard is documented as a user-interface surface ("in the main sidebar, under Analytics").

> **Conclusion: affiliate configuration is a manual Gumroad UI action. It cannot be done through this factory's API integration, and this report does not claim otherwise.**

---

## 5. THE CURRENT LINKS EARN NOTHING AS AFFILIATE COMMISSIONS

The catalog's 53 product links carry:

```
?ref=galaxyforge_products&referrer=c99_catalog
```

`ref=` on a link pointing at **our own storefront is self-attribution.** Gumroad's own affiliate FAQ is explicit about the mechanism:

> *"Sticky affiliate links: `https://gumroad.com/l/:product_permalink?affiliate_id=<affiliate_id>`"*
> *"the only way you can be credited for your affiliate sales is if you share your affiliate links… **We can't credit you for the sale if you accidentally share a product link.**"*

So the existing `ref=` parameters produce **zero commission**. They are analytics labels, not affiliate links. **They have been left in place** — removing them would destroy the existing `referrer` attribution for no commercial gain, and the directive did not ask for a site-wide rewrite.

---

## 6. FOUNDER SETUP — MANUAL, AND NOT YET DONE

**Nothing below has been performed. I have no affiliate API and no write authority.**

> **Rotation is NOT a prerequisite for any of this.** An earlier draft implied it was. That was wrong, and the reason is mechanical: `UNVERIFIED_COMPROMISED` blocks **API writes** (publish, product update, distribution) only. Every operation this task needs — add affiliate, set rate, read the link — is **UI-only because no affiliate API exists**. The gate does not touch it. Token rotation remains sensible hygiene, but it is not on the critical path. See §11.

1. Open **https://gumroad.com/settings/affiliates** (Affiliates Dashboard, in the sidebar under **Analytics**).
2. **Add affiliate** → enter the affiliate's **Gumroad account email**.
3. Select **only** the product named *"EU AI Act Compliance Toolkit — Practical Templates & Implementation Guide for SMEs"* (ID `pzTmMb4v8cih3nbWTj5TeA==`, $155). Do **not** select "All products" — three other "EU AI Act" listings exist at $29, $19 and $9, and none can absorb a 30% commission.
4. Set the commission to **30%**.
5. Click **Copy Link** and send it to the affiliate.

Gumroad then emails the affiliate their link. Do not hand-craft an `affiliate_id` URL; a copied link is the one that credits.

**Note the cookie difference** (official): seller-added affiliates get a **30-day** cookie; the self-serve Gumroad Affiliates program gets 7 days. Seller-added is the better choice here.

---

## 7. THE INVITATION — PREPARED, NOT SENT

> **Subject:** 30% commission — EU AI Act compliance toolkit (deadline-driven)
>
> Hi [name],
>
> I built the **EU AI Act Compliance Toolkit** — 31 pages of implementation templates and reference material for EU SMEs who need to evidence AI Act compliance, built from the regulation's own text.
>
> One thing worth flagging, because most material on this is still wrong: the high-risk obligations were **deferred to 2 December 2027** (Annex I systems to 2 August 2028) by the 2026 Digital Omnibus. The "2 August 2026" date in circulation is superseded. The toolkit states the current dates and says plainly that the amendments were provisionally agreed and pending final adoption.
>
> I also have to be straight with you: **I have zero sales and zero reviews on it.** I'm not going to dress that up. What I can tell you is exactly what is in the file — page count, contents, and the sources it cites — and you can judge it before you say anything about it.
>
> **30% commission on every sale**, paid by Gumroad on their normal payout schedule. There is a 30-day attribution window.
>
> If it isn't useful, say no — no follow-up, no pressure.
>
> [Product link — Gumroad-issued affiliate link goes here]

**Deliberately included:** the 0-sales disclosure, the reason it is still worth a look, and an explicit easy exit. Inflating the offer or hiding the track record would poison the only channel whose entire value is trust.

---

## 8. FREE CHANNELS THAT ARE LEGITIMATE AND AVAILABLE

| Channel | Status here | Note |
|---|---|---|
| **Gumroad Discover** | Available | But 30% flat fee — use only if a direct link is impossible. |
| **LinkedIn** | `channels/linkedin_publisher.py` exists | **No credential in `.env` — unverified, do not assume working.** |
| **X** | `X_ACCESS_TOKEN` set | **BLOCKED — real 402 `credits depleted`. Posting costs money. Not available at $0.** |
| **Nostr** | Module exists | **Not runnable — `nostr_direct.py` missing.** 20 historical posts → 0 replies, 1 relay spam-blocked. Exhausted. |
| **Own audience / email** | — | The only channel with proven conversion. Not yet built. |
| **Gumroad Affiliates sign-up form** | Manual | Lets unknown affiliates request affiliation without you recruiting them. **Cheapest available lever — $0, no outreach required.** |

**The last row is the recommended first move.** It requires no message, no list, and no permission — affiliates come to the product. Set the form up alongside the 30% rate and it works while nobody is doing anything.

---

## 9. PROOF RULES OBSERVED

- No affiliate link was created — only the seller can, in the UI.
- No message was sent. No external contact was made.
- No price, payout setting, account field or product was modified.
- No commission is claimed, because none has been earned. `VERIFIED_REVENUE` remains `$0.00`.
- A prepared invitation is **not** a distributed one. A HTTP 200 IndexNow receipt is **not** a visit.

---

## 10. VERIFICATION — WHAT IS AND IS NOT CHECKABLE

`scripts/cycle85_verify_affiliate.py` (read-only, $0) checks four things automatically:

1. **Has the token been rotated?** Compares the live fingerprint against the recorded one.
2. **Is the credential still live?** Real read against the Gumroad API.
3. **Has the write gate opened?** Off `UNVERIFIED_COMPROMISED`.
4. **Is the target product live and still $155?** Matched by product ID, not by name.

Current result: **2 PASS, 2 FAIL.** Checks 2 and 4 pass (credential live; product `pzTmMb4v8cih3nbWTj5TeA==` published at $155, 0 sales). Checks 1 and 3 fail because **the token has not been rotated yet** — still fingerprint `6c2e73f2…`.

Because there is no affiliate API, five things **cannot** be verified from here and must be read off the Gumroad UI — including the crucial one: **only a real completed purchase proves commission will be paid.** A resolving link, a set 30% rate, and a 200 response all prove only that setup happened.

Run it after rotating:

```
python scripts/cycle85_verify_affiliate.py
```

It exits non-zero until every verifiable check passes.

---

## 11. WHAT THE VERIFICATION ACTUALLY SHOWS (corrected)

The first version of this package reported a binary FAIL on "token rotated" and "write gate". **Both were wrong.**

**Stale-evidence bug.** It read `data/gumroad_auth_state.json`, last written 2026-10-13. Rotation could have happened and it would still have said FAIL, because nothing refreshes that file unless `poll()` is called. It now calls `poll()` live.

**Wrong gate.** It presented rotation as blocking this task. It does not. `UNVERIFIED_COMPROMISED` blocks API writes only, and this task uses none.

**The exposure evidence is unverifiable.** `scripts/audit_credential_exposure.py` searched the full git history and found **no artefact anywhere in this repository showing the credential was ever written down**. The block rests on a claim about a past session's console output that cannot be checked from here. That does not prove the token is safe — a secret shown in a terminal is exposed without ever touching the repo — but it does mean rotation is **prudent hygiene, not a proven incident**, and the report must not say it is.

### Corrected result

| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | Credential live | **PASS** | real API read returned |
| 2 | Target product identity + price | **PASS** | `pzTmMb4v8cih3nbWTj5TeA==`, published, $155, `/l/iaiyt`, 0 sales |
| 3 | Commission paid so far | **PASS** (zero) | 0 sales / $0.00 across all 79 products |
| 4 | Live credential state | **ADVISORY** | `UNVERIFIED_COMPROMISED` — hygiene, not a gate |
| 5 | Commission observability | **UNKNOWN** | no affiliate field exists in any of 35 product fields |
| 6–11 | Affiliate row, rate, eligibility, sibling exclusion, link, first credit | **BLOCKED** | all UI-only; no API exists |

**No check FAILED. The channel is unconfigured, not broken.** Commission is not claimed because no affiliate exists and no sale has ever completed. `VERIFIED_REVENUE` remains `$0.00`.

---

## 12. THE FREE COMMERCIAL STEP — MARKETER ATTRACTION PATH (prepared, not launched)

### What live search actually found

Every target below surfaced from a real search on 2026-10-14. No personas were invented. Full evidence in `data/cycle85_affiliate_targets.json`.

| Target | URL | What they do | Fit |
|---|---|---|---|
| aiacto | aiacto.eu | Free SME compliance checklists | **HIGH** — free content, named audience needs a concrete pack |
| Regulation AI | regulation-ai.eu | Free newsletter + paid Academy | MEDIUM — monetises same audience |
| Khairos AI | khairos.ai | 60+ free guides + consulting | MEDIUM — sells service, not document |
| electe.net | electe.net | Free SME guide | MEDIUM |
| AiComply | aicomplyapp.eu | Free checker → €199 report | **LOW** — direct competitor |
| EU AI Compliance Institute | euaicomplianceinstitute.eu | Free resources + subscription | **LOW** — direct competitor |

### The finding that changes the pitch

**Almost the entire niche publishes this material free.** Leading with "$155 and a deadline" fails on first contact, because every one of these targets already publishes deadline content for free.

The only segment with an un-met need is **consultants who need a client-facing deliverable**. Regulation AI names that segment explicitly in its own audience description. For them $155 is a cost of doing business, not an information purchase — and $46.50 is worth the send.

**Independent bonus:** the search also **corroborated the product's corrected deadline** against three unrelated sources (euai-act.com, aicomplyapp.eu, regulation-ai.eu), all agreeing high-risk obligations moved to 2 Dec 2027 under Regulation (EU) 2026/1744. The claim this factory corrected before ever selling is now confirmed beyond its own research.

### What was built (free, launchable)

`customer_site/affiliate-program.html` — the recruitment page, in the house design system, stating the offer, the free-competition warning, and the zero-sales position openly.

**Nothing was sent.** No invitation, no email, no DM, no post. The page exists and is not published to an audience until you say so.
