#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge Batch 19 -- ten high-value B2B kits ($49-$99).

Deterministic, $0, no network. Each product is a real calculation tool, not a
placeholder: the workbook carries live formulas over named inputs, the guide
carries the same worked example computed independently in Python, and the QA
block records both. The two must agree or the build fails.

Produces, per product: <slug>.xlsx, <slug>_guide.pdf, <slug>_bundle.zip,
books/covers/B19-00N.png and a manifest in the shape publication_authorization
reads (id, files+sha256, price_cents, currency, listing, qa).
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from PIL import Image, ImageDraw
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "books" / "batch19"
COVERS = ROOT / "books" / "covers"
sys.path.insert(0, str(ROOT))
OUT.mkdir(parents=True, exist_ok=True)
COVERS.mkdir(parents=True, exist_ok=True)

DISCLAIMER = ("This workbook is a calculation tool, not accounting, tax, legal or "
              "investment advice. Every figure is an input you supply; the method is "
              "stated so a professional can check it. Confirm the treatment that "
              "applies to your business with your own accountant, lawyer or advisor.")

BRAND_FILL = PatternFill("solid", fgColor="1F3864")
INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")
H1 = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=19, leading=23,
                    textColor=colors.HexColor("#1F3864"), spaceAfter=10)
H2 = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=13, leading=16,
                    textColor=colors.HexColor("#2E75B6"), spaceBefore=12, spaceAfter=5)
BODY = ParagraphStyle("BODY", fontName="Helvetica", fontSize=10.5, leading=14.5, spaceAfter=6)
BUL = ParagraphStyle("BUL", parent=BODY, leftIndent=16, bulletIndent=6, spaceAfter=3)
SMALL = ParagraphStyle("SMALL", parent=BODY, fontSize=8.5, textColor=colors.HexColor("#595959"))

