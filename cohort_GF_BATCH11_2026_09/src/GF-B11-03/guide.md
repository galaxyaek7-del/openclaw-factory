# Restaurant Food Cost Control Kit - Operations Guide

## 1. Who This Guide Serves

This guide serves independent single-unit restaurant owners and kitchen managers who place orders, set menus, and supervise a small team. It assumes you can open a spreadsheet, read an invoice, and count what is on your shelves. It does not assume accounting training. Every formula is shown step by step with illustrative numbers that are labeled as illustrative so you always know which figures are teaching examples and which figures are your own.

If you run more than one unit, operate a commissary, or focus on bar and liquor inventory, this kit is not built for you. Those operations need consolidation and product categories this kit does not contain. For a single dining room with a fixed menu, a walk-in, a dry store, and a freezer, the routine in this guide fits directly.

## 2. The Problem in Plain Terms

Food cost is the ratio of what you used to what you sold. Industry background figures published by the National Restaurant Association place typical restaurant food cost in the 28 to 35 percent band. That band is background context, not a target handed to you. Your menu, your suppliers, and your portion sizes set your own workable number. The problem this kit addresses is not the band itself. It is the quiet drift above your own number that happens when nobody measures weekly.

Drift has familiar sources. Portions creep up when scoops and ladles are not standardized. Spoilage grows when pars are guesses and deliveries arrive before storage is ready. Waste goes unrecorded when staff have nowhere quick to log it. Theft and unrecorded staff meals add small amounts that compound. Supplier prices move while recipe cards stay frozen. Each source alone looks small. Together they move actual food cost two or three points above theoretical cost, and on thin margins that movement matters. A three point gap on twenty thousand dollars of weekly food sales is six hundred dollars of usage you cannot explain. Over a quarter, that unexplained usage exceeds the price of this kit hundreds of times over. No outcome is promised here. The point is that measurement makes the gap visible so you can act on it.

## 3. Method Overview

The method has four parts that run as one weekly ritual. First, theoretical versus actual food cost comparison. Theoretical cost is what you should have used given what you sold and your standardized recipes. Actual cost is what you did use given opening inventory, purchases, and closing inventory. The difference is variance. Second, a weekly variance review meeting of thirty minutes with a fixed agenda. Third, par and reorder discipline so orders match demand instead of habit. Fourth, a two week waste log that runs continuously and feeds the review with real event data.

The order matters. Counts produce actual cost. Recipes produce theoretical cost. The dashboard compares them. The waste log explains part of the gap. The review assigns at most three actions. Pars are adjusted. The next week repeats. After four to six weeks the routine becomes habit and each review gets shorter because the same causes stop repeating.

## 4. Theoretical Versus Actual Food Cost

Theoretical food cost answers one question: given everything you sold this week and the cost of each recipe as written, what should your usage have been. Actual food cost answers a different question: given what was on the shelf at the start, what arrived, and what remains, what did you actually use. Both are dollar figures first and percentages second.

The actual usage formula is the foundation of the whole kit:

Actual usage equals opening inventory plus purchases minus closing inventory.

Write it on the wall of the office. Opening inventory is the extended value of everything on hand at the start of the week, counted at current unit cost. Purchases are the cost of goods received during the week, taken from invoices, not from orders placed. Closing inventory is the extended value counted at the end of the week in the same locations with the same units. The formula works because everything that entered the building either remains on the shelf or was used. What was used is the residual.

Consider an illustrative example, labeled illustrative. Opening inventory is 4,200 dollars. Purchases received during the week total 6,800 dollars. Closing inventory is 3,900 dollars. Actual usage equals 4,200 plus 6,800 minus 3,900, which is 7,100 dollars. Every number in this paragraph is illustrative and exists only to show the arithmetic.

Actual food cost percent adds sales:

Actual food cost percent equals actual usage divided by food sales, times one hundred.

Continuing the illustrative example, food sales for the week are 20,000 dollars. Actual food cost percent equals 7,100 divided by 20,000, times one hundred, which is 35.5 percent. Note that beverage sales are excluded from food sales in this kit. Mixing bar sales into the denominator hides food problems. Keep them separate.

Theoretical usage is computed from sales mix and recipe costs. For each menu item, multiply portions sold by the plate cost from the recipe coster, then sum across the menu:

Theoretical usage equals the sum over all items of portions sold times plate cost.

Theoretical food cost percent equals theoretical usage divided by food sales, times one hundred.

