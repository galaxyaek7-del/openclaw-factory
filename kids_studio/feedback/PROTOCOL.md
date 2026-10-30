# Private parent feedback on the ep01 animatic

The arm's cheapest test (arm_portfolio.py): show the ep01 animatic privately to a few parents and record what
they say, before any narration is paid for or any channel is opened. Nothing here publishes anything.

## Who and how
- 3 to 8 parents of Arabic-speaking children aged 4 to 8, known to the founder. Not a public post, not a paid panel.
- The parent watches first, alone; they decide whether their child watches at all.
- The file is shared privately (direct message or in person). It is not uploaded to a public platform.
- The scripts are still DRAFT pending a native Arabic review; say so before showing.

## What is recorded, and what never is
Recorded: the parent's own answers to the questions below, the child's age band (4-5, 6-8) and whether the child
watched. Never recorded: names, contact details, photos, video or audio of a child, school, location. The
recorder refuses free text that looks like an e-mail address or a phone number.

## Questions (ask in Arabic; record the answer as said)
1. Would you let your child watch this episode on their own? (yes / with me / no)
2. If your child watched: how much of it did they watch? (all / about half / stopped early / did not watch)
3. Was the Arabic right for this age: too hard, right, too easy?
4. Was anything unsuitable, unclear or wrong? (free text)
5. Would you want a next episode? (yes / maybe / no)
6. Where would you look for a show like this? (free text: platform or place, not a link)

## Continue, modify, stop (from the arm's own criteria)
- Continue to native review and narration if at least half of the parents answer "yes" or "with me" to 1 and nobody reports an unsuitable element that cannot be fixed.
- Modify the format (subtitle-first, shorter) if the language is "too hard" for most.
- Stop if a child-safety concern is raised that cannot be fixed.

Record with `python kids_studio/feedback/record_feedback.py --help`. The ledger is
`data/kids_feedback.jsonl` (git-ignored).