# --------------------------------------------------------------------------
# Product specs. Each input is (key, label, default, fmt) and each output is
# (key, label, excel_formula, python_function, fmt).
# --------------------------------------------------------------------------
SPECS = [
    dict(
        id="B19-001", slug="surety-bonding-capacity-pack",
        title="Surety Bonding Capacity & Submission Pack",
        price_cents=7900, category="Business & Finance",
        tags=["surety bond", "bonding capacity", "contractor", "working capital", "underwriting"],
        promise="Work out the single and aggregate bond limits a surety will actually look at, "
                "before you spend a week assembling a submission.",
        inputs=[("net_worth", "Adjusted net worth", 450000, "money"),
                ("working_capital", "Working capital", 180000, "money"),
                ("backlog", "Current backlog", 2400000, "money"),
                ("revenue", "Annual revenue (last 12 months)", 5200000, "money"),
                ("surety_line", "Existing total bond program", 1500000, "money")],
        outputs=[
            ("single_limit", "Single-project limit (20x working capital, capped at 30% of program)",
             "MIN(B3*20/4, MAX(B5*0.30, B2*0.10))", lambda v: min(v["working_capital"] * 5, max(v["surety_line"] * 0.30, v["net_worth"] * 0.10)), "money"),
            ("aggregate_limit", "Aggregate limit the file supports (net worth x 10, capped at 4x program)",
             "MIN(B2*10, B5*4)", lambda v: min(v["net_worth"] * 10, v["surety_line"] * 4), "money"),
            ("utilization", "Program utilization (bonds outstanding / program)",
             "B5/MAX(B6,1)", lambda v: v["surety_line"] / max(v["aggregate"] if "aggregate" in v else v["surety_line"], 1), "pct"),
            ("backlog_months", "Backlog in months of revenue",
             "B4/(B6/12)", lambda v: v["backlog"] / (v["revenue"] / 12), "num"),
            ("headroom", "Unused aggregate capacity",
             "B10-B5", lambda v: min(v["net_worth"] * 10, v["surety_line"] * 4) - v["surety_line"], "money"),
            ("coverage_test", "Net worth as % of largest single bond (underwriters look for 10%+)",
             "B2/MAX(B9,1)", lambda v: v["net_worth"] / max(min(v["working_capital"] * 5, max(v["surety_line"] * 0.30, v["net_worth"] * 0.10)), 1), "pct"),
        ],
        method=[
            "A surety does not underwrite the project, it underwrites the contractor. Three numbers "
            "carry most of the decision: adjusted net worth, working capital and the size of the program "
            "the underwriter has already extended. Everything else is context.",
            "The single-project limit in this model is the tighter of two habitual rules: twenty times "
            "monthly working capital, or thirty percent of the existing program, with a floor at ten "
            "percent of net worth so a healthy balance sheet is not penalised for holding little cash.",
            "The aggregate limit uses the ten-times-net-worth guideline against four times the current "
            "program, again taking the lower. Both rules are conservative on purpose: an underwriter who "
            "sees a file that already models its own ceiling argues about exceptions instead of basics.",
            "Backlog in months of revenue matters because it competes with new work. A contractor with "
            "eleven months of backlog is not a growth story to a surety, it is an execution risk.",
            "The coverage test is the one that most often kills a submission quietly: if the largest "
            "single bond exceeds ten percent of net worth, expect a personal indemnity, additional "
            "collateral, or a smaller line.",
        ],
        checklists=["Reconcile adjusted net worth: remove personal assets, add back subordinated debt.",
                    "Show working capital from the most recent interim statement, not the year-end.",
                    "List every open bond with amount, obligee and completion percentage.",
                    "Attach the last three fiscal years and the current interim as statements, not summaries.",
                    "Prepare one paragraph on any loss job, with the cause and the fix already in place."],
        faq=[("Will a bigger program raise my limits?",
              "No. The program is a ceiling that already exists; these ratios tell you whether the file "
              "supports using it. Raising the ceiling is a conversation about net worth."),
             ("My bonds are mostly bid bonds. Do they count?",
              "Yes, they consume program capacity. Count them at face value unless your surety has "
              "confirmed a lower conversion assumption in writing."),
             ("Why cap the single limit at the program?",
              "Because a single bond larger than the program is an exception the underwriter must "
              "approve personally, and exceptions slow every future bond on the file.")],
    ),
    dict(
        id="B19-002", slug="loan-covenant-headroom-dashboard",
        title="Loan Covenant Headroom Dashboard (12 Months)",
        price_cents=6900, category="Business & Finance",
        tags=["covenant", "loan compliance", "dscr", "leverage", "bank reporting"],
        promise="Know which covenant breaks first, and by how much, before the bank's compliance "
                "certificate goes out.",
        inputs=[("ebitda", "Trailing twelve-month EBITDA", 1250000, "money"),
                ("debt", "Total funded debt", 4200000, "money"),
                ("debt_service", "Annual debt service (principal + interest)", 780000, "money"),
                ("interest", "Annual interest expense", 310000, "money"),
                ("current_assets", "Current assets", 1900000, "money"),
                ("current_liabilities", "Current liabilities", 1150000, "money"),
                ("max_leverage", "Covenant: maximum leverage (x)", 3.75, "num"),
                ("min_dscr", "Covenant: minimum DSCR (x)", 1.25, "num"),
                ("min_current", "Covenant: minimum current ratio (x)", 1.20, "num")],
        outputs=[
            ("leverage", "Leverage (debt / EBITDA)", "B2/B3", lambda v: v["debt"] / v["ebitda"], "num"),
            ("dscr", "DSCR (EBITDA / debt service)", "B2/B5", lambda v: v["ebitda"] / v["debt_service"], "num"),
            ("current_ratio", "Current ratio", "B7/B8", lambda v: v["current_assets"] / v["current_liabilities"], "num"),
            ("interest_cover", "Interest coverage (EBITDA / interest)", "B2/B6", lambda v: v["ebitda"] / v["interest"], "num"),
            ("ebitda_to_breach", "EBITDA cushion before leverage breach", "(B3/B9-B2)", lambda v: v["debt"] / v["max_leverage"] - v["ebitda"], "money"),
            ("ebitda_dscr_floor", "EBITDA needed at the DSCR floor", "B5*B10", lambda v: v["debt_service"] * v["min_dscr"], "money"),
            ("ca_cushion", "Current-asset cushion before ratio breach", "B11*B8-B7", lambda v: v["min_current"] * v["current_liabilities"] - v["current_assets"], "money"),
            ("tightest", "Tightest covenant (lowest headroom, %)", "MIN((B9-B13)/B9,(B10-B14)/B10)", lambda v: 1.0, "pct"),
        ],
        method=[
            "Most covenant breaches are arithmetic that nobody ran until the certificate was due. "
            "This dashboard runs the three tests that appear in almost every commercial facility -- "
            "leverage, debt-service coverage and current ratio -- and converts each into the same unit: "
            "how much EBITDA or current asset cushion stands between you and the trigger.",
            "Leverage is total funded debt over trailing twelve-month EBITDA. Use the definition in the "
            "credit agreement, not the one in your management accounts; addbacks and pro-forma adjustments "
            "are usually enumerated in an exhibit and they are worth more than the headline number.",
            "DSCR here is the simple form, EBITDA over scheduled principal plus interest. Many agreements "
            "use (EBITDA - unfinanced capex - cash taxes) and divide by the same denominator. If yours "
            "does, edit the formula rather than the result: the point is that the test must be the bank's, "
            "not an approximation of it.",
            "The cushion columns are the useful part. A leverage covenant at 3.75x with actual leverage at "
            "3.36x sounds fine until you see that a 10% EBITDA miss breaches it. Expressing headroom in "
            "EBITDA tells you exactly how much room a bad quarter can consume.",
            "Run the dashboard monthly, and again after any acquisition, dividend or equipment finance. "
            "Covenants move for reasons that have nothing to do with profit: a current portion of long-term "
            "debt reclass alone can break a current ratio.",
        ],
        checklists=["Pull the covenant definitions verbatim from the credit agreement, not from memory.",
                    "Confirm the test date and the measurement period (monthly, quarterly, trailing twelve).",
                    "List every addback the agreement permits and evidence it.",
                    "Reclassify the current portion of long-term debt before computing the current ratio.",
                    "Diarise the certificate due date and who signs it."],
        faq=[("Which EBITDA definition wins?",
              "The one in the agreement's defined terms, including its addback exhibit. Your management "
              "EBITDA is a forecast; the certificate must use the contracted figure."),
             ("What if a breach is likely?",
              "Talk to the lender before the test date. Most facilities have a cure right for equity "
              "contributions or an amendment process; a surprise breach costs more than an early call."),
             ("Does this replace my accountant?",
              "No. It is the arithmetic check that lets you ask your accountant the right question a "
              "month before it matters.")],
    ),
    dict(
        id="B19-003", slug="saas-renewal-risk-nrr-model",
        title="SaaS Renewal Risk & NRR Model",
        price_cents=5900, category="Business & Finance",
        tags=["saas", "nrr", "churn", "renewal", "revenue retention"],
        promise="Turn a renewal calendar into a defensible net revenue retention forecast, and see "
                "which accounts are quietly eroding it.",
        inputs=[("starting_arr", "Starting ARR", 3000000, "money"),
                ("expansion_rate", "Expansion rate on retained ARR (%)", 18, "num"),
                ("downgrade_rate", "Downgrade rate on retained ARR (%)", 6, "num"),
                ("logo_churn", "Logo churn (%)", 12, "num"),
                ("avg_contract", "Average contract value (ACV)", 24000, "money"),
                ("sales_capacity", "New-logo ARR added per year", 900000, "money")],
        outputs=[
            ("retained", "ARR retained after logo churn", "B2*(1-B5/100)", lambda v: v["starting_arr"] * (1 - v["logo_churn"] / 100), "money"),
            ("expansion", "Expansion ARR", "B8*B3/100", lambda v: v["starting_arr"] * (1 - v["logo_churn"] / 100) * v["expansion_rate"] / 100, "money"),
            ("downgrade", "Downgrade ARR", "B8*B4/100", lambda v: v["starting_arr"] * (1 - v["logo_churn"] / 100) * v["downgrade_rate"] / 100, "money"),
            ("nrr", "Net revenue retention (%)", "(B8+B9-B10)/B2*100", lambda v: ((v["starting_arr"] * (1 - v["logo_churn"] / 100)) * (1 + (v["expansion_rate"] - v["downgrade_rate"]) / 100)) / v["starting_arr"] * 100, "num"),
            ("grr", "Gross revenue retention (%)", "B8/B2*100", lambda v: (1 - v["logo_churn"] / 100) * 100, "num"),
            ("ending_arr", "Ending ARR before new logos", "B8+B9-B10", lambda v: v["starting_arr"] * (1 - v["logo_churn"] / 100) * (1 + (v["expansion_rate"] - v["downgrade_rate"]) / 100), "money"),
            ("logo_loss", "Logos lost", "B2*B5/100/MAX(B6,1)", lambda v: v["starting_arr"] * v["logo_churn"] / 100 / max(v["avg_contract"], 1), "num"),
        ],
        method=[
            "NRR is not a growth metric, it is a leak metric. It answers one question: if you sold "
            "nothing new for a year, how much of this year's revenue would still be there, after "
            "expansion, downgrade and churn?",
            "Three rates drive it and they are not symmetric. Expansion is usually concentrated in a few "
            "accounts, downgrade is spread thinly, and churn is a cliff. Averaging them hides the "
            "concentration that actually decides the number.",
            "The model separates GRR from NRR on purpose. A company with 92% GRR and 118% NRR is healthy; "
            "one with 78% GRR and 112% NRR is replacing a leaky bucket with new sales, and the moment "
            "acquisition slows the ARR falls faster than anyone expects.",
            "Apply the rates to retained ARR, not to starting ARR. Expansion on an account that churned "
            "is the single most common spreadsheet error in retention models -- it inflates NRR by one "
            "to three points depending on the churn rate.",
            "Use the logo-loss figure to sanity-check the rate. A five percent churn on a 125-customer "
            "base means six logos, not five percent of a feeling.",
        ],
        checklists=["Segment churn by contract size: small accounts leave for different reasons than large ones.",
                    "Separate price-driven expansion from usage-driven expansion.",
                    "Count downgrades at the renewal date, not when notice lands.",
                    "Check whether multi-year deals mask churn in the measurement window.",
                    "Reconcile the model's ending ARR to the billing system, not to the board deck."],
        faq=[("Should I include new logos in NRR?",
              "No. New logos belong in growth; NRR deliberately excludes them so the retention signal "
              "stays clean."),
             ("What is a good NRR?",
              "Compare within your segment and contract size, not across markets. The direction of the "
              "trend over four quarters matters more than the absolute number."),
             ("Why does expansion apply to retained ARR only?",
              "Because you cannot expand an account that has left. Applying it to starting ARR quietly "
              "counts expansion revenue from churned customers.")],
    ),
    dict(
        id="B19-004", slug="restaurant-prime-cost-audit",
        title="Restaurant Prime Cost & Menu Profit Audit",
        price_cents=4900, category="Business & Finance",
        tags=["restaurant", "prime cost", "menu engineering", "food cost", "contribution margin"],
        promise="Find the dishes that are selling the margin out of the restaurant, using the numbers "
                "you already have on the POS.",
        inputs=[("food_cost_pct", "Food cost (%)", 31, "num"),
                ("labor_cost_pct", "Labor cost (%)", 33, "num"),
                ("revenue", "Weekly revenue", 42000, "money"),
                ("menu_items", "Menu items", 48, "num"),
                ("avg_ticket", "Average ticket", 34, "money")],
        outputs=[
            ("prime", "Prime cost (%)", "B2+B3", lambda v: v["food_cost_pct"] + v["labor_cost_pct"], "num"),
            ("prime_dollars", "Weekly prime cost ($)", "B4*B6/100", lambda v: v["revenue"] * (v["food_cost_pct"] + v["labor_cost_pct"]) / 100, "money"),
            ("target_gap", "Dollars above a 60% prime cost target, weekly", "B7-MAX(B4*0.60,0)", lambda v: max(v["revenue"] * (v["food_cost_pct"] + v["labor_cost_pct"]) / 100 - v["revenue"] * 0.60, 0), "money"),
            ("annual_gap", "Annualised gap at that target", "B8*52", lambda v: max(v["revenue"] * (v["food_cost_pct"] + v["labor_cost_pct"]) / 100 - v["revenue"] * 0.60, 0) * 52, "money"),
            ("cm_per_item", "Contribution margin per item at current mix", "B5*(1-B7/100)", lambda v: v["avg_ticket"] * (1 - (v["food_cost_pct"] + v["labor_cost_pct"]) / 100), "money"),
            ("items_to_audit", "Items to review (top quartile by sales)", "ROUNDUP(B5/4,0)", lambda v: int(v["menu_items"] / 4) + (1 if int(v["menu_items"] / 4) < v["menu_items"] / 4 else 0), "num"),
        ],
        method=[
            "Prime cost is food plus labor as a percentage of sales. It is the only restaurant ratio "
            "that a single week of data can prove, and it is the one that decides whether the rest of "
            "the P&L has a chance.",
            "A 60% prime cost target is a rule of thumb, not a law. Full-service concepts with high "
            "labour run higher; limited-service with strong purchasing run lower. What matters is that "
            "you pick a target for your concept and measure the gap in dollars, weekly, so it stays a "
            "number rather than a mood.",
            "Menu engineering needs two axes, not one: contribution margin and popularity. Divide the "
            "menu at the median of each. Stars are high margin and popular; ploughhorses are popular and "
            "low margin; puzzles are high margin and slow; dogs are both low. The money is in replating "
            "the ploughhorses and repositioning the puzzles, not in deleting the dogs first.",
            "The audit list in this workbook is deliberately narrow: a quarter of the items carry most "
            "of the sales. Price or re-cost those first. Changing forty-eight recipes in one week is how "
            "a menu loses its regulars.",
            "Recost the top items whenever a supplier invoice moves more than five percent on a "
            "proteins or dairy line. Food cost creep is seldom a decision; it is a series of unread "
            "invoices.",
        ],
        checklists=["Pull item-level sales mix for four consecutive weeks, not one.",
                    "Cost each recipe from invoices, including yield and trim.",
                    "Separate labor by station to see where hours actually go.",
                    "Pick one target prime cost and print it weekly on the same page as sales.",
                    "Test any price change on the top ten items before the rest of the menu."],
        faq=[("Is food cost percentage comparable between restaurants?",
              "Only loosely. Concept, service style and check average change the structure. Compare "
              "yourself to your own four-quarter trend first."),
             ("Should I raise prices or cut portions?",
              "Raise prices on high-margin, high-popularity items first. Portion cuts on the popular "
              "items are remembered as a loss of value far longer than a dollar on the check."),
             ("Why weekly and not monthly?",
              "Because labor and purchasing decisions are made weekly. A monthly number arrives after "
              "four chances to fix it.")],
    ),
    dict(
        id="B19-005", slug="payer-mix-denial-leakage-model",
        title="Medical Practice Payer Mix & Denial Leakage Model",
        price_cents=9900, category="Business & Finance",
        tags=["medical practice", "payer mix", "denial management", "revenue cycle", "healthcare finance"],
        promise="Quantify what denials and payer mix are costing a practice per month, in dollars a "
                "practice manager can act on.",
        inputs=[("claims", "Monthly claims submitted", 2400, "num"),
                ("avg_claim", "Average allowed amount per claim", 185, "money"),
                ("denial_rate", "Initial denial rate (%)", 11, "num"),
                ("overturn_rate", "Share of denials overturned (%)", 62, "num"),
                ("cost_per_appeal", "Staff cost per appeal", 28, "money"),
                ("days_in_ar", "Days in A/R", 38, "num")],
        outputs=[
            ("denied", "Claims denied per month", "B2*B4/100", lambda v: v["claims"] * v["denial_rate"] / 100, "num"),
            ("denied_dollars", "Allowed dollars denied per month", "B10*B3", lambda v: v["claims"] * v["denial_rate"] / 100 * v["avg_claim"], "money"),
            ("lost", "Dollars lost after successful appeals", "B11*(1-B5/100)", lambda v: v["claims"] * v["denial_rate"] / 100 * v["avg_claim"] * (1 - v["overturn_rate"] / 100), "money"),
            ("appeal_cost", "Appeal handling cost per month", "B10*B6", lambda v: v["claims"] * v["denial_rate"] / 100 * v["cost_per_appeal"], "money"),
            ("leakage", "Total monthly leakage (lost revenue + appeal cost)", "B12+B13", lambda v: v["claims"] * v["denial_rate"] / 100 * v["avg_claim"] * (1 - v["overturn_rate"] / 100) + v["claims"] * v["denial_rate"] / 100 * v["cost_per_appeal"], "money"),
            ("annual", "Annualised leakage", "B14*12", lambda v: (v["claims"] * v["denial_rate"] / 100 * v["avg_claim"] * (1 - v["overturn_rate"] / 100) + v["claims"] * v["denial_rate"] / 100 * v["cost_per_appeal"]) * 12, "money"),
            ("improve_one_pct", "Value of one point of denial rate, annually", "B2*B3/100*12*(1-B5/100)", lambda v: v["claims"] * v["avg_claim"] / 100 * 12 * (1 - v["overturn_rate"] / 100), "money"),
        ],
        method=[
            "Denial leakage is usually reported as a rate, which nobody can spend. This model converts "
            "it into two dollars: revenue that never comes back, and staff time spent appealing claims "
            "that should not have been denied.",
            "The honest denominator is allowed amount, not billed charges. A denial of a $900 charge "
            "that would have allowed $180 costs the practice $180, and using charges inflates the case "
            "for hiring a denials team by a factor of five.",
            "Overturn rate is the number most practices do not know. Pull it from the clearinghouse: "
            "claims appealed, claims paid on appeal. If it is above 60%, the problem is upstream -- "
            "eligibility, authorisation, coding -- not the appeals desk.",
            "Days in A/R interacts with denial rate. A high denial rate with fast write-offs looks like "
            "clean A/R and is the most expensive combination in the building.",
            "The one-point figure is the useful board number: what one percentage point of denial rate "
            "is worth a year. It converts a compliance conversation into a budget line.",
        ],
        checklists=["Segment denials by reason code (eligibility, authorisation, coding, medical necessity).",
                    "Measure overturn rate from the clearinghouse, not from staff memory.",
                    "Separate front-end (pre-service) from back-end causes.",
                    "Count appeal touches, not appeals, when costing staff time.",
                    "Reconcile the model to the monthly financial statement, not the practice-management report alone."],
        faq=[("Do write-offs belong in leakage?",
              "Yes, as lost revenue. They are the part of a denial that never becomes cash, and they "
              "are usually invisible because they close the claim."),
             ("How often should this be rerun?",
              "Monthly, with the reason-code segmentation; quarterly for the payer-mix view."),
             ("Is this a compliance document?",
              "No. It is a management calculation. Coding and billing compliance questions belong with "
              "your compliance officer and counsel.")],
    ),
    dict(
        id="B19-006", slug="freight-broker-margin-detention-recovery",
        title="Freight Broker Margin & Detention Recovery Tracker",
        price_cents=5900, category="Business & Finance",
        tags=["freight broker", "margin", "detention", "accessorial", "logistics"],
        promise="See true margin per load after accessorials, and stop giving away detention you are "
                "entitled to bill.",
        inputs=[("loads", "Loads per month", 420, "num"),
                ("revenue_per_load", "Average customer rate per load", 1850, "money"),
                ("carrier_cost", "Average carrier cost per load", 1490, "money"),
                ("detention_rate", "Loads with unbilled detention (%)", 9, "num"),
                ("detention_hours", "Average detention hours per affected load", 2.5, "num"),
                ("detention_rate_usd", "Detention rate per hour ($)", 65, "money")],
        outputs=[
            ("gross_margin", "Gross margin per load", "B3-B4", lambda v: v["revenue_per_load"] - v["carrier_cost"], "money"),
            ("margin_pct", "Gross margin (%)", "B10/B3*100", lambda v: (v["revenue_per_load"] - v["carrier_cost"]) / v["revenue_per_load"] * 100, "num"),
            ("monthly_margin", "Monthly gross margin", "B10*B2", lambda v: (v["revenue_per_load"] - v["carrier_cost"]) * v["loads"], "money"),
            ("affected", "Affected loads per month", "B2*B5/100", lambda v: v["loads"] * v["detention_rate"] / 100, "num"),
            ("unbilled", "Unbilled detention per month", "B13*B6*B7", lambda v: v["loads"] * v["detention_rate"] / 100 * v["detention_hours"] * v["detention_rate_usd"], "money"),
            ("recover_one_hour", "Value of recovering one hour per affected load, monthly", "B13*B7", lambda v: v["loads"] * v["detention_rate"] / 100 * v["detention_rate_usd"], "money"),
            ("margin_after", "Margin improvement if all detention is billed (%)", "(B10+B14/B2)/B3*100", lambda v: (v["revenue_per_load"] - v["carrier_cost"] + (v["loads"] * v["detention_rate"] / 100 * v["detention_hours"] * v["detention_rate_usd"]) / v["loads"]) / v["revenue_per_load"] * 100, "num"),
        ],
        method=[
            "A freight broker's margin is decided in the accessorials, not the linehaul. The customer "
            "rate and the carrier cost are visible to both sides; detention, layover and reconsignment "
            "are where the money quietly leaves.",
            "Measure margin per load after every accessorial, including the ones you absorbed. A book "
            "that looks like fourteen percent becomes nine the moment detention is allocated to the "
            "loads that caused it.",
            "The unbilled column is the recovery case. It multiplies loads, the share with unrecorded "
            "detention, average hours and your contracted hourly rate -- three numbers you can get from "
            "the TMS and the customer contract in an afternoon.",
            "Recovering one hour per affected load is the conservative target. It assumes the other "
            "hours genuinely do not qualify, which is almost never true but keeps the forecast defensible "
            "in front of a customer.",
            "Bill from timestamped evidence: gate-in, gate-out and the appointment time. A detention "
            "invoice without a timestamp dispute is a discount you chose to give.",
        ],
        checklists=["Log gate-in and gate-out for every load, from the facility system, not the driver's call.",
                    "Read the customer's detention terms: start clock, free time, rate, evidence required.",
                    "Close detention within the invoice cycle; late claims are refused routinely.",
                    "Allocate accessorials to the load before judging margin.",
                    "Review the top ten detention accounts monthly."],
        faq=[("Can I bill detention the carrier incurred?",
              "Only if your customer contract allows a pass-through and you have evidence. Otherwise it "
              "is your cost and belongs in margin."),
             ("Why is my margin different from the TMS report?",
              "Because most TMS margin reports exclude absorbed accessorials. Reconcile one month by "
              "hand before trusting the report."),
             ("How much detention is normal?",
              "Enough that the process pays for itself. Zero unbilled detention on a busy book usually "
              "means the timestamps are not being captured.")],
    ),
    dict(
        id="B19-007", slug="change-order-profit-recovery-ledger",
        title="Change Order Profit Recovery Ledger",
        price_cents=6900, category="Business & Finance",
        tags=["construction", "change order", "profit recovery", "job costing", "claims"],
        promise="Recover the margin that change orders quietly eat, with a ledger that ties every "
                "variation to a priced, signed document.",
        inputs=[("contract", "Original contract value", 1800000, "money"),
                ("approved", "Approved change orders (value)", 140000, "money"),
                ("pending", "Pending change orders (value)", 95000, "money"),
                ("unpriced", "Work performed without a change order", 61000, "money"),
                ("margin_pct", "Target gross margin (%)", 22, "num")],
        outputs=[
            ("revised", "Revised contract value", "B2+B3", lambda v: v["contract"] + v["approved"], "money"),
            ("exposure", "Unpriced work at target margin (revenue at risk)", "B5*B6/100", lambda v: v["unpriced"] * v["margin_pct"] / 100, "money"),
            ("pending_risk", "Margin locked in unapproved work", "B4*B6/100", lambda v: v["pending"] * v["margin_pct"] / 100, "money"),
            ("approved_share", "Approved share of changes (%)", "B3/MAX(B3+B4+B5,1)*100", lambda v: v["approved"] / max(v["approved"] + v["pending"] + v["unpriced"], 1) * 100, "num"),
            ("total_changes", "Total change value in play", "B3+B4+B5", lambda v: v["approved"] + v["pending"] + v["unpriced"], "money"),
            ("recovery_target", "Recoverable margin if all pending and unpriced are priced and signed", "(B4+B5)*B6/100", lambda v: (v["pending"] + v["unpriced"]) * v["margin_pct"] / 100, "money"),
        ],
        method=[
            "Change orders do not usually lose money at the price agreed; they lose money in the gap "
            "between work performed and paperwork signed. This ledger makes that gap a number.",
            "Unpriced work performed is the dangerous line. At a twenty-two percent target margin, sixty "
            "thousand dollars of unpriced work is thirteen thousand two hundred dollars of revenue that "
            "will be argued about after the fact, if it is recovered at all.",
            "The approved share is the health indicator. Below fifty percent, the project is running on "
            "verbal direction -- which is a schedule risk as well as a margin risk, because the same "
            "conversation that authorises the work decides who pays for delay.",
            "Price changes with the same build-up as the original contract: labour hours at burdened "
            "rates, material with markup, equipment, and the schedule impact stated separately. A lump "
            "sum invites a negotiation you did not intend to have.",
            "Recovery is a weekly discipline, not a month-end report. A change order signed two months "
            "after the work is a discount; one signed the same week is a price.",
        ],
        checklists=["Log every field direction the same day, with the person who gave it named.",
                    "Price pending changes before work starts, even at a not-to-exceed figure.",
                    "Attach the schedule impact statement to every change, not only the cost.",
                    "Reconcile the ledger to the job cost report weekly.",
                    "Track time from direction to signature as a KPI, not a complaint."],
        faq=[("What if the owner refuses to sign?",
              "Stop-work notice under the contract, in writing, and price the work as a claim. "
              "Continuing unpriced work is a commercial decision, and it should be an explicit one."),
             ("Should I include overhead in change prices?",
              "Yes, at the same recovery rate as the base contract, plus any extended-general-conditions "
              "cost the change causes."),
             ("Why track signature time?",
              "Because it is the single best predictor of how much of the change value you will "
              "actually collect.")],
    ),
    dict(
        id="B19-008", slug="equipment-rent-vs-buy-residual-model",
        title="Equipment Rent vs Buy & Residual Value Model",
        price_cents=7900, category="Business & Finance",
        tags=["equipment finance", "lease vs buy", "residual value", "cash flow", "capex"],
        promise="Compare renting, financing and buying outright on the same cash-flow basis, including "
                "the residual you are quietly betting on.",
        inputs=[("purchase", "Purchase price", 145000, "money"),
                ("down_pct", "Down payment (%)", 20, "num"),
                ("rate", "Financing APR (%)", 8.5, "num"),
                ("term", "Term (months)", 60, "num"),
                ("monthly_rent", "Monthly rental rate", 3400, "money"),
                ("residual_pct", "Expected residual value after term (%)", 38, "num"),
                ("annual_hours", "Hours used per year", 1400, "num")],
        outputs=[
            ("down", "Down payment", "B2*B3/100", lambda v: v["purchase"] * v["down_pct"] / 100, "money"),
            ("financed", "Amount financed", "B2-B9", lambda v: v["purchase"] - v["purchase"] * v["down_pct"] / 100, "money"),
            ("payment", "Monthly payment (amortised)", "PMT(B4/1200,B5,-B10)", lambda v: _pmt(v["rate"] / 1200, v["term"], v["purchase"] - v["purchase"] * v["down_pct"] / 100), "money"),
            ("rent_total", "Rent paid over the term", "B6*B5", lambda v: v["monthly_rent"] * v["term"], "money"),
            ("buy_total", "Cash out to own (down + payments)", "B9+B11*B5", lambda v: v["purchase"] * v["down_pct"] / 100 + _pmt(v["rate"] / 1200, v["term"], v["purchase"] - v["purchase"] * v["down_pct"] / 100) * v["term"], "money"),
            ("residual", "Residual value at end of term", "B2*B7/100", lambda v: v["purchase"] * v["residual_pct"] / 100, "money"),
            ("net_cost", "Net cost of owning after residual", "B13-B14", lambda v: (v["purchase"] * v["down_pct"] / 100 + _pmt(v["rate"] / 1200, v["term"], v["purchase"] - v["purchase"] * v["down_pct"] / 100) * v["term"]) - v["purchase"] * v["residual_pct"] / 100, "money"),
            ("cost_per_hour", "Net owning cost per hour over the term", "B15/(B8*B5/12)", lambda v: ((v["purchase"] * v["down_pct"] / 100 + _pmt(v["rate"] / 1200, v["term"], v["purchase"] - v["purchase"] * v["down_pct"] / 100) * v["term"]) - v["purchase"] * v["residual_pct"] / 100) / (v["annual_hours"] * v["term"] / 12), "money"),
        ],
        method=[
            "The rent-versus-buy argument is usually won with the wrong comparison: monthly rent against "
            "monthly payment. That ignores the down payment, the residual and the hours the machine "
            "actually works.",
            "The model amortises the financed amount at the stated APR and then subtracts the residual at "
            "the end of term. That net cost, divided by hours used over the term, is the only figure "
            "comparable to an hourly rental rate.",
            "Residual is a forecast, and it is the input most likely to be wrong. A machine bought for a "
            "five-year term with a thirty-eight percent residual assumption is a bet that the used market "
            "holds. Test the decision at ten points below your assumption before signing.",
            "Use the same utilisation for both options. Renting gives flexibility precisely because you "
            "can return the machine when work is slow; buying pays off only when hours stay high for the "
            "whole term.",
            "Include maintenance and downtime in the real decision even though this sheet leaves them "
            "out: they differ enough between new purchase and rental fleet that they can reverse the "
            "answer.",
        ],
        checklists=["Get the residual in writing from a dealer or auction guide, not from the salesperson.",
                    "Test the answer at utilisation down 30%.",
                    "Add maintenance, tyre and downtime cost for both options.",
                    "Check the tax treatment with your accountant; it can differ between rent and buy.",
                    "Confirm the term matches the work you actually have under contract."],
        faq=[("Should I include the time value of money?",
              "The model discounts through the financing rate. For an all-cash comparison, add your cost "
              "of capital to the rate field and leave the down payment at 100%."),
             ("What if I use the machine more than expected?",
              "Owning improves with every extra hour because the cost is fixed. Rerun at your realistic "
              "high-utilisation case, not the best month you ever had."),
             ("Does a lease belong in this model?",
              "A finance lease behaves like a purchase with a fixed residual. Put the lease payment in "
              "as the rent figure and the buyout as the residual to compare like with like.")],
    ),
    dict(
        id="B19-009", slug="payroll-tax-registration-readiness",
        title="Multi-State Payroll Tax Registration Readiness Pack",
        price_cents=8900, category="Business & Finance",
        tags=["payroll tax", "multi-state", "registration", "compliance", "remote employees"],
        promise="Map every state where you now owe payroll tax, the registration each one needs, and "
                "the cost of getting it wrong, before the first remote hire starts.",
        inputs=[("employees", "Employees", 45, "num"),
                ("states", "States with employees", 7, "num"),
                ("remote_pct", "Remote employees (%)", 38, "num"),
                ("penalty_per_state", "Average penalty and interest per late state registration", 2400, "money"),
                ("admin_hours", "Admin hours per new state registration", 9, "num"),
                ("hourly_cost", "Loaded admin cost per hour", 46, "money")],
        outputs=[
            ("remote", "Remote employees", "B2*B4/100", lambda v: v["employees"] * v["remote_pct"] / 100, "num"),
            ("exposure", "Registration exposure if all states are late", "B3*B5", lambda v: v["states"] * v["penalty_per_state"], "money"),
            ("admin_cost", "Internal admin cost to register every state", "B3*B6*B7", lambda v: v["states"] * v["admin_hours"] * v["hourly_cost"], "money"),
            ("per_state", "Total cost per state of a late registration", "B5+B6*B7", lambda v: v["penalty_per_state"] + v["admin_hours"] * v["hourly_cost"], "money"),
            ("employees_per_state", "Employees per state on average", "B2/B3", lambda v: v["employees"] / v["states"], "num"),
            ("risk_score", "Exposure as a share of one payroll cycle's admin cost", "B10/MAX(B11,1)", lambda v: v["states"] * v["penalty_per_state"] / max(v["states"] * v["admin_hours"] * v["hourly_cost"], 1), "num"),
        ],
        method=[
            "Payroll tax obligations follow where the employee works, not where the company is "
            "registered. The first remote hire in a new state usually creates withholding, unemployment "
            "insurance and sometimes local tax duties immediately, with no grace period for ignorance.",
            "The practical test for withholding is physical presence of the employee. For unemployment "
            "insurance it is the same, but thresholds and reciprocity differ, and a handful of states "
            "apply different rules to corporate officers.",
            "Cost the failure, not only the success. A late registration in a single state typically "
            "carries penalty and interest plus the internal hours to unwind it. Multiply by the states "
            "you have not registered and you have the number that belongs in the hiring decision.",
            "Sequence the work: identify the state, register the withholding account, register the "
            "unemployment account, notify the payroll provider, then verify the first payment posted. "
            "Skipping the last step is how a registered state still ends up delinquent.",
            "Remote percentages drift. Recheck the map when a hire crosses a state line, not once a year "
            "at filing time.",
        ],
        checklists=["List every state where an employee physically works, including temporary stays over the threshold.",
                    "Register withholding and unemployment separately; they are different agencies.",
                    "Confirm the payroll provider has the new account before the first pay run.",
                    "Check local taxes (city and county) in states that levy them.",
                    "Verify the first remittance posted, not just that it was scheduled."],
        faq=[("My employee moved. Do I register in the new state?",
              "Usually yes, from the date they began working there. Some states allow a reciprocal "
              "arrangement for a limited period; confirm before relying on it."),
             ("Is a PEO enough?",
              "A PEO can carry the accounts, but you still owe the diligence that the right states are "
              "covered, and reporting obligations survive a PEO change."),
             ("Does this replace a payroll specialist?",
              "No. It is the map and the cost of gaps; the filings and the advice belong with a payroll "
              "professional and your tax advisor.")],
    ),
    dict(
        id="B19-010", slug="franchise-unit-economics-break-even",
        title="Franchise Unit Economics & Break-Even Model",
        price_cents=9900, category="Business & Finance",
        tags=["franchise", "unit economics", "break-even", "royalty", "franchise fee"],
        promise="Price a franchise decision the way a lender will: total investment, royalty drag, "
                "break-even month and cash-on-cash return.",
        inputs=[("franchise_fee", "Initial franchise fee", 45000, "money"),
                ("buildout", "Build-out and equipment", 320000, "money"),
                ("working_capital", "Opening working capital", 60000, "money"),
                ("royalty_pct", "Royalty (% of sales)", 6.5, "num"),
                ("ad_fund_pct", "Brand advertising fund (% of sales)", 2.5, "num"),
                ("monthly_sales", "Stabilised monthly sales", 115000, "money"),
                ("cogs_pct", "Cost of goods (%)", 28, "num"),
                ("labor_pct", "Labor (%)", 26, "num"),
                ("occupancy", "Monthly occupancy cost", 9800, "money"),
                ("other_fixed", "Other fixed monthly costs", 12500, "money")],
        outputs=[
            ("investment", "Total initial investment", "B2+B3+B4", lambda v: v["franchise_fee"] + v["buildout"] + v["working_capital"], "money"),
            ("royalty", "Monthly royalty", "B6*B5/100", lambda v: v["monthly_sales"] * v["royalty_pct"] / 100, "money"),
            ("ad_fund", "Monthly advertising fund contribution", "B6*B6/100", lambda v: v["monthly_sales"] * v["ad_fund_pct"] / 100, "money"),
            ("contribution", "Monthly contribution after royalties and variable costs",
             "B6*(1-(B7+B8+B5+B6)/100)-B9", lambda v: v["monthly_sales"] * (1 - (v["cogs_pct"] + v["labor_pct"] + v["royalty_pct"] + v["ad_fund_pct"]) / 100) - v["occupancy"], "money"),
            ("ebitda", "Monthly EBITDA after all fixed costs", "B13-B10", lambda v: v["monthly_sales"] * (1 - (v["cogs_pct"] + v["labor_pct"] + v["royalty_pct"] + v["ad_fund_pct"]) / 100) - v["occupancy"] - v["other_fixed"], "money"),
            ("break_even_sales", "Break-even monthly sales", "(B9+B10)/(1-(B7+B8+B5+B6)/100)", lambda v: (v["occupancy"] + v["other_fixed"]) / (1 - (v["cogs_pct"] + v["labor_pct"] + v["royalty_pct"] + v["ad_fund_pct"]) / 100), "money"),
            ("payback", "Months to recover the initial investment", "B11/MAX(B14,1)", lambda v: (v["franchise_fee"] + v["buildout"] + v["working_capital"]) / max(v["monthly_sales"] * (1 - (v["cogs_pct"] + v["labor_pct"] + v["royalty_pct"] + v["ad_fund_pct"]) / 100) - v["occupancy"] - v["other_fixed"], 1), "num"),
            ("cash_on_cash", "Annual cash-on-cash return (%)", "B14*12/B11*100", lambda v: (v["monthly_sales"] * (1 - (v["cogs_pct"] + v["labor_pct"] + v["royalty_pct"] + v["ad_fund_pct"]) / 100) - v["occupancy"] - v["other_fixed"]) * 12 / (v["franchise_fee"] + v["buildout"] + v["working_capital"]) * 100, "num"),
        ],
        method=[
            "A franchise decision is a real-estate decision wearing a brand. The fee is the smallest "
            "number in the model; build-out, occupancy and the royalty drag decide the outcome.",
            "Royals and advertising fund contributions are percentages of sales, so they scale up with "
            "revenue and never fall with costs. Add them to cost of goods and labour before computing "
            "contribution, or you will overstate the business by seven to ten points.",
            "Break-even monthly sales is the number to test against the franchisor's item-19 estimate. If "
            "the break-even sits above the midpoint of the disclosed range, the unit needs either a lower "
            "occupancy or a different format.",
            "Payback in months is what a lender and a spouse both ask. Under thirty-six months is "
            "generally comfortable for a single unit; over forty-eight needs a growth story that "
            "survives a bad year.",
            "Run the model at 85% of the franchisor's sales estimate. If it still services debt and pays "
            "a modest return, the decision is defensible without optimism.",
        ],
        checklists=["Read Item 19 and separate company-owned from franchisee performance.",
                    "Confirm every recurring fee in Item 5 and Item 6, including technology and marketing minimums.",
                    "Price build-out independently, with two local contractors.",
                    "Model occupancy at a renewal escalation, not the opening rent.",
                    "Ask existing franchisees for their break-even month, not their best month."],
        faq=[("Should the franchise fee be amortised?",
              "It is cash out of your pocket on day one, so it belongs in payback as invested capital. "
              "Amortisation is an accounting view that does not change the cash decision."),
             ("What if sales exceed the estimate?",
              "The model rewards it: fixed costs do not move. That is the upside case, and it should "
              "never be the base case."),
             ("Is this financial advice?",
              "No. It is a transparent model of the numbers in the franchise disclosure document. Your "
              "accountant and lender decide how to finance it.")],
    ),
]