Consider a small illustrative example, labeled illustrative. A sandwich has a plate cost of 1.77 dollars. The register shows 400 sold. That item contributes 708 dollars of theoretical usage. A salad plates at 2.10 dollars with 200 sold, contributing 420 dollars. A pasta plates at 3.40 dollars with 150 sold, contributing 510 dollars. Theoretical usage for these three items is 1,638 dollars. If these were the only sales and food sales were 5,000 dollars, theoretical food cost percent would be 32.76 percent. Real menus have more items, but the mechanic is identical: each item sold pulls its recipe cost into the theoretical total.

Variance is the gap:

Variance in points equals actual food cost percent minus theoretical food cost percent.

Variance in dollars equals actual usage minus theoretical usage.

In the larger illustrative example, actual was 35.5 percent and theoretical was 32.0 percent, so variance is 3.5 points. That is the number the weekly review exists to shrink. A variance under one point in a scratch kitchen with honest counts is a calm week. Between one and two points deserves one investigation. Above two points demands the full review. These thresholds are working rules from operating practice, not standards handed down by any authority. Set your own after four weeks of your own data.

## 5. Why Variance Happens

Variance is a symptom with a short list of usual causes. Waste and spoilage are the largest in most independent kitchens. Over-portioning is next, especially on proteins and cheese. Unrecorded staff meals, family meals, and comps explain part of the gap in houses that do not track them. Supplier price moves without recipe updates make theoretical cost stale. Receiving errors, short weights, and substitution without credit add quiet dollars. Data errors, meaning missed invoices or counts done in different units, create false variance that wastes investigation time. The review ritual exists to sort real causes from data errors quickly.

A useful discipline is to check data quality before chasing causes. Confirm every invoice for the week is entered. Confirm opening and closing counts covered the same locations. Confirm units match, meaning cases were not counted as pounds in one week and eaches in the next. Confirm comps and staff meals were recorded where the sheet expects them. Only then discuss portions, waste, and prices. About one review in four in a new routine turns out to be a data error rather than a kitchen problem. That is normal and it is good news, because data errors are cheap to fix permanently with a checklist.

## 6. Setting Up the Workbook

The workbook file is named restaurant_food_cost_control_workbook.xlsx. It contains five sheets. Open it and work through them in the order below. Do not skip the setup pass, because every formula downstream depends on clean item names and consistent units.

Sheet one is Inventory Count. Columns are Location, Item Name, Unit, Unit Cost, Count Qty, and Extension. Enter every item you stock, grouped by location: dry storage, walk-in, freezer, and any satellite storage. Choose one unit per item and use it every week. Flour might be pounds, buns eaches, fries cases. Enter the current unit cost from the latest invoice. Extension is computed as Unit Cost times Count Qty, and the total row sums the column. That total is the inventory value you carry into the dashboard as opening or closing.

Sheet two is Recipe Coster. Columns are Recipe, Ingredient, Qty, Unit, Unit Cost, and Line Cost. Each ingredient line computes Qty times Unit Cost. A batch total sums the lines, and plate cost divides the batch total by portions. Cost the ten highest sellers first. Pull quantities from the written recipe, not from memory, and pull unit costs from the same invoice prices used on the count sheet so the two sheets agree. Date each costing. Re-cost when a supplier price moves more than a few percent or when you change a specification.

Sheet three is Variance Dashboard. Columns are Week Ending, Opening Inv, Purchases, Closing Inv, Food Sales, Actual Usage, Actual FC Pct, Theoretical FC Pct, and Variance Pts. Actual Usage is computed as Opening plus Purchases minus Closing. Actual FC Pct divides usage by sales. Variance Pts subtracts theoretical from actual. Theoretical percent is entered from the recipe math for the week, which the guide explains how to build from register sales. Format the percent columns as percent so a value like 0.355 displays as 35.5 percent.

Sheet four is Waste Log. Columns are Date, Item, Qty, Unit Cost, Waste Cost, and Reason. Waste Cost is Qty times Unit Cost. Staff enter lines during the shift. The weekly total transfers to the review agenda.

Sheet five is Par Reorder. Columns are Item, Unit, Avg Daily Use, Lead Days, Par Level, On Hand, and Order Qty. Par Level is computed as Avg Daily Use times Lead Days plus one safety day. Order Qty is Par minus On Hand, floored at zero. The worked method for setting each input is covered in the par chapter later in this guide.

## 7. The Inventory Count Workflow

Counts must be consistent to be comparable. Count the same locations, in the same order, with the same units, at the same time of week. Many operators count Sunday night after close or Monday morning before deliveries. Pick one slot and keep it. The person who counts should not be the person who orders, at least for the first month, so errors surface instead of hiding.

