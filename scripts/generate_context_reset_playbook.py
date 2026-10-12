"""Generates the paid deliverable for 'The 5-Minute Context Reset Playbook'.

Why this script exists instead of the generated PDF being committed: .gitignore
deliberately excludes books/*.pdf, because this repository is served publicly
via GitHub Pages and a tracked product PDF is downloadable by URL guess --
bypassing Gumroad checkout entirely. That rule exists to protect paid
products, so the deliverable is generated from this source and delivered
through the paid channel, never committed.

Verified live (2026-10-12): the PDF produced by this script was uploaded to
Gumroad as a 1-file attachment, downloaded back from the live listing, and its
sha256 matched the local file byte-for-byte.

Run from the repository root:
    python scripts/generate_context_reset_playbook.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from book_generator import generate_book_from_content

TITLE = "The 5-Minute Context Reset Playbook"
SUBTITLE = "A practical system for remote developers who lose focus every time the context switches"
PRODUCTION_ID = "PROD-fresh-ada4a519"

C1 = """Most developers do not lose focus to distraction. They lose it to the cost of rebuilding context.

Every interruption -- a meeting, a review, a Slack thread, a failing test -- does not just cost the thirty seconds it takes to answer it. It costs the several minutes your brain needs to reconstruct what you were doing, why you were doing it, and what "done" looks like. Research on interruption recovery consistently finds the reconstruction cost is several times the interruption itself.

So the arithmetic is brutal. If you switch contexts twelve times a day and lose four minutes recovering each time, that is nearly an hour a day. Across a working year it is more than two full working weeks. That time is invisible on any dashboard, because you were not idle. You were busy. You were just busy being somewhere other than where you needed to be.

This playbook is not about meditation, and it is not about willpower. It is about making the four-minute recovery cost smaller, and about making the decision to switch an explicit one rather than an accidental one.

The core claim is simple: context is a resource with a restoration cost, and most working environments treat it as if it were free."""

C2 = """You cannot reduce a cost you have not measured, and the useful number here is not "hours of focus" from a time tracker. Time trackers measure duration. What matters is recovery.

For five working days, keep a deliberately crude log. Every time you feel yourself arrive back at something after being away, write three things: what you were working on, roughly how many minutes it took to feel oriented again, and what specifically you had to reconstruct.

Do not use a timer for the interruption. Use your honest impression of the recovery time. Crude data that you actually collect beats precise data you abandon by Wednesday.

After five days, sort the entries by recovery cost. You will almost always find the same pattern. The interruptions that hurt most are not the noisy ones. They are the ones that arrive at a moment of maximum commitment -- deep in a hard problem -- and force you to abandon your train of thought at its most expensive point.

That observation has a direct consequence, and it is the one most teams skip: the highest-value thing you can change is not the number of interruptions. It is whether an interruption is allowed to land at your worst moment. Guarding your peak-focus window protects more time than muting every notification ever created."""

C3 = """This is the core technique. It takes five minutes and it is designed to be usable when you are already slightly frazzled.

Minute one -- capture. Write down, in one or two lines, exactly what you were doing and what the next concrete step was. Not "working on the parser." Instead: "parser: the error is on line 214, I need to check whether the token is consumed before the error is raised." The test for a good capture line is that a competent stranger could resume from it.

Minute two -- park the open loops. List every other thing now occupying any part of your attention. Two to five items is typical. For each one, write the single next action that would move it forward. Not the whole task. The next action. "Reply to Dana about the API contract" is a next action. "Deal with API contract" is not.

Minute three -- clear external state. Close what you are not using. Mute the thread. Set a status if your team uses them. This minute is about removing the visual and social reminders that will otherwise pull you back during the reset itself.

Minute four -- do a physical reset. Stand up, get water, look out a window at something more than a few metres away. This sounds like filler and it is not. Context switching leaves residual attention attached to the previous task. A brief genuine change of physical state is the fastest way to break that attachment.

Minute five -- restart with the capture line. Before anything else, re-read what you wrote in minute one. Then begin. Do not open your editor and start exploring. Start from the specific next step you recorded.

Five minutes. That is the entire investment. If an interruption costs you less than five minutes to absorb, skip the procedure entirely and just handle it. The technique is for the interruptions that would otherwise cost you thirty."""

C4 = """The reset procedure handles the interruptions you accept. This section handles the more valuable question: whether to accept them at all.

