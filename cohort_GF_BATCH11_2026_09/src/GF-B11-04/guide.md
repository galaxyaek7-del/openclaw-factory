# Salon Commission Pay Kit - Operations Guide

## 1. Who This Guide Serves

This guide serves independent salon and spa owners who pay staff on commission and handle payroll themselves or with a part time bookkeeper. It assumes you can open a spreadsheet, read a daily sales report, and explain a payout line to a team member. It does not assume payroll training. Every formula is shown step by step with illustrative numbers and illustrative staff labels so you always know which figures are teaching examples and which are your own.

This kit is built only for commission payroll. If your shop runs on booth rental or chair rental, where each professional pays a flat rent and keeps the rest, this kit is not for you. Rental settlement is a different mechanic with different records, and forcing commission sheets onto rental math creates confusion. The exclusion is stated plainly in the listing so the wrong buyer can self select out before purchase.

## 2. The Problem in Plain Terms

Commission payday in a small salon stacks several math layers. Services carry one rate. Retail carries a lower rate. Tiers raise the rate once a threshold is crossed. Bonuses add lump sums. Voids, refunds, and discounts subtract. Corrections from last period adjust. Each layer alone is simple multiplication. Together, computed by hand or from memory, they produce statements that staff cannot verify and owners cannot defend. The result is a dispute that costs an hour of management time and a week of trust.

The common failure points repeat across shops. Service and retail totals are merged into one number with one blended rate, so nobody can check either. Tier thresholds are quoted verbally and remembered differently by each side. Voids stay in the sales total because nobody removes them before computing commission. Discounts are handled one way in January and another way in March. Last period corrections are mentioned but never written down. The fix for all five is the same: one written log, one set of rates, one statement that shows its arithmetic, and one dispute record with a deadline.

## 3. Method Overview

The method has five parts that run each pay period. First, a daily service and retail sales log with one row per team member per day. Second, a tier calculator with exact formulas that applies thresholds and bonuses mechanically. Third, a per stylist payout statement that copies the computed figures and shows each line. Fourth, a dispute log with a forty eight hour rule. Fifth, a written commission agreement per team member that anchors every rate the sheets use.

The order matters. Daily logging prevents end of period reconstruction. The tier sheet computes from the log, never from memory. The statement reports the computation without editing it. Questions go into the dispute log within forty eight hours of payday. Resolutions adjust the next payout as written corrections, not as quiet tweaks. The agreement is reviewed annually or whenever rates change, and signed before the first affected period.

## 4. The Daily Sales Log

The workbook file is named salon_commission_pay_kit_workbook.xlsx. Its first sheet is Sales Log. Columns are Date, Stylist, Service Sales, Retail Sales, Service Rate Pct, Retail Rate Pct, Service Commission, and Retail Commission. One row per stylist per day keeps service and retail visible separately from the start.

Service Commission is computed as Service Sales times Service Rate Pct divided by one hundred. Retail Commission is computed as Retail Sales times Retail Rate Pct divided by one hundred. The sheet carries both formulas on every row so a rate change for one person does not disturb the rest. Staff labels in the example rows, such as Illustrative Stylist A, are fictional labels used only to demonstrate the layout.

Enter sales daily from the register report, not from memory at period end. Copy service totals and retail totals into their own columns even when the register prints a combined figure. If the register mixes a service discount into the total, enter the discounted figure actually charged, because commission pays on what the client paid, not on the menu board figure. Note the discount handling on the agreement so the same rule applies every period.

Rate columns deserve care. Each stylist may carry different service and retail rates based on role, tenure, or the signed agreement. Enter the rate from the agreement, not from last period habit. If a rate changes mid period, split the rows: log days before the change with the old rate and days after with the new rate. The sheet then computes each span correctly without manual blending.

An illustrative day, labeled illustrative, shows the mechanic. Illustrative Stylist A records 320 dollars of service sales at a 50 percent service rate and 85 dollars of retail sales at a 15 percent retail rate. Service commission equals 320 times 50 divided by 100, which is 160.00 dollars. Retail commission equals 85 times 15 divided by 100, which is 12.75 dollars. The day total for this stylist is 172.75 dollars before tiers, bonuses, or adjustments. Every figure and label here is illustrative.