Prepare before counting. Print the count sheet sorted by location. Bring a scale, a calculator, and a pen. Walk each location top to bottom, left to right. Count open packages by weight or by fraction where the sheet expects it, and write the fraction clearly. A half case of buns is not a case. Record partials honestly because proteins in opened bags are exactly where false variance breeds.

Price the count after the physical walk. Multiply each quantity by the current unit cost and extend the lines. Use the most recent invoice cost, not an average of old prices, because the dashboard compares this week against this week. File the priced sheet with the week packet. Enter opening and closing values into the dashboard. The whole count takes forty five to seventy five minutes in a typical independent kitchen once the item list is set. The first count takes longer. That is expected.

Common count errors deserve a checklist of their own. Units changing between weeks is the most frequent. A case of chicken counted as pounds one week and cases the next destroys comparability. New items missing from the sheet is second. Add them the week they appear. Transfer timing is third. A delivery received after the closing count belongs to next week purchases, not this week. Staff meals pulled after the count but recorded this week create a one week distortion. Pick a cutoff minute and honor it.

## 8. Recipe Costing in Depth

Recipe costing turns the menu into numbers the dashboard can use. For each recipe, list every ingredient with its quantity in the recipe unit and the current unit cost. Multiply to get line costs, sum to get batch cost, divide by yield to get plate cost. Divide plate cost by menu price to get the item food cost percent. That last figure tells you which items pull the theoretical average up and which pull it down.

Consider a full illustrative example, labeled illustrative. A chicken sandwich uses a six ounce portion of chicken breast. Six ounces is 0.375 pounds at 2.40 dollars per pound, giving 0.90 dollars. A bun at 0.55 dollars each, one per sandwich, gives 0.55 dollars. Lettuce and tomato portioned at 0.32 dollars gives 0.32 dollars. Batch math is trivial for a one portion recipe: total plate cost is 1.77 dollars. At a menu price of 9.95 dollars, item food cost is 17.8 percent. Every figure in this paragraph is illustrative.

Sauces, dressings, and batch prep need yield math. Make the batch, weigh or portion the finished quantity, and divide total batch cost by the number of portions the batch actually yields, not the number the recipe card hopes for. If a sauce batch costs 12.00 dollars in ingredients and yields forty two-ounce portions, each portion costs about 0.29 dollars. Enter that portion cost as one ingredient line on every recipe that uses the sauce. This single habit fixes a large share of stale theoretical costs, because sauces are where memory quantities drift furthest from reality.

Re-costing cadence keeps theoretical cost honest. Re-cost proteins monthly because prices move fastest there. Re-cost the full top ten quarterly. Re-cost any item immediately when a supplier substitutes a product or changes pack size. Date every card. An undated card is an untrusted card. When the review shows variance concentrating in one menu category, re-cost that category first before accusing the line of over-portioning. Stale cards have blamed many cooks for a purchasing problem.

Menu engineering follows naturally once cards are current. Items with low food cost percent and strong sales are the workhorses to feature. Items with high cost percent and weak sales are candidates for repricing, re-portioning, or removal. Items with high cost percent and strong sales need portion control and waste attention rather than removal, because guests have already voted. None of this requires software. Sort the recipe sheet by item food cost percent and by portions sold and read the two orders side by side.

## 9. The Weekly Variance Review Ritual

The review is a thirty minute meeting with a printed agenda, the dashboard, the waste total, and the invoice stack. Same day, same time, same order, every week. The template file restaurant_food_cost_weekly_review_agenda.docx structures it. The owner or manager chairs. The head cook attends. Anyone who orders attends. No one else is required.

Minutes zero to ten cover numbers. Read actual usage, actual percent, theoretical percent, and variance points from the dashboard. Read the waste total from the log. Name the top variance category by matching waste reasons and re-cost flags to the numbers. Write all five figures on the agenda. Do not debate causes during these ten minutes. The discipline of stating numbers first prevents the meeting from becoming a story session.

Minutes ten to twenty cover causes. Take variances in order of size. For each, ask four questions. Was the data complete, meaning all invoices entered and counts comparable. Was there a price move, meaning any ingredient cost changed without a card update. Was there a volume anomaly, meaning catering, a private event, or an unusual sales mix that shifted theoretical. Was there an execution issue, meaning over-portioning, spoilage, or a training gap. Record one suspected cause per variance. Resist listing five theories. One cause with an owner beats five theories with none.

Minutes twenty to thirty cover actions and pars. Assign at most three actions with a named owner and a due date before the next review. Typical actions are re-cost a category, change a par, retrain a station on portions, repair a storage seal, or switch a pack size. Then confirm pars and order days for the coming week and sign the agenda. File it with the count sheets and invoices as the week packet. The packet is the audit trail that makes month end review fast.

