#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only portfolio overlay over the existing affiliate systems.

This module adds no second opportunity engine and writes no ledger. It reuses
commission_engine's portfolio/freshness rules, affiliate.registry's status
derivation, and affiliate.content_qa's mechanical checks.

The payout question is deliberately a tri-state model:

- VERIFIED: current, authoritative evidence supports the route for Algeria.
  This is route-level evidence, not an account-level guarantee; an unconfirmed
  account is always reported separately and never hidden inside VERIFIED.
  No row currently meets this bar: the only candidate route (DigitalOcean ->
  Awin -> Payoneer) is not confirmed for Algeria by Awin or Payoneer.
- CONDITIONAL: a plausible route exists, but a named requirement, rail, or
  account condition is unresolved.
- UNKNOWN: there is no current, sufficient Algeria-specific evidence. UNKNOWN
  is never treated as a rejection and never promoted to VERIFIED by inference.

The register joins 22 existing program records (17 primary records plus five
secondary candidates) and six researched candidates with four owned
purchase-intent assets, producing a 32-row planning register with 26 affiliate
candidates. Nothing here is an approval, a link, a sale, or an eligibility
guarantee.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import commission_engine as ce
from affiliate import registry as program_registry
from affiliate.content_qa import qa_content

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
_CUSTOMER_SITE = _FACTORY_ROOT / "customer_site"

FAMILIES = (
    "SAAS",
    "AI_AUTOMATION",
    "ECOMMERCE",
    "CREATOR_PUBLISHING",
    "INFRASTRUCTURE",
    "PURCHASE_INTENT_RESEARCH",
)

CANDIDATE_REQUIRED_FIELDS = (
    "opportunity_id",
    "family",
    "target_audience",
    "customer_problem",
    "solution",
    "official_url",
    "evidence_sources",
    "evidence_timestamp",
    "application_status",
    "commission_model",
    "commission_terms",
    "attribution_terms",
    "publisher_eligibility",
    "payout_state",
    "payout_route",
    "payout_gaps",
    "demand_evidence",
    "competition",
    "differentiation",
    "effort",
    "distribution",
    "zero_cost_validation",
    "risks",
    "freshness",
    "confidence",
    "next_action",
    "disposition",
    "activation_status",
)

CANDIDATE_DISPOSITIONS = ("RESEARCH", "CONDITIONAL", "HOLD", "REJECTED")

PROGRAM_FAMILY = {
    "CO-amazon-affiliate": "ECOMMERCE",
    "CO-gumroad-affiliate": "CREATOR_PUBLISHING",
    "CO-gumroad-marketplace": "ECOMMERCE",
    "CO-paddle-partnership": "SAAS",
    "CO-etsy-affiliate": "ECOMMERCE",
    "CO-etsy-marketplace": "ECOMMERCE",
    "CO-creative_market-affiliate": "CREATOR_PUBLISHING",
    "CO-envato-affiliate": "CREATOR_PUBLISHING",
    "CO-adobe-affiliate": "AI_AUTOMATION",
    "CO-google-affiliate": "SAAS",
    "CO-canva-affiliate": "AI_AUTOMATION",
    "CO-zapier-affiliate": "AI_AUTOMATION",
    "CO-n8n-affiliate": "AI_AUTOMATION",
    "CO-digitalocean-affiliate": "INFRASTRUCTURE",
    "CO-brevo-affiliate": "SAAS",
    "CO-aweber-affiliate": "SAAS",
    "CO-siteground-affiliate": "INFRASTRUCTURE",
    "CO-hubspot-affiliate": "SAAS",
    "CO-shopify-affiliate": "ECOMMERCE",
    "CO-baremetrics-affiliate": "SAAS",
    "CO-hostaway-affiliate": "ECOMMERCE",
    "CO-lemsubs-affiliate": "SAAS",
    "CO-systeme-affiliate": "AI_AUTOMATION",
    "CO-semrush-affiliate": "SAAS",
    "CO-kit-affiliate": "SAAS",
    "CO-clickfunnels-affiliate": "SAAS",
    "CO-teachable-affiliate": "CREATOR_PUBLISHING",
    "CO-hostinger-affiliate": "INFRASTRUCTURE",
}

GUIDE_BY_PROGRAM = {
    "CO-adobe-affiliate": "guide-adobe-affiliate.html",
    "CO-amazon-affiliate": "guide-amazon-associates-affiliate.html",
    "CO-brevo-affiliate": "guide-brevo-affiliate-program.html",
    "CO-canva-affiliate": "guide-canva-affiliate.html",
    "CO-creative_market-affiliate": "guide-creative-market-affiliate.html",
    "CO-digitalocean-affiliate": "guide-digitalocean-affiliate-program.html",
    "CO-envato-affiliate": "guide-envato-affiliate.html",
    "CO-etsy-affiliate": "guide-etsy-affiliate.html",
    "CO-google-affiliate": "guide-google-workspace-affiliate.html",
    "CO-gumroad-affiliate": "guide-gumroad-affiliate.html",
    "CO-n8n-affiliate": "guide-n8n-affiliate.html",
    "CO-siteground-affiliate": "guide-siteground-affiliate-program.html",
    "CO-zapier-affiliate": "guide-zapier-affiliate.html",
}

PAYOUT_VERIFIED = "VERIFIED"
PAYOUT_CONDITIONAL = "CONDITIONAL"
PAYOUT_UNKNOWN = "UNKNOWN"
PAYOUT_NOT_APPLICABLE = "NOT_APPLICABLE"
PAYOUT_STATES = (PAYOUT_VERIFIED, PAYOUT_CONDITIONAL, PAYOUT_UNKNOWN)
PAYOUT_MAX_EVIDENCE_AGE_DAYS = 90

# Backward-compatible names for existing internal callers. The old
# COMPATIBLE/INCOMPATIBLE vocabulary is deliberately retired: neither word is
# an honest substitute for route-level VERIFIED or missing-evidence UNKNOWN.
ALGERIA_COMPATIBLE = PAYOUT_VERIFIED
ALGERIA_CONDITIONAL = PAYOUT_CONDITIONAL
ALGERIA_UNKNOWN = PAYOUT_UNKNOWN
ALGERIA_NOT_APPLICABLE = PAYOUT_NOT_APPLICABLE

_PAYPAL_CONDITIONAL_MARKERS = (
    "requires a paypal account",
    "paypal account is required",
    "need a paypal account",
    "paypal standard",
    "via paypal only",
    "paypal only",
)