Close each day by reconciling the log to the register. Sum the service column and the retail column across stylists and compare against the register day totals. Small differences usually mean a misassigned ticket or a missed retail entry. Fix them the same day while the tickets are fresh. A five minute daily reconciliation prevents a two hour period end hunt.

## 5. Service and Retail Rates

Service commission is the core of salon pay. Typical independent shops set service rates as a percentage of service sales actually collected. The agreement states the rate, the sheet applies it, and the statement shows it. When a stylist asks how a service figure was reached, the answer is one line: the period service total times the agreed rate. Nothing else enters the service line.

Retail commission is almost always a lower percentage because retail carries product cost. The sheet keeps retail in its own columns with its own rate so the lower percentage never leaks onto services and the higher percentage never inflates retail. When retail is returned, the refund treatment follows the agreement: most shops deduct the retail commission on the refunded item in the period the refund posts. The deduction appears as an adjustment line, labeled with the original sale date, so the stylist sees cause and effect together.

Discounts need a written rule before they cause a dispute. Three common policies each work if applied consistently. Policy one pays commission on the discounted amount actually collected. Policy two pays on the full menu amount and the house absorbs the discount. Policy three splits the discount effect by a stated fraction. This kit recommends policy one for small shops because it ties pay to cash received, but any of the three is workable if written into the agreement and applied every period without exception.

New hires and apprentices need their own rows from day one. Even when a newcomer earns a flat training wage for the first weeks, log their service and retail sales in the same sheet with a zero rate or a training note. The habit forms early, the data exists when they convert to commission, and nobody has to learn the system under payday pressure.

## 6. The Tier Calculator

Tiers reward higher sales with a higher rate or a lump bonus once a threshold is crossed. The Tier Calculator sheet carries columns for Stylist, Period Service Total, Tier Threshold, Base Rate Pct, Tier Rate Pct, Tier Bonus, and Payout. The period service total flows from the sales log sum for that stylist. The threshold, rates, and bonus come from the signed agreement.

The tier bonus formula pays only on qualification. In the sheet, the Tier Bonus cell reads as follows: if the period service total meets or exceeds the threshold, the bonus amount applies, otherwise zero. Written as a spreadsheet formula for row two: IF(B2>=C2,100,0), where B2 is the period service total, C2 is the threshold, and 100 is the illustrative bonus amount from the agreement. Replace 100 with the real agreed bonus when setting up the sheet.

The payout formula selects the correct rate mechanically. For row two: IF(B2>=C2,B2*E2/100+F2,B2*D2/100), where D2 is the base rate, E2 is the tier rate, and F2 is the computed tier bonus. In words: when qualified, payout equals the service total at the tier rate plus the bonus; when not qualified, payout equals the service total at the base rate with no bonus. No discretion enters at computation time. Discretion belongs in the agreement, signed before the period, not in the math after it.

An illustrative tier case, labeled illustrative, shows both branches. Illustrative Stylist A posts a period service total of 3,200 dollars against a 3,000 dollar threshold, with a base rate of 50 percent, a tier rate of 55 percent, and a 100 dollar bonus. Qualified payout equals 3,200 times 55 divided by 100 plus 100, which is 1,860 dollars. Illustrative Stylist B posts 2,400 dollars against the same threshold at a base rate of 45 percent. Unqualified payout equals 2,400 times 45 divided by 100, which is 1,080 dollars with no bonus. Every figure and label here is illustrative.

Threshold design deserves a short discussion. A threshold set from memory usually lands either unreachable, which demotivates, or automatic, which overpays. Set thresholds from real history: review three prior periods of service totals per stylist, place the threshold modestly above the median, and review annually. One threshold per period is all this sheet supports. Shops running multi step ladders with several breakpoints need payroll software or a custom build, and the limitations section states that boundary plainly.