Follow a worked illustrative review, labeled illustrative. Week ending January 11 shows actual 35.5 percent against theoretical 32.0 percent, variance 3.5 points. Waste totals 156 dollars with overcook chicken as the top item. Data check passes: all invoices entered, same locations counted. Price check finds chicken breast up from 2.10 to 2.40 per pound with no card update, worth about one point. Execution check finds new staff overcooking chicken on the grill, matching the waste log, worth about two points. Actions: re-cost chicken recipes by Wednesday with the owner as holder, retrain grill station Thursday with the head cook as holder, reduce chicken par by one case until waste falls with the manager as holder. Three actions, three owners, one week. Every figure here is illustrative.

## 10. Par and Reorder Discipline

Par is the quantity that should be on hand when the order arrives. Ordering to par replaces guessing with arithmetic. For each item, determine average daily use from recent history, determine lead time in days between placing and receiving, add one safety day, and multiply:

Par level equals average daily use times lead days plus one safety day.

Order quantity equals par level minus on hand, floored at zero.

Consider an illustrative example, labeled illustrative. Chicken breast averages eighteen pounds per day. Lead time is two days. Par equals eighteen times three, which is fifty four pounds. On hand is thirty pounds, so the order is twenty four pounds. Buns average sixty eaches per day with one day lead. Par equals sixty times two, which is one hundred twenty eaches. On hand forty means an order of eighty. Every figure here is illustrative.

Average daily use should come from the last two to four weeks of real counts and purchases, not from memory. A simple way is to sum purchases over fourteen days, adjust for inventory change over the same period, and divide by fourteen. That is the same usage formula stretched over two weeks, which smooths event noise. Update pars monthly and after any menu change, holiday week, or supplier lead change. Seasonal items need their own pars during their season and zero outside it.

Order days matter as much as quantities. Fix delivery days with each supplier and build the count schedule around them so closing counts land just before the largest order. That timing makes the order quantity current instead of stale. Rush orders and off-cycle runs bypass par review, so track them on the agenda. More than two off-cycle orders in a week is itself a review topic.

Storage discipline protects pars from spoilage. First in first out on every shelf. Date every opened package. Keep the walk-in at the correct temperature and log it. Group items by use date during put-away so the oldest is always in front. These sound like kitchen basics because they are, and skipped basics show up as waste log lines within days.

## 11. The Two Week Waste Log

The waste log runs for two full weeks at a time, then totals into the review. Every waste event gets a line at the moment it happens: date, item, quantity, unit cost, computed waste cost, and a reason code. Reason codes stay short and stable: spoilage, overcook, over-prep, dropped, stale, trim, returned plate, and other. Stable codes allow pattern reading. Free text descriptions do not aggregate.

Placement decides compliance. Put the log sheet and a pen at each waste station: grill, fry, prep, and dish. If recording takes more than fifteen seconds, staff will batch it from memory at shift end and accuracy will fall. Review entries mid-shift during the first week and correct vague lines on the spot. Praise honest logging loudly. A cook who logs a ten dollar overcook has given you data worth far more than ten dollars. Punishing honesty kills the log within days.

Read the log weekly by sorting reasons and items. Spoilage clustering on one item points at pars or storage. Overcook clustering on one station points at training or equipment. Over-prep clustering before slow shifts points at prep lists disconnected from sales forecasts. Trim waste rising on proteins points at receiving quality or knife work. Each pattern maps to one of the three weekly actions. The log does not need commentary. Totals and clusters speak.

An illustrative two week read, labeled illustrative, shows the mechanic. Forty one lines total 289 dollars of waste. Spoilage is 96 dollars led by diced tomatoes. Overcook is 88 dollars led by chicken breast. Stale buns are 47 dollars. The review assigns three actions: cut tomato par by one case, retrain grill, move buns to twice weekly delivery. The next two week period totals 141 dollars. The drop is not a promise of results. It is an illustration of how the log directs action. Every figure here is illustrative.

After the first two week run, keep the log running permanently. The marginal effort is minutes per day and the data compounds. When variance is calm, the log confirms calm with evidence instead of hope. When variance spikes, the log shortens the investigation from days to minutes.

## 12. Purchases and Receiving Control

Purchases enter the dashboard from invoices, so invoice discipline is load bearing. Match every delivery to its invoice at the door. Check weights, counts, and temperatures. Note shorts and substitutions on the invoice before signing. File invoices by week, not by supplier, so the week packet is complete. Enter every invoice into the purchases column before the review. A missing invoice creates false variance that sends the meeting chasing kitchen ghosts.