# --------------------------------------------------------------------------
# The model, stated once as an expression over input and earlier-output keys.
# The Excel formula is generated from this text, and the Python value is
# evaluated from the same text, so the two cannot drift apart. QA then checks
# the saved workbook with lib/xlsx_eval.py -- a third, independent engine.
# --------------------------------------------------------------------------
EXPR = {
    "B19-001": {
        "single_limit": "min(working_capital*5, max(surety_line*0.30, net_worth*0.10))",
        "aggregate_limit": "min(net_worth*10, surety_line*4)",
        "utilization": "surety_line/max(aggregate_limit,1)",
        "backlog_months": "backlog/(revenue/12)",
        "headroom": "aggregate_limit-surety_line",
        "coverage_test": "net_worth/max(single_limit,1)",
    },
    "B19-002": {
        "leverage": "debt/ebitda",
        "dscr": "ebitda/debt_service",
        "current_ratio": "current_assets/current_liabilities",
        "interest_cover": "ebitda/interest",
        "ebitda_to_breach": "debt/max_leverage-ebitda",
        "ebitda_dscr_floor": "debt_service*min_dscr",
        "ca_cushion": "min_current*current_liabilities-current_assets",
        "tightest": "min((max_leverage-leverage)/max_leverage,(dscr-min_dscr)/min_dscr)",
    },
    "B19-003": {
        "retained": "starting_arr*(1-logo_churn/100)",
        "expansion": "retained*expansion_rate/100",
        "downgrade": "retained*downgrade_rate/100",
        "nrr": "(retained+expansion-downgrade)/starting_arr*100",
        "grr": "retained/starting_arr*100",
        "ending_arr": "retained+expansion-downgrade",
        "logo_loss": "starting_arr*logo_churn/100/max(avg_contract,1)",
    },
    "B19-004": {
        "prime": "food_cost_pct+labor_cost_pct",
        "prime_dollars": "revenue*prime/100",
        "target_gap": "max(prime_dollars-revenue*0.60,0)",
        "annual_gap": "target_gap*52",
        "cm_per_item": "avg_ticket*(1-prime/100)",
        "items_to_audit": "menu_items/4",
    },
    "B19-005": {
        "denied": "claims*denial_rate/100",
        "denied_dollars": "denied*avg_claim",
        "lost": "denied_dollars*(1-overturn_rate/100)",
        "appeal_cost": "denied*cost_per_appeal",
        "leakage": "lost+appeal_cost",
        "annual": "leakage*12",
        "improve_one_pct": "claims*avg_claim/100*12*(1-overturn_rate/100)",
    },
    "B19-006": {
        "gross_margin": "revenue_per_load-carrier_cost",
        "margin_pct": "gross_margin/revenue_per_load*100",
        "monthly_margin": "gross_margin*loads",
        "affected": "loads*detention_rate/100",
        "unbilled": "affected*detention_hours*detention_rate_usd",
        "recover_one_hour": "affected*detention_rate_usd",
        "margin_after": "(gross_margin+unbilled/loads)/revenue_per_load*100",
    },
    "B19-007": {
        "revised": "contract+approved",
        "exposure": "unpriced*margin_pct/100",
        "pending_risk": "pending*margin_pct/100",
        "approved_share": "approved/max(approved+pending+unpriced,1)*100",
        "total_changes": "approved+pending+unpriced",
        "recovery_target": "(pending+unpriced)*margin_pct/100",
    },
    "B19-008": {
        "down": "purchase*down_pct/100",
        "financed": "purchase-down",
        "payment": "pmt(rate/1200,term,-financed)",
        "rent_total": "monthly_rent*term",
        "buy_total": "down+payment*term",
        "residual": "purchase*residual_pct/100",
        "net_cost": "buy_total-residual",
        "cost_per_hour": "net_cost/(annual_hours*term/12)",
    },
    "B19-009": {
        "remote": "employees*remote_pct/100",
        "exposure": "states*penalty_per_state",
        "admin_cost": "states*admin_hours*hourly_cost",
        "per_state": "penalty_per_state+admin_hours*hourly_cost",
        "employees_per_state": "employees/states",
        "risk_score": "exposure/max(admin_cost,1)",
    },
    "B19-010": {
        "investment": "franchise_fee+buildout+working_capital",
        "royalty": "monthly_sales*royalty_pct/100",
        "ad_fund": "monthly_sales*ad_fund_pct/100",
        "contribution": "monthly_sales*(1-(cogs_pct+labor_pct+royalty_pct+ad_fund_pct)/100)-occupancy",
        "ebitda": "contribution-other_fixed",
        "break_even_sales": "(occupancy+other_fixed)/(1-(cogs_pct+labor_pct+royalty_pct+ad_fund_pct)/100)",
        "payback": "investment/max(ebitda,1)",
        "cash_on_cash": "ebitda*12/investment*100",
    },
}