Timing rules prevent the most bitter tier disputes. Define the period exactly: dates, cutoff hour, and which period a late posted ticket belongs to. Define whether the threshold counts gross service sales or net of voids and refunds. This kit uses net of voids and refunds, and the payout sheet enforces it by computing from adjusted totals. Write the same definition into the agreement so the sheet and the paper agree word for word.

## 7. The Payout Statement

The Payout Statement sheet carries columns for Stylist, Service Comm, Retail Comm, Tier Bonus, Adjustments, Gross Pay, and Voids Deducted. Gross Pay is computed as Service plus Retail plus Tier Bonus plus Adjustments. Written for row two: B2+C2+D2+E2. The Voids Deducted column is informational so the stylist sees what was removed before commission computed.

Each payout figure must trace to exactly one source. Service commission traces to the sales log service sum at the agreed rate, or to the tier sheet payout when tiers apply. Retail commission traces to the sales log retail sum at the agreed retail rate. Tier bonus traces to the tier sheet bonus cell. Adjustments trace to dated correction lines, each labeled with the original period and reason. When every line traces, a stylist with the statement and the agreement can verify the whole payout with a pocket calculator. That verifiability is the product.

The template file salon_stylist_payout_statement.docx formats this for paper. It carries a header with salon name, stylist name, pay period, and statement date; an earnings detail section with each figure and the rate applied; and a sign off with preparer, stylist signature, and date. Issue one statement per stylist per period. Attach the sales log lines for that stylist and period. Keep one signed copy with payroll records and hand one to the stylist. Paper that both sides hold ends most questions before they become disputes.

An illustrative statement, labeled illustrative, reads as follows. Illustrative Stylist A for the February 1 to 7 period: service commission 1,600.00 dollars, retail commission 120.00 dollars, tier bonus 100.00 dollars, adjustments minus 25.00 dollars for a documented refund correction, gross payout 1,795.00 dollars. Voids deducted informational: 45.00 dollars. The arithmetic is 1,600 plus 120 plus 100 minus 25, which equals 1,795. Every figure and label here is illustrative.

Corrections belong on the statement as visible lines, never as silent edits to history. If a prior period error surfaces, enter an adjustment on the current statement with the original period and reason stated. Reopening a closed statement invites cascading confusion. The dispute log resolution for that error will reference this exact adjustment line, closing the loop on paper.

## 8. Voids, Refunds, Discounts, and Corrections

Voids remove a ticket that should never have counted, such as a duplicate entry or a service entered under the wrong stylist. The rule is simple: remove the voided amount from the sales total before computing commission, and record the void in the informational column. The illustrative dispute in the workbook shows a 45 dollar voided service removed from the total with the correction carried on the next payout. Voids are not penalties. They restore the total to what was actually sold.

Refunds return money after a sale counted, such as a retail product brought back. The rule most small shops use, and the one this kit follows, deducts the commission attributable to the refunded item in the period the refund posts. If a 50 dollar retail item paid 15 percent, the deduction is 7.50 dollars on the refund period statement, labeled with the original sale date. The stylist sees the pairing and the question answers itself.

Discounts reduce the collected amount at the time of sale. Commission follows the agreement rule from the rates chapter. Whatever rule is chosen, apply it to every discounted ticket without exception and show the discounted base on the statement when a stylist asks. Selective discount handling, generous for one stylist and strict for another, is a dispute factory.

Corrections fix prior errors: a misassigned ticket, a wrong rate applied, a missed retail line. Each correction gets one adjustment line with three facts: the original period, the amount, and the reason. Positive corrections add, negative corrections subtract. The dispute log entry for the issue references the payout date where the correction appears. Three facts on the line plus one reference in the log is the complete standard. Anything less will be questioned again next period.

## 10. The Dispute Log and the Forty Eight Hour Rule

The Dispute Log sheet carries columns for Date, Raised By, Pay Period, Issue, Resolution, and Status. The template file salon_pay_dispute_log_form.docx provides the paper version with record, detail, and resolution sections. One form per issue keeps records clean.