# Structured evidence for the only rows with a real Algeria-specific payout
# review. This is overlay annotation, not a second program registry: the
# authoritative program facts still come from data/commission_opportunities.jsonl.
_PAYOUT_EVIDENCE = {
    "CO-digitalocean-affiliate": {
        "state": PAYOUT_CONDITIONAL,
        "scope": "country_rail_unconfirmed",
        "account_level_verified": False,
        "publisher_country": "DZ",
        "payout_route": "DigitalOcean -> Awin -> Payoneer",
        "checked_at": "2026-10-21",
        "official_sources": [
            "https://www.digitalocean.com/affiliates",
            "https://www.digitalocean.com/legal/affiliate-program-agreement",
            "https://ui.awin.com/merchant-profile/123996",
            "https://success.awin.com/s/article/When-will-I-receive-payment?language=en_US",
            "https://success.awin.com/articles/en_US/Knowledge/Payoneer-for-Awin-Publishers-FAQs",
        ],
        "conditions": [
            "Awin publisher account required",
            "Payoneer account must be created from Awin, not linked from an existing account",
            "tax documentation required",
            "USD 20 network minimum",
            "payments processed on the 1st and 15th",
        ],
        "gaps": [
            "Payoneer's Algeria payout capability is not confirmed",
            "account-level eligibility is not confirmed",
            "Awin account is not created",
            "Payoneer link is not created from Awin",
            "exact tax form is not confirmed",
        ],
        "reason": (
            "DigitalOcean's official affiliate page routes to Awin merchant 123996; "
            "Awin's official publisher help documents Payoneer payouts, a USD 20 "
            "minimum, and the 1st/15th schedule. Awin does not confirm Algeria: it "
            "directs publishers to Payoneer's Capabilities Map, and Payoneer does "
            "not publish a public country list. The route is identified; Algeria "
            "receive eligibility and the founder's account remain unconfirmed."
        ),
    },
    "CO-aweber-affiliate": {
        "state": PAYOUT_CONDITIONAL,
        "scope": "program_specific_rail_unconfirmed",
        "account_level_verified": False,
        "publisher_country": "DZ",
        "payout_route": "AWeber -> PayPal (USD)",
        "checked_at": "2026-10-21",
        "official_sources": [
            "https://www.aweber.com/advocates.htm",
            "https://docs.aweber.com/aweber-advocate-program/faq-customer-referral-program/how-do-i-get-paid",
            "https://www.paypal.com/dz/legalhub/paypal/recpymt-full",
        ],
        "conditions": [
            "PayPal is the recorded payout method",
            "USD 30 US / USD 50 non-US threshold",
            "PayPal Algeria receiving requires a linked US bank or Visa",
            "30-day hold and withdrawal-only balance use",
        ],
        "gaps": [
            "AWeber's program-specific Algeria rail is not confirmed",
            "PayPal account-level eligibility is not confirmed",
            "the linked US bank/Visa requirement is not resolved",
        ],
        "reason": (
            "AWeber documents PayPal payouts, and PayPal's Algeria receive "
            "agreement lists Algeria only conditionally. The exact AWeber/Algeria "
            "rail and account eligibility are unresolved."
        ),
    },
    "CO-siteground-affiliate": {
        "state": PAYOUT_CONDITIONAL,
        "scope": "program_specific_rail_unconfirmed",
        "account_level_verified": False,
        "publisher_country": "DZ",
        "payout_route": "SiteGround -> PayPal or wire",
        "checked_at": "2026-10-21",
        "official_sources": [
            "https://www.siteground.com/affiliates",
            "https://www.paypal.com/dz/legalhub/paypal/recpymt-full",
        ],
        "conditions": [
            "PayPal standard for low-volume publishers",
            "wire transfer is listed for high-volume publishers",
            "PayPal Algeria receiving requires a linked US bank or Visa",
            "30-day hold and withdrawal-only balance use",
        ],
        "gaps": [
            "SiteGround's program-specific Algeria rail is not confirmed",
            "wire eligibility for a new low-volume Algeria publisher is not confirmed",
            "PayPal account-level eligibility is not confirmed",
        ],
        "reason": (
            "SiteGround lists PayPal and high-volume wire payouts. PayPal's "
            "Algeria receive agreement is conditional, and the wire path is not "
            "verified for a new Algeria publisher."
        ),
    },
    "CO-n8n-affiliate": {
        "state": PAYOUT_CONDITIONAL,
        "scope": "program_specific_rail_unconfirmed",
        "account_level_verified": False,
        "publisher_country": "DZ",
        "payout_route": "n8n -> PartnerStack -> PayPal",
        "checked_at": "2026-10-21",
        "official_sources": [
            "https://n8n.io/affiliates/",
            "https://market.partnerstack.com/page/n8n",
            "https://www.paypal.com/dz/legalhub/paypal/recpymt-full",
        ],
        "conditions": [
            "n8n FAQ requires a PayPal account",
            "monthly payouts with a EUR 100 minimum",
            "PartnerStack also lists Stripe and other methods, which conflicts with the FAQ",
            "PayPal Algeria receiving requires a linked US bank or Visa",
        ],
        "gaps": [
            "the exact n8n/PartnerStack Algeria rail is not confirmed",
            "the PayPal-vs-Stripe conflict is unresolved",
            "account-level eligibility is not confirmed",
        ],
        "reason": (
            "n8n's affiliate FAQ requires PayPal; PartnerStack's directory also "
            "lists alternatives. PayPal's Algeria route is conditional, so no "
            "single rail is verified."
        ),
    },
    "CO-systeme-affiliate": {
        "state": PAYOUT_CONDITIONAL,
        "scope": "program_specific_rail_unconfirmed",
        "account_level_verified": False,
        "publisher_country": "DZ",
        "payout_route": "systeme.io -> PayPal or wire",
        "checked_at": "2026-10-21",
        "official_sources": [
            "https://systeme.io/affiliate-program",
            "https://systeme.io/affiliate-agreement",
            "https://www.paypal.com/dz/legalhub/paypal/recpymt-full",
        ],
        "conditions": [
            "PayPal or wire transfer",
            "USD 30 minimum",
            "monthly payouts on the 10th",
            "PayPal Algeria receiving is conditional",
        ],
        "gaps": [
            "systeme.io's Algeria-specific wire eligibility is not confirmed",
            "PayPal account-level eligibility is not confirmed",
            "the linked US bank/Visa requirement is not resolved",
        ],
        "reason": (
            "systeme.io documents PayPal or wire payouts and a USD 30 minimum. "
            "PayPal's Algeria route is conditional; the wire route is not confirmed "
            "for an Algeria publisher."
        ),
    },
    "CO-semrush-affiliate": {
        "state": PAYOUT_CONDITIONAL,
        "scope": "program_specific_rail_unconfirmed",
        "account_level_verified": False,
        "publisher_country": "DZ",
        "payout_route": "Semrush -> Impact -> EFT or PayPal",
        "checked_at": "2026-10-21",
        "official_sources": [
            "https://www.semrush.com/lp/affiliate-program/en/",
            "https://www.semrush.com/kb/97-affiliate-program",
            "https://www.paypal.com/dz/legalhub/paypal/recpymt-full",
        ],
        "conditions": [
            "Impact network payout",
            "EFT or PayPal",
            "120-day cookie",
            "monetary commissions are per sale/trial",
        ],
        "gaps": [
            "Impact's Algeria payout availability is not confirmed",
            "PayPal account-level eligibility is not confirmed",
            "the exact EFT rail and fees are not confirmed",
        ],
        "reason": (
            "Semrush documents Impact payouts via EFT or PayPal. Neither route has "
            "been confirmed for Algeria at the account level."
        ),
    },
    "CO-kit-affiliate": {
        "state": PAYOUT_CONDITIONAL,
        "scope": "program_specific_rail_unconfirmed",
        "account_level_verified": False,
        "publisher_country": "DZ",
        "payout_route": "Kit -> PartnerStack -> direct deposit, PayPal, or Stripe",
        "checked_at": "2026-10-21",
        "official_sources": [
            "https://kit.com/affiliate",
            "https://help.kit.com/en/articles/2502522-getting-started-as-a-kit-affiliate",
            "https://www.paypal.com/dz/legalhub/paypal/recpymt-full",
        ],
        "conditions": [
            "PartnerStack withdrawal setup",
            "direct deposit, PayPal, or Stripe depending on location",
            "USD 5 minimum",
            "commissions generated after a 31-day refund window",
        ],
        "gaps": [
            "PartnerStack's Algeria payout options are not confirmed",
            "account-level eligibility is not confirmed",
            "the PayPal linked US bank/Visa condition is unresolved",
        ],
        "reason": (
            "Kit's help page says PartnerStack payout options depend on location and "
            "include direct deposit, PayPal, or Stripe. No Algeria-specific option is "
            "confirmed."
        ),
    },
    "CO-clickfunnels-affiliate": {
        "state": PAYOUT_CONDITIONAL,
        "scope": "program_specific_rail_unconfirmed",
        "account_level_verified": False,
        "publisher_country": "DZ",
        "payout_route": "ClickFunnels -> Tipalti -> PayPal, check, ACH, or wire",
        "checked_at": "2026-10-21",
        "official_sources": [
            "https://support.clickfunnels.com/en/articles/12734155-affiliate-tiers-for-the-clickfunnels-affiliate-program",
            "https://support.myclickfunnels.com/docs/getting-started-with-clickfunnels-affiliate-program/",
            "https://www.paypal.com/dz/legalhub/paypal/recpymt-full",
        ],
        "conditions": [
            "Tipalti account and tax form",
            "USD 100 minimum",
            "45-day cooling-off period",
            "PayPal is the preferred recorded method",
        ],
        "gaps": [
            "Tipalti's Algeria payout availability is not confirmed",
            "PayPal account-level eligibility is not confirmed",
            "wire or international ACH eligibility is not confirmed",
        ],
        "reason": (
            "ClickFunnels documents Tipalti payouts with several international "
            "methods. No method has been confirmed as receivable by an Algeria "
            "publisher."
        ),
    },
    "CO-teachable-affiliate": {
        "state": PAYOUT_CONDITIONAL,
        "scope": "program_specific_rail_unconfirmed",
        "account_level_verified": False,
        "publisher_country": "DZ",
        "payout_route": "Teachable -> PartnerStack",
        "checked_at": "2026-10-21",
        "official_sources": [
            "https://www.teachable.com/partners",
            "https://support.teachable.com/en/articles/11682547-affiliate-sales-commission-and-payouts",
        ],
        "conditions": [
            "PartnerStack account",
            "30% recurring for the first year",
            "30-day cookie",
            "payout methods are not specified for Algeria",
        ],
        "gaps": [
            "Teachable/PartnerStack's Algeria payout rail is not confirmed",
            "account-level eligibility is not confirmed",
        ],
        "reason": (
            "Teachable documents PartnerStack but does not specify an Algeria payout "
            "method. The route is plausible, not verified."
        ),
    },
    "CO-hostinger-affiliate": {
        "state": PAYOUT_CONDITIONAL,
        "scope": "program_specific_rail_unconfirmed",
        "account_level_verified": False,
        "publisher_country": "DZ",
        "payout_route": "Hostinger -> PayPal or wire",
        "checked_at": "2026-10-21",
        "official_sources": [
            "https://www.hostinger.com/legal/affiliate-program-agreement",
            "https://www.hostinger.com/support/1583263-how-are-affiliate-commissions-paid-at-hostinger/",
            "https://www.paypal.com/dz/legalhub/paypal/recpymt-full",
        ],
        "conditions": [
            "USD 100 minimum for PayPal",
            "USD 500 minimum for wire",
            "3 approved conversions required",
            "30-day money-back guarantee before commission",
        ],
        "gaps": [
            "Hostinger's Algeria-specific eligibility is not confirmed",
            "PayPal account-level eligibility is not confirmed",
            "wire eligibility is not confirmed",
        ],
        "reason": (
            "Hostinger documents PayPal and bank transfer thresholds. Neither route "
            "is confirmed for an Algeria publisher, and PayPal's Algeria conditions "
            "remain unresolved."
        ),
    },
}