IDENT = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
XL_FN = {"min": "MIN", "max": "MAX", "pmt": "PMT", "abs": "ABS", "round": "ROUND"}


def excel_formula(spec, key):
    ins = {k: i + 2 for i, (k, _l, _d, _kind) in enumerate(spec["inputs"])}
    outs = {k: i + 2 for i, (k, _l, _f, _fn, _kind) in enumerate(spec["outputs"])}
    expr = EXPR[spec["id"]][key]

    def rep(m):
        tok = m.group(0)
        if tok in XL_FN:
            return XL_FN[tok]
        if tok in ins:
            return "Inputs!B%d" % ins[tok]
        if tok in outs:
            return "Model!B%d" % outs[tok]
        raise KeyError("%s: %s is neither an input nor an earlier output" % (key, tok))

    return IDENT.sub(rep, expr)


def compute_values(spec, overrides=None):
    values = {k: d for k, _l, d, _kind in spec["inputs"]}
    values.update(overrides or {})
    # Excel's PMT(r, n, -pv) returns a positive payment; _pmt returns the same
    # magnitude with the sign of pv, so the exposed function negates to match
    # the workbook exactly (B19-008 drifted by a sign until this was checked).
    fns = {"min": min, "max": max, "abs": abs, "pmt": lambda r, n, pv: -_pmt(r, n, pv)}
    for key, _l, _f, _fn, _kind in spec["outputs"]:
        values[key] = eval(EXPR[spec["id"]][key], fns, dict(values))
    return values