The forty eight hour rule states that every question about a payout is logged within forty eight hours of the question being raised, and every logged issue receives a written resolution with a payout reference. The rule does not promise the reporter is right. It promises the question is recorded, checked against the log and the agreement, and answered in writing. Speed plus writing is what rebuilds trust.

The resolution workflow has five steps. First, record the issue in the reporter own words. Second, pull the records: the sales log lines, the tier computation, the agreement rate, and the statement. Third, compute the difference, if any, showing the arithmetic. Fourth, write the resolution and the payout date where any correction appears. Fifth, collect both initials and mark the status closed. Most issues resolve at step three because the records answer the question directly. That is the system working, not a sign the log was unnecessary.

Two illustrative disputes, labeled illustrative, show the pattern. Illustrative Stylist A notes retail paid at 10 percent instead of the agreed 15 percent for the February 1 to 7 period. Records confirm the error on 85 dollars of retail sales. The correction is 85 times 5 divided by 100, which is 4.25 dollars, applied on the next payout and referenced in the log. Illustrative Stylist B notes a voided 45 dollar service still sitting in the total. Records confirm the void was logged but never removed from the sum. The correction removes 45 dollars from the service total, reducing commission by the agreed service rate share, applied on the next payout. Every figure and label here is illustrative.

Status discipline keeps the log honest. Open means recorded and under check. Corrected means the adjustment sits on a dated future statement. Closed means both parties initialed the resolution. Void means the question was answered with no correction needed, with the reasoning written down. A log full of open rows is a management signal, not a filing success. Review open rows every payday before issuing new statements.

Owner conduct during disputes decides whether the system survives. Listen without interrupting while the issue is recorded. Check the records before stating a position. Admit errors plainly when the arithmetic favors the stylist; a fast admission builds more trust than a slow perfect record. When the records favor the house, walk through the lines calmly instead of declaring the matter closed. Never revise a closed period silently. Every correction appears as a labeled line on a current statement. Shops that follow this conduct see dispute volume fall within two periods because the team learns the numbers are checkable.

## 11. The Payday Workflow

Payday follows the same sequence every period. First, close the sales log: verify every day of the period has a row per active stylist and reconcile column totals to the register period report. Second, remove voids and post refunds per the agreement rules. Third, run the tier calculator from the adjusted service totals. Fourth, build one payout statement per stylist, copying computed figures without editing them. Fifth, review the dispute log for open rows from prior periods and confirm their corrections appear on the correct statements. Sixth, issue statements with pay, collect signatures, and file copies.

Reconciliation comes before computation, not after. If the log and the register disagree, find the missing ticket now. Common causes are a retail sale rung under the wrong stylist, a service ticket posted after the cutoff hour, or a discount entered in the register but not in the log. Each has a one line fix. Computing payouts on unreconciled totals guarantees corrections later, which costs more time than the reconciliation would have.

The cutoff hour deserves emphasis. Define the exact minute a period ends, for example Saturday at close or Sunday at midnight, and assign every ticket by its transaction time. Late posted tickets belong to the period they post in, with a note referencing the service date. Without a cutoff rule, threshold cases will always be arguable: a ticket posted Sunday morning either qualifies someone for a tier or it does not, and both sides will remember the verbal rule differently. The written cutoff ends that argument permanently.

Filing closes the period. Each period packet holds the sales log printout, the tier sheet, one signed statement per stylist, the dispute log page, and the register period report. File by period, not by stylist, so an audit of any question pulls one folder. Retain packets per local record keeping requirements. When a question arrives weeks later, the packet answers it in minutes.

Period timing advice helps small shops further. Run payroll on the same weekday each period so staff can plan. Allow at least one full business day between the cutoff hour and payday for reconciliation, computation, and review. Rushing the close on the same night as the cutoff produces the errors the dispute log then has to absorb. A steady cadence matters more than a fast one.

## 12. Checklists

Use these checklists as written for the first two pay periods, then adapt them to the shop.

Daily logging checklist. Register report pulled. Service totals entered per stylist. Retail totals entered per stylist. Correct rates on every row. Discount tickets entered at the collected amount. Day totals reconciled to the register. Voids noted the same day.