Price monitoring is a monthly task, not a weekly one. Once a month, compare current unit costs against the prior month for the top twenty items by spend. Flag moves above five percent. Update recipe cards for flagged items and note the change on the next agenda. Even without formal bids, a monthly price pass with two competing quotes on proteins keeps suppliers honest.

Substitutions need a written rule. If the ordered product is unavailable, the receiver calls the manager before accepting a substitute, records the substitute price and pack size on the invoice, and flags the recipe cards that use the item. Silent substitutions change plate cost without changing the card, which poisons theoretical cost for weeks until someone notices.

## 13. Portion Control Systems

Portion control is where theoretical cost meets the plate. Standardize the tools: scales at prep, portion scoops with fixed sizes, ladles with marked volumes, and count-based builds for high cost items. A chicken sandwich gets one six ounce portion, not a handful. Cheese gets a weighed amount, not a pinch. These are not suggestions for the team. They are the quantities the recipe cards assume, so any deviation is variance by definition.

Build cards with photos for the top sellers. One photo of the correct plate, one ingredient list with quantities, posted at the station. Photos settle arguments faster than words and make training new staff a matter of minutes. Audit portions weekly by weighing five random plates from each high cost station during service. Record the results on the agenda. Audits are calibration, not accusation, and experienced cooks usually welcome them once the routine is framed that way.

Staff meals and comps need a recording rule, not a ban. Unrecorded food is indistinguishable from waste in the numbers. Provide a simple meal log at the pass with name, item, and time. Record comps and voids from the register on the same sheet. Transfer weekly totals into the review so the meeting can separate policy food from problem food. Houses that track this line often find half a point of variance that was never a kitchen failure at all.

## 14. Checklists

Use these checklists as written for the first month, then adapt them to your kitchen.

Weekly count checklist. Same day and time each week. Same locations in the same order. Same units as last week. Scale and calculator on hand. Open packages weighed or fractioned honestly. New items added to the sheet. Priced at latest invoice cost. Totals entered to dashboard as opening and closing. Prior week packet filed.

Review meeting checklist. Dashboard printed. Waste total transferred. Invoices complete for the week. Numbers read before causes discussed. Data quality checked first. At most three actions assigned with owners and dates. Pars confirmed. Agenda signed and filed.

Receiving checklist. Delivery matched to invoice. Weights and counts verified. Temperatures checked. Shorts noted before signing. Substitutions flagged to manager. Invoices filed by week. Purchases column updated.

Daily line checklist. Portion tools at stations. Build cards visible. Waste log and pen at each station. Staff meals recorded. Walk-in temperatures logged. Put-away follows first in first out.

Monthly maintenance checklist. Top twenty prices compared. Flagged recipe cards re-costed. Pars updated from recent use. Scale calibrated. Storage seals and gaskets inspected. Slow sellers reviewed for repricing or removal.

## 15. More Illustrative Walkthroughs

Walkthrough one, labeled illustrative, traces a full week for a small bistro. Opening inventory 3,100 dollars. Purchases 5,400 dollars. Closing 2,900 dollars. Usage equals 3,100 plus 5,400 minus 2,900, which is 5,600 dollars. Food sales 16,000 dollars. Actual percent equals 5,600 divided by 16,000, which is 35.0 percent. Theoretical from recipe math is 32.4 percent. Variance is 2.6 points, or 416 dollars. Waste log shows 132 dollars with over-prep salads leading. Data check passes. Price check finds cheese up eight percent without a card update. Actions: re-cost cheese items, cut salad prep par on slow days, audit grill portions Friday. Every figure here is illustrative.

Walkthrough two, labeled illustrative, shows a calm week. Opening 2,800, purchases 5,100, closing 2,700. Usage is 5,200. Sales 16,200. Actual is 32.1 percent. Theoretical is 31.8 percent. Variance is 0.3 points. Waste totals 58 dollars with no cluster. The meeting takes ten minutes, confirms pars, and files the packet. Calm weeks still get the meeting, because skipping calm weeks is how drift returns unnoticed. Every figure here is illustrative.

Walkthrough three, labeled illustrative, shows a data error. Variance reads 4.1 points and the room tenses. Data check finds a 640 dollar produce invoice filed in the wrong week. Moving it to the correct week drops variance to 1.2 points. The meeting assigns one action: file invoices by week with a second initial. No kitchen action needed. This is a successful review, not a failed one. Every figure here is illustrative.

## 16. Frequently Asked Questions

How long until the routine shows patterns. Most kitchens see the first useful pattern in week two when the waste log clusters, and the first trustworthy variance trend after four consistent weeks. Before that, treat every number as provisional and focus on building the counting habit.