Before you switch away from a hard problem, ask three questions. First: is this interruption time-sensitive, meaning will it still matter in two hours? Most chat threads and most meeting requests are not. Second: am I at a point of high commitment, where stopping costs more than it saves? Third: can this wait until a natural break, which in practice means a finished function, a passing test, or a written commit message?

If the answer to the first question is no and the answer to the third is yes, this is a batchable interruption. Put it in the parked list from minute two of the reset and handle it at your next natural break. You have lost nothing. The task was never urgent and it is not more urgent because you attended to it immediately.

If all three answers are yes, switch now and reset properly. Urgent, mid-flow, and genuinely blocking is the legitimate case.

This gate will feel restrictive at first. Most interruptions feel urgent because they arrive from outside your attention and carry other people's priorities with them. The value of this technique is precisely that it makes you decide rather than react.

A useful side effect: the batchable list is real data. If the same three interruptions appear on it every single day, you have found a genuine process problem, and the fix belongs with whoever generates those interruptions rather than in your notification settings."""

C5 = """Context is most expensive to rebuild when it is fresh and complex, which means the beginning of a focused block is the most fragile thing you own. Defend it.

Choose a start time and treat the first twenty minutes as non-negotiable. Not the first hour, which is unrealistic for most people with meetings and children and commutes. Twenty minutes is short enough to protect on a bad day and long enough to matter.

During that window: no chat client open, no email, no browser tabs from yesterday. If you cannot manage the tool, manage the input instead, by writing yesterday's parked list to a piece of paper and putting your phone in another room. The point is not purity. The point is that arriving at a fresh problem twenty minutes later costs materially more than arriving at it rested.

Two supporting habits make this stick. The night before, write one line naming the single first thing you will do in the morning. Starting is the expensive part, and a written first step removes the decision entirely. And when you finish the twenty minutes, write down where you are, so tomorrow's twenty minutes begin from a known state rather than from zero.

This is the single highest-leverage change in the playbook. Everything else improves how you recover from interruptions. This improves how often you avoid needing to."""

C6 = """Some interruptions should not be reset around. If you are switching away because the current task has become genuinely confusing rather than temporarily interrupted, a five-minute capture will faithfully record a state you do not want to return to.

The signal is that the parked next action is vague. If minute one produces something like "figure out the auth flow," the problem is not your context. It is that the task is under-specified, and you are about to pay four minutes of recovery to return to exactly the same confusion.

When that happens, do not run the reset. Spend the five minutes narrowing the task instead, until you can write a concrete next action. "Figure out the auth flow" becomes "find where the token is issued and whether it expires" becomes "read lines 40 to 60 of the token module." Only once you reach a concrete action is the reset worth running.

The second case where the reset does not apply is a genuinely deep block that you should refuse to interrupt at all. Not every interruption is worth absorbing. If the work is high-commitment and the interruption is neither urgent nor blocking, declining it is the correct application of the 30-second gate, not a failure to follow the system.

A final honest limitation: none of this works if the underlying problem is task overload. The reset reduces recovery cost. It cannot make six concurrent priority-one tasks into one. If your parked list regularly contains more than five items, the real next step is a conversation about scope, not a better note-taking technique."""

CHAPTERS = [
    {"title": "Why You Lose the Thread, and What It Actually Costs", "content": C1},
    {"title": "The Context Cost Ledger: Measuring Your Own Number", "content": C2},
    {"title": "The 5-Minute Reset: The Actual Procedure", "content": C3},
    {"title": "Deciding Whether to Switch: The 30-Second Gate", "content": C4},
    {"title": "Protecting the First Twenty Minutes of the Day", "content": C5},
    {"title": "When the Reset Does Not Work", "content": C6},
]

OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "books", "five_minute_context_reset_playbook.pdf",
)


def main():
    result = generate_book_from_content(
        title=TITLE,
        subtitle=SUBTITLE,
        chapters=CHAPTERS,
        price=15.00,
        theme="teal",
        author="Galaxy Forge",
        output=OUTPUT,
        product_type="book",
        production_id=PRODUCTION_ID,
    )
    print("PDF written :", result.get("path"))
    print("pages       :", result.get("pages"))
    print("content src :", result.get("content_source"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())