Period close checklist. Every day of the period has rows. Column totals match the register period report. Voids removed from totals. Refunds posted as labeled adjustments. Tier sheet run from adjusted totals. Statements built by copying, not retyping. Prior open disputes resolved onto statements. Cutoff hour honored on late tickets.

Statement issue checklist. One statement per stylist. Every line traces to one source. Rates shown on the statement match the agreement. Adjustments carry original period and reason. Both copies signed. Packet filed by period.

Agreement checklist. One signed agreement per team member. Every rate line initialed. Voids, refunds, discounts, and correction window stated. Pay schedule and review rights stated. Rate changes initialed before the affected period. Professional review completed before first use.

Dispute checklist. Logged within forty eight hours. Issue recorded in the reporter own words. Records pulled and difference computed. Resolution written with payout reference. Both initials collected. Status updated.

## 13. More Illustrative Walkthroughs

Walkthrough one, labeled illustrative, traces a full period for a two chair shop. Illustrative Stylist A posts service sales of 2,850 dollars for the period at 50 percent, retail of 320 dollars at 15 percent, with no tier qualification against a 3,000 dollar threshold. Service commission equals 1,425.00 dollars. Retail commission equals 48.00 dollars. Gross equals 1,473.00 dollars with no adjustments. Illustrative Stylist B posts service of 3,150 dollars at a 50 percent base with a 55 percent tier rate and a 100 dollar bonus at the same threshold, plus retail of 120 dollars at 10 percent. Qualified service payout equals 3,150 times 55 divided by 100 plus 100, which is 1,832.50 dollars. Retail equals 12.00 dollars. Gross equals 1,844.50 dollars. Every figure and label here is illustrative.

Walkthrough two, labeled illustrative, traces a correction period. Illustrative Stylist A was underpaid on retail by 4.25 dollars on the prior statement per the dispute log. Current period service commission is 1,200.00 dollars, retail is 60.00 dollars, no tier applies, plus an adjustment line of positive 4.25 dollars labeled with the original period and reason. Gross equals 1,264.25 dollars. The dispute row is marked corrected with this payout date, then closed on initials. Every figure and label here is illustrative.

Walkthrough three, labeled illustrative, traces a void heavy period. A duplicate ticket of 120 dollars was entered under Illustrative Stylist B and voided the same day. The sales total is reduced by 120 dollars before commission. At a 50 percent service rate the commission effect is 60.00 dollars correctly excluded. The informational voids column shows 120.00 dollars. No dispute arises because the statement shows the removal on its face. Every figure and label here is illustrative.

Walkthrough four, labeled illustrative, traces a discount ticket handled under a collected amount policy. A 200 dollar service is discounted to 170 dollars at checkout. The log carries 170 dollars in service sales. At a 50 percent rate the commission is 85.00 dollars. The agreement page states the collected amount rule, so the 15 dollar difference between menu and collected never becomes an argument. If the shop instead used a full menu policy, the same ticket would pay 100.00 dollars and the house would absorb the 15 dollar discount share. Either rule works when written first and applied always. Every figure and label here is illustrative.

## 14. Frequently Asked Questions

How long does setup take. One pay period of normal operation: enter staff, rates, and thresholds from the signed agreements, then log daily. The first period end takes longer because every step is new. The second period end moves quickly.

Can rates differ between stylists. Yes. Each row carries its own service and retail rate from that stylist agreement. The tier sheet carries per stylist thresholds and rates as well. Different experience levels and roles commonly carry different rates.

What happens when nobody crosses a tier threshold. The sheet pays the base rate with no bonus, and the period is documented the same as any other. Quiet periods still get full statements and filing. Skipping documentation in quiet periods is how later questions become unanswerable.

How are refunds handled when the original sale was several periods ago. Post the deduction in the refund period with the original sale date labeled. The correction window in the agreement governs how far back questions can reopen a closed period, but a real refund posts where the money moved regardless.

Can this kit handle cash tips or card tips. No. Tip computation, reporting, and distribution follow separate rules and are outside this kit. Keep tips on their own record entirely.

