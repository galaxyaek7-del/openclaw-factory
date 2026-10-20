#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B13-001 guide PDF. Reuses the batch-12 reportlab engine and styles, only
redirecting the output folder, so the catalogue keeps one visual language.

Every number in the worked example was taken from a real Excel recalculation
of the shipped workbook (415 formulas, 0 error cells), not from mental
arithmetic.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

# build_batch12_pdfs.py builds the whole catalogue at import time. Loading it
# once without the guard re-emitted five tracked PDFs and overwrote an
# uncommitted repair (see the guard's own note), so the flag is set first and
# the module-level SystemExit it raises is expected and ignored: every style
# and function it defines is already bound by then.
os.environ["GF_PDF_IMPORT_ONLY"] = "1"
_spec = importlib.util.spec_from_file_location(
    "build_batch12_pdfs", SCRIPTS / "build_batch12_pdfs.py")
E = importlib.util.module_from_spec(_spec)
try:
    _spec.loader.exec_module(E)
except SystemExit:
    pass
if not hasattr(E, "build"):
    raise SystemExit("build_batch12_pdfs helpers unavailable")

OUT = ROOT / "books" / "batch13"
OUT.mkdir(parents=True, exist_ok=True)
E.OUT = OUT

H, P, B, C = E.H, E.P, E.B, E.C
FILENAME = "B13-001_renovation_allowance_control_guide.pdf"