What if my menu changes often. Cost new items before they launch, even roughly, and date the card as preliminary. Update within the first week of sales. Specials need a cost card too if they run more than three days, because an uncosted special corrupts theoretical cost for its whole run.

What if suppliers change prices constantly. Re-cost proteins monthly at minimum and flag any move above five percent immediately. Keep a price history column on the count sheet so trends are visible. Where two suppliers compete, quote both on the top five items quarterly.

What if staff resist logging waste. Shorten the walk to the log, praise honest entries, and share the weekly total with the team. Show one fix that came from their entries, like a par cut that reduced spoilage handling. Resistance usually fades after the first visible fix.

What if I cannot attend the review every week. Delegate the chair with the printed agenda and require the signed packet on your desk. The ritual matters more than your presence. Missing two weeks in a row restarts the drift clock.

What if variance stays above two points for a month. Re-cost the full top ten, audit portions daily for one week, and review pars against actual use rather than memory. If all three check out, examine receiving records and comps logging for leaks. Persistent variance with clean data points at specification drift across several items rather than one large failure.

What if my kitchen is very small. Run the same routine with fewer rows. Count everything, cost the top five, log waste at one station. The formulas do not care about scale. Small kitchens often see faster results because one fix touches a larger share of sales.

What if I use a point of sale with recipe features. Keep the register as the sales source and this workbook as the control layer until the register data proves consistent for a full month. Many operators run both permanently because the spreadsheet review takes minutes and reads differently than a register report.

## 17. Limitations

This kit fits single-unit independent restaurants with fixed menus and standard storage. It does not consolidate multiple units, manage commissary transfers, or track banquet production with its own costing rules. It does not cover bar or liquor inventory, which needs different units and controls. The spreadsheet uses standard formulas with no live supplier feed, so price moves enter by hand. The waste log depends on honest same-shift recording, which no sheet can compel. Theoretical cost is only as current as the recipe cards behind it. Stale cards produce confident wrong numbers.

## 18. Disclosure

This guide is educational material. It is not accounting, tax, or legal advice. All worked numbers are illustrative fictional examples used to demonstrate arithmetic. Your suppliers, menu, labor, and local conditions determine your actual figures. No specific financial result is promised. Industry background figures referenced from the National Restaurant Association describe broad bands, not targets for your operation. Review tax and labor practices with qualified professionals in your area.

## 19. Getting Started This Week

Day one, print the count sheet and list every item with its unit. Day two, enter current invoice costs and take the first full count as opening. Day three, cost the top five sellers and post the waste log. Days four through seven, log waste and file invoices by week. Day eight, take the closing count, fill the dashboard, and hold the first review. Repeat. The routine is the product. The sheets are only its memory.

## 10. Par and Reorder Discipline

Par is the quantity that should be on hand when the order arrives. Ordering to par replaces guessing with arithmetic. For each item, determine average daily use from recent history, determine lead time in days between placing and receiving, add one safety day, and multiply:

Par level equals average daily use times lead days plus one safety day.

Order quantity equals par level minus on hand, floored at zero.

Consider an illustrative example, labeled illustrative. Chicken breast averages eighteen pounds per day. Lead time is two days. Par equals eighteen times three, which is fifty four pounds. On hand is thirty pounds, so the order is twenty four pounds. Buns average sixty eaches per day with one day lead. Par equals sixty times two, which is one hundred twenty eaches. On hand forty means an order of eighty. Every figure here is illustrative.

Average daily use should come from the last two to four weeks of real counts and purchases, not from memory. A simple way: sum purchases over fourteen days, adjust for inventory change over the same period, divide by fourteen. That is the same usage formula stretched over two weeks, which smooths event noise. Update pars monthly and after any menu change, holiday week, or supplier lead change. Seasonal items need their own pars during their season and zero outside it.

Order days matter as much as quantities. Fix delivery days with each supplier and build the count schedule around them so closing counts land just before the largest order. That timing makes the order quantity current instead of stale. Rush orders and off-cycle runs are variance fuel because they bypass par review. Track them on the agenda. More than two off-cycle orders in a week is itself a review topic.

Storage discipline protects pars from spoilage. First in first out on every shelf. Date every opened package. Keep the walk-in at the correct temperature and log it. Group items by use date during put-away so the oldest is always in front. These sound like kitchen basics because they are, and skipped basics show up as waste log lines within days.

## 11. The Two Week Waste Log

The waste log runs for two full weeks at a time, then totals into the review. Every waste event gets a line at the moment it happens: date, item, quantity, unit cost, computed waste cost, and a reason code. Reason codes stay short and stable: spoilage, overcook, over-prep, dropped, stale, trim, returned plate, and other. Stable codes allow pattern reading. Free text descriptions do not aggregate.