What if a stylist disputes the agreement itself, not the math. That is a contract conversation, not a computation question. Pause, review the signed page together, and record the outcome in writing. If the agreement needs changing, follow the rate change procedure with initials and an effective date.

What if the register cannot split service and retail by stylist. Export what it can, assign tickets daily by stylist from receipts, and consider that register limitation when evaluating tools at renewal. Daily assignment takes minutes. Period end reconstruction from an unsplit report takes hours and introduces errors.

What if two stylists split one service. Divide the ticket at logging time per the shop split rule stated in the agreement, with each share on its own stylist row. Splits decided weeks later are unreliable. The daily log is the place where splits are recorded.

## 15. Limitations

This kit covers commission payroll computation and records for independent salons and spas. It does not compute payroll taxes, tip reporting, benefits, or deductions. It does not support booth rental or chair rental accounting in any form. Tier logic covers one threshold per period per stylist. The spreadsheet has no export to payroll software. The agreement template requires review by a qualified professional before use. Correction windows, cutoff hours, and discount policies must be set by the owner to fit local practice and law.

## 16. Disclosure

This guide is educational material. It is not payroll, tax, or legal advice. Commission structures must follow local labor law. All staff labels, numbers, and walkthroughs are illustrative fictional examples used to demonstrate arithmetic. Your sales, rates, and local rules determine your actual figures. No specific financial result is promised. Have the agreement template reviewed by a qualified professional before use.

## 17. Getting Started This Pay Period

Day one, complete one agreement per team member and enter staff, rates, and thresholds into the workbook. Each day, log service and retail sales per stylist and reconcile to the register. At period end, remove voids, post refunds, run the tier sheet, and issue one statement per stylist. Log every question within forty eight hours. File the period packet. Repeat. The routine is the product. The sheets are only its memory.

## 9. The Commission Agreement

The template file salon_commission_agreement_template.docx carries four sections: parties, commission rates, voids and adjustments, and pay schedule with signatures. Complete one agreement per team member before their first commission period and review it annually or whenever rates change.

The parties section records salon name, team member name, start date, and role. The rates section records the exact service rate, retail rate, tier threshold, tier rate, tier bonus amount, and bonus conditions, with each line initialed. Initialing each line feels formal for a small shop and that is the point: later questions are answered from this page instead of from memory.

The voids and adjustments section states in plain sentences how voids, refunds, discounts, and corrections are handled, plus the correction window in days. A thirty day window is common: questions raised within thirty days of the payout are corrected on the next statement; older periods stay closed. The window protects both sides. Staff get a real right to review, and the books gain finality.

The signatures section states the pay schedule, confirms a statement is provided each period, states review rights, and collects owner and team member signatures with dates. Have a qualified professional review the template before first use so it aligns with local labor law. This kit is an organizational tool, not legal counsel, and the disclaimer states that boundary.

Rate changes need their own procedure. Write the new rate, the effective date, and the treatment of the transition period. Both parties initial the change before the first affected period starts. Mid period changes split the sales log rows as described in the daily log chapter. Retroactive rate changes are prohibited by policy in this kit because they rewrite history staff already relied on.

## 10. The Dispute Log and the Forty Eight Hour Rule

The Dispute Log sheet carries columns for Date, Raised By, Pay Period, Issue, Resolution, and Status. The template file salon_pay_dispute_log_form.docx provides the paper version with record, detail, and resolution sections. One form per issue keeps records clean.

The forty eight hour rule states that every question about a payout is logged within forty eight hours of the question being raised, and every logged issue receives a written resolution with a payout reference. The rule does not promise the stylist is right. It promises the question is recorded, checked against the log and the agreement, and answered in writing. Speed plus writing is what rebuilds trust.

The resolution workflow has five steps. First, record the issue in the stylist own words. Second, pull the records: the sales log lines, the tier computation, the agreement rate, and the statement. Third, compute the difference, if any, showing the arithmetic. Fourth, write the resolution and the payout date where any correction appears. Fifth, collect both initials and mark the status closed. Most issues resolve at step three because the records answer the question directly. That is the system working, not a sign the log was unnecessary.