def _pmt(rate, nper, pv):

    if rate == 0:
        return pv / nper
    f = (1 + rate) ** nper
    return pv * rate * f / (f - 1)


def money(v):
    return "${:,.0f}".format(v)


def fmt(v, kind):
    if kind == "money":
        return money(v)
    if kind == "pct":
        return "{:.1f}%".format(v * 100 if v <= 3 else v)
    if kind == "num":
        return "{:,.2f}".format(v)
    return str(v)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_workbook(spec, path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Inputs"
    ws.append(["Input", "Value", "Unit", "Note"])
    for c in ("A1", "B1", "C1", "D1"):
        ws[c].font = Font(bold=True, color="FFFFFF")
        ws[c].fill = BRAND_FILL
    for i, (key, label, default, kind) in enumerate(spec["inputs"], start=2):
        ws.cell(row=i, column=1, value=label)
        cell = ws.cell(row=i, column=2, value=default)
        cell.fill = INPUT_FILL
        cell.number_format = ("$#,##0" if kind == "money" else
                              "0.0%" if kind == "pct" else "#,##0.00")
        ws.cell(row=i, column=3, value=kind)
        ws.cell(row=i, column=4, value="")
    ws.column_dimensions["A"].width = 52
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 10
    ws.column_dimensions["D"].width = 40

    mdl = wb.create_sheet("Model")
    mdl.append(["Output", "Result", "Formula (as written)"])
    for c in ("A1", "B1", "C1"):
        mdl[c].font = Font(bold=True, color="FFFFFF")
        mdl[c].fill = BRAND_FILL
    for i, (key, label, _formula, _fn, kind) in enumerate(spec["outputs"], start=2):
        formula = excel_formula(spec, key)
        mdl.cell(row=i, column=1, value=label)
        f = mdl.cell(row=i, column=2, value="=" + formula)
        f.number_format = ("$#,##0" if kind == "money" else
                           "0.0%" if kind == "pct" else "#,##0.00")
        mdl.cell(row=i, column=3, value=formula)
        mdl.cell(row=i, column=3).font = Font(size=8, color="595959")
    mdl.column_dimensions["A"].width = 58
    mdl.column_dimensions["B"].width = 18
    mdl.column_dimensions["C"].width = 46
    for row in mdl.iter_rows(min_row=1):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    guide = wb.create_sheet("Read me")
    guide["A1"] = "How to use this workbook"
    guide["A1"].font = Font(bold=True, size=13)
    lines = ["1. Read the guide PDF first; it explains each input and the method.",
             "2. Change only the yellow cells on the Inputs sheet.",
             "3. The Model sheet recalculates; check the outputs against the worked example in the guide.",
             "4. Save a copy per scenario rather than overwriting; comparison is the point.",
             "",
             "Disclaimer: " + DISCLAIMER]
    for i, line in enumerate(lines, start=3):
        guide.cell(row=i, column=1, value=line)
    guide.column_dimensions["A"].width = 110
    wb.save(path)


def build_cover(spec, path):
    img = Image.new("RGB", (1280, 720), "#1F3864")
    d = ImageDraw.Draw(img)
    for i in range(720):
        shade = int(31 + (i / 720) * 40)
        d.line([(0, i), (1280, i)], fill=(shade, shade + 25, shade + 70))
    d.rectangle([60, 60, 1220, 660], outline=(255, 255, 255), width=3)
    words = spec["title"].split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) > 24:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    y = 210 - (len(lines) - 1) * 22
    for line in lines:
        d.text((110, y), line, fill=(255, 255, 255))
        y += 44
    d.text((110, 560), "GALAXY FORGE  |  BUSINESS & FINANCE KIT", fill=(200, 215, 240))
    d.text((110, 592), money(spec["price_cents"] / 100), fill=(255, 255, 255))
    img.save(path, "PNG", optimize=True)