Placement decides compliance. Put the log sheet and a pen at each waste station: grill, fry, prep, and dish. If recording takes more than fifteen seconds, staff will batch it from memory at shift end and accuracy will fall. Review entries mid-shift during the first week and correct vague lines on the spot. Praise honest logging loudly. A cook who logs a ten dollar overcook has given you data worth far more than ten dollars. Punishing honesty kills the log within days.

Read the log weekly by sorting reasons and items. Spoilage clustering on one item points at pars or storage. Overcook clustering on one station points at training or equipment. Over-prep clustering before slow shifts points at prep lists disconnected from sales forecasts. Trim waste rising on proteins points at receiving quality or knife work. Each pattern maps to one of the three weekly actions. The log does not need commentary. Totals and clusters speak.

An illustrative two week read, labeled illustrative, shows the mechanic. Forty one lines total 289 dollars of waste. Spoilage is 96 dollars led by diced tomatoes. Overcook is 88 dollars led by chicken breast. Stale buns are 47 dollars. The review assigns: cut tomato par by one case, retrain grill, move buns to twice weekly delivery. Next two weeks total 141 dollars. The drop is not a promise of results. It is an illustration of how the log directs action. Every figure here is illustrative.

After the first two week run, keep the log running permanently. The marginal effort is minutes per day and the data compounds. When variance is calm, the log confirms calm with evidence instead of hope. When variance spikes, the log shortens the investigation from days to minutes.

## 12. Purchases and Receiving Control

Purchases enter the dashboard from invoices, so invoice discipline is load bearing. Match every delivery to its invoice at the door. Check weights, counts, and temperatures. Note shorts and substitutions on the invoice before signing. File invoices by week, not by supplier, so the week packet is complete. Enter every invoice into the purchases column before the review. A missing invoice creates false variance that sends the meeting chasing kitchen ghosts.

Price monitoring is a monthly task, not a weekly one. Once a month, compare current unit costs against the prior month for the top twenty items by spend. Flag moves above five percent. Update recipe cards for flagged items and note the change on the next agenda. Contracts and bid sheets belong here for larger operators, but even without formal bids, a monthly price pass with two competing quotes on proteins keeps suppliers honest.

Substitutions need a written rule. If the ordered product is unavailable, the receiver calls the manager before accepting a substitute, records the substitute price and pack size on the invoice, and flags the recipe cards that use the item. Silent substitutions change plate cost without changing the card, which poisons theoretical cost for weeks until someone notices.

## 13. Portion Control Systems

Portion control is where theoretical cost meets the plate. Standardize the tools: scales at prep, portion scoops with fixed sizes, ladles with marked volumes, and count-based builds for high cost items. A chicken sandwich gets one six ounce portion, not a handful. Cheese gets a weighed amount, not a pinch. These are not suggestions for the team. They are the quantities the recipe cards assume, so any deviation is variance by definition.

Build cards with photos for the top sellers. One photo of the correct plate, one ingredient list with quantities, posted at the station. Photos settle arguments faster than words and make training new staff a matter of minutes. Audit portions weekly by weighing five random plates from each high cost station during service. Record the results on the agenda. Audits are not accusations. They are calibration, and experienced cooks usually welcome them once the routine is framed that way.

Staff meals and comps need a recording rule, not a ban. Unrecorded food is indistinguishable from waste in the numbers. Provide a simple meal log at the pass: name, item, time. Record comps and voids from the register on the same sheet. Transfer weekly totals into the review so the meeting can separate policy food from problem food. Houses that track this line often find half a point of variance that was never a kitchen failure at all.

## 14. Checklists

Use these checklists as written for the first month, then adapt them to your kitchen.

Weekly count checklist. Same day and time each week. Same locations in the same order. Same units as last week. Scale and calculator on hand. Open packages weighed or fractioned honestly. New items added to the sheet. Priced at latest invoice cost. Totals entered to dashboard as opening and closing. Prior week packet filed.

Review meeting checklist. Dashboard printed. Waste total transferred. Invoices complete for the week. Numbers read before causes discussed. Data quality checked first. At most three actions assigned with owners and dates. Pars confirmed. Agenda signed and filed.

Receiving checklist. Delivery matched to invoice. Weights and counts verified. Temperatures checked. Shorts noted before signing. Substitutions flagged to manager. Invoices filed by week. Purchases column updated.

Daily line checklist. Portion tools at stations. Build cards visible. Waste log and pen at each station. Staff meals recorded. Walk-in temperatures logged. Put-away follows first in first out.