Two illustrative disputes, labeled illustrative, show the pattern. Illustrative Stylist A notes retail paid at 10 percent instead of the agreed 15 percent for the February 1 to 7 period. Records confirm the error on 85 dollars of retail sales. The correction is 85 times 5 divided by 100, which is 4.25 dollars, applied on the next payout and referenced in the log. Illustrative Stylist B notes a voided 45 dollar service still sitting in the total. Records confirm the void was logged but never removed from the sum. The correction removes 45 dollars from the service total, reducing commission by the agreed service rate share, applied on the next payout. Every figure and label here is illustrative.

Status discipline keeps the log honest. Open means recorded and under check. Corrected means the adjustment sits on a dated future statement. Closed means both parties initialed the resolution. Void means the question was answered with no correction needed, with the reasoning written down. A log full of open rows is a management signal, not a filing success. Review open rows every payday before issuing new statements.

## 11. The Payday Workflow

Payday follows the same sequence every period. First, close the sales log: verify every day of the period has a row per active stylist and reconcile column totals to the register period report. Second, remove voids and post refunds per the agreement rules. Third, run the tier calculator from the adjusted service totals. Fourth, build one payout statement per stylist, copying computed figures without editing them. Fifth, review the dispute log for open rows from prior periods and confirm their corrections appear on the correct statements. Sixth, issue statements with pay, collect signatures, and file copies.

Reconciliation comes before computation, not after. If the log and the register disagree, find the missing ticket now. Common causes are a retail sale rung under the wrong stylist, a service ticket posted after the cutoff hour, or a discount entered in the register but not in the log. Each has a one line fix. Computing payouts on unreconciled totals guarantees corrections later, which costs more time than the reconciliation would have.

The cutoff hour deserves emphasis. Define the exact minute a period ends, for example Saturday at close or Sunday at midnight, and assign every ticket by its transaction time. Late posted tickets belong to the period they post in, with a note referencing the service date. Without a cutoff rule, threshold cases will always be arguable: a ticket posted Sunday morning either qualifies someone for a tier or it does not, and both sides will remember the verbal rule differently. The written cutoff ends that argument permanently.

Filing closes the period. Each period packet holds the sales log printout, the tier sheet, one signed statement per stylist, the dispute log page, and the register period report. File by period, not by stylist, so an audit of any question pulls one folder. Retain packets per local record keeping requirements. When a question arrives weeks later, the packet answers it in minutes.

## 12. Checklists

Use these checklists as written for the first two pay periods, then adapt them to the shop.

Daily logging checklist. Register report pulled. Service totals entered per stylist. Retail totals entered per stylist. Correct rates on every row. Discount tickets entered at the collected amount. Day totals reconciled to the register. Voids noted the same day.

Period close checklist. Every day of the period has rows. Column totals match the register period report. Voids removed from totals. Refunds posted as labeled adjustments. Tier sheet run from adjusted totals. Statements built by copying, not retyping. Prior open disputes resolved onto statements. Cutoff hour honored on late tickets.

Statement issue checklist. One statement per stylist. Every line traces to one source. Rates shown on the statement match the agreement. Adjustments carry original period and reason. Both copies signed. Packet filed by period.

Agreement checklist. One signed agreement per team member. Every rate line initialed. Voids, refunds, discounts, and correction window stated. Pay schedule and review rights stated. Rate changes initialed before the affected period. Professional review completed before first use.

Dispute checklist. Logged within forty eight hours. Issue recorded in the reporter own words. Records pulled and difference computed. Resolution written with payout reference. Both initials collected. Status updated.

## 13. More Illustrative Walkthroughs

