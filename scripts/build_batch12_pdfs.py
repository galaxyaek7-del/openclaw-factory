#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge Batch 12 — PDF builders (reportlab platypus). Deterministic,
$0, no network. Writes into books/batch12/. Content is real working text:
scripts, checklists, form fields, method guides — no filler.
"""
import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, PageBreak)
from reportlab.lib import colors

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "books" / "batch12"
OUT.mkdir(parents=True, exist_ok=True)

H1 = ParagraphStyle("h1", fontSize=20, leading=24, spaceAfter=10, textColor=colors.HexColor("#1F3864"), fontName="Helvetica-Bold")
H2 = ParagraphStyle("h2", fontSize=14, leading=17, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#2E75B6"), fontName="Helvetica-Bold")
BODY = ParagraphStyle("body", fontSize=10.5, leading=14.5, spaceAfter=5)
BUL = ParagraphStyle("bul", parent=BODY, leftIndent=18, bulletIndent=8, spaceAfter=3)
SMALL = ParagraphStyle("small", fontSize=9, leading=12, textColor=colors.HexColor("#595959"))
FOOT = ParagraphStyle("foot", fontSize=8.5, leading=11, textColor=colors.HexColor("#595959"))


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#808080"))
    canvas.drawString(inch, 0.55 * inch, doc._batchid)
    canvas.drawRightString(7.5 * inch, 0.55 * inch, "Page %d" % doc.page)
    canvas.restoreState()


def build(filename, batchid, title, subtitle, blocks, disclaimers=()):
    # Cycle 98: an optional filter so a single product's guide can be rebuilt
    # without regenerating every sibling PDF. Unset (the default) builds all,
    # byte-for-byte as before.
    only = os.environ.get("BUILD12_ONLY", "").strip().upper()
    if only and only != batchid.upper():
        return None
    doc = BaseDocTemplate(str(OUT / filename), pagesize=LETTER,
                          leftMargin=0.85 * inch, rightMargin=0.85 * inch,
                          topMargin=0.8 * inch, bottomMargin=0.8 * inch)
    doc._batchid = batchid
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=_footer)])
    story = [Paragraph(title, H1), Paragraph(subtitle, SMALL), Spacer(1, 8)]
    for kind, payload in blocks:
        if kind == "h2":
            story.append(Paragraph(payload, H2))
        elif kind == "p":
            story.append(Paragraph(payload, BODY))
        elif kind == "bul":
            for b in payload:
                story.append(Paragraph(b, BUL, bulletText="\u2022"))
        elif kind == "check":
            rows = [[Paragraph("\u2610  " + c, BODY)] for c in payload]
            story.append(Table(rows, colWidths=[doc.width]))
        elif kind == "form":
            rows = []
            for label, lines in payload:
                cell = [Paragraph("<b>%s</b>" % label, BODY)]
                for _ in range(lines):
                    cell.append(Paragraph("_" * 88, SMALL))
                rows.append(cell)
            story.append(Table([[c] for row in rows for c in [row]], colWidths=[doc.width],
                               style=TableStyle([("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                                                 ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                                                 ("VALIGN", (0, 0), (-1, -1), "TOP")])))
        elif kind == "script":
            for line in payload:
                story.append(Paragraph("<i>%s</i>" % line, BODY))
        elif kind == "break":
            story.append(PageBreak())
    for d in disclaimers:
        story.append(Spacer(1, 6))
        story.append(Paragraph(d, FOOT))
    doc.build(story)
    p = OUT / filename
    print("built", p.name, p.stat().st_size, "bytes")
    return p


B = "bul"
P = "p"
H = "h2"
C = "check"

# ── B12-002 handoff guide ──────────────────────────────────────────────
build("B12-002_client_handoff_guide.pdf", "B12-002", "Client Project Handoff Pack",
      "A calm, complete transfer: the 45-minute session script, the email templates, the close gate, and the asset checklist that prevents post-handoff disputes.",
      [(H, "1. What this pack is (and what it is not)"),
       (P, "This pack is the procedure for one specific moment in a project's life: the moment you stop working and someone else starts. Done badly, that moment becomes the disagreement that erases the goodwill of the whole engagement. Done well, it is quiet, evidence-backed, and finished in under a week. It contains a session script you read out loud, three emails you copy and paste, a close gate with hard criteria, and a companion register (an Excel workbook) that records the transfer so nothing depends on memory. It is a working method for freelancers, agencies and contractors handing work to a client or to another team. It is not a contract and it is not legal advice; it is the operational spine that keeps a contract's promise."),
       (P, "The single idea underneath everything that follows: <b>a handoff ends when the receiver can prove they own it, not when the sender stops working.</b> Every step below exists to produce that proof."),

       (H, "2. The principle — transfer by evidence, not by memory"),
       (P, "Most disputes after a handoff are not caused by bad faith. They are caused by two people remembering a friendly conversation differently. Email threads hide the gap because nobody ever states, in one place, what was transferred, what was left open, and who is responsible for each remaining item. The fix is not more meetings. It is a written, checkable list that both sides look at together, live, and sign. That list is the AssetChecklist in the companion register. If you adopt only one habit from this pack, adopt this: on the call, mark each item Y or N in front of the other person, and read the open ones aloud before you end the call."),

       (H, "3. Ten days before the handoff (prep)"),
       (P, "Start this the day you agree the handoff date. Rushing the prep is the most common reason the session overruns and the receiver leaves more confused than when they arrived."),
       (C, ["Lower DNS TTL at least 48 hours before any domain move, so the change propagates fast when you make it.",
            "Freeze new scope in writing: the handoff covers the work already done, not the work you have not started.",
            "Reissue every credential into an account the client owns — do not hand over passwords to your accounts.",
            "Copy the items you will transfer from ChecklistTemplate into AssetChecklist and set the Project name on each row.",
            "Write the known-bugs list now, with severity, so you are never tempted to omit one under pressure.",
            "Issue the final invoice and state the payment terms before the call, not during it.",
            "Book one 45-minute call and ask the incoming owner to attend with their logins ready."]),

       (H, "4. The 45-minute handoff session (run this verbatim)"),
       (P, "Book one call and share your screen. Run the register live. Do not send it afterwards and hope; the shared act of filling it in is what removes the ambiguity later."),
       (B, ["<b>Minutes 0 to 10 — demo the working system.</b> Walk the product as a user, end to end: sign in, do the core job, show where it stores data. A receiver who has watched it work believes it exists.",
            "<b>Minutes 10 to 25 — walk the checklist.</b> Open AssetChecklist and go row by row: Code, Docs, Accounts, Money, Data, Security, People, Support. Mark Y or N in front of them. Do not skip a blank row; a blank row is the exact item that becomes next month's argument.",
            "<b>Minutes 25 to 35 — the receiver plays back the riskiest items.</b> Ask them to repeat, in their own words, the three items you marked N and the two highest risks from RiskRegister. If they cannot, the transfer has not really happened yet.",
            "<b>Minutes 35 to 45 — agree the support window in writing.</b> State the dates, what is included, the response time, and what costs extra. Confirm it in the follow-up email before the call ends. An undefined support window becomes free, permanent, unlimited support."]),

       (H, "5. The five asset categories (nothing ships without all five)"),
       (P, "Assets leak through gaps between categories. Treat all five as one set: if any category is incomplete, the handoff is incomplete."),
       (B, ["<b>Code:</b> repository ownership moved to the client's organisation, deploy keys and CI secrets reissued to them, the old ones revoked, and staging plus production reproduced by the incoming owner while you watch.",
            "<b>Docs:</b> architecture notes that say where everything lives and what depends on what, a runbook for deploy, rollback, restart and credential rotation, and an honest known-bugs list with severity.",
            "<b>Accounts:</b> hosting, DNS, analytics, error tracking and third-party APIs — transfer ownership and billing, and never share a password where you can create a named account instead.",
            "<b>Money:</b> the final invoice, any outstanding expenses, the retainer balance, and an explicit statement of who pays for what after today.",
            "<b>People:</b> stakeholder introductions with one line of context each, and one named decision-maker on each side, in writing. Names without context are useless to the receiver."]),

       (H, "6. Access and security rules"),
       (P, "Access is where a handoff quietly becomes a security incident. Follow these rules without exception."),
       (B, ["Every shared login is replaced by a named account per person. Shared logins can never be revoked or audited.",
            "Access you still hold after the handoff is either revoked or explicitly time-boxed to the support window and then revoked.",
            "Your working copies of client data are deleted, and the deletion is confirmed and dated.",
            "Any credential that was ever visible to you is rotated: you cannot prove it was never copied, so replace it.",
            "Client data is exported to an open format and delivered to the client, not left living only inside your tool."]),

       (H, "7. Copy-paste emails"),
       (P, "<b>7.1 Handoff invitation (send when you agree the date):</b>"),
       ("script", ["Subject: [Project] handoff session — 45 min, please bring [Name]",
                    "Body: We will transfer [system] on [date]. The agenda is a live demo, the access checklist, a risk review, and the support-window agreement. Please come with your logins ready so we can move ownership live on the call."]),
       (P, "<b>7.2 Support-window and completion confirmation (send the same day as the session):</b>"),
       ("script", ["Subject: [Project] handoff complete — support window [dates]",
                    "Body: Transferred today: [list]. Support until [date] covers [scope] with a [response time] response. Beyond that date my rate is [rate]. The items still open are: [list]. Please reply to confirm receipt and that the transferred access works for you."]),
       (P, "The second email is the one that ends the project cleanly. It converts a pleasant conversation into a dated record that both sides can point to if a question appears weeks later."),

       (H, "8. Acceptance criteria and the close gate"),
       (P, "The companion register computes a Close gate for every project. A project is marked READY TO CLOSE only when three facts are all true: every named asset has Access transferred = Y (100 percent complete), there are no open high risks (any risk scoring 12 or more, on a Severity times Likelihood scale, is CLOSED), and the client sign-off is Y. Until all three hold, the gate stays OPEN. This is deliberate: it stops the common failure where the sender feels finished while the receiver is still blocked. Do not close a project by lowering the criteria; close it by finishing the work."),

       (H, "9. The 14-day support window (what it is and is not)"),
       (P, "A support window is a short, defined period after the handoff during which you answer questions about the transfer itself. It is not ongoing development, not a bug-fix contract, and not free consulting. Write it down as four facts: the start and end dates, what is included (questions about access, configuration and how the transferred system works), the response time you commit to, and the rate that applies to anything outside the window. Narrow and clear beats generous and vague; an undefined window costs more than any invoice you will ever send."),

       (H, "10. The 30, 60 and 90-day review"),
       (C, ["Day 30: confirm the receiver is still unblocked; close any item that was open at handoff.",
            "Day 60: confirm billing and access are fully in the client's name; nothing should still route through you.",
            "Day 90: ask for the outcome in writing (a short testimonial), while the work is still fresh and the result is real."]),

       (H, "11. Common failure modes this pack prevents"),
       (B, ["<b>Memory drift:</b> two people remember the conversation differently. Prevented by the shared, live checklist.",
            "<b>Standing access:</b> the sender keeps a key for years. Prevented by the rotation and time-box rules.",
            "<b>Silent charges:</b> a service keeps billing the sender. Prevented by moving billing on the call and verifying it.",
            "<b>Data hostage:</b> client data lives only in the sender's tool. Prevented by the Data and export rows.",
            "<b>Endless support:</b> an undefined window becomes permanent. Prevented by the written four-fact window.",
            "<b>Ghost risks:</b> an undisclosed bug surfaces later. Prevented by the honest known-bugs list and RiskRegister."]),

       (H, "12. FAQ"),
       (B, ["<b>How long should a handoff take?</b> The call is 45 minutes; the prep is spread over about ten days.",
            "<b>What if the client will not attend?</b> Then there is no handoff, only a hope. Reschedule; a handoff without the receiver is not a handoff.",
            "<b>What if a risk cannot be closed in time?</b> Say so in writing, keep the close gate OPEN, and agree an owner and a date for it.",
            "<b>Do I need this if the client is a friend?</b> Especially then. Friendships survive documented handoffs and rarely survive ambiguous ones.",
            "<b>Is this legal advice?</b> No. It is an operational record. Have a lawyer review any contract language that matters to you."]),

       (H, "13. Pre-handoff checklist (final pass)"),
       (C, ["Support window scope, rate and response time agreed in writing",
            "All passwords rotated; shared logins replaced with named accounts",
            "Staging deploy reproduced by the incoming owner, live",
            "Final invoice sent and payment terms stated",
            "DNS or domain transfer initiated if applicable",
            "Analytics and error-tracking ownership transferred",
            "Known-bugs list handed over honestly, with severity",
            "Client sign-off line ready (Y or N in the register)"])])


# ── B12-003 access continuity ──────────────────────────────────────────
build("B12-003_access_continuity_organizer.pdf", "B12-003", "Founder Access Continuity Organizer",
      "If you are unreachable tomorrow, someone you trust can keep the business alive — without you ever writing a password in this kit.",
      [(H, "1. How to use this kit (read this first)"),
       (P, "Read this guide once, then work the companion workbook sheet by sheet. The workbook is the record; this guide is the method. Nothing here asks you to make a decision you cannot undo, and nothing here asks you to trust a stranger: every step is something you do yourself, today, while you are calm, so that someone else does not have to improvise later while they are not. A one-person business has no second pair of hands by design — which is exactly why the knowledge of how it runs has to live somewhere other than your head. The work is small: about ninety minutes to fill the inventory the first time, half an hour to set up emergency access, and thirty minutes a year to keep it true. What it buys is the difference between a business that pauses if you are gone and a business that ends."),
       (B, ["<b>This guide:</b> the method, the rule that makes it safe, the three-envelope system, and the successor's first 72 hours.",
            "<b>The workbook:</b> the inventory (Systems, Holders, Envelopes, DrillLog) and a Dashboard that computes your coverage and flags the gaps.",
            "<b>Where to start:</b> fill Systems and Holders first. Those two sheets are the whole point; everything else protects them."]),

       (H, "2. The one rule that makes this safe: an inventory, never a vault"),
       (P, "The most dangerous version of this kit is the one where you write your passwords down. A printed password list in a drawer, a spreadsheet called passwords.xlsx, a note in your phone — each of them converts a business problem into a security breach, and the breach is the more likely of the two events. So this kit is built on a single rule: <b>it records what exists, where it lives, and who may touch it — never the secret itself.</b> Where you would be tempted to write a password, write the recovery route instead: how a legitimate owner restores access (an email reset to a shared inbox, a branch visit with identity documents, a support ticket from a recovery address). The recovery route is what your successor actually needs, and it is not a liability if it is ever exposed."),
       (P, "The secrets themselves belong in a real password manager with an emergency-access feature — most major managers include one, and this kit is deliberately provider-agnostic so you can use whichever you already trust. The manager holds your vault; the manager's emergency-access setting decides who can reach it, and after how long; and this kit records only the name of the manager and the name of the person you granted access to. That split is the whole design: one place holds the secrets and is defended by the manager's own cryptography, and one place holds the map and can be read by anyone without harm."),

       (H, "3. What \u201cunreachable\u201d actually means for a one-person business"),
       (P, "It is a mistake to plan only for the worst case. A founder can be effectively gone for a week to the business while still very much alive: a hospital stay with no laptop, a family emergency, a long flight to a place with no signal, a bad flu that removes you for ten days. In each of those, the business still has clients waiting for replies, invoices that need sending, subscriptions that auto-renew, and a bank that will not talk to anyone but you. The plan you are building is not a death plan. It is a plan for any period during which you cannot be reached, and the same plan happens to cover the terminal case for free."),
       (P, "That reframing matters because it changes what you have to protect. The goal is not to hand over the whole business; it is to make sure the business does not quietly break while you are away. That is a much smaller job: keep the lights on for thirty days, keep clients informed, keep money moving, and leave the big decisions for you to make when you are back. The workbook calls this the keep-alive plan, and thirty days is a deliberate choice — long enough to cover a serious event, short enough that nobody has to make irreversible calls on your behalf."),

       (H, "4. The three-envelope method"),
       (P, "The method names three things that must exist, who holds each, and how each is opened. The envelopes are a way of thinking, not literal stationery, though a physical envelope is a fine way to store the third one."),
       (B, ["<b>Envelope A — the map.</b> This inventory. It lists what exists, where it lives, and who may touch it. It contains no secrets, so it can be printed, stored with the workbook, and read by your successor without risk. Anyone who finds it learns how the business is organised, not how to break into it.",
            "<b>Envelope B — the keys.</b> Password-manager emergency access. You grant one trusted person access today, and the manager enforces a waiting period before it unlocks, so an unauthorised request gives you time to notice and cancel it. This kit records only the manager's name and the holder's name.",
            "<b>Envelope C — the letter.</b> A sealed document held by a lawyer or kept in a safe. It contains a master-password <i>hint</i> (never the password), the lawyer's and accountant's contacts, and the thirty-day keep-alive steps in your own words. It is opened only by the named successor or on a stated condition you choose."]),
       (P, "The reason for three and not one is that each fails differently. A single document that holds everything is one theft or one lost drawer away from disaster. Three, separated by who holds them and what they contain, mean that the loss of any one of them degrades your plan instead of destroying it."),

       (H, "5. Step one — inventory what exists"),
       (P, "Open the Systems sheet and walk through your business as if you were a stranger trying to run it. For each thing the business needs, record what it is, where it lives, which account owns it, and — importantly — the route by which a legitimate owner restores access. Do not stop at the obvious. The list that matters is the one that includes the unglamorous items nobody thinks of as critical until they are gone: the domain registrar (lose it and your website and email stop), the business bank (the only place money can move), the payment processor (where revenue actually lands), the email account that is the recovery address for everything else, and the file storage that holds the work itself."),
       (P, "Assign each a criticality from one to five. A five means the business stops within days if it is lost; a one means it is a convenience. Be honest rather than generous — a list where everything is a five cannot be prioritised, and the value of this sheet is the ranking. Then fill the recovery route for each one while you still remember it. This is the step people skip, and it is the step that makes the difference between a successor who is stuck and a successor who is moving."),

       (H, "6. Step two — the two-person rule and the criticality test"),
       (P, "For every system rated four or higher, ask a single hard question: could a second trusted person restore access to this without me? If the answer is no — if the only route runs through your memory, your phone, or your personal email — mark the two-person rule as N, and treat that as a real gap rather than a technicality. The Dashboard adds up the critical systems with no second person and shows the count at the top. Most founders who do this exercise honestly discover between three and six such systems the first time, and those are the ones that decide whether the business survives a bad week."),
       (B, ["A shared login is not a second person. If two people use one account, neither can prove who did what, and revoking one revokes both. Create a named account for the second person instead.",
            "The recovery email is the weakest link in most setups. If every account resets through one inbox that only you can open, then every system you rate as critical is really only protected by that one inbox.",
            "Fix the highest criticality gap first. Do not try to make everything perfect on day one; close the five that would end the business, then stop."]),

       (H, "7. Step three — name who may act"),
       (P, "Open the Holders sheet. Name the people who may act on the business, what each may touch, and the basis on which they may do it. Keep it short: a successor or executor, a backup operator who can reach the systems, and the professionals who already know the business — your accountant and your lawyer. For each, record how they are reached, which categories they may touch, and whether you have actually confirmed the arrangement with them. A holder you have never spoken to is not a holder; they are a name on a list."),
       (P, "Be clear with yourself about the boundary here. Authority that carries legal weight — a power of attorney, an executor's role, a will — is not something this kit can grant or replace; it has to be drawn up properly by a lawyer where you live, and it has to match the reality of how your business is registered. What this sheet does is the part the law does not do for you: it records who you have told, what you have told them, and that you have confirmed they are willing. Get the legal instruments drawn up separately, and use this sheet to make sure the people named in them can actually find the map."),

       (H, "8. Step four — set up password-manager emergency access, today"),
       (P, "This is the one step worth doing immediately, because it is the step that takes your plan from a document to a working system. The mechanics are the same in broad outline whichever manager you use, and none of them require you to share a password with anyone."),
       (C, ["Install or open your password manager and make sure your vault is actually complete — an emergency grant to an empty vault helps nobody.",
            "Find the emergency-access or account-recovery setting; most major managers offer one, sometimes under a name like emergency contact or trusted contact.",
            "Grant access to exactly one trusted person, and choose a waiting period long enough that you would notice an unexpected request and could cancel it.",
            "Note in the Envelopes sheet the manager's name and the holder's name — and nothing else. Never write the master password or the hint here.",
            "Walk the flow once, on purpose, so you know what your successor will see. Then close it again.",
            "Tell the person you granted access that they have it, and what you want them to do if the waiting period ever completes."]),

       (H, "9. Step five — the thirty-day keep-alive plan"),
       (P, "The keep-alive plan is what your successor does first, and it is deliberately small. Write it in your own words on the last page of this kit and in Envelope C, and keep it to things that must happen for the business not to break: answer or acknowledge the clients with live work, keep the essential subscriptions from lapsing, make sure any payroll or contractor payments still go out, and pause any spending that only makes sense while you are working — new campaigns, new purchases, new commitments. Thirty days of keeping the machine idling is a realistic ask of someone who is not you. Thirty days of running the business is not, and planning for it would be a way of avoiding the simpler plan that actually works."),
       (P, "Name, in the same place, the decisions your successor must <i>not</i> make: do not sign new contracts, do not sell or transfer the business, do not cancel anything you might want back, do not close accounts. Your absence should not become the moment the business changes shape. The keep-alive plan exists precisely so that the only thing that has to be decided in your absence is the decision to wait for you."),

       (H, "10. Step six — the annual thirty-minute drill"),
       (P, "An untested plan is a wish. Once a year, set thirty minutes aside and run the DrilLog. Do not merely read the sheets — test them. Confirm that the emergency contact is still the right person and still reachable, that the password-manager emergency flow still exists and still works the way you expect, that the inventory still matches reality (new tools and closed accounts are the usual drift), that the location of Envelope C is still known to its holder, and that the accountant and lawyer are still the current ones. Record what broke, fix it, and let the workbook compute the next due date so the calendar nags you instead of your memory."),
       (P, "The drill is not busywork. Almost every plan that fails in reality failed at a detail the owner could have caught in thirty minutes: a recovery email that was a dead address, a phone number that changed, a manager whose free tier had dropped the emergency feature. The drill is how you find those while they are still cheap."),

       (H, "11. Your successor's first 72 hours"),
       (P, "Give your successor this sequence, in this order, so they are not improvising. Open Envelope A and read the map. Contact the named holders and tell them the situation, starting with the backup operator and the accountant. Open Envelope B through the password manager's own emergency flow — this is why you tested it. Send the client acknowledgement from the keep-alive plan, so nobody with live work is left wondering. Then do only what the keep-alive plan lists, and stop: the plan is written for thirty days of stability, and everything beyond it waits for you. The whole point of the work you did today is that this sequence is boring, and boring is what you want in the hands of someone who is worried."),

       (H, "12. The ten failure modes this prevents"),
       (B, ["<b>The single point of failure:</b> one inbox, one phone, or one memory that every recovery route runs through. Prevented by the two-person rule.",
            "<b>The dead recovery address:</b> every reset goes to an inbox nobody else can open. Prevented by the Systems recovery column and the annual drill.",
            "<b>The written password:</b> a list that turns a business problem into a security breach. Prevented by the inventory-only rule.",
            "<b>The untested emergency grant:</b> access that was set up years ago and no longer works. Prevented by walking the flow once a year.",
            "<b>The unknowable domain:</b> a registrar only you can reach, expiring quietly. Prevented by naming it as a critical system.",
            "<b>The silent renewal:</b> subscriptions billing a card nobody else can see. Prevented by the keep-alive plan.",
            "<b>The unnamed successor:</b> people willing to help who never agreed to, or were never told they were named. Prevented by the Holders confirmation column.",
            "<b>The improvised decision:</b> a frightened substitute selling or cancelling what should have waited. Prevented by writing down what not to decide.",
            "<b>The stale plan:</b> a document that described the business two years ago. Prevented by the annual drill and its gaps column.",
            "<b>The plan nobody can find:</b> a perfect document in a drawer no one knows about. Prevented by telling the holders where Envelope C lives."]),

       (H, "13. Boundaries — what this kit is not"),
       (P, "This kit is an organising system. It is not a will, it does not create a power of attorney, and it does not replace legal, financial, tax or insurance advice. It records what you have arranged; it does not arrange it. Any instrument that has legal effect where you live must be prepared by a qualified professional in your jurisdiction. Password storage must follow the security rules of the manager you use, and you should never write a master password, a hint that amounts to one, or a full account number into these pages. Treat the completed workbook as sensitive for a different reason than a password list: not because it contains secrets, but because it contains the map to everything that matters."),

       (H, "14. FAQ"),
       (B, ["<b>How long does this take the first time?</b> About ninety minutes for the inventory and half an hour for emergency access. The annual upkeep is thirty minutes.",
            "<b>What if I have no one to name?</b> Name a professional instead — your accountant or lawyer — at least as a starting point, and revisit it. A plan with one imperfect holder beats no plan.",
            "<b>Do I need a lawyer for this?</b> Not for the inventory. Yes for anything with legal effect, such as a will or a power of attorney. The two are complementary, not alternatives.",
            "<b>Is the workbook safe to keep on my computer?</b> It contains no secrets, so treating it as a map is fine; still, keep it somewhere you would keep business records, and never add a password to it.",
            "<b>What if my business is really just me and a laptop?</b> Then you have fewer systems but the same single point of failure, and the plan matters more, not less, because there is no colleague to cover for you.",
            "<b>Can I use a different password manager?</b> Yes. This kit is deliberately provider-agnostic. Use the one you trust, and record only its name and the person you granted access to."]),

       ("break", ""),
       (H, "15. Fill-in tables (print or type)"),
       (P, "These are the same fields as the workbook's Systems and Holders sheets, for anyone who prefers to work on paper. Fill them in pen, then transfer the critical rows into the workbook so the Dashboard can compute your gaps."),
       ("form", [("Domain registrar (provider, account owner, recovery route)", 3),
                 ("Hosting / deployments (provider, who can redeploy, recovery route)", 3),
                 ("Money in and out (bank, payment processor, payout schedule)", 4),
                 ("Email account that is the recovery address for everything else", 2),
                 ("File storage holding the actual work", 2),
                 ("Password manager (product name, holder, waiting period)", 2),
                 ("Holders (name, contact, what they may touch, confirmed)", 4),
                 ("Thirty-day keep-alive steps, in your own words", 4)]),
       (H, "16. One-page completion checklist"),
       (C, ["Every system rated 4 or 5 has a named second person who can restore access",
            "Every critical system has a written recovery route, not a password",
            "No password, hint or full account number appears anywhere in this kit",
            "Password-manager emergency access granted to exactly one trusted person, and tested",
            "Holders sheet names a successor, a backup operator, and the current professionals",
            "Envelope C prepared, sealed, and its location known to its holder",
            "Thirty-day keep-alive plan written in your own words, including what not to decide",
            "First drill scheduled, and the DrillLog's next-due date left to compute itself"])],
      disclaimers=["ORGANISING SYSTEM ONLY \u2014 NOT LEGAL, FINANCIAL, TAX OR INSURANCE ADVICE. This kit is not a will and does not create a power of attorney. Any instrument with legal effect where you live must be prepared by a qualified professional in your jurisdiction. Never record a password, master-password hint or full account number in this kit or its workbook."])

# ── B12-004 method guide ───────────────────────────────────────────────
build("B12-004_meeting_method_guide.pdf", "B12-004", "Meeting Cost & ROI Method Guide",
      "Price every recurring meeting, rank them by real annual cost, and cancel the ones that produce no decision.",
      [(H, "1. What this guide is for"),
       (P, "This guide turns meeting time into a visible annual cost and, more importantly, into a decision. It is the companion to the B12-004 workbook, which does the arithmetic for you. Read this once, then work through the workbook sheet by sheet. The goal is not an auditable payroll report - it is a management tool that answers one uncomfortable question: does this recurring meeting still earn its place on the calendar?"),
       (P, "Meetings almost never appear as a line item. The spend hides inside payroll, which is exactly why it is easy to underestimate and hard to cut. A recurring meeting that felt free in week one becomes a six-figure commitment over a year across a whole team. The method below makes that number visible and comparable."),

       (H, "2. Step one - price a meeting honestly"),
       (P, "Most people price a meeting with a raw salary guess and stop there. That undercounts. The honest figure is the fully-loaded hourly rate: <b>loaded rate = annual salary / 2080 hours x (1 + employer surcharge)</b>. The 2080 assumes a standard full-time year. The surcharge covers tax, benefits, pension, equipment and overhead, and it is the step people skip - which undercounts meeting cost by roughly 17% to 26%."),
       (P, "Use a surcharge of about <b>20% for EU teams</b> and about <b>35% for US teams</b> as a working default. Worked derivation: a $90,000 salary is $43.27/hour at 2080 hours; add a 30% surcharge and the loaded rate is $56.25/hour, not $43.27. A six-person weekly hour that looked like $260 is really $337. Nobody needs the exact figure - they need a number they cannot wave away."),
       (B, ["<b>Blended vs per-role:</b> one blended rate is fast and fine for a small, similar team. If a leadership meeting and a team huddle share a headcount but not a pay band, use per-role rates - the blended rate hides the difference.",
            "<b>Do not over-engineer:</b> round to the nearest dollar. The decision you make from $56/hr and $57/hr is identical.",
            "<b>Write it down once:</b> put your default rate on the Setup sheet so every row uses the same assumption."]),

       (H, "3. Step two - log every recurring meeting"),
       (P, "Recurring meetings are where the money quietly compounds: they repeat by default and rarely get removed. For each one, capture the attendee count, the loaded rate, the length in hours, how many times it runs per week, and how many real decisions it produces. Do not skip the unglamorous ones - the daily standup and the weekly round-robin are usually the biggest annual lines precisely because nobody thinks of them as expensive."),
       (B, ["Use real attendee counts, not ideal ones. If eight people accept the invite, it is an eight-person meeting.",
            "Record the length as scheduled, then decide separately whether it should be shorter.",
            "If a meeting only sometimes produces a decision, average it honestly - a standup that decides once a week is '0.2 decisions per meeting', not '1'."]),

       (H, "4. Step three - ask the one question"),
       (P, "For every recurring meeting, ask the single question that reframes the cost: <b>what decision does this meeting exist to make?</b> If the answer is 'none - it is an update', it is a status meeting, and status belongs in a document or a chat thread. That one question separates meetings that earn their cost from meetings that merely feel productive. An expensive meeting that makes decisions is fine. A cheap meeting that decides nothing is still waste - and there are usually far more of them than anyone expects."),

       (H, "5. Step four - cost per decision"),
       (P, "<b>Cost per decision = (attendees x loaded rate x hours) / decisions produced.</b> This is the figure worth arguing about, and it is the one number that turns a cost people dismiss into a cost they have to answer for. A meeting that costs $600 and decides three things is $200 per decision. A meeting that costs $200 and decides nothing is infinite. The workbook computes cost per decision for every row and flags any meeting that crosses the threshold you set on the Setup sheet, so the worst offenders surface on their own."),

       (H, "6. Step five - annualise"),
       (P, "A weekly meeting is not a weekly cost - it is that cost multiplied by your working weeks. At 46 working weeks, a $450/week meeting is about $20,700/year. Multiply the meeting across a team and the numbers get serious fast: a recurring hour with five people is a five-figure annual commitment; with twelve, six figures. Annualising is what makes the review happen, because nobody argues about a number that small at weekly scale."),

       (H, "7. Step six - the quarterly kill review"),
       (P, "Set a recurring review or the cost quietly returns. Once a quarter, open the workbook's Dashboard, sort the logged meetings by annual cost, and apply three verdicts: keep, shorten, or kill. Kill every meeting that produced no decision. Shorten the meetings whose length cannot be justified. Protect the survivors with a clear owner, a stated decision, and a deadline."),
       (C, ["Export the Dashboard and sort by annual cost",
           "Kill meetings with zero decisions last quarter",
           "Shorten meetings longer than their agenda needs",
           "Set an end date on every surviving recurring meeting",
           "Agree the date of the next review before the meeting ends"]),

       (H, "8. How to use the workbook"),
       (B, ["<b>Setup:</b> set your default loaded hourly rate, working weeks per year, and the decision-value threshold. The optional helper derives a loaded rate from a salary plus surcharge if you prefer that route.",
            "<b>MeetingLog:</b> one row per recurring meeting. Fill only the white cells - attendees, loaded rate, hours, times per week, and decisions per meeting. The blue cells compute cost and must not be overwritten. Yellow rows are examples - replace or delete them.",
            "<b>Dashboard:</b> totals, monthly and annual cost, total person-hours, the most expensive meeting, and the annual saving from cancelling every zero-decision meeting. Start your kill review here.",
            "<b>Rules:</b> the operating defaults. Re-read them before each quarterly review, because the defaults decay when nobody is watching.",
            "<b>README:</b> a one-screen recap of how the sheets fit together and what each output means."]),

       (H, "9. Worked example - a team of seven"),
       (P, "A team of seven, loaded at $65/hour. The daily standup: 7 x $65 x 0.25 hours x 5 days = $568.75/week, about $26,160/year at 46 weeks - for status that fits in a chat thread. Kill it, and keep a Monday 15-minute blocker review at $113.75/week. The biweekly planning meeting: 7 x $65 x 2 hours x 0.5 times/week = $455/week; shorten it to 90 minutes and it drops to $341.25/week. Two changes to one team's calendar recover roughly $26,000 a year of paid time - time that is now spent on work instead of on describing work."),

       (H, "10. Five mistakes that ruin the number"),
       (B, ["<b>Skipping the surcharge:</b> pricing off raw salary undercounts by 17-26% and makes every meeting look cheaper than it is.",
            "<b>Using a blended rate for a mixed team:</b> it hides the senior-heavy meetings, which are usually the expensive ones.",
            "<b>Counting announced attendees, not accepting attendees:</b> optional attendees still cost money when they attend.",
            "<b>Forgetting that recurring means annual:</b> a weekly meeting is 46 times its weekly cost, every year, until someone ends it.",
            "<b>Reviewing once, then never again:</b> without a quarterly review, meetings creep back and the recovered time is lost."]),

       (H, "11. Objections, answered"),
       (P, "<b>'Our meetings are valuable.'</b> Then the cost per decision will be low and the workbook will say so - the method protects good meetings, it does not cap them. <b>'I do not have exact salaries.'</b> You do not need them; a defensible loaded rate and honest attendee counts are enough to find the worst offenders. <b>'We are remote, so meetings matter more.'</b> Remote makes async easier, not harder - status in a doc is cheaper than a call in every time zone. <b>'Nothing will change.'</b> The point is not to change the culture in one meeting; it is to make the cost visible once a quarter until cutting the obvious waste becomes routine."),

       ("break", ""),
       (H, "12. What this is not"),
       (P, "This is arithmetic on your own inputs. Loaded rates and decision counts are estimates you own, and the workbook only shows what your numbers imply - it promises no savings and no outcomes. It is not HR, legal, payroll or financial advice. Sample rows are fictional illustrations.")])


# ── B12-005 guest scripts ──────────────────────────────────────────────
build("B12-005_podcast_guest_scripts.pdf", "B12-005", "Podcast Guest Booking Scripts",
      "Word-for-word pitch, follow-ups, and post-appearance thank-you — plus the rules that keep you out of spam territory.",
      [(H, "1. The pitch (under 120 words, always)"), ("script",
       ["Subject: guest idea for [Show]: [angle in 8 words]",
        "Hi [Name], I help [audience] with [problem]. Two angles for your listeners: (1) [angle + one concrete number], (2) [angle + one story]. I guested on [show/link] and bring [lead magnet] for your audience. Available [2 windows]. Worth a 15-min fit call? — [You]"]),
       (H, "2. Follow-up 1 (day 7)"), ("script", ["Subject: Re: guest idea for [Show]",
        "Bumping this once — new proof since last week: [one line]. If the angles miss, tell me what you ARE booking and I will either fit it or bow out."]),
       (H, "3. Follow-up 2 and close (day 21)"), ("script", ["Subject: closing the loop — [Show]",
        "Last nudge from me: I am closing outreach for [quarter] Friday. If [angle] ever fits, my one-pager is here: [link]. Thanks either way."]),
       (H, "4. Rules"), (B, ["Two follow-ups maximum, then close. More is spam.",
        "One pitch per show per quarter. Never pitch two shows on the same network the same week with the same angle.",
        "Every pitch names a specific episode you actually heard. Producers can tell."]),
       (H, "5. Post-appearance (within 24h)"), ("script", ["Subject: thanks + assets for [Episode]",
        "Thanks for having me. Assets: headshot [link], links [2 max], audience freebie [link]. I shared the episode with [list] today. Happy to return for a part 2 on [angle]."]),
       (H, "6. Angle workshop (fill before any pitch)"),
       ("form", [("Angle 1 + the number/story that proves it + 3 best-fit shows", 3), ("Angle 2 + proof + shows", 3), ("Angle 3 + proof + shows", 3)]),
       (H, "7. Producer red flags (never do these)"),
       (C, ["Mass pitch with no episode reference", "Asking to 'pick your brain' instead of offering an angle", "Sending 500-word bios unasked", "Following up more than twice", "Pitching the same angle to two shows on one network in one week"])])

# ── B12-006 method guide ───────────────────────────────────────────────
build("B12-006_home_office_method_guide.pdf", "B12-006", "Home-Office Deduction Method Guide (US)",
      "Actual vs simplified method, exclusive-use rule, and the receipt discipline that survives an audit. Companion to the B12-006 expense log.",
      [(H, "1. Pick ONE method for the year"),
       (B, ["<b>Simplified:</b> flat rate per square foot of exclusive office space, capped area. No depreciation recapture, minimal records — but often a smaller deduction.",
            "<b>Actual:</b> home percentage applied to real costs (this kit's log). Bigger potential deduction, real records required.",
            "You cannot mix methods for the same space in one year. Switching methods later has strings attached — read current IRS guidance first."]),
       (H, "2. The exclusive-use test (where most claims die)"),
       (P, "The space must be used REGULARLY and EXCLUSIVELY for business. A guest room with a desk fails. A partitioned corner used only for work can pass. Photograph the space annually; keep the photo with your tax file."),
       (H, "3. Receipt discipline"), (C, ["Every expense logged within 7 days", "Receipt file linked in the log (photo/scan, not memory)",
        "Home % applied to every shared bill", "Method choice recorded once, never mid-year", "Space photo + measurements filed"]),
       (H, "4. Red lines"), (B, ["Never deduct commuting from home to a regular workplace.", "Never claim the same space under two methods.",
        "W-2 employees: federal rules differ from self-employed — confirm YOUR category applies before claiming anything."])],
      disclaimers=["PROCEDURE INFORMATION ONLY — NOT TAX ADVICE. Tax rules and limits change yearly; verify the current tax year's IRS publications (or your country's equivalent) before filing. Confirm your worker category with a licensed tax professional."])

# ── B12-007 30-day plan ────────────────────────────────────────────────
build("B12-007_digital_declutter_plan.pdf", "B12-007", "Digital Declutter & Backup: 30-Day Plan",
      "Four weeks, four surfaces: accounts, files, backups, subscriptions. Companion inventory workbook included.",
      [(H, "Week 1 — Accounts (password manager + 2FA sweep)"),
       (C, ["Install/verify a password manager; import every reused password", "Turn on 2FA for email, bank, cloud storage, socials", "Log every account in the Inventory workbook", "Mark Delete candidates; delete 10+ dead accounts", "Confirm recovery emails on the 5 critical accounts"]),
       (H, "Week 2 — Files (downloads + desktop + duplicates)"),
       (C, ["Empty downloads after sorting (keep/archive/delete only)", "Desktop to zero files (dock + 5 current max)", "Run a duplicate finder on photos + documents", "Archive finished projects to cold storage", "Log locations in the Files sheet"]),
       (H, "Week 3 — Backups (3-2-1 or it did not happen)"),
       (C, ["List what would hurt to lose (Backups sheet)", "Verify 3 copies / 2 media / 1 offsite for each", "Perform one real restore test (photos or docs)", "Automate what you tested (cloud + scheduled local)", "Write the restore steps down — future-you is a stranger"]),
       (H, "Week 4 — Subscriptions + maintenance mode"),
       (C, ["List every recurring charge (Subscriptions sheet)", "Cancel everything unused 30+ days — screenshot confirmations", "Set calendar: quarterly 1-hour maintenance", "Unsubscribe 20+ marketing senders", "Declare victory: record before/after counts"]),
       (H, "Room-by-room sweep (week 2 accelerator)"),
       (C, ["Phone home screen: 1 page, rest in folders or deleted", "Email: inbox to zero via archive-sweep (search older-than:1y)", "Cloud drive: one INBOX folder, file weekly", "Photos: delete screenshots + duplicates monthly", "Desktop/downloads: scheduled 10-min Friday sweep"]),
       (H, "Maintenance calendar (after day 30)"),
       (C, ["Monthly: subscriptions glance + downloads sweep", "Quarterly: 1-hour account + backup review", "Yearly: full 3-2-1 restore test + password audit"])])

# ── B12-008 checklist ──────────────────────────────────────────────────
build("B12-008_moving_checklist.pdf", "B12-008", "Moving House: 8-Week Checklist",
      "Week by week from notice to keys. Companion budget tracker workbook included.",
      [(H, "Week 8–7 — Decide + book"),
       (C, ["Give notice / confirm dates", "Get 3 mover quotes (MoverCompare sheet)", "Verify insurance + read 10+ recent reviews", "Book movers or truck; confirm in writing", "Start declutter: sell/donate/trash before you pack"]),
       (H, "Week 6–5 — Pack non-essentials"),
       (C, ["Pack seasonal + rarely-used rooms first", "Label every box: room + contents + priority", "Photograph electronics cabling before unplugging", "Collect medical/dental/vet records", "Arrange time off for moving day"]),
       (H, "Week 4–3 — Admin sprint"),
       (C, ["Work the AddressChanges sheet (bank, payroll, subscriptions, voter)", "Transfer/renters insurance for the new place", "Schedule utility shutoff + turn-on (no gap nights)", "Confirm mover arrival window in writing", "Pack a first-night box (bedding, chargers, meds, tools)"]),
       (H, "Week 2–1 — Close out"),
       (C, ["Defrost freezer; finish perishables", "Disassemble furniture; bag the screws", "Walk-through photos of the old place", "Confirm keys/handover for both places", "Cash + snacks + phone charger on moving day"]),
       (H, "Day 0–7 — Land"),
       (C, ["Beds + bathroom first, everything else later", "Unpack by priority labels, not randomly", "Test smoke/CO detectors day one", "File damage claims within 48h if any", "Update address anywhere week-3 missed"]),
       (H, "First-night box manifest (pack last, open first)"),
       (C, ["Bedding + pillows + towels", "Meds, chargers, toilet paper, soap", "Basic tools (knife, screwdriver, tape)", "Snacks + water + coffee", "Important documents folder + cash"]),
       (H, "Damage-claim email (within 48h)"), ("script", ["Subject: Damage claim — move [date], job [ref]",
        "Hello [Mover], on delivery I found: (1) [item + damage + photo attached]. Contract ref [x], declared value [y]. Please confirm your claim process and deadline. — [Name, phone]"])])

# ── B12-009 sitter kit ─────────────────────────────────────────────────
build("B12-009_pet_sitter_handover_kit.pdf", "B12-009", "Pet Sitter Handover Kit",
      "Everything a sitter needs when you cannot be reached: contacts, feeding, meds, vet authorization info, house rules. Print, fill, fridge.",
      [(H, "How to use"), (P, "Print this kit. Fill every table by hand. Leave it on the fridge plus a photo of it in your sitter's phone. Walk the sitter through it once in person — paper nobody explained is paper nobody reads."),
       (H, "1. Emergency contacts"), ("form", [("Your name + cell + backup contact", 2), ("Vet (name, address, phone, hours)", 2), ("Emergency vet / animal hospital (24h)", 2), ("Trusted neighbor with keys", 1), ("Poison control / insurance policy #", 1)]),
       (H, "2. Pet profile (one block per pet)"), ("form", [("Name / species / breed / age / weight", 2), ("Feeding: food, amount, times, treats allowed?", 3), ("Medication: what, dose, time, how given", 3), ("Walks / litter / exercise routine", 2), ("Fears, triggers, escape habits", 2)]),
       (H, "3. Vet authorization info"),
       (P, "Write your vet's payment + authorization policy here (call them BEFORE your trip and ask what they need to treat your pet under a sitter). Many clinics require a signed authorization on file — arrange that directly with YOUR clinic; this page records what you arranged, it does not replace it."),
       ("form", [("What my vet requires (signed form on file? spending cap?)", 3), ("Payment method left for vet bills", 1)]),
       (H, "4. House rules"), ("form", [("Allowed / forbidden rooms + furniture", 2), ("Keys, codes, alarm (change after trip)", 2), ("Trash day, thermostat, plants", 2)])],
      disclaimers=["ORGANIZER ONLY — NOT LEGAL OR VETERINARY ADVICE. Confirm authorization requirements directly with your own clinic."])

print("PDF batch done.")