_CANDIDATE_RESEARCH = {
    "CO-digitalocean-affiliate": {
        "target_audience": "Developers, startups, and small engineering teams choosing cloud infrastructure",
        "customer_problem": "Cloud hosting cost and operating complexity when moving from prototype to production",
        "solution": "A technical guide comparing DigitalOcean's developer-focused cloud path against alternatives",
        "demand_evidence": "UNKNOWN -- no measured search, click, or purchase-intent data yet",
        "competition": "UNKNOWN -- no competitor-content audit recorded",
        "differentiation": "Only register row with a documented program-specific payout route; Algeria capability unconfirmed",
        "effort": "LOW_MEDIUM -- official terms are captured; a guide already exists",
        "distribution": "Owned guide plus technical content surface; no live link",
        "zero_cost_validation": "Read the official terms and check one real demand query without creating an account",
        "risks": "Awin account, Payoneer created from Awin, tax form, and account-level eligibility remain unresolved",
        "confidence": "MEDIUM",
        "next_action": "Founder decides whether to apply to DigitalOcean via Awin; then prepare the application packet",
    },
    "CO-n8n-affiliate": {
        "target_audience": "Technical automation builders and small operations teams",
        "customer_problem": "Workflow automation that is hard to self-host, integrate, or maintain",
        "solution": "A practical n8n automation checklist with an honest payout and setup disclosure",
        "demand_evidence": "UNKNOWN -- no measured search, click, or purchase-intent data yet",
        "competition": "UNKNOWN -- no competitor-content audit recorded",
        "differentiation": "Strong product-content fit and a real guide, but the payout rail is unresolved",
        "effort": "LOW -- official terms and a draft checklist already exist",
        "distribution": "Owned guide plus automation content surface; no live link",
        "zero_cost_validation": "Read the official FAQ and PartnerStack terms, then record the unresolved rail without applying",
        "risks": "PayPal-only requirement, PartnerStack conflict, and Algeria account conditions",
        "confidence": "LOW",
        "next_action": "Keep in research; do not add a CTA until the program-specific Algeria rail is confirmed",
    },
    "CO-aweber-affiliate": {
        "target_audience": "Small businesses, creators, and coaches choosing email marketing",
        "customer_problem": "Email marketing setup, deliverability, and list growth for small teams",
        "solution": "An evidence-first AWeber advocate guide with a conditional-payout disclosure",
        "demand_evidence": "UNKNOWN -- no measured search, click, or purchase-intent data yet",
        "competition": "UNKNOWN -- no competitor-content audit recorded",
        "differentiation": "Existing guide and a named conditional rail; no CTA until resolved",
        "effort": "LOW -- official terms are captured",
        "distribution": "Owned guide; no live link",
        "zero_cost_validation": "Read the official payout FAQ and PayPal Algeria terms without creating an account",
        "risks": "PayPal-only rail, linked US bank/Visa requirement, 30-day hold, and withdrawal-only balance",
        "confidence": "LOW",
        "next_action": "Hold the CTA; resolve the AWeber/PayPal Algeria route before producing more content",
    },
    "CO-siteground-affiliate": {
        "target_audience": "Small businesses and creators choosing web hosting",
        "customer_problem": "Hosting reliability, speed, and support for a small online presence",
        "solution": "A hosting-selection guide with an explicit conditional-payout disclosure",
        "demand_evidence": "UNKNOWN -- no measured search, click, or purchase-intent data yet",
        "competition": "UNKNOWN -- no competitor-content audit recorded",
        "differentiation": "Existing guide and a named conditional rail; no CTA until resolved",
        "effort": "LOW -- official terms are captured",
        "distribution": "Owned guide; no live link",
        "zero_cost_validation": "Read the official affiliate page and PayPal Algeria terms without creating an account",
        "risks": "PayPal standard, high-volume-only wire, and unresolved account eligibility",
        "confidence": "LOW",
        "next_action": "Hold the CTA; verify a program-specific Algeria payout path first",
    },
    "CO-brevo-affiliate": {
        "target_audience": "Small businesses and creators choosing email and CRM tooling",
        "customer_problem": "Fragmented email, CRM, and automation tools for a small team",
        "solution": "An email-platform comparison with honest payout and eligibility gaps",
        "demand_evidence": "UNKNOWN -- no measured search, click, or purchase-intent data yet",
        "competition": "UNKNOWN -- no competitor-content audit recorded",
        "differentiation": "Existing guide; payout evidence is genuinely unresolved",
        "effort": "LOW -- official terms are captured",
        "distribution": "Owned guide; no live link",
        "zero_cost_validation": "Read the official program and payout pages without creating an account",
        "risks": "Algeria rail is UNKNOWN; do not create a CTA",
        "confidence": "LOW",
        "next_action": "Research the program-specific Algeria rail before any content investment",
    },
    "CO-amazon-affiliate": {
        "target_audience": "Online shoppers comparing practical home-office products",
        "customer_problem": "Choosing a standing desk converter without a trustworthy comparison",
        "solution": "A real product-data comparison page using the existing standing-desk dataset",
        "demand_evidence": "UNKNOWN -- no measured search, click, or purchase-intent data yet",
        "competition": "HIGH -- broad ecommerce comparison space",
        "differentiation": "Real product dataset and existing comparison surface",
        "effort": "LOW -- product data and page already exist",
        "distribution": "customer_site affiliate page; no live tag",
        "zero_cost_validation": "Reuse the existing product dataset and run a no-account content review",
        "risks": "24-hour cookie, 3-sale/180-day approval test, and unresolved Algeria payout",
        "confidence": "LOW",
        "next_action": "Keep as a content asset; do not claim affiliate attribution until a tag and payout path exist",
    },
    "CO-hubspot-affiliate": {
        "target_audience": "B2B SaaS and marketing teams evaluating CRM and automation",
        "customer_problem": "Connecting CRM, marketing, and recurring-revenue operations",
        "solution": "A CRM-fit guide with an explicit secondary-research caveat",
        "official_url": "https://www.hubspot.com/partners/affiliates",
        "demand_evidence": "UNKNOWN -- no measured search, click, or purchase-intent data yet",
        "competition": "UNKNOWN -- no competitor-content audit recorded",
        "differentiation": "Recurring commission model and direct SaaS-spend audience overlap",
        "effort": "MEDIUM -- official terms still need a direct-source re-read",
        "distribution": "Owned SaaS-spend content surface; no live link",
        "zero_cost_validation": "Re-read the official program terms and record the current rate without applying",
        "risks": "Secondary research only; payout and program-specific Algeria rail are unresolved",
        "confidence": "LOW",
        "next_action": "Verify the program at the official source before adding it to the research shortlist",
    },
    "CO-shopify-affiliate": {
        "target_audience": "Small businesses and creators choosing an ecommerce platform",
        "customer_problem": "Launching and running an online store without custom infrastructure",
        "solution": "An ecommerce-platform selection guide with an explicit payout caveat",
        "official_url": "https://help.shopify.com/en/affiliates/earnings",
        "demand_evidence": "UNKNOWN -- no measured search, click, or purchase-intent data yet",
        "competition": "UNKNOWN -- no competitor-content audit recorded",
        "differentiation": "Existing merchant intent surface, but payout evidence is unresolved",
        "effort": "MEDIUM -- official terms captured; no buyer-specific guide exists",
        "distribution": "Owned ecommerce content surface; no live link",
        "zero_cost_validation": "Read the official affiliate earnings page and payout terms without applying",
        "risks": "No current Algeria-specific payout evidence; do not add a CTA",
        "confidence": "LOW",
        "next_action": "Resolve the Algeria payout question before drafting a CTA or applying",
    },
    "CO-systeme-affiliate": {
        "target_audience": "Solo creators and small businesses building funnels, courses, and email lists",
        "customer_problem": "Assembling separate funnel, email, and course tools into one affordable workflow",
        "solution": "A funnel-stack comparison for creators, with an honest payout-route disclosure",
        "demand_evidence": "UNKNOWN -- no measured search, click, or purchase-intent data yet",
        "competition": "UNKNOWN -- no competitor-content audit recorded",
        "differentiation": "60% lifetime recurring and a real existing link record in the factory",
        "effort": "LOW -- official terms are captured and the link record already exists",
        "distribution": "Owned funnel/creator content surface; no live public CTA",
        "zero_cost_validation": "Re-read the official affiliate terms and payout page without creating a new account",
        "risks": "PayPal Algeria conditions and unconfirmed wire eligibility",
        "confidence": "LOW",
        "next_action": "Confirm the Algeria payout rail before adding a CTA; do not rotate the existing link without a founder decision",
    },
    "CO-semrush-affiliate": {
        "target_audience": "Marketers, SEO consultants, and small agencies",
        "customer_problem": "Search, content, and competitor research fragmented across too many tools",
        "solution": "An SEO-tool comparison with a clear evidence and payout disclosure",
        "demand_evidence": "UNKNOWN -- no measured search, click, or purchase-intent data yet",
        "competition": "HIGH -- established SEO affiliate content space",
        "differentiation": "High per-sale commission and a long 120-day attribution window",
        "effort": "MEDIUM -- requires a current direct re-read and a credible SEO content surface",
        "distribution": "Owned marketing/SEO content surface; no live link",
        "zero_cost_validation": "Re-read the official program page and Impact payout terms without applying",
        "risks": "Impact's Algeria payout availability and PayPal conditions are unresolved",
        "confidence": "LOW",
        "next_action": "Verify Impact payout eligibility for Algeria before content investment",
    },
    "CO-kit-affiliate": {
        "target_audience": "Creators and small publishers building email newsletters",
        "customer_problem": "Choosing an email platform that supports audience growth without high upfront cost",
        "solution": "A newsletter-platform comparison with a transparent payout caveat",
        "demand_evidence": "UNKNOWN -- no measured search, click, or purchase-intent data yet",
        "competition": "UNKNOWN -- no competitor-content audit recorded",
        "differentiation": "50% first-year commission plus a real recurring tier",
        "effort": "MEDIUM -- official terms are captured; a buyer-specific guide does not exist",
        "distribution": "Owned creator/newsletter content surface; no live link",
        "zero_cost_validation": "Re-read the official program and PartnerStack withdrawal help without applying",
        "risks": "PartnerStack's Algeria payout options are not confirmed",
        "confidence": "LOW",
        "next_action": "Resolve the PartnerStack Algeria payout question before drafting a CTA",
    },
    "CO-clickfunnels-affiliate": {
        "target_audience": "Funnel builders, course creators, and small marketing teams",
        "customer_problem": "Building and maintaining a conversion funnel without a dedicated developer",
        "solution": "A funnel-builder comparison with an explicit Tipalti payout caveat",
        "demand_evidence": "UNKNOWN -- no measured search, click, or purchase-intent data yet",
        "competition": "HIGH -- crowded funnel-builder affiliate space",
        "differentiation": "30-40% commissions and a clear documented tier system",
        "effort": "MEDIUM -- official terms are captured; the space is competitive",
        "distribution": "Owned funnel/creator content surface; no live link",
        "zero_cost_validation": "Re-read the official support pages and Tipalti payout documentation without applying",
        "risks": "Tipalti's Algeria availability and the USD 100 threshold",
        "confidence": "LOW",
        "next_action": "Confirm Tipalti payout eligibility for Algeria before any content investment",
    },
    "CO-teachable-affiliate": {
        "target_audience": "Course creators and independent educators",
        "customer_problem": "Launching and monetizing an online course without building payment infrastructure",
        "solution": "A course-platform comparison with a transparent PartnerStack payout caveat",
        "demand_evidence": "UNKNOWN -- no measured search, click, or purchase-intent data yet",
        "competition": "UNKNOWN -- no competitor-content audit recorded",
        "differentiation": "30% recurring first-year commission and a real creator audience fit",
        "effort": "MEDIUM -- requires a current direct re-read before drafting",
        "distribution": "Owned creator/course content surface; no live link",
        "zero_cost_validation": "Re-read the partner page and help center without applying",
        "risks": "Teachable/PartnerStack's Algeria payout rail is not confirmed",
        "confidence": "LOW",
        "next_action": "Resolve the PartnerStack Algeria payout question before drafting a CTA",
    },
    "CO-hostinger-affiliate": {
        "target_audience": "Small businesses and creators launching a first website",
        "customer_problem": "Affordable, reliable hosting and website setup for a new online presence",
        "solution": "A first-website hosting guide with a clear payout-threshold disclosure",
        "demand_evidence": "UNKNOWN -- no measured search, click, or purchase-intent data yet",
        "competition": "HIGH -- crowded hosting affiliate space",
        "differentiation": "Up to 40% initial-purchase commission and a documented program",
        "effort": "LOW_MEDIUM -- official terms are captured; a guide does not exist",
        "distribution": "Owned hosting/small-business content surface; no live link",
        "zero_cost_validation": "Re-read the official agreement and payout support page without applying",
        "risks": "USD 100 PayPal / USD 500 wire thresholds and unconfirmed Algeria eligibility",
        "confidence": "LOW",
        "next_action": "Confirm the Algeria payout route before investing in a hosting guide",
    },
}


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [item for item in value if item]
    return [value]