Walkthrough one, labeled illustrative, traces a full period for a two chair shop. Illustrative Stylist A: service sales 2,850 dollars for the period at 50 percent, retail 320 dollars at 15 percent, no tier qualification against a 3,000 dollar threshold. Service commission equals 1,425.00 dollars. Retail commission equals 48.00 dollars. Gross equals 1,473.00 dollars with no adjustments. Illustrative Stylist B: service 3,150 dollars at 50 percent base with a 55 percent tier rate and 100 dollar bonus at the same threshold, retail 120 dollars at 10 percent. Qualified service payout equals 3,150 times 55 divided by 100 plus 100, which is 1,832.50 dollars. Retail equals 12.00 dollars. Gross equals 1,844.50 dollars. Every figure and label here is illustrative.

Walkthrough two, labeled illustrative, traces a correction period. Illustrative Stylist A prior statement underpaid retail by 4.25 dollars per the dispute log. Current period service commission 1,200.00 dollars, retail 60.00 dollars, no tier, plus an adjustment line of positive 4.25 dollars labeled with the original period and reason. Gross equals 1,264.25 dollars. The dispute row is marked corrected with this payout date, then closed on initials. Every figure and label here is illustrative.

Walkthrough three, labeled illustrative, traces a void heavy period. A duplicate ticket of 120 dollars was entered under Illustrative Stylist B and voided the same day. The sales total is reduced by 120 dollars before commission. At a 50 percent service rate the commission effect is 60.00 dollars correctly excluded. The informational voids column shows 120.00 dollars. No dispute arises because the statement shows the removal on its face. Every figure and label here is illustrative.

## 14. Frequently Asked Questions

How long does setup take. One pay period of normal operation: enter staff, rates, and thresholds from the signed agreements, then log daily. The first period end takes longer because every step is new. The second period end moves quickly.

Can rates differ between stylists. Yes. Each row carries its own service and retail rate from that stylist agreement. The tier sheet carries per stylist thresholds and rates as well. Different experience levels and roles commonly carry different rates.

What happens when nobody crosses a tier threshold. The sheet pays the base rate with no bonus, and the period is documented the same as any other. Quiet periods still get full statements and filing. Skipping documentation in quiet periods is how later questions become unanswerable.

How are refunds handled when the original sale was several periods ago. Post the deduction in the refund period with the original sale date labeled. The correction window in the agreement governs how far back questions can reopen a closed period, but a real refund posts where the money moved regardless.

Can this kit handle cash tips or card tips. No. Tip computation, reporting, and distribution follow separate rules and are outside this kit. Keep tips on their own record entirely.

What if a stylist disputes the agreement itself, not the math. That is a contract conversation, not a computation question. Pause, review the signed page together, and record the outcome in writing. If the agreement needs changing, follow the rate change procedure with initials and an effective date.

What if the register cannot split service and retail by stylist. Export what it can, assign tickets daily by stylist from receipts, and consider that register limitation when evaluating tools at renewal. Daily assignment takes minutes. Period end reconstruction from an unsplit report takes hours and introduces errors.

What if two stylists split one service. Divide the ticket at logging time per the shop split rule stated in the agreement, with each share on its own stylist row. Splits decided weeks later are unreliable. The daily log is the place where splits are recorded.

## 15. Limitations

This kit covers commission payroll computation and records for independent salons and spas. It does not compute payroll taxes, tip reporting, benefits, or deductions. It does not support booth rental or chair rental accounting in any form. Tier logic covers one threshold per period per stylist. The spreadsheet has no export to payroll software. The agreement template requires review by a qualified professional before use. Correction windows, cutoff hours, and discount policies must be set by the owner to fit local practice and law.

## 16. Disclosure

This guide is educational material. It is not payroll, tax, or legal advice. Commission structures must follow local labor law. All staff labels, numbers, and walkthroughs are illustrative fictional examples used to demonstrate arithmetic. Your sales, rates, and local rules determine your actual figures. No specific financial result is promised. Have the agreement template reviewed by a qualified professional before use.

## 17. Getting Started This Pay Period

Day one, complete one agreement per team member and enter staff, rates, and thresholds into the workbook. Each day, log service and retail sales per stylist and reconcile to the register. At period end, remove voids, post refunds, run the tier sheet, and issue one statement per stylist. Log every question within forty eight hours. File the period packet. Repeat. The routine is the product. The sheets are only its memory.