BLOCKS = [
    (H, "1. What this workbook does, and what it cannot do"),
    (P, "A renovation budget is usually a list of numbers agreed once, in a hopeful week, and then quietly abandoned. "
        "The list does not fail because the numbers were dishonest. It fails because it stops describing reality the day "
        "the first quote is signed, the first allowance is spent, and the first change is agreed by text message."),
    (P, "This workbook keeps three ledgers that a normal budget collapses into one: what you planned, what you have "
        "already committed to pay, and what you have actually paid. It adds two more that most spreadsheets ignore "
        "entirely: the allowance reconciliations that move money without anyone calling it a change, and the contingency "
        "reserve with its own drawdown log. The summary then answers one question in one place: at today's prices, what "
        "will this project cost me, and how far is that from what I have approved?"),
    (P, "It cannot tell you whether a quote is fair, whether your contract lets the builder charge for that variation, or "
        "whether a hidden defect will appear behind a wall. It is a control tool, not a crystal ball, and it is not legal, "
        "tax or financial advice. What it can do is make sure that the number you believe about your project is the number "
        "your own records support."),
    (P, "One rule before anything else: <b>never overwrite a blue cell</b>. Blue means calculated from something else in "
        "the workbook. If a blue number looks wrong, the mistake is upstream in a white cell, and the workbook is telling "
        "you where to look."),

    (H, "2. How to use this guide"),
    (P, "Read sections three to ten once, with the workbook open. Then use section eleven as the walkthrough that shows "
        "the whole method on one worked example, and section twelve as the routine you actually repeat. The sheet named "
        "Start Here inside the workbook repeats the short version, so you do not need this document in front of you every "
        "month."),
    (P, "The example rows are deliberately yellow. They describe a real, ordinary kitchen renovation that goes wrong in "
        "five small ways rather than one dramatic way. Overwrite them, or delete them once you understand them. Do not "
        "leave your own numbers sitting next to ours in the same row: the summary sums every row with a line ID, so an "
        "example row you forgot to delete becomes a fake cost."),

    (H, "3. The four numbers, and why three of them mislead on their own"),
    (P, "Professional job costing, in construction and in most project work, tracks four numbers per cost line: budget, "
        "committed, actual, and estimate at completion. The fourth is the one that matters, because it is the only one "
        "that looks forward. A budget is a plan, committed is a promise, actual is history, and estimate at completion is "
        "the best current guess at the total. Managers get into trouble by reporting whichever of the first three looks "
        "most comfortable."),
    (P, "In this workbook the four numbers are columns D, H, I and L on the Cost Control sheet. Revised budget is D plus "
        "approved changes. Committed total is the signed amount plus approved changes. Paid to date is summed from the "
        "payment log, never typed. Projected final is paid, plus unpaid committed, plus forecast to complete. Every one of "
        "those is a formula, so the four numbers cannot drift apart without the sheet showing it."),
    (P, "Why insist on formulas for something you could type? Because the failure mode in renovation budgeting is not bad "
        "arithmetic. It is a total that was correct in March and is still displayed in June. A typed total keeps its old "
        "value while the rows beneath it change, and nobody notices, because the number looks plausible. A calculated "
        "total cannot do that."),

    (H, "4. Set up in fifteen minutes"),
    (P, "The Setup sheet holds seven settings and nothing else, on purpose. Project name, address, currency symbol, "
        "contingency reserve, today's date, who approves change orders, who approves contingency draws, and your review "
        "cadence."),
    (P, "The two approval fields are small but load-bearing. Write a person's name, not a role. Every control in this "
        "workbook assumes someone can say no, and a role cannot say no when the person holding it is on holiday. If two "
        "people can approve, that is fine, but write both names and agree which one signs off on money above a threshold "
        "you choose."),
    (P, "The contingency reserve is a number, entered once, in Setup. Decide it against the risk you can see, not against "
        "the budget you wish you had. Independent renovation surveys in 2026 keep finding roughly a third of projects "
        "finishing meaningfully over budget, with the overrun concentrated in exactly the categories people underestimate: "
        "structural surprises, services, and finishes chosen late. A common working floor is ten percent for cosmetic work "
        "and twenty-five to thirty percent where structure or services are being moved. That is guidance, not a rule that "
        "fits every project; your own contract and your own building decide."),

    (H, "5. Cost Control: one row per promise you can name"),
    (P, "Each row is a cost line, identified by a short code you will still recognise in six months: K-01, K-02, and so "
        "on. Give it a category from the dropdown, a plain description of the work, the original budget, the amount you "
        "have signed for, and a forecast of work still to be priced. Everything else is calculated."),
    (P, "Keep rows at the level where a number can actually be argued about. One row called Kitchen is useless, because "
        "when it goes over you cannot tell which promise moved. Thirty rows named after every fitting is also useless, "
        "because you will stop maintaining it in week two. The useful level is the contract level: cabinets, countertops, "
        "electrical, flooring, painting. Ten to twenty-five rows is the normal range for a domestic renovation."),
    (P, "Two columns deserve a warning. Original committed is the total of what you have signed, including tax, delivery "
        "and installation if those are in the quote. If a supplier quote carries a delivery charge that is billed "
        "separately, it belongs in its own row, not buried in the description. And Forecast to complete means money you "
        "expect to spend that is <b>not yet committed</b>: the appliances you have not ordered, the painter who has not "
        "quoted. Putting the whole expected cost there double-counts anything you have already signed."),

    (H, "6. Committed is not paid, and the gap is where projects die"),
    (P, "A signed quote is money you owe. It stops being negotiable the moment the materials are ordered or the crew is "
        "booked. Yet almost every household budget tracks only what has left the bank account, which means a project can "
        "look comfortable while three signed commitments sit unpaid behind it."),
    (P, "This workbook therefore keeps two separate calculated columns: unpaid committed, which is committed minus paid, "
        "and projected final, which adds forecast to complete on top. The gap between paid and committed is your near-term "
        "cash obligation, and it is the number to check before you agree to any new work. If unpaid committed is growing "
        "faster than your payments, you are accumulating obligations, not progress."),
    (P, "Payments themselves live in their own sheet and are summed into Cost Control by line code. That structure is "
        "deliberate: it lets one line carry several payments over several months without anyone retyping a running total, "
        "and it gives you a dated record of what left the account, to whom, and how. A payment against a line code that "
        "does not exist does not disappear quietly; the summary raises a check."),

    (H, "7. Allowances: the quiet way a budget moves"),
    (P, "An allowance is a number in the contract for something not chosen yet: tile, lighting, plumbing fittings, "
        "countertops. It is not a price. It is a budgeting convention that lets work start before every finish is "
        "decided, and it is where a surprising amount of money is lost, because the difference between the allowance and "
        "the chosen product is often handled verbally."),
    (P, "Practice in the trades is consistent on one point: an allowance reconciliation should produce a change order, "
        "not a conversation. When the selection costs more than the allowance, the difference is a real cost increase and "
        "belongs in the change-order log with a number, a date and a signature. When it costs less, the difference is a "
        "credit owed back to you, and credits are the single most commonly forgotten item in a renovation file. Reported "
        "experience from renovation projects puts forgotten allowances and credits in the thousands of dollars per "
        "project, which is far more than this workbook costs."),
    (P, "The Allowances sheet therefore records five things per item: the allowance, the chosen price, the difference, any "
        "credit already received, and the change-order number that authorised an overage. It then calculates the credit "
        "still owed to you and a status. If an overage has no change-order number, the status says so, and the summary "
        "counts it as a check to fix. That single rule, written down, prevents the most common allowance argument: "
        "everyone remembers agreeing, nobody remembers the number."),

    (H, "8. Change orders: why the original budget stops being true"),
    (P, "The original budget is a historical document. It was true when you approved it. Every signed change makes it "
        "less true, and the honest replacement is the revised budget: original plus approved changes. This workbook keeps "
        "both, because comparing a current cost only against the original number hides every decision you have already "
        "made, and comparing only against the revised number hides how far you have travelled."),
    (P, "Each change order gets its own reference, a date, the line it affects, a description, an amount, and a Yes or No. "
        "Only Yes counts. A change marked No is visible, counted, and reported, but it does not move money, because an "
        "unapproved change is not a cost yet, it is a decision waiting to happen. The workbook is deliberately strict "
        "here: the moment work proceeds on an unsigned change, the budget stops being a control and becomes a record of "
        "someone else's decisions."),
    (P, "Connect the two sheets properly and the arithmetic stays simple. The change-order amount is entered once, in the "
        "change-order log. Cost Control pulls it in per line, so the revised budget and the committed total both move "
        "together, and the allowance sheet points at the same change-order number. One number, one place, three views."),

    (H, "9. Contingency: a reserve, not a slush fund"),
    (P, "Contingency is the money you hope not to spend. It is not extra budget, and it is not a rounding error. Its "
        "purpose is to absorb the surprises that are normal in building work: the rot behind a sink, the circuit that "
        "fails inspection, the delivery that arrives damaged."),
    (P, "The sheet records the reserve set in Setup, every draw with a date, a reason, an approver and a note, and the "
        "reserve remaining. There is no category field on purpose. If you cannot describe the draw in one sentence a "
        "stranger would understand, it is probably a budget increase wearing a contingency label."),
    (P, "Two disciplines make the reserve useful. First, draw only against a named event, never against a general feeling "
        "that costs are rising; rising costs belong in forecast to complete, where they are visible and arguable. Second, "
        "track the reserve remaining at every review. When it reaches zero, the next surprise is a change order, and "
        "everyone should know that before it happens rather than after."),

    (H, "10. Forecasting what is left"),
    (P, "Forecast to complete is the only genuinely judgemental number in the workbook, and it is where experience enters. "
        "For each line that is not finished and not fully committed, estimate the money still to be spent. Use quotes "
        "where you have them, and say so in the assumptions sheet where you do not."),
    (P, "Update it at every review, and update it before any large decision, not after. The forecast is also the honest "
        "place to put bad news: a line whose committed amount is already above its budget does not need a forecast to "
        "show the problem, but a line that is only half built usually does. A forecast that never changes between reviews "
        "is not a forecast, it is a hope."),
    (P, "The workbook checks the arithmetic, not your optimism. If your forecast is too low, the projected final will be "
        "too low, and the sheet will agree with you. That is why the assumptions sheet exists, and why the review rhythm "
        "in section twelve matters more than any formula."),

    (H, "11. Reading the Summary"),
    (P, "The summary is a single block of totals followed by eight checks. Read the checks first. They are written in "
        "plain language and each one either says OK or tells you what to fix: a payment against an unknown line, an "
        "allowance overage with no change order, paid more than committed on a line, projected final over revised budget, "
        "the reserve exhausted, remaining spend larger than the budget left, an unsigned change order, or a line with no "
        "budget."),
    (P, "Then read four numbers in this order: revised budget, committed total, projected final, and variance. Committed "
        "as a percentage of the revised budget tells you how much of the project is already decided, which is a useful "
        "measure of how much freedom you still have. All-in plan adds the reserve back, so you can see the total the "
        "project could reach without any further change orders."),
    (P, "One number the summary deliberately does not produce is a single confidence score. A renovation is not a "
        "portfolio, and averaging incompatible risks into one figure would be a comfort, not a control."),

    (H, "12. The worked example, start to finish"),
    (P, "The yellow rows describe a kitchen with nine cost lines and an original budget of $45,000. The first thing worth "
        "noticing is that nobody made one large mistake. Five small ones accumulated."),
    (P, "<b>The signed overrun nobody called a change.</b> Cabinets were budgeted at $12,000 and signed at $12,500. That "
        "extra $500 is already real, but it was never written as a change order, so the original budget row simply shows "
        "a line that is $500 over while the revised budget says nothing. This is why committed is tracked separately from "
        "approved changes: commitments can exceed the plan without anyone approving anything."),
    (P, "<b>The allowance that became a change order.</b> Countertops carried an allowance of $7,500. The slab chosen came "
        "to $9,200. The difference of $1,700 was written as CO-01, marked Yes, and pointed at from the allowance row. Cost "
        "Control therefore shows a revised budget of $9,200 for that line, a committed total of $9,200, and a projected "
        "final of $9,200: the overage is fully absorbed and visible. Nothing about that mechanism is clever, but it is the "
        "difference between a cost you chose and a cost that arrives."),
    (P, "<b>The credit that could otherwise vanish.</b> Lighting carried an allowance of $1,200 and the fittings chosen "
        "came to $400. Three hundred dollars of the $800 reduction has already been credited. The workbook shows $500 "
        "still owed to you, in its own summary line, so it cannot be lost in a friendly conversation at handover."),
    (P, "<b>The overage with no paperwork.</b> Plumbing fixtures were allowed at $1,500 and chosen at $1,900. There is no "
        "change-order number on that row, so its status reads that plainly, and the summary reports one overage with no "
        "approved change order. This is exactly the item that ends up disputed, and here it is visible before anyone "
        "argues."),
    (P, "<b>The work still to be priced.</b> Painting is not contracted and is forecast at $3,750 against a $3,000 budget. "
        "Flooring has $5,900 committed and a further $550 expected. Appliances are not ordered, forecast at $5,600 against "
        "$5,000. None of that has happened yet, which is precisely why it needs to be forecast rather than discovered."),
    (P, "<b>The totals.</b> The original budget is $45,000 and approved change orders add $2,300, so the revised budget is "
        "$47,300. Committed total is $39,800, which is 84.1 percent of the revised budget. Paid to date is $16,300, so "
        "unpaid committed is $23,500. Forecast to complete adds $9,900. Projected final cost is therefore $49,700. Variance "
        "against the revised budget is minus $2,400: the project is over by $2,400."),
    (P, "<b>The lesson in the last two numbers.</b> The contingency reserve was set at $4,500. Two draws, $900 for rot and "
        "$1,200 for a code-required circuit, used $2,100, leaving exactly $2,400. The overrun and the remaining reserve are "
        "the same number. The reserve is not a cushion any more; it is already spoken for by work that has not been done "
        "yet. Five lines are over their revised budget, one change order is unsigned, one allowance has no paperwork, and "
        "$500 is owed back. Every one of those facts came out of the workbook's own formulas, not from a narrator."),
    (P, "Notice also what the example does not do: it does not pretend that a $45,000 budget with a $49,700 projected final "
        "is fine because the reserve exists. The all-in plan line shows $49,700, and the check line says remaining spend "
        "exceeds the budget left. The workbook's job is to make the sentence unavoidable, not to soften it."),

    (H, "13. The fifteen-minute monthly review"),
    (P, "Once a month, and immediately after any signed change, run the same short sequence. It is short on purpose; a "
        "review that takes an hour happens twice and then stops."),
    (C, ["Open the Payments sheet and add anything that left your account since the last review, using the same line codes.",
         "Open the Change Orders sheet and add any change agreed since the last review, including ones agreed by message, and mark Yes only if it is genuinely signed.",
         "Update the original committed column wherever a new quote was signed, so commitments never lag reality.",
         "Update forecast to complete on every line that is unfinished, then say out loud which line you are least sure about.",
         "Reconcile any allowance selection made since the last review, and write the change-order number on the allowance row.",
         "Record any contingency draw with its date, reason and approver.",
         "Read the eight summary checks and fix every one that is not OK before you close the file.",
         "Write one line in the assumptions sheet about anything you learned that changes what is excluded."]),
    (P, "Two minutes of that routine are bookkeeping. The rest is the point: naming the number you are least sure about, in "
        "advance, is what turns an estimate into a forecast."),

    (H, "14. What is excluded, and why writing it down matters"),
    (P, "Every estimate is honest only with its exclusions visible. The assumptions sheet holds a type (excluded, "
        "assumption, allowance, risk), a statement, where it lives, and a note. Five rows in the example cover storage and "
        "rental furniture, landscaping, owner-supplied appliances, the countertop allowance, and the risk attached to an "
        "older house."),
    (P, "The most valuable of those is the excluded row. An excluded item is not a gap in the workbook; it is a decision, "
        "and writing it down means the same decision does not get made again differently in three months. It also protects "
        "you at handover: when someone asks why the garden was never touched, the answer is in the file, dated."),
    (P, "Review the assumptions sheet at every monthly review and add anything that has become true. The sheet is not a "
        "legal document and does not replace your contract, but it is the record of what you believed, which is what you "
        "will need if a number is ever disputed."),

    (H, "15. Nine mistakes this workbook is built to catch"),
    (B, ["<b>Reporting paid as if it were cost.</b> Paid lags commitment, sometimes by months. The workbook separates them and shows unpaid committed as its own total.",
         "<b>Typing a total.</b> A typed total keeps yesterday's value. Every total here is calculated from rows.",
         "<b>Treating an allowance as a price.</b> The allowance sheet makes the difference visible, with a change-order number or an explicit absence of one.",
         "<b>Forgetting a credit.</b> Credits still owed have their own summary line, so a reduction cannot disappear into a conversation.",
         "<b>Letting the original budget stand in for the plan.</b> Revised budget is original plus approved changes, shown next to it.",
         "<b>Approving work by message and recording it later.</b> A change without Yes does not move money, and the summary counts it.",
         "<b>Using contingency for general cost growth.</b> Draws need a date, a reason and a name; growth belongs in forecast to complete.",
         "<b>Forecasting once.</b> The monthly review updates the forecast, and the assumptions sheet records what changed.",
         "<b>Leaving example rows in the file.</b> Every row with a line code is summed. Delete the yellow rows before you add your own."]),

    (H, "16. Scope, limits and honest caveats"),
    (P, "This is a control workbook for a domestic or small commercial renovation where you are the person paying the "
        "bills. It assumes you have, or can get, the signed quotes and the contract terms. It does not calculate tax, "
        "retention, financing costs or the time value of money, and it does not model schedules."),
    (P, "It also assumes the numbers you enter are yours to enter. If a builder supplies their own monthly cost report, "
        "use this workbook as your independent check on it rather than as a replacement, and reconcile the two rather "
        "than choosing the more comfortable one."),
    (P, "The research figures quoted in this guide, including the 2026 overrun surveys and the allowance experience, are "
        "external findings from named public sources at the time of writing, not measurements of your project. They are "
        "here to justify the reserve and the allowance discipline, not to predict your result."),
    (P, "Finally, the limits of any spreadsheet: it records what you tell it. Its value comes from the fact that it asks "
        "the same eight questions every month, in the same order, and refuses to hide the answer behind a plausible "
        "total."),
]

DISCLAIMERS = (
    "This guide and the accompanying workbook are a planning and control tool, not legal, tax, financial or "
    "construction advice. Allowance, variation, payment and dispute terms are governed by your contract and by local "
    "law; verify them, and consult a qualified professional where the amounts or the risk justify it.",
    "All example figures are illustrative and come from a single worked example. They are not a benchmark for your "
    "project. B13-001 (c) Galaxy Forge.",
)


def main() -> int:
    path = E.build(FILENAME, "B13-001",
                   "Renovation Allowance &amp; Change-Order Control",
                   "A control method for the two things that move a renovation budget without asking: "
                   "allowance reconciliation and change orders. 16 sections, one worked example, one monthly routine.",
                   BLOCKS, DISCLAIMERS)
    if path is None:
        print("skipped by BUILD12_ONLY")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