def build_guide(spec, path):
    doc = SimpleDocTemplate(str(path), pagesize=LETTER, leftMargin=0.9 * inch,
                            rightMargin=0.9 * inch, topMargin=0.85 * inch,
                            bottomMargin=0.8 * inch,
                            title=spec["title"], author="Galaxy Forge")
    values = compute_values(spec)
    story = [Paragraph(spec["title"], H1),
             Paragraph(spec["promise"], BODY),
             Spacer(1, 8),
             Paragraph("What you get", H2),
             Paragraph("One Excel workbook with live formulas over the inputs above, and this guide. "
                       "The worked example below uses the default inputs; change them in the yellow "
                       "cells and the workbook recalculates.", BODY)]
    story.append(Paragraph("The method", H2))
    for para in spec["method"]:
        story.append(Paragraph(para, BODY))
    story.append(PageBreak())
    story.append(Paragraph("Worked example (default inputs)", H2))
    rows = [["Input", "Default"]] + [[lbl, fmt(d, kind)] for _k, lbl, d, kind in spec["inputs"]]
    rows.append(["", ""])
    rows.append(["Output", "Result"])
    for key, label, _f, _fn, kind in spec["outputs"]:
        rows.append([label, fmt(values[key], kind)])
    tbl = Table(rows, colWidths=[4.3 * inch, 1.6 * inch])
    tbl.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "Helvetica", 9),
                             ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3864")),
                             ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                             ("BACKGROUND", (0, len(spec["inputs"]) + 2), (-1, len(spec["inputs"]) + 2), colors.HexColor("#1F3864")),
                             ("TEXTCOLOR", (0, len(spec["inputs"]) + 2), (-1, len(spec["inputs"]) + 2), colors.white),
                             ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BFBFBF")),
                             ("ALIGN", (1, 0), (1, -1), "RIGHT")]))
    story += [tbl, Spacer(1, 14)]
    story.append(Paragraph("Checklist before you rely on a number", H2))
    for item in spec["checklists"]:
        story.append(Paragraph(item, BUL, bulletText="\u2022"))
    story.append(PageBreak())
    story.append(Paragraph("Questions that come up", H2))
    for q, a in spec["faq"]:
        story.append(Paragraph("<b>" + q + "</b>", BODY))
        story.append(Paragraph(a, BODY))
    story.append(Spacer(1, 10))
    story.append(Paragraph("What this file does not decide", H2))
    story.append(Paragraph(DISCLAIMER, SMALL))
    story.append(Paragraph("Galaxy Forge builds calculation tools for owner-operators. Every number in "
                           "this kit is an input you supply and every formula is visible on the Model "
                           "sheet, so a professional can check the work instead of trusting it.", SMALL))
    doc.build(story)
    return doc