Monthly maintenance checklist. Top twenty prices compared. Flagged recipe cards re-costed. Pars updated from recent use. Scale calibrated. Storage seals and gaskets inspected. Slow sellers reviewed for repricing or removal.

## 15. More Illustrative Walkthroughs

Walkthrough one, labeled illustrative, traces a full week for a small bistro. Opening inventory 3,100 dollars. Purchases 5,400 dollars. Closing 2,900 dollars. Usage equals 3,100 plus 5,400 minus 2,900, which is 5,600 dollars. Food sales 16,000 dollars. Actual percent equals 5,600 divided by 16,000, which is 35.0 percent. Theoretical from recipe math is 32.4 percent. Variance is 2.6 points, or 416 dollars. Waste log shows 132 dollars with over-prep salads leading. Data check passes. Price check finds cheese up eight percent without a card update. Actions: re-cost cheese items, cut salad prep par on slow days, audit grill portions Friday. Every figure here is illustrative.

Walkthrough two, labeled illustrative, shows a calm week. Opening 2,800, purchases 5,100, closing 2,700. Usage is 5,200. Sales 16,200. Actual is 32.1 percent. Theoretical is 31.8 percent. Variance is 0.3 points. Waste totals 58 dollars with no cluster. The meeting takes ten minutes, confirms pars, and files the packet. Calm weeks still get the meeting, because skipping calm weeks is how drift returns unnoticed. Every figure here is illustrative.

Walkthrough three, labeled illustrative, shows a data error. Variance reads 4.1 points and the room tenses. Data check finds a 640 dollar produce invoice filed in the wrong week. Moving it to the correct week drops variance to 1.2 points. The meeting assigns one action: file invoices by week with a second initial. No kitchen action needed. This is a successful review, not a failed one. Every figure here is illustrative.

## 16. Frequently Asked Questions

How long until the routine pays attention to itself. Most kitchens see the first useful pattern in week two when the waste log clusters, and the first trustworthy variance trend after four consistent weeks. Before that, treat every number as provisional and focus on building the counting habit.

What if my menu changes often. Cost the new items before they launch, even roughly, and date the card as preliminary. Update within the first week of sales. Specials need a cost card too if they run more than three days, because an uncosted special corrupts theoretical cost for its whole run.

What if suppliers change prices constantly. Re-cost proteins monthly at minimum and flag any move above five percent immediately. Keep a price history column on the count sheet so trends are visible. Where two suppliers compete, quote both on the top five items quarterly.

What if staff resist logging waste. Shorten the walk to the log, praise honest entries, and share the weekly total with the team. Show one fix that came from their entries, like a par cut that reduced spoilage handling. Resistance usually fades after the first visible fix.

What if I cannot attend the review every week. Delegate the chair with the printed agenda and require the signed packet on your desk. The ritual matters more than your presence. Missing two weeks in a row restarts the drift clock.

What if my variance stays above two points for a month. Re-cost the full top ten, audit portions daily for one week, and review pars against actual use rather than memory. If all three check out, examine receiving records and comps logging for leaks. Persistent variance with clean data points at specification drift across several items rather than one large failure.

What if my kitchen is very small. Run the same routine with fewer rows. Count everything, cost the top five, log waste at one station. The formulas do not care about scale. Small kitchens often see faster results because one fix touches a larger share of sales.

What if I use a point of sale with recipe features. Keep the register as the sales source and this workbook as the control layer until the register data proves consistent for a full month. Many operators run both permanently because the spreadsheet review takes minutes and reads differently than a register report.

## 17. Limitations

This kit fits single-unit independent restaurants with fixed menus and standard storage. It does not consolidate multiple units, manage commissary transfers, or track banquet production with its own costing rules. It does not cover bar or liquor inventory, which needs different units and controls. The spreadsheet uses standard formulas with no live supplier feed, so price moves enter by hand. The waste log depends on honest same-shift recording, which no sheet can compel. Theoretical cost is only as current as the recipe cards behind it. Stale cards produce confident wrong numbers.

## 18. Disclosure

This guide is educational material. It is not accounting, tax, or legal advice. All worked numbers are illustrative fictional examples used to demonstrate arithmetic. Your suppliers, menu, labor, and local conditions determine your actual figures. No specific financial result is promised. Industry background figures referenced from the National Restaurant Association describe broad bands, not targets for your operation. Review tax and labor practices with qualified professionals in your area.

## 19. Getting Started This Week

Day one, print the count sheet and list every item with its unit. Day two, enter current invoice costs and take the first full count as opening. Day three, cost the top five sellers and post the waste log. Days four through seven, log waste and file invoices by week. Day eight, take the closing count, fill the dashboard, and hold the first review. Repeat. The routine is the product. The sheets are only its memory.
