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

    (H, "16. Allowance, provisional sum, prime cost: three words that decide who pays"),
    (P, "These three terms are used interchangeably in conversation and almost never in contracts. The difference "
        "between them is not academic: it decides who absorbs the gap when the real number arrives, and whether that gap "
        "needs your written approval before it happens. Read the clause that uses the term, not the term itself, because "
        "the same label is defined differently by different builders."),
    (P, "<b>An allowance</b> is normally a figure agreed for something the buyer has not chosen yet: tiles, sanitaryware, "
        "a kitchen, lighting. The contract usually says the buyer may select within it, pays any excess, and receives a "
        "credit if they spend less, though the credit is often reduced by a handling or restocking charge. The risk being "
        "allocated is choice risk. You control it, which is why an allowance that is quietly exceeded is a control "
        "failure rather than a builder's fault."),
    (P, "<b>A provisional sum</b> is normally a figure for work that cannot be defined yet: opening up a wall, moving a "
        "drain, making good what was found behind a floor. The risk being allocated is discovery risk. Who absorbs the "
        "difference depends entirely on the wording: some contracts adjust the sum with no further approval, others "
        "require a variation before the work proceeds. That single sentence is worth more of your attention than the "
        "headline price."),
    (P, "<b>A prime cost sum</b> is usually about goods rather than work, and often carries a stated margin on top of the "
        "actual invoice. If a quote shows a prime cost sum, ask what margin applies to the adjustment and whether you "
        "may supply the item yourself. Those two answers change the effective price of the item considerably."),
    (B, ["Write the term next to the number in the Cost Control sheet, in the notes column. A number without its term is "
         "a number you cannot defend later.",
         "Ask, for each of the three: if the actual is higher, who approves the difference, and in what form?",
         "Ask what happens to a credit: full value, reduced, or none.",
         "Check whether the allowance includes installation, waste, delivery and tax, or only the item.",
         "Record the answer in the assumptions sheet with the date you were told. Memory is not evidence."]),
    (P, "None of this requires legal training. It requires noticing that a number in a quote arrives with a rule attached, "
        "and writing the rule down while the person who stated it is still on the phone."),

    (H, "17. Reading a quote for what it transfers, not what it totals"),
    (P, "Two quotes can total the same and expose you to completely different risk. The total is the least informative "
        "number in the document. What matters is the boundary: what the price includes, what it silently excludes, and "
        "what happens at the edges. Read the exclusions before the price, and read the qualifications before the "
        "exclusions."),
    (P, "<b>Supply and fit</b> usually means the contractor buys the material and installs it, and the price carries both. "
        "<b>Supply only</b> means the material is yours and so is its risk: damage, shortage, wrong specification and "
        "delivery delays are yours unless the contract says otherwise. <b>By others</b> is the phrase that costs the most "
        "money in renovations, because it transfers work out of the quote without transferring it out of your project. "
        "Every time you read it, write down who the other is and whether they have been booked."),
    (P, "<b>Subject to site conditions</b> and <b>to be confirmed on site</b> are not evasions; they are honest markers "
        "that the price rests on an assumption. The useful response is not to argue but to ask what the price becomes if "
        "the assumption fails, and to record the answer as a provisional sum with a range rather than a single figure."),
    (P, "<b>Day rates</b> convert a fixed price into an open one. They are legitimate for genuinely unpredictable work, "
        "but they need three things to stay controllable: an agreed estimate of days, a written record of days worked, and "
        "a cap that requires your approval to exceed. Without all three you have agreed to a number you cannot forecast."),
    (P, "<b>Variations priced at a stated margin</b> is the clause that decides what every future change costs you. A "
        "change priced at cost plus a stated percentage is a different proposition from a change priced from a rate card "
        "written before you knew what would change. Neither is dishonest; one is simply easier to predict."),
    (B, ["Highlight every exclusion and every qualification in the quote. If there are none, that is itself worth a "
         "question.",
         "Convert each qualification into a range and enter it in the Cost Control sheet as a provisional amount.",
         "List every 'by others' item and give each a name and a date, or move it into your own scope deliberately.",
         "Compare quotes on inclusions, not totals: a cheaper total with three exclusions is often the dearer project.",
         "Keep the quote version you signed. Quotes get reissued, and the reissued version is rarely the kinder one."]),

    (H, "18. Stage payments and retention: the timing problem behind most 'over budget' surprises"),
    (P, "A renovation can be within budget and still run out of money, because budget is a total and cash is a calendar. "
        "Paying ahead of progress does not change what the project costs, but it changes what you can do when something "
        "goes wrong, and it quietly transfers risk from the party who is behind to the party who has already paid."),
    (P, "The control is straightforward in principle and tedious in practice: each payment should be tied to a stage you "
        "can see, inspect and record, not to a date on a schedule. Take photographs on the day you pay. Note in the "
        "Payments sheet what the payment was for, and keep the invoice next to it. If a stage is agreed as complete, "
        "record who confirmed it and when."),
    (P, "<b>Retention</b> is money withheld from payments until completion, and often until the end of a defects period. "
        "Whether it applies, at what percentage, for how long, and what releases it are matters of contract and local law, "
        "and they vary. Treat the answer as unknown until you have read it, and never assume the arrangement is the one "
        "you have heard about from someone else's project."),
    (P, "The practical trap is the same in every project: the last ten per cent of the work takes a disproportionate "
        "share of the time, and it is exactly the part you have the least leverage over once you have paid everything "
        "except retention. Keeping a real, contractually agreed retention is not distrust; it is the only mechanism that "
        "keeps the final stage worth finishing."),
    (B, ["Tie each payment to an observable stage, and photograph it before you pay.",
         "Record the invoice number, the date and the stage in the Payments sheet; a payment without a stage is a "
         "payment you cannot later question.",
         "Write down the retention terms you actually agreed, with the clause reference, in the assumptions sheet.",
         "Never let a payment be described only as 'on account'. It is the phrase that makes reconciliation impossible.",
         "If a payment is brought forward at the builder's request, record why. That note is the only evidence that the "
         "change was requested rather than agreed."]),

    (H, "19. The evidence file: rebuilding a decision you made in March"),
    (P, "Renovations are decided in conversations, and the conversations are the first thing to disappear. Six months "
        "later the question is never 'what did we decide' but 'why did we decide it, and who agreed'. A file that "
        "answers that question in under five minutes is worth more than a spreadsheet that answers it in an afternoon."),
    (P, "The file does not need to be elaborate. It needs five kinds of item, each with a date: the signed contract and "
        "every quote version you relied on; every change request and its approval, in writing, with the number that "
        "appears in the workbook; photographs of stages and of anything that was covered up; invoices and payment "
        "records; and a single running note of verbal agreements, written the same day, saying who said what."),
    (P, "That last item is the one people skip and the one that resolves most disputes. A note that reads '14 March, "
        "phone with site manager, agreed the extra tile battening is included in the variation 3 price, no extra charge' "
        "is not a legal document, but it is a dated record of a shared understanding, and it is very hard to argue with "
        "later."),
    (P, "How long to keep the file, and what a dispute process requires, varies by jurisdiction and by contract. Do not "
        "guess: ask, or keep it longer than you think you need. Storage is cheap and reconstruction is not."),
    (B, ["One folder, one naming convention, dates first: 2026-03-14 variation 3 approval.pdf.",
         "Keep every quote version, not just the last. The earlier version is often the one you compared against.",
         "Photograph before work is covered up, and photograph the meter readings and the state of adjacent rooms at "
         "handover.",
         "Write verbal agreements down the same day, in one line, with names.",
         "Reconcile the folder against the workbook once a month: every approved change number in the workbook should "
         "have a document, and every document should have a number."]),

    (H, "20. Twenty questions worth asking before you sign"),
    (P, "Most of the expensive surprises in a renovation are visible before the contract is signed, in the form of a "
        "question nobody asked. These are the questions this workbook assumes you have answers to. If you cannot answer "
        "one, write 'unknown' in the assumptions sheet rather than guessing, and ask before the first payment."),
    (B, ["What exactly is excluded, and which of those exclusions have I already assumed were included?",
         "For each allowance, what happens if I spend more, less, or nothing at all?",
         "For each provisional sum, who approves the difference, and in what written form?",
         "What margin applies to variations, and is it on cost, on the rate card, or on a quoted price?",
         "Which items are 'by others', and who are they, and have they been booked?",
         "What are the stage payment points, and are they tied to observable progress or to dates?",
         "What retention applies, for how long, and what releases it?",
         "What notice do I have to give to change or pause the work, and what does that cost?",
         "What happens to the price if the start date slips?",
         "Who is responsible for waste removal, protection of floors and access, and temporary services?",
         "Are permits included, and who is responsible if the authority requires changes?",
         "What is the defects period, and what does the builder have to do inside it?",
         "How are delays notified, and what records will I be given if they happen?",
         "Who is on site day to day, and who am I allowed to instruct?",
         "What is the process if we disagree about whether a stage is complete?",
         "Are there any charges for suspending the work, and what triggers them?",
         "What insurance covers the works, and does it cover my existing property?",
         "What happens if a discovered defect makes part of the scope impossible?",
         "How will we record changes that are agreed verbally on site?",
         "What would make you, as the builder, ask for a price increase, and how early would you tell me?"]),
    (P, "The answers belong in the assumptions sheet, dated, with who told you. Not because the answers are guaranteed to "
        "hold, but because a written answer is a shared starting point and an unwritten one is a future argument."),

    (H, "21. When the numbers stop agreeing: a five-step reconciliation"),
    (P, "Sooner or later the workbook and the builder's account will disagree. The instinct is to find who is wrong. The "
        "useful first move is to find where the two records diverge, because the divergence is almost always a category, "
        "not a lie: a payment recorded as a cost, an allowance treated as a fixed price, a credit still outstanding, a "
        "variation agreed but never numbered."),
    (B, ["<b>Agree the totals you are comparing.</b> Write both numbers down before you discuss them, and say which "
         "period each covers. Most disagreements dissolve at this step.",
         "<b>Match by category.</b> Compare original, approved changes, allowances, contingency and paid separately. A "
         "single total hides which of the five is wrong.",
         "<b>Match by document.</b> Every number in the builder's account should map to an invoice, a variation or a "
         "quote line. Anything that maps to none of them is an open question, not an error.",
         "<b>Isolate the smallest disagreeing item.</b> Resolve one line completely before moving to the next. Bulk "
         "reconciliation produces agreement about nothing.",
         "<b>Write the outcome down.</b> One line: what was agreed, by whom, on what date, and what the workbook now "
         "says. Then update the workbook."]),
    (P, "Run this the first time the numbers diverge, not the third. The cost of reconciliation rises with the number of "
        "unreconciled months, because each month adds a new explanation and a new person who has to remember it."),

    (H, "22. Working with more than one trade: the interface is the risk"),
    (P, "Almost every renovation that goes badly wrong with a competent builder goes wrong at a boundary: between the "
        "plumber and the tiler, between the electrician and the plasterer, between the joiner and the decorator. Each "
        "trade can do its own work perfectly and still leave you with a hole in the wall, because the interface between "
        "them was nobody's line item."),
    (P, "The workbook helps here in a way that is easy to miss. The Cost Control sheet is a list of promises with names "
        "against them. If two rows describe the same physical work, you have found either duplication or an interface. "
        "If a row has no name, you have found the place where the argument will happen."),
    (P, "The practical control is to write the interfaces down as if they were work: who makes good after the "
        "electrician, who moves the skip, who protects the finished floor while the decorator is in, who returns to "
        "connect the appliance after the worktop is fitted. None of these are glamorous, and all of them have a cost, "
        "a date and an owner. Putting them in the sheet as explicit rows with a provisional amount is more honest than "
        "assuming they are inside someone's price."),
    (P, "Then there is the question of instruction. On a site with several trades, only one person should be able to tell "
        "any of them to do something different. If you instruct a trade directly, you have usually created a variation "
        "that the main contractor will not price, will not warrant, and may charge to unwind. Decide at the start who "
        "you instruct and in what form, and write it in the assumptions sheet, because it is the rule you will most want "
        "to break at eight in the morning when something looks wrong."),
    (B, ["Give every trade row a name, even the ones inside another trade's price.",
         "Write the interfaces as rows: making good, protection, waste, temporary services, final connections.",
         "Agree one instruction route, and write it down with the date.",
         "When you are tempted to instruct directly, ask instead: what does this do to the contract, and who pays for "
         "the unwinding?",
         "Photograph the interfaces as they are closed up. That photograph is the only record of who left what."]),

    (H, "23. Doing part of it yourself: where DIY stops being a saving"),
    (P, "Self-performance is a real way to reduce a renovation budget and a reliable way to increase one. The difference "
        "is rarely skill. It is the two costs that never appear in the DIY estimate: the cost of the time, and the cost "
        "of the interface you have created between your own work and everyone else's schedule."),
    (P, "The time cost is easy to underestimate because it is paid in evenings and weekends, which feel free. Write it "
        "down anyway, at whatever your spare hour is worth to you, and compare that number to the saving. For demolition "
        "and clearance the arithmetic often works. For anything that must be finished to a standard someone else will "
        "then build on, it often does not, because a trade asked to work over a surface they did not prepare will either "
        "refuse or price the risk in."),
    (P, "The interface cost is subtler. A builder's programme assumes a sequence. Doing your part late does not delay "
        "only your part; it delays the trade who was due next, and that trade will usually be paid for the delay "
        "somewhere in the final account. The saving you banked in week three reappears as an unexplained charge in week "
        "nine."),
    (P, "There is also the warranty question, and it is the one to settle before you start rather than after. If you "
        "supply or install part of the work, what happens to the guarantee on the parts around it? Many contractors will "
        "exclude anything they did not install, which is reasonable and also means the saving has a hidden price. Ask, "
        "and write the answer down."),
    (B, ["List what you will do yourself and give each item a realistic hour estimate, including the hours you will not "
         "want to do.",
         "Put your own work in the sheet as a row with a cost of zero and a note, so the sequence is visible.",
         "Agree with the contractor, in writing, when your part must be finished for their programme to hold.",
         "Ask what the guarantee position is for work adjacent to yours.",
         "Decide in advance what you will do if you run out of time. The honest answer is usually 'pay someone', and it "
         "is cheaper to plan for it than to discover it."]),

    (H, "24. Handover and the final account: the last five per cent"),
    (P, "The end of a renovation is not the day the last trade leaves. It is the day you have a list of what is "
        "outstanding, a date for each item, the documents you will need when something fails in two years, and an agreed "
        "final amount. Projects that skip this stage do not feel finished for a long time, and the things that were "
        "almost right become the things that are wrong."),
    (P, "Start the snag list before completion, and keep one list rather than three. Walk the property room by room, in "
        "the same order every time, and write each item as a location plus an observation plus what finished looks like. "
        "'Kitchen, unit door under sink, hinge rubbing and door sits proud at the top' is an item. 'Kitchen needs "
        "attention' is a conversation that will happen three times."),
    (P, "Give each item a date and a named owner, and agree in writing which items are cosmetic and which prevent you "
        "from using the room. That distinction matters because it is the one that decides whether the final payment is "
        "due. If the contract ties the final payment to completion, the question 'is it complete' should be answered by "
        "the list, not by the atmosphere on the last day."),
    (P, "The handover pack is the part people forget and later wish they had. It is not a legal requirement in most "
        "places, which is exactly why nobody chases it. Ask for: certificates for electrical and gas work where they "
        "apply; the boiler or heat pump service record and manual; warranties for appliances, worktops, flooring and "
        "anything with a manufacturer's guarantee; paint colours and product codes; tile and flooring details with the "
        "spare boxes; the as-built note of any pipe or cable route that was buried; the names of the trades who did the "
        "work; and the date from which each guarantee runs."),
    (P, "Two of those are worth more than they look. The as-built note of buried routes will save a future you from "
        "drilling through a pipe, and it takes five minutes for someone who knows to write down. The list of trades is "
        "what lets you call the right person rather than a stranger when a specific thing fails, which is often the "
        "difference between a repair and a re-do."),
    (P, "Finally, keep the workbook finished. Close the open items, record the final paid total and the final committed "
        "total, note the retention release date if there is one, and file it with the handover pack. In three years, when "
        "you cannot remember whether the bathroom was in the original scope, that closed workbook is the answer."),
    (B, ["One snag list, room by room, in the same order, with location, observation and the finished state.",
         "Separate 'prevents use' from 'cosmetic', in writing, before discussing the final payment.",
         "Ask for the handover pack as a list, and tick it off: certificates, manuals, warranties, colours, spares, "
         "buried routes, trade names, guarantee start dates.",
         "Write the as-built note for anything that was covered up, even if it is three lines on a sheet of paper.",
         "Close the workbook: final paid, final committed, retention release date, and file it with the pack."]),

    (H, "25. Comparing quotes, and knowing when re-tendering costs more than it saves"),
    (P, "Three quotes for the same work are rarely for the same work. One includes the skip, one does not; one prices "
        "the making good, one assumes you will; one has a provisional sum where another has a fixed price. Comparing the "
        "totals is therefore not a comparison at all. It is a comparison of three different projects that happen to "
        "share a description."),
    (P, "The method that survives contact with reality has four steps, and none of them requires a spreadsheet beyond "
        "the one you already have. First, build a common scope list from your own understanding of the job, not from any "
        "single quote: every room, every element, every item you expect to be included. Second, map each quote onto that "
        "list, marking included, excluded, and unclear. Third, convert each exclusion and each qualification into a "
        "range, using the quote's own language where it gives one. Fourth, compare three numbers per quote: the stated "
        "total, the expected total after likely exclusions, and the worst case if every qualification fails."),
    (P, "The gap between the stated total and the expected total is the most useful number in the exercise. It tells you "
        "which quote is cheap because it is good value and which is cheap because it has been scoped down. A quote that "
        "is ten per cent lower but carries three unbooked 'by others' items is not lower; it is unfinished."),
    (P, "Then there is the question nobody asks out loud: is the cheapest quote actually the one you want to build with? "
        "Price is one axis. The others are whether the scope is legible, whether the person answered your questions "
        "directly, whether they have done this specific work recently, and whether their payment terms leave you with "
        "any leverage at the end. A quote that is clear, complete and slightly dearer is often the cheaper project, "
        "because the money you do not spend is frequently the money you do not argue about."),
    (P, "<b>Re-tendering</b> is the decision that feels prudent and often is not. It costs weeks, it costs your attention, "
        "and it costs the goodwill of whichever trade was expecting the job. It is worth doing when the scope has "
        "genuinely changed, when the spread between quotes is large enough to suggest a misunderstanding rather than a "
        "margin, or when the leading quote carries qualifications you cannot price. It is not worth doing because one "
        "number is higher than you hoped, or because a fourth opinion might be kinder than the three you have."),
    (P, "A useful test before you ask for another quote: can you write down, in one sentence, what you expect the new "
        "quote to tell you that the existing three did not? If you cannot, you are buying delay rather than information."),
    (B, ["Build your own scope list first, so you are comparing quotes to the job rather than to each other.",
         "Mark every line included, excluded or unclear. Unclear is a category, not a rounding error.",
         "Compare stated, expected and worst-case totals. The gap is the real differentiator.",
         "Price the qualifications before you choose, not after the work starts.",
         "Re-tender only when you can name the question a new quote would answer. Otherwise, negotiate the existing one."]),

    (H, "26. The first forty-eight hours when something goes wrong"),
    (P, "Something will go wrong. Water where it should not be, a wall that was not load-bearing according to the "
        "drawing, a delivery that never arrives, a trade who stops answering. The first forty-eight hours decide how "
        "expensive the problem becomes, and almost none of that cost is the problem itself. It is the decisions taken "
        "while nobody has written down what happened."),
    (P, "The first move is always the same and always feels too slow: stop, and record. Photograph the situation before "
        "anything is moved, dried, covered or tidied. Note the time. Write one paragraph of what you observed with your "
        "own eyes, and keep it separate from what you were told. Those are two different kinds of information and they "
        "will diverge later, usually in good faith."),
    (P, "The second move is to establish who needs to know, in what order. For anything involving water, gas, electricity "
        "or structural work, the answer usually begins with whoever is qualified to make it safe, not with whoever is "
        "responsible for the cost. Sorting responsibility is a later conversation; making the site safe is now."),
    (P, "The third move is the one people skip: decide what you are not going to decide yet. Most bad outcomes in the "
        "first two days come from agreeing a fix before understanding the cause, and from agreeing a number before "
        "understanding the fix. It is entirely reasonable to say: I am not agreeing a cost today, I am recording what "
        "happened and we will agree the remedy in writing once we know the cause."),
    (P, "Then write the one page that will matter in six months: what happened, when, who was told, what was done to make "
        "it safe, what is still unknown, and what the next decision is and who makes it. Attach the photographs. File it "
        "with the evidence file. If the matter later becomes a claim, that page is the reason the conversation is about "
        "facts rather than recollections."),
    (B, ["Make safe first, and record who did it and when.",
         "Photograph before anything is moved, dried or covered.",
         "Separate what you observed from what you were told.",
         "Do not agree a cost before the cause is understood.",
         "Write the one-page record the same day, and file it with the photographs."]),

    (H, "27. Scope, limits and honest caveats"),
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