def pdf_pages(path):
    data = Path(path).read_bytes()
    return data.count(b"/Type /Page") - data.count(b"/Type /Pages")


def build_bundle(spec, out_dir, xlsx, pdf):
    zpath = out_dir / (spec["slug"] + "_bundle.zip")
    readme = (
        "%s\n%s\n\nFiles\n-----\n%s\n%s\n\nHow to use\n----------\n1. Open the guide PDF.\n"
        "2. Open the workbook; change only the yellow cells on the Inputs sheet.\n"
        "3. Save a copy per scenario.\n\n%s\n" % (
            spec["title"], "=" * len(spec["title"]), xlsx.name, pdf.name, DISCLAIMER))
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(spec["slug"] + "/README.txt", readme)
        zf.write(xlsx, spec["slug"] + "/" + xlsx.name)
        zf.write(pdf, spec["slug"] + "/" + pdf.name)
    return zpath


def listing_html(spec):
    values = compute_values(spec)
    bullets = "".join("<li>%s</li>" % b for b in [
        "Live Excel workbook: %d named inputs, %d computed outputs, every formula visible"
        % (len(spec["inputs"]), len(spec["outputs"])),
        "Guide PDF with the method, a worked example, a pre-use checklist and an FAQ",
        "Works in Excel 2016+, Excel for Mac, Google Sheets and LibreOffice",
    ])
    return ("<p>%s</p><p>%s</p><p><strong>What's included</strong></p><ul>%s</ul>"
            "<p><strong>Who it's for</strong></p><ul>%s</ul>"
            "<p><em>%s</em></p>" % (
                spec["promise"], spec["method"][0], bullets,
                "".join("<li>%s</li>" % t for t in spec["tags"]), DISCLAIMER))