def _first_url(opportunity):
    candidates = _as_list(opportunity.get("official_url"))
    candidates += _as_list(opportunity.get("terms_url"))
    candidates += _as_list(opportunity.get("evidence_url"))
    return candidates[0] if candidates else None


def _parse_iso_date(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _is_current(checked_at, now=None, max_age_days=PAYOUT_MAX_EVIDENCE_AGE_DAYS):
    checked = _parse_iso_date(checked_at)
    if checked is None:
        return False
    current = now or datetime.now(timezone.utc)
    if isinstance(current, datetime):
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
    else:
        current = datetime.combine(current, datetime.min.time(), tzinfo=timezone.utc)
    age_days = (current - checked).total_seconds() / 86400
    return 0 <= age_days <= max_age_days

_EXTRA_PROGRAMS = (
    {
        "opportunity_id": "CO-hubspot-affiliate",
        "program_name": "HubSpot affiliate",
        "partner_name": "HubSpot",
        "category": "affiliate",
        "commission_value": "30% recurring up to 1 year, 180-day cookie",
        "recurring_commission": True,
        "geography": "UNKNOWN",
        "payout_terms": "UNKNOWN",
        "verification_status": "SECONDARY_RESEARCH",
        "last_verified": "2026-09-22",
        "source": "data/opportunity_candidates.jsonl (AFF-hubspot-2026; affiliate.watch/MonsterClaw citation, no direct URL captured)",
    },
    {
        "opportunity_id": "CO-shopify-affiliate",
        "program_name": "Shopify affiliate",
        "partner_name": "Shopify",
        "category": "affiliate",
        "commission_value": "USD 25-150 per referred user, 30-day cookie",
        "recurring_commission": False,
        "geography": "UNKNOWN",
        "payout_terms": "UNKNOWN",
        "verification_status": "SECONDARY_RESEARCH",
        "last_verified": "2026-09-22",
        "source": "data/opportunity_candidates.jsonl (AFF-shopify-2026; affiliate.watch/VT Affiliates citation, no direct URL captured)",
    },
    {
        "opportunity_id": "CO-baremetrics-affiliate",
        "program_name": "Baremetrics affiliate",
        "partner_name": "Baremetrics",
        "category": "affiliate",
        "commission_value": "20% recurring for the lifetime of the referral, 60-day cookie",
        "recurring_commission": True,
        "geography": "UNKNOWN",
        "payout_terms": "UNKNOWN",
        "verification_status": "SECONDARY_RESEARCH",
        "last_verified": "2026-09-26",
        "evidence_url": "https://www.referly.so/affiliate-programs/baremetrics",
        "source": "data/partnership_pipeline.jsonl (research only; no signup, no outreach)",
    },
    {
        "opportunity_id": "CO-hostaway-affiliate",
        "program_name": "Hostaway affiliate",
        "partner_name": "Hostaway",
        "category": "affiliate",
        "commission_value": "20% monthly for 12 months",
        "recurring_commission": True,
        "geography": "UNKNOWN",
        "payout_terms": "UNKNOWN",
        "verification_status": "SECONDARY_RESEARCH",
        "last_verified": "2026-09-26",
        "evidence_url": "https://www.hostaway.com/affiliate-program",
        "source": "data/partnership_pipeline.jsonl (research only; no signup, no outreach)",
    },
    {
        "opportunity_id": "CO-lemsubs-affiliate",
        "program_name": "Lemsubs affiliate",
        "partner_name": "Lemsubs",
        "category": "affiliate",
        "commission_value": "25% recurring, 60-day cookie, no minimum payout",
        "recurring_commission": True,
        "geography": "UNKNOWN",
        "payout_terms": "UNKNOWN",
        "verification_status": "SECONDARY_RESEARCH",
        "last_verified": "2026-09-26",
        "evidence_url": "https://lemsubs.com/affiliate",
        "source": "data/partnership_pipeline.jsonl (research only; no signup, no outreach)",
    },
    {
        "opportunity_id": "CO-systeme-affiliate",
        "program_name": "systeme.io affiliate",
        "partner_name": "systeme.io",
        "category": "affiliate",
        "commission_value": "60% lifetime recurring; USD 30 minimum; monthly on the 10th",
        "recurring_commission": True,
        "geography": "Global; PayPal or wire transfer, Algeria rail unconfirmed",
        "payout_terms": "PayPal or wire transfer; USD 30 minimum; monthly on the 10th",
        "verification_status": "SECONDARY_RESEARCH",
        "last_verified": "2026-10-21",
        "terms_url": "https://systeme.io/affiliate-agreement",
        "evidence_url": [
            "https://systeme.io/affiliate-program",
            "https://systeme.io/affiliate-agreement",
        ],
        "source": "Official systeme.io affiliate page (WebSearch result, 2026-10-21); no account, no outreach",
    },
    {
        "opportunity_id": "CO-semrush-affiliate",
        "program_name": "Semrush affiliate",
        "partner_name": "Semrush",
        "category": "affiliate",
        "commission_value": "USD 100-300 per sale plus USD 10 per trial; 120-day cookie",
        "recurring_commission": False,
        "geography": "Global; Impact payout via EFT or PayPal, Algeria rail unconfirmed",
        "payout_terms": "Impact network; EFT or PayPal; transaction lock and payment after month end",
        "verification_status": "SECONDARY_RESEARCH",
        "last_verified": "2026-10-21",
        "terms_url": "https://www.semrush.com/kb/97-affiliate-program",
        "evidence_url": [
            "https://www.semrush.com/lp/affiliate-program/en/",
            "https://www.semrush.com/kb/97-affiliate-program",
        ],
        "source": "Official Semrush affiliate page (WebSearch result, 2026-10-21); no account, no outreach",
    },
    {
        "opportunity_id": "CO-kit-affiliate",
        "program_name": "Kit affiliate",
        "partner_name": "Kit (ConvertKit)",
        "category": "affiliate",
        "commission_value": "50% for the first 12 months, then 10-20% recurring at status; USD 5 minimum",
        "recurring_commission": True,
        "geography": "Global; PartnerStack payout options depend on location",
        "payout_terms": "PartnerStack; direct deposit, PayPal, or Stripe depending on location; USD 5 minimum",
        "verification_status": "SECONDARY_RESEARCH",
        "last_verified": "2026-10-21",
        "terms_url": "https://kit.com/affiliate",
        "evidence_url": [
            "https://kit.com/affiliate",
            "https://help.kit.com/en/articles/2502522-getting-started-as-a-kit-affiliate",
        ],
        "source": "Official Kit affiliate and help pages (WebSearch result, 2026-10-21); no account, no outreach",
    },
    {
        "opportunity_id": "CO-clickfunnels-affiliate",
        "program_name": "ClickFunnels affiliate",
        "partner_name": "ClickFunnels",
        "category": "affiliate",
        "commission_value": "30% starting rate; 40% at higher tiers; 45-day cookie",
        "recurring_commission": False,
        "geography": "Global; Tipalti payout options, Algeria rail unconfirmed",
        "payout_terms": "Tipalti; USD 100 minimum; paid on the 1st and 15th after a 45-day cooling-off period",
        "verification_status": "SECONDARY_RESEARCH",
        "last_verified": "2026-10-21",
        "terms_url": "https://support.clickfunnels.com/en/articles/12734155-affiliate-tiers-for-the-clickfunnels-affiliate-program",
        "evidence_url": [
            "https://support.clickfunnels.com/en/articles/12734155-affiliate-tiers-for-the-clickfunnels-affiliate-program",
            "https://support.myclickfunnels.com/docs/getting-started-with-clickfunnels-affiliate-program/",
        ],
        "source": "Official ClickFunnels support pages (WebSearch result, 2026-10-21); no account, no outreach",
    },
    {
        "opportunity_id": "CO-teachable-affiliate",
        "program_name": "Teachable affiliate",
        "partner_name": "Teachable",
        "category": "affiliate",
        "commission_value": "30% recurring for the first year; 30-day cookie",
        "recurring_commission": True,
        "geography": "Global; PartnerStack payout options, Algeria rail unconfirmed",
        "payout_terms": "PartnerStack; payout methods not specified for Algeria",
        "verification_status": "SECONDARY_RESEARCH",
        "last_verified": "2026-10-21",
        "terms_url": "https://www.teachable.com/partners",
        "evidence_url": [
            "https://www.teachable.com/partners",
            "https://support.teachable.com/en/articles/11682547-affiliate-sales-commission-and-payouts",
        ],
        "source": "Official Teachable partner and help pages (WebSearch result, 2026-10-21); no account, no outreach",
    },
    {
        "opportunity_id": "CO-hostinger-affiliate",
        "program_name": "Hostinger affiliate",
        "partner_name": "Hostinger",
        "category": "affiliate",
        "commission_value": "Up to 40% initial purchase; up to 60% AI Builder offers",
        "recurring_commission": False,
        "geography": "Global; PayPal or wire transfer, Algeria rail unconfirmed",
        "payout_terms": "USD 100 minimum for PayPal, USD 500 for wire; 3 approved conversions required",
        "verification_status": "SECONDARY_RESEARCH",
        "last_verified": "2026-10-21",
        "terms_url": "https://www.hostinger.com/legal/affiliate-program-agreement",
        "evidence_url": [
            "https://www.hostinger.com/legal/affiliate-program-agreement",
            "https://www.hostinger.com/support/1583263-how-are-affiliate-commissions-paid-at-hostinger/",
        ],
        "source": "Official Hostinger affiliate agreement and support page (WebSearch result, 2026-10-21); no account, no outreach",
    },
)

_OWNED_ASSETS = (
    {
        "opportunity_id": "PI-GPSR-ACTION-KIT",
        "program_name": "GPSR EU Seller Action Kit",
        "partner_name": "Galaxy Forge",
        "family": "PURCHASE_INTENT_RESEARCH",
        "category": "owned_product",
        "commission_value": "Direct product sale, USD 79 listed",
        "recurring_commission": False,
        "geography": "Global (Gumroad)",
        "payout_terms": "Gumroad seller payout; founder account",
        "verification_status": "OBSERVED",
        "last_verified": "2026-10-20",
        "evidence_url": "https://aekraft.gumroad.com/l/fetmu",
        "source": "data/catalog.json; 0 verified sales; traffic UNKNOWN",
        "algeria_payout": ALGERIA_NOT_APPLICABLE,
    },
    {
        "opportunity_id": "PI-SAAS-SPEND",
        "program_name": "SaaS Spend & Renewal Audit System for Small Teams",
        "partner_name": "Galaxy Forge",
        "family": "PURCHASE_INTENT_RESEARCH",
        "category": "owned_product",
        "commission_value": "Direct product sale, USD 49 listed",
        "recurring_commission": False,
        "geography": "Global (Gumroad)",
        "payout_terms": "Gumroad seller payout; founder account",
        "verification_status": "OBSERVED",
        "last_verified": "2026-10-20",
        "evidence_url": "https://aekraft.gumroad.com/l/pahxdv",
        "source": "data/c86_missing_products.json; 0 verified sales; traffic UNKNOWN",
        "algeria_payout": ALGERIA_NOT_APPLICABLE,
    },
    {
        "opportunity_id": "PI-STR-DIRECT",
        "program_name": "STR Direct Booking Revenue Kit",
        "partner_name": "Galaxy Forge",
        "family": "PURCHASE_INTENT_RESEARCH",
        "category": "owned_product",
        "commission_value": "Direct product sale, USD 59 listed",
        "recurring_commission": False,
        "geography": "Global (Gumroad)",
        "payout_terms": "Gumroad seller payout; founder account",
        "verification_status": "OBSERVED",
        "last_verified": "2026-10-20",
        "evidence_url": "https://aekraft.gumroad.com/l/ppsluq",
        "source": "data/c86_missing_products.json; 0 verified sales; traffic UNKNOWN",
        "algeria_payout": ALGERIA_NOT_APPLICABLE,
    },
    {
        "opportunity_id": "PI-DESK-COMPARISON",
        "program_name": "Standing desk converter comparison",
        "partner_name": "Amazon Associates (planned)",
        "family": "PURCHASE_INTENT_RESEARCH",
        "category": "affiliate_content",
        "commission_value": "Amazon category commission, rate varies",
        "recurring_commission": False,
        "geography": "Amazon Associates country availability UNKNOWN for Algeria payout",
        "payout_terms": "Amazon Associates payout terms; direct deposit/check thresholds UNKNOWN",
        "verification_status": "OBSERVED_PRODUCT_DATA",
        "last_verified": "2026-07-30",
        "official_url": "https://affiliate-program.amazon.com/help/operating/agreement",
        "evidence_url": None,
        "source": "affiliate_commerce/products.py (4 real ASINs, manually verified 2026-07-30); 0 commissions",
        "algeria_payout": ALGERIA_UNKNOWN,
    },
)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _read_jsonl(path):
    if not Path(path).exists():
        return []
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def load_programs():
    """Existing 17 records plus six already-researched secondary candidates."""
    rows = [dict(r) for r in ce.load_opportunity_portfolio()]
    rows.extend(dict(r) for r in _EXTRA_PROGRAMS)
    return rows


def _is_paypal_primary(opportunity):
    """A PayPal-only or PayPal-required rail is conditional, not impossible.

    PayPal's Algeria receive agreement lists Algeria, but the program's own
    payout rail and account eligibility are still unconfirmed. Multi-rail
    programs such as Brevo are not treated as PayPal-primary.
    """
    methods = [
        str(method).lower()
        for method in (opportunity.get("payout_methods") or [])
    ]
    if methods and all("paypal" in method for method in methods):
        return True
    text = " ".join(
        str(opportunity.get(key) or "")
        for key in ("payout_terms", "geography", "source")
    ).lower()
    return any(marker in text for marker in _PAYPAL_CONDITIONAL_MARKERS)


def _payout_result(
    state,
    basis,
    *,
    scope="insufficient_evidence",
    account_level_verified=False,
    publisher_country="DZ",
    payout_route="UNKNOWN",
    checked_at=None,
    official_sources=None,
    conditions=None,
    gaps=None,
):
    allowed_states = PAYOUT_STATES + (PAYOUT_NOT_APPLICABLE,)
    state = state if state in allowed_states else PAYOUT_UNKNOWN
    return {
        "status": state,
        "state": state,
        "basis": basis,
        "scope": scope,
        "account_level_verified": bool(account_level_verified),
        "publisher_country": publisher_country,
        "payout_route": payout_route or "UNKNOWN",
        "checked_at": checked_at,
        "official_sources": list(official_sources or []),
        "conditions": list(conditions or []),
        "gaps": list(gaps or []),
    }


def _structured_payout_status(opportunity, now=None):
    oid = opportunity.get("opportunity_id")
    evidence = _PAYOUT_EVIDENCE.get(oid)
    if not evidence:
        return None
    state = evidence["state"]
    gaps = list(evidence.get("gaps") or [])
    sources = list(evidence.get("official_sources") or [])
    if not sources:
        state = PAYOUT_UNKNOWN
        gaps.append("no official payout source is attached")
    if not _is_current(evidence.get("checked_at"), now=now):
        state = PAYOUT_UNKNOWN
        gaps.append("payout evidence is stale or undated")
    if state == PAYOUT_CONDITIONAL and not gaps:
        state = PAYOUT_UNKNOWN
        gaps.append("CONDITIONAL has no named unresolved requirement")
    if state == PAYOUT_VERIFIED and not evidence.get("scope"):
        state = PAYOUT_UNKNOWN
        gaps.append("VERIFIED has no declared evidence scope")
    if state == PAYOUT_VERIFIED and not evidence.get("account_level_verified"):
        gap = "account-level eligibility is not confirmed"
        if gap not in gaps:
            gaps.append(gap)
    return _payout_result(
        state,
        evidence.get("reason", "structured payout evidence"),
        scope=evidence.get("scope", "insufficient_evidence"),
        account_level_verified=evidence.get("account_level_verified", False),
        publisher_country=evidence.get("publisher_country", "DZ"),
        payout_route=evidence.get("payout_route", "UNKNOWN"),
        checked_at=evidence.get("checked_at"),
        official_sources=sources,
        conditions=evidence.get("conditions"),
        gaps=gaps,
    )


def algeria_payout_status(opportunity, now=None):
    """Return VERIFIED, CONDITIONAL, or UNKNOWN with its evidence gaps.

    This never turns missing evidence into a rejection and never promotes a
    route to VERIFIED without a current official source. VERIFIED is explicitly
    route-level; account-level confirmation is reported separately.
    """
    if not isinstance(opportunity, dict):
        return _payout_result(
            PAYOUT_UNKNOWN,
            "no program record",
            gaps=["no program record to evaluate"],
        )

    structured = _structured_payout_status(opportunity, now=now)
    if structured is not None:
        return structured

    explicit = opportunity.get("payout_algeria_compatible")
    text = " ".join(
        str(opportunity.get(key) or "")
        for key in ("payout_terms", "geography", "eligibility")
    ).lower()
    sources = _as_list(opportunity.get("official_url"))
    sources += _as_list(opportunity.get("terms_url"))
    sources += _as_list(opportunity.get("evidence_url"))
    checked_at = opportunity.get("last_verified")

    if explicit is True:
        gaps = []
        if not sources:
            gaps.append("no official payout source is attached")
        if not _is_current(checked_at, now=now):
            gaps.append("payout evidence is stale or undated")
        state = PAYOUT_VERIFIED if not gaps else PAYOUT_UNKNOWN
        if state == PAYOUT_VERIFIED:
            gaps.append("account-level eligibility is not confirmed")
        return _payout_result(
            state,
            (
                "explicit record-level Algeria route, official-source checked; "
                "account-level eligibility remains separate"
            ),
            scope="route_only" if state == PAYOUT_VERIFIED else "insufficient_evidence",
            account_level_verified=False,
            checked_at=checked_at,
            official_sources=sources,
            conditions=_as_list(opportunity.get("payout_methods")),
            gaps=gaps,
        )

    if _is_paypal_primary(opportunity) and "algeria" in text:
        gaps = [
            "program-specific payout rail is not confirmed",
            "account-level eligibility is not confirmed",
        ]
        if not sources:
            gaps.append("no official payout source is attached")
        if not _is_current(checked_at, now=now):
            gaps.append("payout evidence is stale or undated")
        return _payout_result(
            PAYOUT_CONDITIONAL,
            (
                "PayPal-primary rail; PayPal's Algeria receive agreement lists "
                "Algeria only subject to a linked US bank/Visa, a 30-day hold, and "
                "withdrawal-only balance use, while the program-specific rail is unconfirmed"
            ),
            scope="program_specific_rail_unconfirmed",
            payout_route="PayPal",
            checked_at=checked_at,
            official_sources=sources,
            conditions=_as_list(opportunity.get("payout_methods")),
            gaps=gaps,
        )

    return _payout_result(
        PAYOUT_UNKNOWN,
        "no current Algeria-specific payout evidence in the program record",
        gaps=["no current Algeria-specific payout evidence"],
    )


def _plain_text(html):
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def audit_guide(filename):
    path = _CUSTOMER_SITE / filename
    if not path.exists():
        return {
            "path": "customer_site/%s" % filename,
            "exists": False,
            "status": "MISSING",
            "failures": ["guide file missing"],
        }
    html = path.read_text(encoding="utf-8", errors="replace")
    body = _plain_text(html)
    title_match = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    title = _plain_text(title_match.group(1)) if title_match else ""
    disclosure = (
        "affiliate disclosure" in body.lower()
        or ("disclosure" in body.lower() and "commission" in body.lower())
    )
    cta_present = bool(re.search(r"<a\s+[^>]*href\s*=", html, re.I))
    verdict = qa_content({
        "title": title,
        "body": body,
        "disclosure": disclosure,
        "cta_present": cta_present,
    })
    return {
        "path": "customer_site/%s" % filename,
        "exists": True,
        "title": title,
        "words": len(body.split()),
        "disclosure": disclosure,
        "cta_present": cta_present,
        "unknown_markers": body.upper().count("UNKNOWN"),
        "status": verdict["status"],
        "failures": verdict["failures"],
    }


def _freshness(opportunity):
    try:
        return ce._freshness_from_last_verified(opportunity.get("last_verified"))
    except Exception:
        return "UNKNOWN"


def _clean(value):
    if value is None:
        return "UNKNOWN"
    text = str(value).strip()
    if not text or text.upper().startswith("UNKNOWN"):
        return "UNKNOWN"
    return text


def _candidate_research(opportunity, algeria, guide):
    """Return the register's required research fields for one candidate.

    Every field is populated only from an existing source or an explicitly
    disclosed research note. Missing facts stay UNKNOWN; they are never filled
    with a plausible-sounding number.
    """
    oid = opportunity.get("opportunity_id", "UNKNOWN")
    profile = _CANDIDATE_RESEARCH.get(oid, {})
    official_url = profile.get("official_url") or _first_url(opportunity)
    evidence_sources = _as_list(official_url)
    evidence_sources += _as_list(opportunity.get("evidence_url"))
    evidence_sources += _as_list(opportunity.get("terms_url"))
    evidence_sources += _as_list(opportunity.get("source"))
    evidence_sources = list(dict.fromkeys(str(source) for source in evidence_sources))

    if algeria["status"] == PAYOUT_VERIFIED:
        next_action = (
            "Founder decides whether to open the account and complete the named "
            "payout conditions; no automatic application"
        )
    elif algeria["status"] == PAYOUT_CONDITIONAL:
        next_action = (
            "Resolve the named program-specific payout gap before producing a CTA "
            "or applying"
        )
    else:
        next_action = (
            "Re-read the official program and payout pages; do not apply or add a "
            "link until Algeria evidence exists"
        )

    return {
        "target_audience": profile.get(
            "target_audience",
            _clean(opportunity.get("target_customer")),
        ),
        "customer_problem": profile.get(
            "customer_problem",
            _clean(opportunity.get("customer_problem")),
        ),
        "solution": profile.get(
            "solution",
            _clean(opportunity.get("product_or_service"))
            if _clean(opportunity.get("product_or_service")) != "UNKNOWN"
            else _clean(opportunity.get("program_name")),
        ),
        "official_url": official_url,
        "evidence_sources": evidence_sources,
        "evidence_timestamp": (
            opportunity.get("last_verified")
            or opportunity.get("evidence_timestamp")
            or "UNKNOWN"
        ),
        "application_status": "NOT_APPLIED",
        "commission_model": _clean(opportunity.get("commission_type")),
        "commission_terms": _clean(opportunity.get("commission_value")),
        "attribution_terms": _clean(
            opportunity.get("cookie_or_tracking_window")
            or opportunity.get("commission_duration")
        ),
        "publisher_eligibility": _clean(opportunity.get("eligibility")),
        "payout_state": algeria["status"],
        "payout_route": algeria.get("payout_route", "UNKNOWN"),
        "payout_gaps": list(algeria.get("gaps") or []),
        "demand_evidence": profile.get(
            "demand_evidence",
            "UNKNOWN -- no measured search, click, or purchase-intent data yet",
        ),
        "competition": profile.get(
            "competition",
            "UNKNOWN -- no competitor-content audit recorded",
        ),
        "differentiation": profile.get(
            "differentiation",
            "UNKNOWN -- no differentiated content angle recorded",
        ),
        "effort": profile.get(
            "effort",
            "UNKNOWN -- no build or content estimate recorded",
        ),
        "distribution": profile.get(
            "distribution",
            "UNKNOWN -- no distribution surface recorded",
        ),
        "zero_cost_validation": profile.get(
            "zero_cost_validation",
            "Read the official program and payout pages without creating an account",
        ),
        "risks": profile.get(
            "risks",
            "; ".join(algeria.get("gaps") or ["payout evidence is unresolved"]),
        ),
        "freshness": _freshness(opportunity),
        "confidence": profile.get(
            "confidence",
            _clean(opportunity.get("confidence")),
        ),
        "next_action": profile.get("next_action", next_action),
        "guide_status": (guide or {}).get("status", "NONE"),
    }


def _candidate_disposition(opportunity, algeria):
    category = opportunity.get("category")
    verification = str(opportunity.get("verification_status", "")).upper()
    oid = opportunity.get("opportunity_id", "")
    if category != "affiliate":
        return "REJECTED"
    if "DISCONTINU" in verification or "CLOSED" in verification:
        return "REJECTED"
    if "THIRD_PARTY" in verification or oid == "CO-shopify-affiliate":
        return "HOLD"
    if algeria["status"] == PAYOUT_CONDITIONAL:
        return "CONDITIONAL"
    return "RESEARCH"


def _readiness_gates(opportunity, guide, algeria):
    gates = ["FOUNDER_ACCOUNT_ACTION_REQUIRED", "AFFILIATE_LINK_NOT_CONFIGURED"]
    if opportunity.get("category") != "affiliate":
        gates.append("NOT_AN_AFFILIATE_PROGRAM")
    if algeria["status"] == PAYOUT_CONDITIONAL:
        gates.append("PAYOUT_ALGERIA_CONDITIONAL")
    elif algeria["status"] == PAYOUT_UNKNOWN:
        gates.append("PAYOUT_ALGERIA_UNKNOWN")
    elif algeria["status"] == PAYOUT_VERIFIED:
        if not algeria.get("account_level_verified"):
            gates.append("PAYOUT_ACCOUNT_LEVEL_UNVERIFIED")
    if _freshness(opportunity) in ("AGING", "STALE"):
        gates.append("EVIDENCE_%s" % _freshness(opportunity))
    if guide and guide.get("status") == "HOLD":
        gates.append("CONTENT_QA_HOLD")
    return gates


_PAYOUT_VERDICT_BY_STATUS = {
    PAYOUT_VERIFIED: "PASS",
    PAYOUT_CONDITIONAL: "HOLD",
    PAYOUT_UNKNOWN: "UNKNOWN",
    PAYOUT_NOT_APPLICABLE: "N/A",
}


def payout_verdict(status):
    """Map a payout state onto the founder-facing PASS/HOLD/UNKNOWN vocabulary."""
    return _PAYOUT_VERDICT_BY_STATUS.get(status, "UNKNOWN")


def can_transition_payout(current, next_state, evidence=None):
    """Pure evidence gate for payout-state changes.

    A stronger state needs current authoritative evidence. A weaker state is
    always allowed when evidence is revoked, stale, or contradicted.
    """
    if current == next_state:
        return True
    if next_state not in PAYOUT_STATES:
        return False
    if current == PAYOUT_VERIFIED:
        return next_state in (PAYOUT_CONDITIONAL, PAYOUT_UNKNOWN)
    if current == PAYOUT_CONDITIONAL:
        if next_state == PAYOUT_UNKNOWN:
            return True
        if next_state != PAYOUT_VERIFIED:
            return False
    elif current != PAYOUT_UNKNOWN or next_state == PAYOUT_UNKNOWN:
        return False

    if not isinstance(evidence, dict):
        return False
    if not evidence.get("official_sources"):
        return False
    if not _is_current(evidence.get("checked_at")):
        return False
    if next_state == PAYOUT_VERIFIED:
        return bool(evidence.get("scope"))
    return bool(evidence.get("gaps"))


def program_rows():
    rows = []
    for opportunity in load_programs():
        oid = opportunity.get("opportunity_id", "UNKNOWN")
        guide_name = GUIDE_BY_PROGRAM.get(oid)
        guide = audit_guide(guide_name) if guide_name else None
        algeria = algeria_payout_status(opportunity)
        category = opportunity.get("category", "UNKNOWN")
        research = _candidate_research(opportunity, algeria, guide)
        disposition = _candidate_disposition(opportunity, algeria)
        if category != "affiliate":
            verdict = "NOT_AFFILIATE"
        elif algeria["status"] == PAYOUT_CONDITIONAL:
            verdict = "HOLD_PAYOUT"
        elif algeria["status"] in (PAYOUT_VERIFIED, PAYOUT_UNKNOWN):
            verdict = "RESEARCH_READY"
        else:
            verdict = "DISCOVERY"
        row = {
            "opportunity_id": oid,
            "program_name": opportunity.get("program_name", "UNKNOWN"),
            "partner_name": opportunity.get("partner_name", "UNKNOWN"),
            "family": PROGRAM_FAMILY.get(oid, "UNKNOWN"),
            "category": category,
            "status": program_registry.derive_status(opportunity, None),
            "verification_status": opportunity.get("verification_status", "UNKNOWN"),
            "commission_value": opportunity.get("commission_value", "UNKNOWN"),
            "recurring": bool(opportunity.get("recurring_commission")),
            "last_verified": opportunity.get("last_verified", "UNKNOWN"),
            "freshness": _freshness(opportunity),
            "algeria": algeria,
            "payout_state": algeria["status"],
            "payout_verdict": payout_verdict(algeria["status"]),
            "guide": guide,
            "verdict": verdict,
            "disposition": disposition,
            "gates": _readiness_gates(opportunity, guide, algeria),
            "activation_status": "NOT_ACTIVATION_READY",
        }
        row.update(research)
        rows.append(row)
    return rows


def owned_rows():
    rows = []
    for item in _OWNED_ASSETS:
        row = dict(item)
        state = row.get("algeria_payout", PAYOUT_UNKNOWN)
        if state == PAYOUT_NOT_APPLICABLE:
            algeria = _payout_result(
                PAYOUT_NOT_APPLICABLE,
                "owned/direct asset; an affiliate payout route does not apply",
                scope="not_applicable",
                payout_route="N/A",
                checked_at=row.get("last_verified"),
                gaps=["N/A -- direct product sale; no affiliate payout route applies"],
            )
        else:
            algeria = _payout_result(
                state,
                "owned/purchase-intent row; payout evidence is not program-specific",
                payout_route="UNKNOWN",
                checked_at=row.get("last_verified"),
                gaps=["no program-specific Algeria payout evidence"],
            )
        row["family"] = "PURCHASE_INTENT_RESEARCH"
        row["status"] = "LOCAL_OR_LIVE_ASSET"
        row["freshness"] = "OBSERVED"
        row["algeria"] = algeria
        row["payout_state"] = algeria["status"]
        row["payout_verdict"] = payout_verdict(algeria["status"])
        row["gates"] = ["FOUNDER_ACCOUNT_ACTION_REQUIRED", "AFFILIATE_LINK_NOT_CONFIGURED"]
        row["activation_status"] = "NOT_ACTIVATION_READY"
        row["disposition"] = (
            "RESEARCH" if row.get("category") == "affiliate_content" else "HOLD"
        )
        row.update(_candidate_research(item, algeria, None))
        row["disposition"] = (
            "RESEARCH" if row.get("category") == "affiliate_content" else "HOLD"
        )
        rows.append(row)
    return rows


def build_register():
    programs = program_rows()
    owned = owned_rows()
    rows = programs + owned
    return {
        "generated_at": _now(),
        "total": len(rows),
        "programs": programs,
        "owned_purchase_intent": owned,
        "candidate_count": len(rows),
        "affiliate_candidate_count": sum(
            1 for row in rows
            if row.get("category") in ("affiliate", "affiliate_content")
        ),
        "payout_states": list(PAYOUT_STATES),
        "required_candidate_fields": list(CANDIDATE_REQUIRED_FIELDS),
        "evidence_rule": "Only fields present in a real source are populated; all other values are UNKNOWN.",
        "activation_rule": "No row is activation-ready while an account, affiliate link, or payout path is unresolved.",
        "payout_rule": "VERIFIED is route-level evidence only; account-level confirmation is reported separately.",
    }


def summary(register=None):
    register = register or build_register()
    rows = register["programs"] + register["owned_purchase_intent"]
    by_family = {family: 0 for family in FAMILIES}
    by_algeria = {state: 0 for state in PAYOUT_STATES}
    by_algeria[PAYOUT_NOT_APPLICABLE] = 0
    by_verdict = {}
    by_payout_verdict = {
        verdict: 0 for verdict in set(_PAYOUT_VERDICT_BY_STATUS.values())
    }
    by_disposition = {state: 0 for state in CANDIDATE_DISPOSITIONS}
    for row in rows:
        by_family[row.get("family", "UNKNOWN")] = by_family.get(row.get("family", "UNKNOWN"), 0) + 1
        algeria = (row.get("algeria") or {}).get(
            "status", row.get("payout_state", PAYOUT_UNKNOWN)
        )
        by_algeria[algeria] = by_algeria.get(algeria, 0) + 1
        by_verdict[row.get("verdict", row.get("status"))] = by_verdict.get(
            row.get("verdict", row.get("status")), 0
        ) + 1
        verdict = row.get("payout_verdict") or payout_verdict(algeria)
        by_payout_verdict[verdict] = by_payout_verdict.get(verdict, 0) + 1
        disposition = row.get("disposition", "HOLD")
        by_disposition[disposition] = by_disposition.get(disposition, 0) + 1
    return {
        "generated_at": register["generated_at"],
        "total": register["total"],
        "candidate_count": register.get("candidate_count", register["total"]),
        "affiliate_candidate_count": register.get("affiliate_candidate_count", 0),
        "by_family": by_family,
        "by_algeria_payout": by_algeria,
        "by_payout_verdict": by_payout_verdict,
        "by_verdict": by_verdict,
        "by_disposition": by_disposition,
        "activation_ready": sum(1 for r in rows if r.get("activation_status") == "ACTIVATION_READY"),
    }

ASSET_STAGES = (
    "IDEA",
    "RESEARCHED",
    "ELIGIBILITY_BLOCKED",
    "ELIGIBILITY_PASS",
    "DRAFTED",
    "QA_PASS",
    "QA_HOLD",
    "LINK_BLOCKED",
    "AUTH_PENDING",
    "PUBLISHED",
    "MEASURING",
    "SCALED",
    "HELD",
    "HIBERNATED",
)

_ALLOWED_ASSET_TRANSITIONS = {
    "IDEA": ("RESEARCHED",),
    "RESEARCHED": ("ELIGIBILITY_BLOCKED", "ELIGIBILITY_PASS"),
    "ELIGIBILITY_BLOCKED": ("RESEARCHED",),
    "ELIGIBILITY_PASS": ("DRAFTED",),
    "DRAFTED": ("QA_PASS", "QA_HOLD"),
    "QA_HOLD": ("DRAFTED",),
    "QA_PASS": ("LINK_BLOCKED", "AUTH_PENDING"),
    "LINK_BLOCKED": ("AUTH_PENDING",),
    "AUTH_PENDING": ("PUBLISHED",),
    "PUBLISHED": ("MEASURING",),
    "MEASURING": ("SCALED", "HELD", "HIBERNATED"),
    "SCALED": (),
    "HELD": ("DRAFTED", "HIBERNATED"),
    "HIBERNATED": (),
}


def can_transition(current, next_stage):
    """Pure asset-substate gate. It never upgrades a blocked asset."""
    return next_stage in _ALLOWED_ASSET_TRANSITIONS.get(current, ())