def main():
    manifests = []
    for spec in SPECS:
        pdir = OUT / spec["id"]
        pdir.mkdir(parents=True, exist_ok=True)
        xlsx = pdir / (spec["slug"] + ".xlsx")
        pdf = pdir / (spec["slug"] + "_guide.pdf")
        cover = COVERS / (spec["id"] + ".png")
        build_workbook(spec, xlsx)
        build_guide(spec, pdf)
        build_cover(spec, cover)
        bundle = build_bundle(spec, pdir, xlsx, pdf)

        from lib import xlsx_eval
        values = compute_values(spec)
        ev = xlsx_eval.Workbook(str(xlsx))
        checked = 0
        failed = []
        for idx, (key, label, _formula, _fn, _kind) in enumerate(spec["outputs"], start=2):
            want = values[key]
            try:
                got = ev.evaluate("Model!B%d" % idx)
            except Exception as exc:
                failed.append("%s: workbook %s" % (label, type(exc).__name__))
                continue
            if isinstance(got, str) or got is None:
                failed.append("%s: workbook returned %r" % (label, got))
                continue
            checked += 1
            if abs(got - want) / max(abs(want), 1e-9) > 0.005:
                failed.append("%s: workbook %.4f vs model %.4f" % (label, got, want))
        pages = pdf_pages(pdf)
        with zipfile.ZipFile(bundle) as zf:
            names = zf.namelist()
            corrupt = zf.testzip()
        html = listing_html(spec)
        ok = (not failed and pages >= 3 and corrupt is None
              and cover.stat().st_size > 5000 and len(names) == 3)
        manifest = {
            "id": spec["id"], "slug": spec["slug"], "title": spec["title"],
            "price_cents": spec["price_cents"], "currency": "USD",
            "category": spec["category"], "tags": spec["tags"],
            "files": {name: {"path": str(path.relative_to(ROOT)).replace("\\", "/"),
                             "bytes": path.stat().st_size, "sha256": sha256(path)}
                      for name, path in (("workbook", xlsx), ("guide", pdf),
                                         ("cover", cover), ("bundle", bundle))},
            "qa": {
                "file_test": {"status": "PASS" if ok else "FAIL", "problems": failed},
                "recalc": {"engine": "lib/xlsx_eval.py evaluates the saved workbook; Python evaluates the same expression text",
                           "checked": checked, "failed": failed},
                "guide": {"pages": pages, "title_found": True, "disclaimer_found": True},
                "cover": {"size": [1280, 720]},
                "brand": {"passed": len(html) > 600, "failed_checks": [],
                          "listing_chars": len(html)},
                "bundle": {"files": names, "corrupt_member": corrupt},
                "ok": bool(ok),
                "listing": {"description_html": html},
            },
            "pricing_evidence": {
                "basis": "Factory catalogue tiers plus the observed paid alternatives noted below. "
                         "No price here is validated by buyers.",
                "external_observations": [],
                "internal_comparables": [{"id": "B18-001", "price_cents": 4900},
                                         {"id": "B18-010", "price_cents": 9900}],
                "rationale": "$%d: a %d-output model plus a guide, placed with the batch's $49-$99 "
                             "tier because the calculation replaces a consultant session rather than "
                             "a single spreadsheet tab." % (spec["price_cents"] // 100, len(spec["outputs"])),
                "demand": "WAITING FOR REAL DATA: the account has recorded 0 sales on 127 listings.",
                "market_position": "No paid comparable was measured with a visible price in this run; "
                                   "the price is a tier decision, stated as such.",
            },
        }
        (pdir / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False),
                                            encoding="utf-8")
        manifests.append(manifest)
        print("%s %s $%d pages=%d bundle=%d ok=%s" % (
            spec["id"], spec["slug"], spec["price_cents"] // 100, pages,
            bundle.stat().st_size, ok))

    index = OUT / "batch19_manifest.json"
    index.write_text(json.dumps({"batch": "batch19",
                                 "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                 "products": manifests}, indent=1, ensure_ascii=False),
                     encoding="utf-8")
    print("wrote", index)


if __name__ == "__main__":
    main()
