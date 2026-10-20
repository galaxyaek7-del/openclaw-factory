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

# Importing this module must NOT rebuild the catalogue: the build() calls
# below run at import time. Cycle 106 lost real working-tree bytes this way -
# importing it to reuse build() for B13-001 silently re-emitted 5 tracked PDFs
# (reportlab embeds a timestamp, so the bytes change) and overwrote an
# uncommitted B12-004 repair with the older committed blob. Set
# GF_PDF_IMPORT_ONLY=1 before importing to reuse the helpers instead.
if os.environ.get("GF_PDF_IMPORT_ONLY") == "1" and __name__ != "__main__":
    raise SystemExit("GF_PDF_IMPORT_ONLY=1: catalogue build skipped")

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


# ── B12-005 guest booking kit (Cycle 99 rebuild to the deep-QA bar) ────
build("B12-005_podcast_guest_scripts.pdf", "B12-005", "Podcast Guest Booking Kit",
      "The fit-first method for getting booked as a podcast guest: word-for-word pitch and follow-ups, the tracker that stops you spamming, and the rules that tell you when to walk away.",
      [(H, "1. What this kit is (and what it is not)"),
       (P, "This kit is the paperwork and the discipline behind one specific goal: being invited onto podcasts as a guest, and being invited back. It contains five scripts you read or paste almost as written (a pitch, two follow-ups, a confirmation brief, and a post-appearance note), the method that decides which shows are worth any of those words, and a companion workbook that tracks every show so nothing depends on memory. Together they replace the two failure modes that make most guest outreach worthless: sending the same generic email to everyone, and following up so often that a producer filters you forever."),
       (P, "The single idea underneath everything that follows: <b>a pitch is a guess about fit, and fit is decided by the host's audience, not by you.</b> Every step below exists to make each pitch a smaller, better-informed guess - and to stop you sending the ones that are simply wrong."),
       (P, "<b>What it is not:</b> it is not a placement service. Nothing here submits you to a database, buys you a slot, or contacts anyone on your behalf. It cannot promise a booking, because reply rates depend on your topics, your evidence and the host's current calendar - no template controls any of those. It is not PR, legal or financial advice, and it does not write your story for you."),

       (H, "2. The principle - fit before pitch"),
       (P, "Producers do not read pitches looking for a person to say yes to. They read them looking for a reason to stop reading, because their inbox is full of people who did not do the work. The fastest way to stop being one of those people is to only pitch shows where you can name the episode that proves you listen. If you cannot name an episode, you have not done the research, and the producer will know within two lines."),
       (P, "This is why the method starts with assets and a target list, and reaches the pitch email only at step two. A pitch sent before you can state your angle, your proof and your offer is not outreach; it is a coin flip with your name on it."),

       (H, "3. Step 0 - build three assets before you pitch anyone"),
       (P, "Do this once. It is the same work for every show, so an hour here saves a bad first impression at every show on your list."),
       (B, ["<b>Three angles (not one topic).</b> An angle is a specific, arguable, useful claim for a named audience, e.g. 'the three pricing mistakes that make freelancers undercharge on fixed bids'. 'I talk about freelancing' is not an angle. Write three to six in the Angles sheet, each with the concrete proof you can cite for it (a number, a story, an outcome) and the show type it best fits.",
            "<b>A one-sheet.</b> One page a host can scan in 30 seconds: what you talk about, three topic lines, a short bio, your proof, and your logistics (timezone, remote-ready, episode length you can carry). Keep it under 250 words of actual prose. It is a filter, not a CV.",
            "<b>Your bio at three lengths,</b> 60, 150 and 300 words, ready to paste. Most hosts ask at the worst moment, and some ask for 60 words when you only have a paragraph written.",
            "<b>A lead magnet,</b> one free, genuinely useful thing you can offer the audience (a checklist, a template, a calculator). This is the line that turns 'why should I care' into 'what is in it for my listeners'."]),
       (P, "Record all four in the workbook's Assets sheet and mark each one Ready. The sheet will not let the kit pretend you are ready when a required asset is blank."),

       (H, "4. Step 1 - build a target list of 25 to 40 shows, not 200"),
       (P, "Volume is the wrong lever. Forty shows you have actually listened to beat two hundred you scraped off a chart, because the forty let you write a specific line and the two hundred force a template. Build the list in the workbook's Pipeline sheet, one row per show."),
       (P, "<b>Six fit signals - score each show 1 (poor) to 5 (strong) before you rank the list:</b>"),
       (B, ["<b>Audience overlap.</b> The listeners are the people your angle is for, not just people in a broad industry.",
            "<b>Recent activity.</b> Episodes in the last 60 days; a dormant show cannot book you.",
            "<b>Guest format.</b> It regularly features guests (some shows are solo by design - pitching them wastes both your time).",
            "<b>Topic gap.</b> Your angle is close to what they cover but not something they published in the last few months.",
            "<b>Length and cadence.</b> Episode length you can genuinely carry well.",
            "<b>Reachable.</b> A real contact route (a producer, a contact form, or a public email) - not a guess."]),
       (P, "<b>The cut rule.</b> Anything scoring 3 or below is deleted, not queued. A short list you finish is worth more than a long list you never work, and a poorly fitted pitch is not neutral - it spends your name in that host's inbox."),

       (H, "5. Step 2 - the pitch"),
       (P, "One email. Under 120 words in the body. No attachments on the first contact (a one-sheet link is fine; an attached PDF is a spam signal in some filters and a decision to defer in every inbox). Name the specific episode you heard, state one angle and its proof, say what you offer the audience, give two concrete availability windows, and ask one low-commitment question."),
       ("script", ["Subject: guest idea for [Show]: [your angle in under 8 words]",
        "Hi [Name],",
        "I listened to [Episode title, date] - the part about [one specific detail] is why I am writing.",
        "One angle for your listeners: [angle in one sentence], and I can back it with [one concrete number or story].",
        "I bring [lead magnet] for your audience, no strings.",
        "I am free [date/time window 1] or [date/time window 2], 30 minutes either way.",
        "Worth a short fit call, or would you rather I send the one-pager first?",
        "- [You], [one-line credential], [one link]"]),
       (P, "<b>Why each line is there.</b> The subject names the show and the angle so it is obviously not a blast. The second line proves you listened - it is the only line that cannot be faked cheaply. The third line is the actual offer, stated as a claim you can support. The lead-magnet line answers 'what is in it for my listeners'. The two windows remove a scheduling round-trip. The closing question is deliberately easy to answer with one word, which is the most you can realistically ask of a stranger."),
       (P, "<b>Non-negotiable rules:</b> one pitch per show per quarter; never the same angle to two shows on the same network in the same week; never a mass mail with no episode reference; never ask to 'pick your brain' - offer an angle instead."),

       (H, "6. Step 3 - exactly two follow-ups, then close"),
       (P, "Most bookings come from the follow-up. Most blocks come from the third one. So the cadence is fixed: one follow-up on day 7, one on day 21, then you stop - permanently, unless they reply."),
       ("script", ["FOLLOW-UP 1 - day 7",
        "Subject: Re: guest idea for [Show]",
        "Hi [Name], adding one thing rather than just bumping this: [new proof since last week - one line, a result, a new resource, a timely hook].",
        "If the angle misses, tell me what you ARE booking right now and I will either fit it or bow out.",
        "- [You]"]),
       ("script", ["FOLLOW-UP 2 AND CLOSE - day 21",
        "Subject: closing the loop - [Show]",
        "Hi [Name], last note from me. I am closing my outreach for [quarter] on [day]. If [angle] ever fits your calendar, my one-pager is here: [link] - the offer stands.",
        "Either way, thank you for the episodes. - [You]"]),
       (P, "<b>Why two.</b> The first follow-up adds information, which is a reason to reply. The second closes the loop with dignity, which is the only move that preserves a future yes. A third is not persistence; it is a request to be filtered. In the workbook, the two due dates are computed from the pitch date automatically, so the cadence cannot drift and 'overdue' is visible rather than remembered."),

       (H, "7. Step 4 - the yes: confirm, prepare, protect the recording"),
       (P, "A yes is not a booking until the details are in writing. Send the confirmation brief the same day, and keep it short enough that a busy host can reply to it from a phone."),
       ("script", ["CONFIRMATION BRIEF - send within 24 hours of the yes",
        "Subject: [Show] - [date] at [time] [timezone]: what to expect",
        "Recording: [date], [start-end], [timezone], [platform/link]. Backup: [phone or second platform].",
        "Format: [solo interview / panel], about [length], audio / video.",
        "Agreed angle: [angle]. If useful, I can also bring [second angle].",
        "Prep: 3 sample questions attached or pasted below; I do not need them in advance.",
        "Promo: I will share the episode with [audience/channels] on release day. Anything you want said about your show, tell me and I will say exactly that.",
        "Reschedule: if something changes, [contact] up to [hours] before is fine.",
        "- [You]"]),
       (C, ["Write 5 to 8 real questions you would enjoy answering; they help a host who is short on prep and cost you nothing.",
            "Run a 60-second tech check on the exact platform, on the exact device, the day before.",
            "Headphones on, phone silenced, notifications off, and a backup way to reach the host if the link fails.",
            "Have your 60-word bio and one link copied to the clipboard before you join.",
            "Have one clear, honest call to action ready for the end. Rehearse it once - a rambled CTA wastes the whole appearance."]),

       (H, "8. Fill these in once: your one-sheet and your question bank"),
       (P, "Two pages pay for themselves at every show, so build them before you pitch and reuse them for the rest of the year."),
       (P, "<b>8.1 The one-sheet.</b> One page, under 250 words of prose, in this order. Fill the block below, save it as a PDF, put it on a link, and never attach it to a first pitch."),
       ("form", [("Your name + one-line credential (who you are, in 12 words)", 1),
                 ("Three topic lines, each a specific claim with its proof", 3),
                 ("Short bio (60 words) - what you do, who for, what changed", 3),
                 ("Proof: the two numbers, results or names you can cite on air", 2),
                 ("Logistics: timezone, remote-ready, episodes lengths you can carry", 2),
                 ("The two links you allow, and the lead magnet you offer", 2)]),
       (P, "<b>8.2 The question bank.</b> A guest who brings real questions is the easiest guest to book again, because the host has less prep to do. Write at least eight you would enjoy answering; below are the shapes that work, so replace each with your own specifics."),
       (B, ["<b>Origin:</b> the moment you first noticed the problem your angle is about.",
            "<b>Belief:</b> the common advice in your field you think is wrong, and what you suggest instead.",
            "<b>Method:</b> the exact steps of your approach, in order, for a listener starting today.",
            "<b>Evidence:</b> the result or number that proves the method works, and how you measured it.",
            "<b>Failure:</b> a time your approach did not work, and what you changed afterwards.",
            "<b>Objection:</b> the reason a listener would say 'this will not work for me', answered honestly.",
            "<b>Cost of inaction:</b> what staying on the current path actually costs, in money or time.",
            "<b>Action:</b> the one thing a listener can do in the next hour to start.",
            "<b>Story:</b> one specific person you helped, told in a sentence - without their identity.",
            "<b>Contrarian:</b> a prediction about where your field is going, with the reasoning."]),

       (H, "9. Step 5 - after the appearance (within 24 hours)"),
       ("script", ["THANK-YOU AND ASSETS - within 24 hours of recording",
        "Subject: thank you - assets for [Episode]",
        "Thanks for having me on - that was genuinely enjoyable.",
        "Assets you may want: headshot [link], short bio [link], and my links, two at most: [link 1], [link 2].",
        "I shared the recording with [audience] today and will point to the episode again on release day.",
        "If a part 2 on [specific angle] is ever useful, I am in. - [You]"]),
       (P, "The give-back matters more than the ask. Point your own audience at the episode, quote the host once, and offer a specific part-2 angle - a specific offer is far more likely to be remembered than 'let's do this again sometime'. Then log the outcome in the workbook so the cycle that produced the yes is visible in your numbers."),

       (H, "10. The weekly ritual and how to read your own numbers"),
       (P, "Once a week, forty-five minutes, in this order: rank any new shows and cut the weak ones; send this week's pitches; work the follow-ups the sheet marks due; update statuses honestly; then look at the Metrics sheet for thirty seconds before you close it."),
       (B, ["<b>Reply rate</b> tells you whether your fit and your subject lines work. A low rate with a good list means the pitch, not the list.",
            "<b>Booking rate</b> tells you whether your angle lands with the hosts who do reply.",
            "<b>Per-angle reply rate</b> tells you which of your three angles is actually wanted. Kill the weakest angle after roughly 15 pitches, do not defend it.",
            "<b>Closed without reply</b> is not failure and should not be hidden - it is the honest baseline your next quarter is measured against."]),
       (P, "Judge batches, not individual emails. Ten pitches is noise; thirty is a signal. Change one thing at a time (angle, or subject line, not both) so a later improvement has a cause you can name."),

       (H, "11. The first 14 days, if you are starting today"),
       (P, "If a blank tracker is the reason nothing has happened yet, book fourteen days in your calendar and do exactly this. The first fortnight is deliberately about building the assets and a real list, not about volume."),
       (B, ["<b>Day 1-2.</b> Choose three angles and write each as a specific claim plus its proof. Reject any angle you cannot support with a number, a result or a named experience.",
            "<b>Day 3.</b> Build the one-sheet from section 8.1 - one page, under 250 words of prose, one link and one lead magnet.",
            "<b>Day 4.</b> Write your eight-plus question bank from section 8.2. This is the asset that makes a host want you back.",
            "<b>Day 5-6.</b> Build a target list of 30 shows in your subject's world. Listen to one episode of each and note the episode you will reference.",
            "<b>Day 7.</b> Score every show against the six fit signals and cut everything at 3 or below. A shorter, honest list beats a long, indifferent one.",
            "<b>Day 8.</b> Write the pitch for each remaining show in its own words, with its own episode reference and one scheduling line.",
            "<b>Day 9-10.</b> Send the first batch, no more than ten, and log the send date, show, angle and subject line.",
            "<b>Day 11-13.</b> Work the follow-ups the tracker marks due. Do not send a third.",
            "<b>Day 14.</b> Read the Metrics sheet once. Note your reply rate, which angle earned replies, and one change you will make to the next batch - then stop, and repeat the week."]),
       (P, "Nothing here requires an audience, a sponsor or a paid tool. It requires a real list, a specific angle and a kept log."),

       (H, "12. Worked example (illustrative)"),
       (P, "The following is a fictional illustration of the method, not a real person or show. A bookkeeping-automation consultant wants to guest on small-business shows. Instead of a topic, she writes an angle: 'the three recurring admin jobs a small business can automate in a week without hiring anyone', with proof: '23 small businesses audited, average 9 hours a week recovered'. She builds a target list of 31 shows, cuts 12 that score 3 or below, and pitches the remaining 19 - each time naming the episode she heard."),
       ("script", ["Subject: guest idea for The Small Biz Kitchen: automating three admin jobs",
        "Hi Marisol,",
        "I heard your episode with the bakery owner about drowning in paperwork - the part about invoicing at 11pm is why I am writing.",
        "One angle for your listeners: the three recurring admin jobs a small business can automate in a week without hiring anyone, backed by 23 audits where owners got back about 9 hours a week on average.",
        "I bring a one-page 'which job first' checklist your listeners can use the same day.",
        "I am free Tuesday 10am or Thursday 2pm, 30 minutes either way.",
        "Worth a short fit call, or would you rather I send the one-pager first?",
        "- [Name], small-business automation, [link]"]),
       (B, ["Of 19 pitches, the honest expectation is a minority of replies and fewer bookings - the point of the numbers is to measure that minority, not to pretend it is larger.",
            "Two angles outperformed the third, so the third was retired after about 15 sends and the strongest angle was split into two more specific ones.",
            "Three shows that never replied are kept as closed, dated, and untouched for a quarter - a future, better-timed pitch is legitimate; a third follow-up is not."]),

       (H, "13. Ten mistakes that get you ignored"),
       (B, ["Pitching a show you have never listened to - the missing episode reference is always visible.",
            "Leading with your bio instead of the audience's benefit.",
            "Sending a wall of text, or a 500-word bio, unasked.",
            "Attaching files on first contact.",
            "Pitching the same angle to two shows on one network in the same week.",
            "Following up a third time. Two, then stop.",
            "Vague angles ('I talk about leadership') that give the host nothing to schedule.",
            "No lead magnet - so the host has nothing to offer their audience on your behalf.",
            "Asking to 'pick your brain', which asks for time and offers none.",
            "Tracking nothing, so you cannot tell which angle or subject ever worked."]),

       (H, "14. Objections, answered"),
       (P, "<b>'Nobody replies.'</b> That is normal at first, and it is why the tracker exists: thirty pitches with a kept log tells you whether the list or the pitch is wrong, which guessing never does. <b>'I am not famous enough.'</b> Hosts book useful guests, not famous ones; a specific, provable angle with a real offer the audience can use beats a large following for most shows. <b>'I do not have a lead magnet yet.'</b> Then build one small, genuinely useful page first - it is the difference between 'why should I care' and 'what is in it for my listeners'. <b>'Two follow-ups feels too few.'</b> It is exactly the number that keeps the door open; the third is the one that closes it. <b>'What if they say no?'</b> A no, logged and closed, is information about your fit and your angle, and it costs you nothing you cannot try again next quarter with a better pitch."),

       ("break", ""),
       (H, "15. What this is not"),
       (P, "This is a working method and a set of scripts, not a service and not a promise. No purchase of this kit submits you to any database, contacts any host, or guarantees any booking, listener number or business result. Reply and booking rates depend on your topics, your evidence, the host's calendar and factors outside anyone's control; the workbook only shows you what your own logged numbers imply. Names and scenarios in the worked example are fictional illustrations. The templates are for your own guesting; do not resell or redistribute the files.")],
      disclaimers=["NOT A PLACEMENT SERVICE - NO BOOKING IS PROMISED OR IMPLIED. No part of this kit contacts any show on your behalf. Reply rates depend on fit, timing and your own evidence. Not PR, legal or financial advice; the worked example is fictional."])

# ── B12-006 method guide ───────────────────────────────────────────────
build("B12-006_home_office_method_guide.pdf", "B12-006", "Home-Office Deduction Method Guide (US)",
      "Actual vs simplified method, the exclusive-and-regular-use rule, the arithmetic behind each method, and the record discipline that survives a review. Companion to the B12-006 expense log.",
      [(H, "1. What this kit is, and what it is not"),
       (P, "This kit is an organizing system for one of the most commonly mis-claimed items on a small-business return: business use of your home. It gives you a decision (which method), a rule (exclusive and regular use), a log (every cost, with the home share applied), a calculator (both methods, so you can see which is larger before you commit), and a record discipline that holds up when someone asks you to prove it. That is a real, complete workflow, and it is deliberately narrow."),
       (P, "What it is not: it is not tax advice, it is not a filing, and it does not know your situation. The federal rules are layered — there are limits, ordering rules, and exceptions that depend on your entity, your income, your state and your year. This guide explains the mechanics in plain language and shows the arithmetic with worked examples so you can hold a competent conversation with a preparer instead of guessing. Before you file anything, confirm the current tax year's figures in the current IRS publications for business use of your home, and confirm your own worker or entity category. Limits and rates change; procedure does not."),
       (P, "One sentence to remember: <b>the deduction is won or lost on records, not on the size of the room.</b> A modest measured office with a clean log is worth more than a large room with nothing behind it."),

       (H, "2. The only decision at the top: one method, for the whole year"),
       (B, ["<b>Simplified method:</b> a flat rate per square foot of qualified space, applied to a capped area. Almost no recordkeeping beyond proving the size and the use. Because it is a fixed rate it does not track your actual costs, so it is smaller when your costs are high and larger when your costs are low.",
            "<b>Actual (regular) method:</b> you compute the business percentage of your home and apply it to real eligible costs — rent or mortgage interest, real estate taxes, utilities, insurance, repairs, and depreciation where applicable. Bigger potential result, and real records required for every number.",
            "You pick one method per year for that space. You cannot run both and add them, and you cannot mix them across the same room. The workbook's MethodCompare sheet computes both side by side so the choice is arithmetic rather than a feeling."]),
       (P, "There is a common and useful myth to clear up: you may not 'use simplified in a slow year and actual in a good year' for the same space without understanding the consequences. Switching later has conditions attached, and the simplified method gives up depreciation — which matters if you own the home, because depreciation you did not claim can still affect the gain when you sell. If you own and expect to sell, that single point is worth a conversation with a preparer before you choose."),
       (P, "The practical rule for most people: if your eligible home costs are substantial (you rent, or you own with a mortgage and real bills), compute the actual method and let the comparison sheet tell you the number. If your costs are small — no rent, low utilities, renting a room informally — the simplified rate often wins by itself, and the comparison shows that too."),

       (H, "3. Exclusive and regular use: the rule that decides most claims"),
       (P, "The space must be used <b>regularly</b> and <b>exclusively</b> for the business. Both words carry weight. Regularly means the use is ongoing and not incidental. Exclusively means the space is used for nothing else — no guest bed that doubles as a sofa, no dining table that clears for dinner, no storage of personal paperwork in the same room. A corner of a room can qualify if that corner is used only for business and is identifiable; the rest of the room being personal does not automatically spoil it, but a shared desk does."),
       (B, ["<b>Pass:</b> a dedicated room used only as an office, with a door you can close.",
            "<b>Pass, with care:</b> a defined, measurable corner used only for work, photographed and measured, with no personal use of that corner.",
            "<b>Fail:</b> a guest room with a desk that becomes a bedroom when visitors arrive.",
            "<b>Fail:</b> a kitchen table used for work and for meals.",
            "<b>Fail:</b> a space used for storage only, unless storage of inventory or product samples is itself the business purpose and the rule for that applies."]),
       (P, "Two facts that make this rule survivable in practice. First, the measurement matters more than the description: write down the square footage of the qualifying space and the square footage of the whole home, and keep both. Second, the photographic record is cheap and decisive: take a photo of the space once a year, dated, showing the setup as it actually is, and keep it with your file. A photo answers the question 'was it exclusive' in a way an argument never does."),
       (P, "The single most common fatal mistake is claiming the home percentage on a space the household also uses. That is not a small error — it can invalidate the whole home-office position for the year, not just part of it. When in doubt, measure less space honestly rather than more space aggressively."),

       (H, "4. The simplified method, with a worked example"),
       (P, "The simplified method is deliberately simple: a published rate per square foot, applied to the qualifying square footage, up to a cap on the number of square feet. The rate and the cap are set by the IRS and have been stable in recent years — the rate has been five dollars per square foot with a cap of three hundred square feet, which gives a maximum of fifteen hundred dollars — but you must confirm the current figures for your tax year, because this is exactly the kind of number that changes."),
       (P, "What it costs you in exchange for that simplicity: the simplified method does not produce a depreciation deduction for the business portion of the home, so if you own the property there is a long-term tradeoff that may matter on sale. It also cannot produce or increase a business loss — the deduction is limited to the gross income from the business, and any amount you cannot use is simply not available (the regular method has its own ordering rules and can, in some situations, carry amounts forward)."),
       (P, "Worked example, simplified. Your qualifying office measures 150 square feet and your home measures 1,200 square feet. Under the simplified method you ignore the home size entirely for the deduction: 150 square feet multiplied by the example rate of five dollars gives <b>$750</b>. Notice what did not matter: the rent, the utilities, the home size. That is the entire method — and it is why it is fast, and why it is often the smaller answer when a home is expensive to run."),
       (P, "Now the cap in action. Suppose the same office were 400 square feet. The simplified method does not use all 400: it applies the rate only up to the capped area (three hundred square feet at the example rate), so the answer stays at <b>$1,500</b>. The extra hundred square feet are ignored under this method. If your office is genuinely large, that is the moment the actual method usually wins by a wide margin — the comparison sheet will show it."),

       (H, "5. The actual method, step by step"),
       (P, "The actual method is four steps and one number. Do them in order; the workbook automates steps two and four."),
       (C, ["Measure the home (total square footage) once and write it down.",
        "Measure the qualifying space (square footage) once and write it down.",
        "Divide the space by the home: 150 divided by 1,200 equals 0.125, or 12.5 percent. That is your home percentage.",
        "Group your eligible annual costs and multiply the group total by that percentage.",
        "Keep every document that proves a cost — the bill, the statement, the receipt, or the invoice."]),
       (P, "Eligible costs under the actual method are the costs of running the home itself, apportioned by business use. They typically include rent, mortgage interest, real estate taxes, utilities (electricity, gas, water, heating, trash, and often internet when used for business), homeowners or renters insurance, repairs and maintenance to the qualifying area, and depreciation if you own the property. Personal and non-qualifying costs are excluded — a whole-home landscaping bill, for example, is not the same as re-painting the office you use exclusively for work."),
       (P, "Worked example, actual. Same home and office: 1,200 square feet and 150 square feet, so the home percentage is 12.5 percent. Annual eligible costs are rent of $18,000, utilities of $2,400, insurance of $1,200, and $600 of repairs to the office area alone. The eligible subtotal is 18,000 plus 2,400 plus 1,200 plus 600 = <b>$22,200</b>. Multiply by the home percentage: 22,200 times 0.125 = <b>$2,775</b>."),
       (P, "Compare the two answers on the same facts: $750 simplified against $2,775 actual. The actual method is larger by $2,025 here, and the reason is that this home is expensive to run — the costs are real and the space is a meaningful share of them. A single number did all the work: the home percentage. That is why step three, the measurement, is worth doing carefully and writing down permanently."),

       (H, "6. Which method wins: three cases you can check yourself"),
       (P, "The comparison is not always in favor of the actual method, and the workbook is built so you can see that rather than assume it. Three cases, all using the same 1,200 square foot home:"),
       (B, ["<b>Big office, costly home (150 sq ft, $22,200 of eligible costs):</b> simplified $750 versus actual $2,775. Actual wins, by a wide margin, because the space share is meaningful and the costs are high.",
            "<b>Big office, cheap home (300 sq ft, $3,600 of eligible costs):</b> simplified $1,500 versus actual $900 (3,600 times 0.25). Simplified wins here, because the flat rate does not care that your actual costs are low.",
            "<b>Small office, costly home (60 sq ft, $22,200 of eligible costs):</b> simplified $300 versus actual $1,110 (22,200 times 0.05). Actual still wins, even though the office is small, because the cost base is large."]),
       (P, "The pattern to take away: the simplified method is a fixed number determined by area, and the actual method is a percentage of real cost. When your home is cheap to run, the fixed number can beat the percentage. When your home is expensive to run, the percentage wins and grows with the cost base. The comparison sheet computes all three columns for your own figures in seconds, and — this matters — it shows you the number you are giving up by choosing the smaller method."),

       (H, "7. What counts, and what never counts"),
       (P, "The expense log's Categories sheet keeps a working version of this list next to your data. The short form:"),
       (B, ["<b>Counts, at the home percentage:</b> rent, mortgage interest, real estate taxes, utilities, homeowners or renters insurance, repairs and maintenance to the qualifying area, and depreciation if you own.",
            "<b>Counts at one hundred percent if it is genuinely business-only:</b> supplies, equipment, and a dedicated business phone line that is not also the household line.",
            "<b>Never counts:</b> commuting between your home and a regular workplace; the personal portion of any shared bill; lawn care and whole-home improvements that the business space did not need; and the same space claimed under two methods."]),
       (P, "Two boundary cases people get wrong. First, a shared household bill is entered at its business share, never at its full amount — entering the full internet bill as a business expense is one of the most common reasons a home-office claim attracts attention. Second, the internet question: taken as a home cost it belongs in the home percentage; if you have a separate business service or a dedicated business line, that is a different line and belongs in your one-hundred-percent costs. Do not count the same dollars twice."),

       (H, "8. One number used everywhere"),
       (P, "Everything above depends on a single figure: the home percentage. Compute it once in the SpaceMeasure sheet and let it flow into the log, so a shared bill is never entered at one hundred percent by accident. If your situation changes mid-year — you move, you change rooms, you start using a second room — then the honest treatment is to split the year and use two percentages, one for each period, rather than averaging them into one figure that was never true at any point in the year. The SpaceMeasure sheet has room for a second measurement block for exactly this reason."),
       (P, "If you rent and your lease covers utilities, treat the utilities as part of your cost base only to the extent you actually pay them. If you own, the depreciation piece is real and consequential: it increases this year's eligible costs and it affects the basis of the home when you sell the business portion. That is the one line where the actual method carries a future consequence, and it is the line to raise explicitly with a preparer rather than estimate alone."),

       (H, "9. Records that survive a review"),
       (P, "You do not need a perfect file. You need three kinds of proof, and the log exists to hold all three."),
       (C, ["<b>Space proof:</b> the measured square footage of the home and of the qualifying area, plus a dated photograph of the space each year.",
        "<b>Cost proof:</b> a document for every cost — bill, statement, receipt or invoice — named and filed so a specific line in the log points to a specific file.",
        "<b>Use proof:</b> something showing the business actually ran there and used the space regularly — client records, a calendar, invoices, or a work log."]),
       (P, "The receipt discipline is deliberately mechanical, because mechanical habits survive busy weeks: log every expense within seven days, link the receipt file in the log's own column rather than relying on memory, apply the home percentage to every shared bill, record the method choice once for the year and do not drift mid-year, and file the space photo and the measurements together. A log written from memory in April is worth very little in an examination; a log written in seven-day increments is worth a great deal. Keep the records at least as long as the current IRS guidance requires for your situation and type of claim — the usual advice is a minimum of three years after filing, and longer in some cases — and verify the current retention guidance rather than relying on this sentence."),

       (H, "10. The limits nobody mentions"),
       (P, "Three limits sit behind this whole exercise, and the workbook deliberately does not hide them."),
       (B, ["<b>The gross income limit.</b> The home-office deduction cannot, by itself, turn your business into a loss: in general it is limited to the gross income from the business that used the space. If your eligible costs exceed that income, the excess is not simply deductible — the treatment differs between the methods, and the regular method has ordering rules about which costs are allowed first.",
            "<b>Ordering rules.</b> Under the regular method, categories of cost are applied in a prescribed order and some are subject to further limits. The workbook's annual summary approximates this with simple arithmetic; a preparer applies the real ordering.",
            "<b>Depreciation and sale.</b> If you own the home, the business-use portion of depreciation interacts with the gain when you sell. The simplified method produces no depreciation, which can feel simpler now and cost more later."]),
       (P, "Read those three against your own situation before you treat any number in this kit as final. The log's job is to produce an accurate, defensible, organized figure from real documents — not to make the limit questions disappear."),

       (H, "11. Edge cases worth knowing"),
       (B, ["<b>Part-year use.</b> If the business use started or stopped during the year, the space share is allocated by the period of use, not by assuming twelve months.",
            "<b>Changing rooms.</b> If you stopped using one room and started using another, use a separate measurement block per period; do not average.",
            "<b>A separate structure.</b> A studio, workshop or detached garage used in the business is treated under its own rule and generally does not need to share the home percentage — record it as its own space.",
            "<b>Daycare.</b> Providers who care for children in the home have their own rule that uses hours as well as area, and a different treatment of the exclusive-use test; it is genuinely different from the office case and must be handled on its own terms.",
            "<b>Renting part of your home.</b> If you rent out part of the home, the treatment changes; the rented portion is generally not your business-use space.",
            "<b>W-2 employees.</b> For employees the availability of this deduction is narrow and rules differ from self-employed treatment. Confirm your category before claiming anything — the log is not a shortcut around that question."]),
       (P, "If any of those matches your year, the workbook still organizes the numbers correctly — that is what the log is for — but the treatment is a question for a preparer, not for a template."),

       (H, "12. Fifteen-minute setup in the workbook"),
       (C, ["Open SpaceMeasure. Enter total square feet and qualifying square feet; the percentage computes itself. Choose Actual or Simplified, and enter your example rate if you want the simplified estimate.",
        "Open MethodCompare. Enter your eligible cost categories once; both methods and the difference appear side by side.",
        "Open Expenses2026. Log real rows from your bills. Category is a dropdown, the home share comes from SpaceMeasure, and the deductible estimate computes per row and in total.",
        "Open AnnualSummary. Check the totals, then read the Limits notes before treating the figure as final.",
        "Read the Checklist sheet once, satisfy every line, and file your space photo with that month's receipts."]),
       (P, "Fifteen minutes of setup turns a sprawling pile of bills into a defensible number, and it takes about thirty seconds a week to keep it that way for the rest of the year."),

       (H, "13. Common mistakes that cost real money"),
       (B, ["Claiming a shared room as exclusive, which can invalidate the position rather than reduce it.",
            "Mixing methods within the year for the same space.",
            "Entering shared bills at one hundred percent instead of the home share.",
            "Never measuring anything, then guessing a percentage at filing time.",
            "Forgetting the cap on the simplified method's area and overstating the result.",
            "Ignoring the gross income limit and assuming the full figure is deductible.",
            "Choosing the simplified method while owning the home without understanding the depreciation tradeoff on sale.",
            "Keeping receipts in a drawer with no link from the log to the specific document."]),

       (H, "14. What this is not, in one paragraph"),
       (P, "This is an organizing system and a worked explanation of a real procedure, not tax, legal or accounting advice, and it is not a filing. It does not know your entity, your income, your state, your lease, your title to the property or your year's rules. Figures are illustrative examples with the arithmetic shown so you can check every number yourself. Tax rules, rates, caps and limits change, sometimes annually; verify the current tax year's guidance in the current IRS publications for business use of your home, or your country's equivalent, and confirm your own worker or entity category with a licensed tax professional before you rely on any number here.")],
      disclaimers=["PROCEDURE INFORMATION ONLY — NOT TAX ADVICE. Rates, caps and limits change; verify the current tax year's IRS publications (or your country's equivalent) before filing, and confirm your worker or entity category with a licensed tax professional. Worked figures are illustrative examples with visible arithmetic."])

# ── B12-007 30-day plan ────────────────────────────────────────────────
build("B12-007_digital_declutter_plan.pdf", "B12-007", "Digital Declutter & Backup: 30-Day Plan",
      "Four weeks, four surfaces: accounts, files, backups, subscriptions. One decision per item, recorded in the companion workbook, with a restore test you actually perform.",
      [(H, "1. What this plan is"),
       (P, "This is a thirty-day operating plan for the digital part of a household: the accounts you can no longer count, the files nobody has opened in three years, the backups that have never been restored, and the subscriptions that renew themselves quietly. It is built for someone with a job, not for someone with a free weekend. Each day asks for twenty to thirty minutes and one kind of decision. The companion workbook is where the record lives, because the failure mode this plan is designed against is not laziness; it is deciding the same thing twice."),
       (P, "The plan is deliberately narrow. It does not cover email etiquette, digital minimalism as a philosophy, or the correct way to name a file. It covers four surfaces in an order that makes each week's work easier than the last: accounts first, because they are the keys; files second, because they are the mass; backups third, because they are only meaningful once you know what you have; subscriptions last, because by then you can see the whole picture and the cancellations are obvious."),
       (P, "There is no app to buy and no service to subscribe to. Whatever you already pay for, you keep or cancel on its own merits during week four, not because this document told you to."),

       (H, "2. Why decluttering fails, and the one rule that fixes it"),
       (P, "Most attempts fail in the same way. You open a folder, find something ambiguous, and put it in a new folder called Later. Later becomes a fourth surface that is worse than the original three, because now the ambiguity has a home and no deadline. The second failure is tool-chasing: a new app, a new folder structure, a new naming convention, all of which feel like progress and none of which remove a single file."),
       (P, "The rule is this: every item gets exactly one verdict - keep, archive, or delete - and the verdict goes into the workbook the moment it is made. Keep means it stays where it is used. Archive means it moves out of daily sight to storage you will not browse, with a date after which you may delete it without opening it. Delete means it is gone this week, not someday. If you cannot decide in twenty seconds, the item is Archive, not Later. Archive is the pressure valve that makes the rest of the plan possible."),
       (P, "Write the decision down even when it is obvious. The record is what stops the second pass, and it is the only part of this plan that survives past day thirty."),

       (H, "3. Before day one (thirty minutes, once)"),
       (C, ["Install or open a password manager and confirm you can log into it from your phone as well as your computer",
           "Create three folders that will hold the work: INBOX, ARCHIVE-2026, and REVIEW-90 (a date, not a mood)",
           "Set a repeating twenty-minute timer for the daily session - shorter is better than skipped",
           "Tell the people you live with what the thirty days are for, so a shared drive is not reorganised underneath you",
           "Photograph your current desktop and downloads folder. It is the before picture, and in week four you will want it"]),

       (H, "4. Week 1 - accounts and access (days 1 to 7)"),
       (P, "Day 1. Start with email, because almost every other account can be reset through it. Log into your main address, open the security settings, and turn on two-factor authentication if it is not already on. Then check the recovery address and phone number. If the recovery address is an old account you no longer read, fix that first; a recovery route you cannot reach is worse than none."),
       (P, "Day 2. Open the password manager and import whatever browser is currently remembering your passwords. Then sort the imported list by re-use. Any password used in more than one place is today's work: change it at the sites that matter first - email, banking, cloud storage - and let the manager generate the replacement. You are not fixing everything today; you are breaking the chain where one leak becomes five."),
       (P, "Day 3. List every account you can remember, and then find the ones you cannot: search your email for the word welcome, and for confirm your account. That search is a surprisingly complete inventory. Enter each account in the Accounts sheet with one status: live, dormant, or delete. Do not delete anything yet; today is inventory only."),
       (P, "Day 4. Work the dormant list. For each one, ask a single question: would I be upset if this disappeared tomorrow? If no, mark it delete and change the password to something random first, so that nothing you currently reuse is still valid there. Then request deletion, and put the date in the sheet. Many services take thirty days to close an account, which is why this happens in week one rather than day twenty-nine."),
       (P, "Day 5. Confirm the five critical accounts - email, bank, cloud storage, phone carrier, and the one account that holds your money or your identity documents. For each: two-factor on, recovery route current, password unique and in the manager. Five accounts, done properly, is more protection than a hundred half-done ones."),
       (P, "Day 6. Handle the old accounts you cannot delete because something depends on them: the address attached to a utility, an old workplace portal, a forum where your username is your real name. Mark them keep but change the password and remove the payment method if one is stored. A login you never use but that still holds a card is a standing risk."),
       (P, "Day 7. Close the week by counting. How many accounts did you list? How many are dormant? How many are now scheduled for deletion? Write the three numbers on the Dashboard sheet. Numbers are what make week four's comparison honest."),

       (H, "5. Week 2 - files, photos and documents (days 8 to 14)"),
       (P, "Day 8. Empty the downloads folder completely. Everything in it gets one of the three verdicts: keep means it belongs somewhere specific, so move it there and rename it; archive means it goes to ARCHIVE-2026; delete means it goes. An empty downloads folder is the single cheapest visible win in this plan, and it is also the place where half of the duplicate files in the next few days are hiding."),
       (P, "Day 9. Do the desktop, and be strict about the definition of done: no files on the desktop at all, only shortcuts or nothing. If you work from the desktop, create one folder called CURRENT and allow at most five files in it."),
       (P, "Day 10. Run a duplicate finder on your documents, not your photos. Duplicates in documents are usually versions of the same file with different names, which means the finder will show you groups that need a human decision rather than a bulk delete. Keep the newest, keep a copy of any signed original, and send the rest to archive rather than deleting outright."),
       (P, "Day 11. Photos, part one: delete screenshots. This is mechanical, it is safe, and it usually removes more files than any other single action in the month. Do it on the phone and the computer separately, because they sync differently."),
       (P, "Day 12. Photos, part two: duplicates and bursts. Keep the best frame from each burst, keep the original of anything you might print, and archive rather than delete the rest. Photos are the category people regret, so this is the one place where archive earns its keep even when delete would be defensible."),
       (P, "Day 13. Documents that matter: identification, insurance, contracts, tax records, medical records, warranties. For each, confirm you have a copy that is not only on one device, and that you know which copy is authoritative. Scan anything that exists only on paper, and name the scan with the year first so it sorts correctly in every system forever."),
       (P, "Day 14. Finish the Files sheet: one row per location, not per file. The question the sheet answers is not what is in each folder but where things live now that you have decided, so that in ninety days you can find them without repeating this week."),

       (H, "6. Week 3 - backups that would actually restore (days 15 to 21)"),
       (P, "The rule is three copies, on two different kinds of media, with one of them offsite. It is old advice and it is still correct, but the part people get wrong is what counts as a copy. Two folders on the same laptop are one copy. A cloud sync folder is not a backup of the folder it syncs: if you delete a file locally, the deletion propagates, and if ransomware encrypts the folder, the encrypted version propagates too. A backup is a separate historical copy that does not follow your live mistakes."),
       (P, "Day 15. List what would genuinely hurt to lose, in the Backups sheet. Be specific: the photo library, the tax archive, the password manager export, the folder of contracts, the scan of the deed. Most households find the list is short, which is good news, because a short list can be backed up properly."),
       (P, "Day 16. For each item on the list, write where its copies currently are. Count them honestly. A great many items will have exactly one copy, and that copy will be on the device you carry around."),
       (P, "Day 17. Fix the single-copy items with a second copy on a different medium. An external drive is the usual answer and it is a good one, provided it is not permanently plugged in - a drive that is always connected is exposed to the same event as the computer."),
       (P, "Day 18. Add the offsite copy. This can be a cloud backup service, or it can be an encrypted drive that lives somewhere else - at a relative's house, in a locker, at work. The test is not which option you chose; it is whether a fire in your home would leave you with a copy."),
       (P, "Day 19. Perform a real restore test. Choose three files: one photo, one document, one thing from the archive. Delete them from your working machine, restore them from the backup, and open them. Not one of them - all three, then a fourth chosen at random. A backup that has never been restored is a hope, and hope is not a recovery plan."),
       (P, "Day 20. Automate only what you have tested. Set the schedule, confirm the first run completes, and check the log or the notification rather than assuming. Automation you have not watched once is the same hope with a calendar attached."),
       (P, "Day 21. Write the restore steps down in the README sheet: where the backup lives, what the password is (in the manager, not here), how long a restore takes, and who else knows. Future-you will be stressed and will not remember any of it."),

       (H, "7. Week 4 - subscriptions and money (days 22 to 28)"),
       (P, "Day 22. Find every recurring charge. Two sources: your bank and card statements for the last three months, and the subscriptions sections of the app stores. Store billing hides charges that never appear as a normal card transaction, and annual charges hide from any search that only looks at this month."),
       (P, "Day 23. Enter each one in the Subscriptions sheet with its real amount and its real billing period. Normalise to a monthly figure so the total means something: an annual charge divided by twelve, not the annual number pretending to be monthly. The total is usually larger than people expect, and it is the number that makes the next decision easy."),
       (P, "Day 24. Apply the unused test, but do it honestly. Unused means you have not opened it with intent in thirty days - not that you have not wanted to. If the honest answer is that you keep it for two weeks a year, the question becomes whether two weeks is worth twelve months."),
       (P, "Day 25. Cancel the clear cases and take a screenshot of each confirmation. Cancellations fail silently more often than anyone expects: the button leads to a survey, the survey leads to a discount offer, and somewhere in there the cancellation never happens. The screenshot is the only proof you will have when the next charge appears."),
       (P, "Day 26. For the ones you keep, do the boring optimisations: switch annual where the discount is real and you are certain you will still want it in a year, downgrade a tier you are not using, and remove stored payment methods from services you keep but rarely buy from."),
       (P, "Day 27. Check for the charges that are not subscriptions at all: insurance renewals, memberships, storage plans, domain renewals, and anything on an annual cycle that arrives as a surprise. These are the ones that cost the most per year because nobody puts them in a list."),
       (P, "Day 28. Set a quarterly review date, in a calendar you actually look at, with the total from day 23 written in the event title. The total is the alarm; the date is the trigger."),

       (H, "8. Days 29 and 30 - make it survive"),
       (P, "Day 29. Compare the after picture with the photograph from before day one. Count the accounts, the files, the backups that now exist, and the monthly subscription total. Write the four numbers on the Dashboard. This is not decoration: it is the evidence that the month happened, and it is what you will read in ninety days when the drift starts."),
       (P, "Day 30. Schedule the maintenance and then stop. Monthly: a ten-minute downloads sweep and a glance at the subscription total. Quarterly: one hour for accounts and backups, and a single restore test. Yearly: a full audit of the five critical accounts and a fresh archive decision for anything that has been sitting in REVIEW-90."),
       (P, "Then leave it alone. The plan is designed to end. A declutter that becomes a permanent project has failed at the last step, which is the step where you trust the system you built."),

       (H, "9. Five ways this plan fails"),
       (C, ["Perfectionism: you spend three days on the folder structure and never reach the passwords. The structure is not the work.",
           "Tool-chasing: you buy storage, a scanner app and a second password manager, and the files stay where they were.",
           "Deciding twice: you sort a folder, do not write the verdict down, and sort it again in week four. The workbook prevents this; use it.",
           "The one-weekend plan: you compress thirty days into two, run out of decisions, and abandon the last three surfaces entirely.",
           "No maintenance: day thirty is the start of the drift, not the end of the problem. One hour a quarter is the whole cost."]),

       (H, "10. A worked example, with real arithmetic"),
       (P, "Suppose the household has three email addresses, two laptops, one phone per adult, 37 recurring charges, a photo library of 22,000 files, and two external drives of which one is unplugged. The account sweep finds 118 logins, 41 of them dormant and 12 genuinely deletable. The file week removes 1,900 duplicate photos, 2,300 screenshots and an empty downloads folder that had been the default destination for four years. The backup week finds that 22,000 photos exist in exactly one place; the fix is a drive that stays unplugged plus a cloud copy, and the restore test takes eleven minutes for three files. The subscription week normalises 37 charges to a monthly total and cancels 9 of them. None of those numbers is a promise about your household; they are the shape of a realistic month, so that a day where you find forty dormant accounts feels normal rather than like failure."),

       (H, "11. What this is not"),
       (P, "This is an organising procedure, not advice about security, law, tax or finance. It does not audit your accounts for you, it does not tell you which cloud provider is trustworthy, and it makes no claim about any product or service. Two-factor authentication, backup practice and account deletion are all areas where the specific rules depend on the service and on your jurisdiction, so confirm the details with the provider's own documentation before you rely on them. The worked example is illustrative arithmetic, not a forecast for your household, and the thirty-day structure is a suggestion: shift the days to fit your week rather than abandoning the plan because Tuesday did not work.")],
      disclaimers=["PROCEDURE INFORMATION ONLY — NOT SECURITY, LEGAL, TAX OR FINANCIAL ADVICE. Confirm backup, account-deletion and two-factor requirements with each provider; the worked example is illustrative arithmetic, not a promise about your household."])

# ── B12-008 checklist ──────────────────────────────────────────────────
build("B12-008_moving_checklist.pdf", "B12-008", "Moving House: 8-Week Checklist",
      "Week by week from notice to keys, with the money decided before the boxes: how to vet a mover, what the deposit is at risk from, the address changes that cost money when they are missed, and the claim procedure if something arrives broken.",
      [(H, "1. What this plan is"),
       (P, "This is an eight-week operating plan for a household move, written for the person who is also working full time. It covers the order of work, the money, the paperwork that quietly costs money when it is missed, and the evidence you need before you hand over keys or accept a deposit back. The companion workbook holds the numbers: every cost with both quotes, every mover scored on the same three facts, every address change with its confirmation number, and the utility dates that decide whether you spend a night without power."),
       (P, "It is not a packing guide. How to wrap a glass is a solved problem and not where moves go wrong. Moves go wrong in four places: a mover was chosen on price alone; the budget was a guess with no buffer; the address changes were done in the last week, or not at all; and condition evidence was never captured, so a deposit could not be argued for. Each of those is a decision, and every decision in this plan has a place in the workbook."),
       (P, "The plan assumes a rental or a first home purchase inside the same country. It does not assume you own a van, have family nearby, or can take a week off. Two evenings a week and one weekend hour is enough if you follow the order."),

       (H, "2. The three numbers to decide in week eight"),
       (P, "Before you book anything, decide three numbers. The first is the total move budget: every cost you expect, added up, on one sheet. The second is the buffer, and it is not optional - moves generate a late cost in nearly every case, whether it is a cleaning charge, a second van, a mattress bag, or a night in a hotel because the keys were late. A practical buffer is ten to fifteen percent of the total; decide the figure now, because in week two it will feel like money you could spend on furniture instead."),
       (P, "The third number is the money that is at risk: the deposit you are trying to get back, plus the deposit you have just paid. That number is worth writing down because it is the one that gets lost in the chaos. A deposit is only returned against evidence of condition, and the only evidence that counts is dated and shows the state of each room."),
       (P, "Write the three numbers on the Summary sheet the day you decide them. From that point the question at every step is not can I afford this, but does this cost fit the total, and does it come out of the buffer."),

       (H, "3. How to choose a mover without being taken"),
       (P, "Get at least three quotes, in writing, for the same scope. The scope matters more than the price: a quote that includes packing, stairs, a long carry and insurance is not comparable with one that assumes a ground-floor flat and an easy parking space. If a quote is dramatically lower than the others, the difference is usually one of those items - and it will be found on moving day, when you have no position to negotiate from."),
       (P, "Score each one on three facts, which is what the MoverCompare sheet does: the price, whether they are insured, and whether you actually read recent reviews from places that are not the company's own website. The workbook weights them 40 for price, 30 for insurance and 30 for checked reviews, and the reason for that weighting is simple: an uninsured mover can cost you more than any price difference, and a company with a pattern of damage and no-shows will not be fixed by being cheap."),
       (P, "Confirm in writing before the day: the arrival window, the crew size, who supplies packing materials, whether the price is a fixed quote or an hourly rate, and what happens if the job runs long. A hourly rate without a cap is the single most common way a reasonable quote becomes an unreasonable invoice."),

       (H, "4. Weeks 8 and 7 - decide, book and start reducing"),
       (P, "Week 8 is paperwork week, and it is the week that removes most of the later stress. Give notice or confirm your end date if you are renting, and read the notice clause rather than assuming a month. If you are buying, keep the completion date flexible until you have a mover booked, because a mover you like on a date you cannot move is not a mover."),
       (P, "Book the mover now. Good movers on end-of-month dates are gone four to six weeks ahead, and the alternative to booking early is not booking the same mover later; it is booking a worse one. Then confirm insurance in writing and, if your household contents exceed the mover's standard liability, price proper transit cover."),
       (P, "Start the reduction this week, and start it in the rooms you use least. Reduction is not packing - it is deciding what will not come with you. Sell, donate, recycle or discard, and do it now while you still have time to sell rather than the week you move, when the only realistic destination is the bin. Anything you have not used in two years and cannot name a use for is a candidate, and the cost of moving it is real: a mover's price is driven by volume, so every box you remove is money you do not spend and an afternoon you do not spend unpacking."),
       (P, "Week 7 is quotes week. Get the second and third quote, enter all three in MoverCompare, and read the terms of the one you intend to book. Photograph anything valuable that you are keeping, and start a single folder - physical or cloud - for the move: contracts, quotes, the inventory of what the mover is taking, and the condition photographs as they accumulate."),

       (H, "5. Weeks 6 and 5 - pack what you do not need"),
       (P, "Pack the rooms you barely use first: the spare room, the loft, the seasonal clothes, the decorative items. The principle is that early packing should never block your week, so it should only involve things nobody will want before the move. Label every box with the room it is going to, not the room it came from, and add one word for its priority: first, soon, or later. A box labelled Kitchen that contains two pans and a photo album is a box you will open three times."),
       (P, "Photograph the back of your television, your router and any device with more than two cables before you unplug it. This takes ten minutes and saves an evening of guessing at the other end. Bag and label the screws of anything you disassemble, and tape the bag to the piece of furniture it belongs to - a bag of screws in a box labelled Furniture is indistinguishable from a bag of screws for something else."),
       (P, "While the boxes are being filled, collect the records that are annoying to replace: medical, dental and veterinary records, school records, immunisation records, and the service history for anything under warranty. Request them now, because a records request takes days and the week you move you will not have days."),
       (P, "Book time off, or at least the moving day itself, and book it before you tell anyone else the date. Then tell your employer, and if your move changes your commute or your tax position, ask the question now rather than discovering it in a payslip."),

       (H, "6. Weeks 4 and 3 - the admin sprint"),
       (P, "Weeks four and three are where money is protected. The AddressChanges sheet is the centre of it: each row is an account or service, and each needs a real update, not an email saying you moved. The ones that cost money when missed are the ones nobody thinks of - insurance, because a policy for an address you no longer occupy can be void; vehicle registration and driving licence, because a fine sent to an old address is still a fine; anything with a credit balance, because a refund goes to the old address; and subscriptions, because a cancelled card at the old bank does not cancel the subscription."),
       (P, "Record the confirmation number for every change. If a service later claims it never received the update, the confirmation number ends the conversation, and a screenshot of a form submission does not."),
       (P, "Insurance and utilities are the two that need dates, not just notifications. For utilities, enter the old close date and the new start date in the Utilities sheet; the sheet subtracts them and shows the gap. A positive number is a night with no electricity, no heating or no water, and the fix is to move the start date earlier, not to hope. A negative number is an overlap you are paying for twice."),
       (P, "Confirm the mover again in writing, with the arrival window. Confirm access at both ends: parking permits, lift booking, building rules on moving hours, and whether the new place allows a van at the door. A blocked access point adds an hour of long carry, and long carry is billed."),
       (P, "Pack a first-night box and seal it last: bedding and pillows for each bed, towels, toilet paper, soap, basic tools, chargers, medication, a change of clothes, snacks and water, and the documents folder. This box travels with you, not on the van."),

       (H, "7. Weeks 2 and 1 - close out clean"),
       (P, "Two weeks out, do the last of the reduction and start packing the kitchen properly: defrost the freezer, finish the perishables, and pack the everyday items you will not need in the final week. Anything that cannot travel - gas bottles, some cleaning chemicals, paint - has to be disposed of or given away, so check the rules before the last day rather than at 6am on it."),
       (P, "Photograph every room in the old place immediately before the furniture goes, and again after it is empty. Those two sets of images are your deposit evidence: they show condition with furniture in place and, more importantly, the state of walls, floors, doors and fixtures once everything is out. Photograph the meters, and write down the readings."),
       (P, "Confirm the handover on both sides in writing, including who holds which keys and when the new set is available. Do a walk-through of the new place before the van arrives if you possibly can: if the previous occupants left damage or rubbish, you want that recorded before your own furniture is in the photographs."),
       (P, "In the final week, keep the last boxes for the things you use daily, and keep the documents folder with you. Cash, chargers and snacks for moving day, and a charger in your bag rather than in a box labelled Study."),

       (H, "8. Moving day and the first week"),
       (P, "On the day, do four things in this order. Photograph the loaded van if the mover is doing the loading, because it fixes what left the house. Keep the inventory list with you and tick items off as they arrive. Set the beds and the bathroom up first, so that when you are exhausted there is somewhere to sleep and somewhere to wash. And test the smoke and carbon monoxide alarms the same day, before a single box is unpacked, because a house with no working alarm is a house you cannot sleep safely in."),
       (P, "Inspect arriving items before you sign the delivery note, and note any damage on the note itself. A signature without a note is the easiest way to lose a claim. If something is broken, photograph it in place, keep the packaging, and start the claim the same week - the procedure and a template are below."),
       (P, "Unpack by priority label rather than at random. The boxes labelled first are the ones that make the house function; later boxes can wait weeks without any real cost. Then update anything the address sprint missed, because the first forwarded letter is usually the one that matters."),

       (H, "9. Deposit and condition evidence"),
       (P, "A deposit is a negotiation conducted with documents, and most people lose it by having none. The evidence that works is dated: photographs of every room and every fixture, ideally with a timestamp, taken before the move-in and again before the move-out; the signed condition report or inventory from the start of the tenancy, checked rather than accepted; meter readings with dates; and any written agreement about repairs or changes you were allowed to make."),
       (P, "On the way out, clean to the standard the property was let at, and photograph the result. Keep the receipts for anything you paid for - cleaning, rubbish removal, a replacement part. If a deduction is proposed that you disagree with, ask for the itemised breakdown with receipts, in writing, and answer in writing. Landlord and tenant deposit rules differ by jurisdiction, so check what your own jurisdiction requires about deadlines and dispute resolution, and keep to the deadlines it sets."),

       (H, "10. If something arrives damaged - the claim, step by step"),
       (P, "Report the damage the same day, in writing, to the mover and to your own insurer if your policy covers it. Keep every message in one thread. Photograph the item and its packaging in place. Do not repair or dispose of anything before the claim is settled, because a repaired item cannot be inspected. Provide the mover's reference number, the date of the move, the inventory entry, and the declared value."),
       (P, "Most policies require notice within a short window - often measured in days, sometimes 48 hours - so the same-day message matters more than getting the wording perfect. If the mover is unresponsive within a week, escalate in writing and state your deadline. If they are insured, the insurer is the next contact, and the claim is usually made against the mover, not directly by you."),
       (H, "Damage-claim message (copy, fill, send the same day)"),
       ("script", ["Subject: Damage claim - move [date], job reference [ref]",
        "Hello [Mover], on delivery on [date] I found: (1) [item] - [damage] - photograph attached; (2) [item] - [damage] - photograph attached.",
        "Contract reference [ref], declared value [amount]. The item is unrepaired and the packaging is retained for inspection.",
        "Please confirm your claims process, the claim reference number, and your response deadline in writing. I am keeping all messages in this thread. - [Name, phone, address]"]),
       (P, "Send it to the address and the email the contract names, not to the person who quoted you on the phone. Keep the sent copy."),

       (H, "11. A worked example, with real arithmetic"),
       (P, "Suppose the total move budget comes to 6,900 dollars: 2,100 for a three-bedroom move, 400 for materials, 3,000 for a deposit and first month, 300 for utility transfers, 400 for a cleaning charge and lock change, 500 for a piece of furniture that will not fit, and 200 for the unforeseen. A fifteen percent buffer is 1,035 dollars, so the real ceiling is 7,935. One mover quotes 2,100 insured, one quotes 1,700 uninsured, and one quotes 1,950 insured with reviews that mention two late arrivals. On the 40/30/30 score the cheapest takes price 40, nothing for insurance and 30 for reviews: 70, and no claim route if the sofa arrives broken. The 1,950 insured mover scores price 34, insurance 30 and reviews 30: 94, the top score, so it is the one the sheet shortlists. The 2,100 insured mover scores 31 + 30 + 30 = 91: insured, but 250 dollars more than the shortlisted quote for the same cover. Price 34 comes from 40 x (1 - 250 / 1,700), rounded - the score is relative to the cheapest quote, not to zero, which is why the top price score does not simply go to the biggest quote. The 250 dollars between the cheapest quote and the shortlisted one is what buys a claim route, and that is the comparison the sheet is designed to make visible."),
       (P, "In the same household, the address sprint finds 27 accounts, of which four are easy to forget: home insurance, vehicle registration, a pension, and a magazine subscription paid annually. The utilities sheet shows a gap of two nights on electricity because the new start date was two days after the old close, which is fixed by moving the start date rather than by a night in the dark. The deposit at risk is 4,500 dollars across two properties, and the only reason it comes back is 22 photographs with timestamps. None of these figures is a promise about your move; they are the shape of a normal one."),

       (H, "12. Weekly checklist, on one page"),
       (H, "Weeks 8-7: decide and book"),
       (C, ["Set the total budget, the buffer and the at-risk deposit on the Summary sheet",
           "Give notice or confirm dates; read the notice clause",
           "Get three written quotes for the same scope; book the mover",
           "Confirm insurance in writing; price transit cover if the contents exceed it",
           "Start the reduction in the least-used rooms"]),
       (H, "Weeks 6-5: pack what you do not need"),
       (C, ["Pack seasonal and rarely used items; label room plus priority",
           "Photograph electronics and cabling before unplugging",
           "Bag and label screws; tape each bag to its furniture",
           "Request medical, dental, veterinary and school records",
           "Book time off for the moving day"]),
       (H, "Weeks 4-3: the admin sprint"),
       (C, ["Work every row of AddressChanges; record each confirmation number",
           "Update insurance, vehicle registration, licence and pension",
           "Enter old close and new start dates for every utility; remove any positive gap",
           "Confirm mover arrival window and access at both ends, in writing",
           "Pack the first-night box and seal it last"]),
       (H, "Weeks 2-1: close out clean"),
       (C, ["Defrost the freezer; dispose of anything that cannot travel",
           "Photograph every room of the old place, furnished and then empty",
           "Photograph and record the meter readings",
           "Confirm keys and handover for both properties in writing",
           "Walk through the new home before the van arrives if possible"]),
       (H, "Moving day and week one"),
       (C, ["Photograph the loaded van; keep the inventory with you",
           "Inspect on arrival; note damage on the delivery note before signing",
           "Set up beds, bathroom and alarms first; test smoke and CO alarms",
           "Unpack by priority label, not at random",
           "Start any damage claim the same day; keep every message in one thread"]),

       (H, "13. What this is not"),
       (P, "This is an organising procedure, not legal, financial, insurance or tax advice. Deposit rules, notice periods, tenancy law, vehicle registration deadlines and insurance obligations all differ by jurisdiction and by contract, and the contract and the law always win over anything written here. The mover scoring is a disclosed weighting, not a recommendation of any company, and the workbook does not audit a mover's insurance for you - it records what you found out. The worked example is illustrative arithmetic, not a forecast. Confirm the specific requirements with your landlord or agent, your insurer, your mover's own terms, and the relevant public authority before you rely on them.")],
      disclaimers=["PROCEDURE INFORMATION ONLY — NOT LEGAL, FINANCIAL, INSURANCE OR TAX ADVICE. Deposit, notice, registration and insurance rules differ by jurisdiction; the contract and the law always win over this document. The mover score is a disclosed weighting, not a recommendation."])

# ── B12-009 sitter kit ─────────────────────────────────────────────────
build("B12-009_pet_sitter_handover_kit.pdf", "B12-009", "Pet Sitter Handover Kit",
      "Everything a sitter needs when you cannot be reached: the emergency protocol, the poisoning and escape rules, feeding and medication, vet authority you arranged in advance, and the forms to record it all on.",
      [(H, "1. How to use this kit"),
       (P, "Print the whole kit. Fill in the forms by hand, in pen, before you leave. Keep one copy on the fridge and put a photograph of the emergency page in your sitter's phone, because the moment it is needed is the moment nobody wants to be reading a document from a shelf. Then walk the sitter through it once, in person, in the order below. A handover that was never spoken aloud is a document the sitter will discover they cannot interpret at the worst possible time."),
       (P, "The kit has two halves. The first pages are the part that matters in an emergency, and they are written to be followed under stress: short steps, in order, with the decision points named. The forms after them are where the facts about your animal live, and they are only as good as the conversation you have while filling them in."),
       (P, "Fill in the forms for each animal separately if you have more than one. A sitter caring for two animals with different medication schedules needs two schedules, not one paragraph that mentions both."),

       (H, "2. The emergency protocol - read this page first"),
       (P, "Step 1. Decide whether this is an emergency. The sitter should treat any of the following as an emergency and act immediately, without waiting to see whether it improves: difficulty breathing or noisy breathing; collapse or inability to stand; a seizure, or a fit that lasts more than a minute or repeats; a distended abdomen with unproductive retching, especially in a large dog; suspected poisoning or eating something not meant for animals; heat stroke, heavy panting with confusion or wobbliness in hot weather; a road accident or a fall; bleeding that does not stop after a few minutes of firm pressure; a swollen, painful eye or an eye that cannot open; a male cat straining to urinate with little or nothing produced, which is an emergency within hours; a pet that cannot pass urine or stools at all; a female in labour that has been straining for more than twenty minutes without producing a puppy or kitten; and any situation where the sitter's own judgement says something is badly wrong. When in doubt, treat it as an emergency. The cost of an unnecessary visit is a bill; the cost of a delayed one is not negotiable."),
       (P, "Step 2. Call the vet before you call the owner. This is the hardest instruction in the kit and the most important. The sitter's instinct will be to call you first, and that call may be the one that goes unanswered because you are on a plane, in a meeting, or asleep in a different time zone. The vet can begin to help while the owner is still being contacted. So the order is: vet first, owner second, and if the owner cannot be reached, proceed with the authorisation you arranged in advance. Write the vet's number on the fridge copy in large figures so that nobody has to find it under pressure."),
       (P, "Step 3. What to say on the phone. Give the clinic the animal's species, breed if known, weight, age, and whether it is insured; what happened and when; what the animal is doing now, in plain observations rather than diagnosis; and, for a suspected poisoning, the name of the substance, the amount, and how long ago. They will ask those questions in that order, and having the answers ready saves the minutes that matter. Tell them you are the sitter and that the owner is unreachable, and ask what they need from you before you arrive."),
       (P, "Step 4. Transport safely. Use a carrier or a crate for cats and small animals. For a large dog, a second person is worth waiting thirty seconds for. Do not let a distressed animal travel loose in a car, and do not stop to look up symptoms on the way. Take the insurance details, the payment method you left, and this document with you."),
       (P, "Step 5. Authorisation and money. The form in section eleven records what you arranged with your own clinic before you left: what they require on file, whether there is a signed authorisation, and the spending limit you are willing to authorise. The sitter cannot make a clinical decision and should not be asked to. What the sitter can do is carry out the instruction you already gave: treat up to the limit you set, and call you for anything beyond it. If you have not arranged that with the clinic in advance, do it before you leave the house, not during the emergency."),
       (P, "Step 6. What the sitter must never do. Never give human medication, including painkillers, antihistamines or anything in the household medicine cabinet, because several common human medicines are toxic to animals at doses people consider small. Never induce vomiting unless a vet or an animal poison service has told you to, and never after a suspected caustic or sharp substance. Never wait a day to see whether it gets better when the list in step one applies. Never feed an animal that is vomiting repeatedly or unable to keep water down. Never attempt to treat a wound with household disinfectants. And never leave a seriously unwell animal alone to go and buy something. Recognition, containment, transport and communication are the sitter's job; treatment is the clinic's."),

       (H, "3. Poisoning and household toxins"),
       (P, "The household is full of things that are dangerous to animals and unremarkable to people. The common groups are worth knowing so that the sitter can react rather than reason: chocolate and anything containing caffeine; grapes and raisins; xylitol, which appears in sugar-free gum, some peanut butters and some sweets; onions, garlic and leeks; alcohol; antifreeze; rodent and slug poisons; human medicines, especially painkillers; lilies, which are particularly dangerous to cats; and some common houseplants. Cleaning products, batteries and nicotine are also on the list. The list is not complete, and no list can be, which is why the rule is to call rather than to check."),
       (P, "If the sitter suspects poisoning, the response is the same every time: remove the animal from the source without putting hands into a struggling animal's mouth, keep the packaging or the remains of the substance, note the time, and call the vet or an animal poison service immediately. Do not wait for symptoms, because with several common toxins the first symptom is already serious. Do not give milk, oil, salt water or any home remedy; several of the traditional remedies make absorption worse. Write down what the animal ate, how much, and when, because that information determines the treatment."),

       (H, "4. If the animal gets out"),
       (P, "The first thirty minutes decide most outcomes, so the kit gives the sitter a sequence rather than advice. Search the home first, calmly and thoroughly, including cupboards, under beds, behind appliances and inside any space a cat could have slipped into; a frightened cat is often still indoors. Then search the immediate area on foot, calling the animal's name in a normal voice rather than shouting, and take a torch even in daylight. Do not chase a scared dog: a dog that is running will outrun a person and may run into traffic. Instead, crouch, call, and let it come, or use food and a familiar toy."),
       (P, "Then tell people. Call the owner, then the local vet clinics and the local animal shelter, because a found animal is usually taken to the nearest one. Post in the local lost-and-found groups with a clear photograph, the area, the time and a contact number, and put a note on the door. If the area has a microchip registry and the animal is chipped, ask the vet or shelter to scan any animal handed in. Keep a record of where the sitter searched and when, because a search that is repeated feels like progress while a search that is extended finds animals. Do not put the sitter at risk by searching roads at night alone; call for help instead."),

       (H, "5. Medication, feeding and routine"),
       (P, "The medication form is the one form a sitter will use every day, so fill it in per dose, not per drug. For each medicine the sitter needs: the name, the amount, the route, the times, whether it must be given with food, and what to do if a dose is missed. The last field is the one people leave blank, and it is the one that causes the accident. Write the answer your vet gave you, in your vet's words, and if you never asked, ask before you leave. The general rule a sitter should follow when a dose is missed is not to double the next one; the safe answer depends on the medicine, which is why the blank must be filled by your clinic rather than guessed."),
       (P, "Every dose gets a tick and a time in the daily log. This is not bureaucracy: a missed dose and a double dose look identical to a sitter who is relying on memory, and the log is what turns an anxious evening into a telephone call with facts. If an animal refuses a dose, spits it out, or vomits soon after, that is a call to the vet, not a reason to try again with more."),
       (P, "Feeding should change as little as possible while you are away. Keep the same food, the same amount and the same times, and measure rather than estimate. A sitter who free-feeds because the animal seems hungry can cause a real problem, and a sudden change of food is a common cause of stomach upset. Write down the treats allowed and, more importantly, the ones forbidden, because a well-meaning sitter with a bag of treats can undo a diet or trigger a sensitivity. Fresh water at all times, and the water bowl washed daily."),
       (P, "Routine is not a luxury for animals; it is how they predict the day. Walks at roughly the same time, meals at roughly the same time, and the same sleeping place reduce stress and reduce the chance of an escape attempt. Tell the sitter which parts of the routine are fixed and which are flexible, so that a late evening does not become a skipped walk."),

       (H, "6. The in-person handover, in order"),
       (P, "Do the walkthrough in the order the sitter will need it, not the order that is easiest to explain. Start with the routine: where the food is kept, how it is measured, when the walks happen, where the lead and the carrier live, and where the animal sleeps. Then the medication, physically in hand, with a demonstration of how the animal takes it and where the log is kept. Then the emergency page: the vet's number, the route to the clinic, the authorisation you arranged, and the six steps above, read aloud rather than pointed at. Then the house: keys, alarm, bins, thermostat, plants, and which rooms the animal may use."),
       (P, "Then let the sitter do it while you watch. Hand over the lead, the bowl, the pill and the key, and have the sitter repeat each task back. The gap between understanding and doing is where handovers fail, and it closes in about ten minutes of practice. Finish by exchanging the numbers you will both use, including a backup contact who can make a decision if you cannot be reached, and write that backup's name on the fridge copy."),

       (H, "7. Keys, access and the house"),
       (P, "Write down who else can enter the property while you are away, and tell the sitter. A neighbour with a key who arrives unannounced is a security question the sitter should not have to resolve alone. Record the alarm code, what to do if it triggers, and the name of the person to call if it cannot be reset. Note where the stopcock and the fuse box are, because a sitter facing a leak at eleven at night needs a location rather than a phone call."),
       (P, "House rules worth writing rather than saying: which furniture is allowed, whether the animal may sleep on the bed, whether visitors are welcome, how the bins work, and whether anything in the house is dangerous to the animal. If the garden is accessible, check the fence and the gate before you leave and record what you found, because an escape is more often a gap nobody looked at than a door left open."),

       (H, "8. The daily log, and the handover back"),
       (P, "Ask the sitter to write four things each day: what was eaten and when, what was drunk, what came out the other end and whether it was normal, and anything that seemed different in behaviour. Those four lines answer almost every question a vet will ask later, and they take a minute. A photograph a day is also worth more than it sounds, because it shows a change in posture or coat that is hard to describe."),
       (P, "At the end of the booking, take the log back, read it while the sitter is still there, and ask about anything unexplained. Check the medication sheet against the log, confirm the keys are returned, and walk the house for damage before the sitter leaves rather than discovering it by message a week later. If something went wrong, write it down while it is fresh: what happened, when, what was done, and who was called. That record is what makes the next handover better."),

       (H, "9. Emergency contacts"),
       ("form", [("Owner name, mobile, and the times you can be reached", 2),
                 ("Backup contact who can decide if the owner cannot be reached", 2),
                 ("Vet: practice name, address, phone, opening hours", 2),
                 ("Emergency vet / animal hospital (24 hours): name, address, phone", 2),
                 ("Animal poison service number for your country", 1),
                 ("Insurance provider and policy number", 1),
                 ("Neighbour or family member with a key", 1)]),

       (H, "10. Pet profile (one block per animal)"),
       ("form", [("Name, species, breed, age, weight", 2),
                 ("Feeding: food, amount, times, treats allowed and forbidden", 3),
                 ("Medication: name, dose, route, times, with or without food", 3),
                 ("What to do if a dose is missed (the answer your vet gave)", 3),
                 ("Walks, litter, exercise and the fixed parts of the routine", 2),
                 ("Fears, triggers, escape habits and how the animal signals pain", 2),
                 ("Microchip number and where it is registered", 2)]),

       (H, "11. Vet authorisation (arrange this before you leave)"),
       (P, "Call your own clinic before your trip and ask what they require in order to treat your animal when a sitter brings it in. Many practices want a signed authorisation on file, a named person who may consent, and a payment method. Arrange that directly with the clinic; this page records what you arranged and does not replace it. Then tell the sitter exactly what has been arranged, because an authorisation the clinic holds and the sitter does not know about is the same as no authorisation at all."),
       ("form", [("What my clinic requires (signed form on file, named consent, other)", 3),
                 ("Who may authorise treatment while I am away", 2),
                 ("Spending limit I authorise without further contact", 1),
                 ("Payment method left for vet bills", 2)]),

       (H, "12. House and access"),
       ("form", [("Allowed and forbidden rooms, furniture and beds", 2),
                 ("Keys, alarm code, and what to do if the alarm triggers", 2),
                 ("Who else may enter the property while I am away", 2),
                 ("Bins, thermostat, plants, and anything dangerous to the animal", 2),
                 ("Stopcock and fuse box location", 1)]),

       (H, "13. Daily log (one row per day)"),
       ("form", [("Date and time of each visit or stay", 2),
                 ("Food eaten, water drunk", 3),
                 ("Toileting: normal or not, and anything unusual", 3),
                 ("Medication given: dose, time, and whether it was accepted", 3),
                 ("Behaviour, mood, and anything that seemed different", 3),
                 ("Anything to report to the owner", 2)])],
      disclaimers=["ORGANIZER AND PROCEDURE ONLY — NOT VETERINARY OR LEGAL ADVICE. Recognition, containment, transport and communication are the sitter's job; diagnosis and treatment belong to a veterinarian. Your own clinic's instructions always override anything written here. Arrange authorisation and a spending limit with your clinic before you leave, and confirm the animal poison service number for your country."])

# ── B12-010 grant pipeline method guide (Cycle 100 build) ──────────────
build("B12-010_grant_pipeline_guide.pdf", "B12-010", "Nonprofit Grant Pipeline Tracker — Method Guide",
      "How to run a grant pipeline so time goes into applications that can actually be funded, and so no report on an award you already hold is ever missed. Companion to the B12-010 workbook.",
      [(H, "1. What this kit is"),
       (P, "This kit is a working system for tracking grant funding from first sighting of a funder to the last report on an award. It has two parts that are meant to be used together. The workbook is where the facts live: one row per funder and program, the documents each application needs, the money you asked for and the money you were given, and every report due after an award. This guide is the method: what each field means, how the calculations behave, the order in which decisions should be made, and the mistakes that cost the most time."),
       (P, "The system exists because grant work fails in two specific ways. The first is effort spent on applications that were never eligible - weeks of writing that a single line of the guidelines would have prevented. The second is an award being put at risk because a report due date lived in one person's head. Both are organisational failures, not talent failures, and both are cheap to fix with a little structure."),
       (P, "Everything here is deliberately unglamorous. There is no discovery engine, no database of funders, no automatic alerting, and no scoring of your organisation. A pipeline is a list you keep current, a set of gates you refuse to skip, and arithmetic that does the remembering for you."),

       (H, "2. What this kit is not"),
       (P, "It is not a funder directory and it does not find funding opportunities for you. It does not submit, send or file anything, and it does not communicate with any funder or portal. It contains no promise of funding, no estimate of your chances, and no claim about any specific funder's rules; those live in the funder's own guidelines, which always win over anything written here."),
       (P, "It is not legal, tax, accounting or fundraising advice. Eligibility, registration, matching requirements, reporting obligations and deductibility rules are governed by law and by each funder's terms. Confirm those with the funder and with your own accountant, auditor or lawyer. The workbook records what you decided; it does not decide for you."),
       (P, "It is also not a document management system. It records where a document lives and whether it is currently ready, with a date you last checked. The files themselves belong in your own storage, with your organisation's own access rules."),

       (H, "3. The one rule that saves the most time"),
       (P, "Nothing enters Drafting until Eligibility exits clean. That single rule is the reason this workbook is stage-gated rather than a flat list. In practice, most wasted grant effort is a fully written application that was never eligible: the applicant was not the right legal entity, the service area was outside the funder's area, the award range was wrong, the match could not be documented, or a required licence had lapsed. Each of those is cheap to check in twenty minutes and expensive to discover after forty hours of writing."),
       (P, "This is why the Eligibility sheet is a screen of twelve must-pass questions rather than a score. A score invites negotiation with yourself - the application scores 71, so it can proceed. A screen does not: one NO stops the application, and no other quality of the application changes that. If you take one habit from this guide, take that one."),

       (H, "4. The seven stages and their exit gates"),
       (P, "The workbook's Stages sheet lists the seven stages. The important column is the exit gate: the condition that must be true before a row moves on. Movement without a satisfied gate is how a pipeline becomes fiction."),
       (B, ["<b>Research.</b> Exit gate: the funder's guidelines are saved and the award range overlaps what you can actually deliver. Blocked by: no saved guidelines, which means nobody can check the rules later, and a rumour about a funder standing in for the funder's own words.",
            "<b>Eligibility.</b> Exit gate: every must-pass question on the Eligibility sheet is answered YES for this specific application. Blocked by: partial answers, and by treating a maybe as a yes.",
            "<b>Drafting.</b> Exit gate: the narrative, the budget and every required document are complete, and the Docs sheet shows no MISSING for that row. Blocked by: drafting while a required document does not exist, which forces a rewrite once it does.",
            "<b>Internal review.</b> Exit gate: a second person has read the narrative, the budget and the numbers, and signed off. Blocked by: single-person review, which reliably finds your own assumptions rather than your own mistakes.",
            "<b>Submitted.</b> Exit gate: the submission confirmation or receipt is saved next to the row. Blocked by: no receipt, which means no proof of what you sent if a portal loses it.",
            "<b>Decision.</b> Exit gate: the award or decline letter is on file and the amount is recorded in the Awarded column. Blocked by: verbal intentions, which are not decisions and must not be treated as money.",
            "<b>Reporting.</b> Exit gate: every report due date is on the Timeline sheet with its cadence. Blocked by: an award letter nobody re-read, which is how a report gets missed and an award gets questioned."]),
       (P, "Stages are not a workflow engine. Nothing in the workbook forces a row forward or refuses to let it move; the sheet tells you the stage's condition and the Dashboard tells you when something is overdue. The discipline is yours. A gate that nobody checks is decoration."),
       (P, "<b>Which stage is the money stage?</b> Reporting. Research, eligibility and drafting are how you win money; reporting is how you keep it, and it is the stage most often run from memory. If you only use one sheet regularly, use Timeline."),

       (H, "5. Setting up in twenty minutes"),
       (P, "Do this once, with the funder list you already have, even if it is scribbled on paper."),
       (C, ["Open Opportunities and delete the four EXAMPLE rows, or keep them until your own first four rows are in, then delete them. Yellow rows are examples, and they are not real funders.",
            "Add one row per funder AND program. If the same funder runs two programs you might apply to, that is two rows: they have different deadlines, different documents and different award ranges.",
            "Fill the white cells only: ID, Funder, Program, Focus area, Geography, Award min, Award max, Deadline, Status, Owner, Source URL, Next action, and later Submitted, Decision and Awarded.",
            "Set Status to Research for anything you have not yet screened, and warm it through the stages as you work it.",
            "On Docs, add one row per document this application needs, from the DocLibrary sheet's standard twelve. Mark Required? Y only where the funder asks for it.",
            "On Budget, add the budget lines you intend to request, with the amount per line. Leave Confirmed blank until an award commits a figure.",
            "On Timeline, add every post-award report with its first due date from the award letter and the gap in days. If you hold no awards yet, leave it empty - the Dashboard will simply not report on it."]),
       (P, "Twenty minutes of setup is enough for the first five or six funders. The system gets more valuable as the list gets longer, because the questions it answers - what is due next, which application is blocked on a document, what has actually been awarded against what was asked - get harder to answer by hand."),

       (H, "6. Field dictionary - the Opportunities sheet"),
       (P, "One row per funder and program. This is the spine of the workbook; every other sheet joins back to it by the ID you give each row."),
       (B, ["<b>ID</b> (yours to fill). Anything unique and short: a number, or a funder code. Every other sheet references this value, so never change an ID once documents and reports point at it.",
            "<b>Funder.</b> The exact legal name of the funding body. Use the name from the guidelines, not a nickname, so a future reader can find it without asking you.",
            "<b>Program.</b> The exact program or call name. Two programs at one funder are two rows.",
            "<b>Focus area.</b> What this program funds, in your own words, in a few words. It is your reminder of why the row exists.",
            "<b>Geography.</b> The area the funder serves, and - if relevant - the area you serve. This is the field that catches out-of-area applications before they are written.",
            "<b>Award min and Award max (USD).</b> The funder's published range. Entering this lets the row check catch an award maximum below the minimum, and later catches an awarded amount that is larger than the range you recorded, which usually means a typo or a second award.",
            "<b>Deadline.</b> The funder's stated closing date. Enter a real date, not text. This single field drives the days-to-deadline figure, the deadline state, the next-deadline figure on the Dashboard, and the overdue count.",
            "<b>Status.</b> One of Research, Eligibility, Drafting, Internal review, Submitted, Awarded, Declined, Withdrawn. Awarded, Declined and Withdrawn are the three closed states, and they are the only statuses that stop the deadline maths treating the row as live.",
            "<b>Owner.</b> One person's name. Not a team, not a committee. An application with no named owner is an application that will not be submitted.",
            "<b>Source URL.</b> Where you got the information. When a deadline is questioned six weeks later, this is the difference between a check and an argument.",
            "<b>Next action.</b> The next physical step, written as a verb. 'Confirm eligibility with the programme officer' is an action; 'check eligibility' is a mood.",
            "<b>Submitted.</b> The date you actually sent it. The row check flags Submitted status with no date, because an undated submission cannot be followed up or evidenced.",
            "<b>Decision.</b> The date the funder decided. Useful even when the answer was no: decision dates cluster, and a funder who has been silent past their own notification window is a funder to chase.",
            "<b>Awarded (USD).</b> The amount actually committed. The row check flags Awarded status with no amount, and the Dashboard compares the total here against the total you requested."]),
       (P, "The six computed columns on this sheet are the workbook doing the remembering. Do not overwrite them: Docs ready, Docs gap, Days to deadline, Deadline state, Duplicate? and Row check. Each is explained in its own section below."),

       (H, "7. Field dictionary - the Docs sheet and the DocLibrary"),
       (P, "The Docs sheet holds one row per application and document. Its two questions - is this document required by this funder, and is it ready - are separate on purpose, because they fail for different reasons and are fixed by different people."),
       (B, ["<b>Opportunity ID.</b> The ID from Opportunities. This is what links a document to an application.",
            "<b>Document.</b> The document's name, taken from the DocLibrary list where possible so the same document is not stored under four different names across applications.",
            "<b>Required? (Y/N).</b> Y only where this particular funder asks for it. An optional document marked required inflates the readiness figure and hides the real gaps; a required document marked optional hides a disqualifying omission.",
            "<b>Ready? (Y/N).</b> Y only when the file exists AND is current: signed where a signature is needed, dated within its refresh window, and matching the organisation's current numbers. 'I know where it is' is not ready.",
            "<b>Where it lives.</b> The folder or link. This is what turns a checklist into something a colleague can act on while you are away.",
            "<b>Last checked.</b> The date a human last opened it. A document ready two years ago may still be ready; a document nobody has opened may be neither ready nor current."]),
       (P, "The DocLibrary sheet lists the standard twelve documents for a small nonprofit or a fiscally sponsored project, what each must show, and how often it needs refreshing. Use it as the source list for the Docs sheet, and edit it to match your own reality - the list is a starting point, not a rule. This is where the readiness figure on Opportunities comes from."),

       (H, "8. Field dictionary - the Budget sheet"),
       (P, "One row per budget line, with the amount you requested. The sheet exists so the gap between asking and getting is visible, and so a funder's awarded amount can be compared with a real breakdown rather than a single number."),
       (B, ["<b>Opportunity ID.</b> Links the line to an application.",
            "<b>Line item.</b> The category as the funder will read it: staff, materials, evaluation, travel, administration. Use their language where you know it.",
            "<b>Requested (USD).</b> What you are asking for on this line. The Dashboard sums this column into total requested.",
            "<b>Confirmed (USD).</b> What the award letter actually committed to this line. Leave blank until then, and do not fill it with a hopeful figure.",
            "<b>Notes.</b> The calculation, the unit cost, or the reason the line exists. Budgets are read by people who will ask why a number is what it is."]),
       (P, "The Dashboard's awarded-against-requested figure compares total awarded on Opportunities with total requested here. It is a management figure, not a performance metric: a low percentage across a whole portfolio may mean over-asking, or it may mean funders trimming by policy. What matters is that the figure is visible and rises or falls for reasons you can name."),

       (H, "9. Field dictionary - the Timeline sheet"),
       (P, "One row per post-award report or deliverable. This is the sheet that protects money you already hold."),
       (B, ["<b>Opportunity ID.</b> The award this report belongs to.",
            "<b>Report or deliverable.</b> What the funder expects: a narrative report, a financial report, an interim update, an outcomes table, a final report.",
            "<b>First due.</b> The first due date, taken from the award letter or the reporting schedule. Enter a real date; leave it blank and the row tells you it needs one instead of guessing.",
            "<b>Repeat every (days).</b> The gap between reports, in DAYS: 30 for monthly, 90 for quarterly, 180 for half-yearly, 365 for annual. Using days rather than words removes the ambiguity of 'quarterly' across calendar years.",
            "<b>Next due.</b> Computed. It steps forward from the first due date in whole intervals until it lands on or after today, so it never shows a date you have already passed.",
            "<b>Status.</b> Computed: OVERDUE with the number of days, DUE IN with the number of days when it is within 30 days, OPEN otherwise, or CHECK INPUTS when the first due date or the cadence is missing or impossible.",
            "<b>Notes.</b> The template, the portal, the contact, or what the report must contain."]),
       (P, "A blank first due date and an impossible cadence - zero, negative, or text - produce a plain instruction rather than a wrong date. This is deliberate: a report schedule that silently computes from a bad input is worse than no schedule at all."),

       (H, "10. How the deadline maths behaves"),
       (P, "Three computed columns do the deadline work, and their rules are simple enough to check by hand."),
       (P, "<b>Days to deadline</b> is the deadline minus today, shown only when there is both an ID and a real date. It can be negative, and a negative number is the honest signal that the date has passed. It is blank when there is no date, rather than showing a zero that would read as 'due today'."),
       (P, "<b>Deadline state</b> turns that number into a sentence, in a deliberate order of precedence:"),
       (B, ["If the status is Awarded, Declined or Withdrawn, the state is <b>CLOSED</b>. A closed row stops shouting about its old deadline, which is why the closed statuses matter beyond bookkeeping.",
            "Otherwise, if there is no deadline date, the state is <b>NO DEADLINE SET</b> - an instruction, not a blank.",
            "Otherwise, if the deadline is before today, the state is <b>OVERDUE</b> followed by the number of days, so the size of the problem is visible at a glance.",
            "Otherwise, if the deadline is within 14 days, the state is <b>DUE IN</b> followed by the number of days.",
            "Otherwise the state is <b>OPEN</b>."]),
       (P, "The Dashboard's <b>next deadline</b> figure uses a separate helper column, which returns the deadline only for rows that are not closed. The minimum of that column is the next live deadline, and if every row is closed the figure is blank rather than a stale date from last year."),
       (P, "<b>Why states rather than colour alone.</b> A colour cannot be counted, sorted reliably, or read by someone who cannot distinguish it. A state string can: the Dashboard counts the rows starting with OVERDUE and the rows starting with DUE IN, and a sorted column tells you exactly what to do this week."),
       (P, "<b>The one caveat.</b> Everything here is measured against today's date on the machine that opens the file. A date is not an alarm: the workbook cannot wake anyone up, and nothing is sent anywhere. The value is entirely in the fact that the figure is correct the moment somebody looks."),

       (H, "11. How document readiness behaves"),
       (P, "Two columns on Opportunities summarise the Docs sheet for each application."),
       (P, "<b>Docs ready</b> counts the required documents that are also ready, and required documents overall, and shows them as ready/required - for example 4/6. Documents marked not required are excluded from both halves, so the figure measures what this funder asked for, not everything the organisation owns."),
       (P, "<b>Docs gap</b> says MISSING the moment a single document is required and not ready, and OK otherwise. When there are no required documents recorded at all, the readiness figure reads 0/0 and the gap reads OK - honest emptiness rather than a false all-clear. The Dashboard counts the MISSING rows, which is the number that should be driven to zero before anything is submitted."),
       (P, "<b>The document that most often hides.</b> In practice, the document that blocks submission is rarely the narrative. It is the current board list, the most recent filed Form 990, the signed letter of support, or a registration renewal nobody remembered. The DocLibrary sheet lists these as their own rows precisely so they are checked early, while there is still time to obtain them, rather than in the final week."),

       (H, "12. How the money comparison behaves"),
       (P, "The Dashboard reports total awarded, total requested, and awarded against requested as a percentage. The percentage is blank until something has been requested, because a fraction with a zero denominator is not information."),
       (P, "Two further row checks on Opportunities protect the money fields. A row with status Awarded and no awarded amount is flagged, because an award without a number is a rumour that will be counted as nothing. A row where the awarded amount is larger than the award maximum recorded for that funder is flagged too: sometimes that is a legitimate second award or a matched amount, and sometimes it is a typo in the thousands, and the flag makes a human look either way."),
       (P, "The workbook does not attempt to model pipelines, probabilities or expected value. Multiplying an award size by a guessed success rate produces a number that looks like a forecast and behaves like a wish. Count what is real: applications submitted, decisions received, and awards received."),

       (H, "13. How the reporting cadence maths behaves"),
       (P, "The Timeline sheet computes a next due date from two numbers you supply: the first due date and the repeat interval in days. The rule is to count how many whole intervals have passed since the first due date and add them back on, never allowing a negative count, so the result is always the first due date or a later one."),
       (P, "Three examples show the behaviour. A first due date of 15 December with a 90-day interval, read in October, gives 15 December: no interval has yet passed, so the next report really is the first one. The same row read in January gives 15 March, because one interval has passed. A quarterly report whose first due date is in the past falls forward to the next quarter automatically, so an old award does not leave a row stuck on a date you already missed."),
       (P, "The status then reads OVERDUE with a day count if the computed date is behind today - which happens only when a report is genuinely late relative to its own first due date rather than to the interval - DUE IN with a day count inside 30 days, and OPEN otherwise. The Dashboard counts the overdue and the due-within-30 rows, which is the short list worth reading every week."),
       (P, "<b>Why intervals in days.</b> Monthly, quarterly and annual are periods, not dates: three months from 31 January is not a date anyone agrees on. Days are unambiguous, can be summed and compared, and are what the award letter can be translated into once."),

       (H, "14. Duplicate rows and the row check"),
       (P, "Two columns keep the register honest, and both exist because the same mistakes get made every year."),
       (P, "<b>Duplicate?</b> compares each row's funder and program with every other row. If the same combination appears more than once, both rows are flagged as duplicates. This is the single most common pipeline mess: a funder gets added twice by two people, work starts on both, and the organisation submits two applications to the same program. A duplicate flag does not delete anything - only a human knows whether the second row is a genuine second application, a different program, or simply a mistake. The Dashboard counts the flagged rows."),
       (P, "<b>Row check</b> reads each row's own fields and names concrete problems in plain language: no funder name; an award maximum below the award minimum; status Submitted with no submitted date; status Awarded with no awarded amount; a missing deadline on anything that is not still at Research; an awarded amount above the range recorded for that funder. Several problems can appear in one cell, separated by full stops. A blank cell means the row has nothing obviously wrong with it - which is not the same as being correct, only as not being self-contradictory."),
       (P, "Both columns are read-only in practice: do not type into them. They exist so that bad data is named once, at the point it is entered, rather than discovered during a funder's verification call."),

       (H, "15. The eligibility screen: twelve must-pass questions"),
       (P, "Answer these for one application, on paper, before any writing starts. One NO stops the application. If the honest answer is 'probably' or 'I think so', the answer is NO until it is confirmed in the funder's own words."),
       (C, ["Is the applicant a legal entity this funder accepts - nonprofit, fiscal sponsor, school, tribe, or other eligible body?",
            "Is the geographic area you serve inside the funder's stated area, as written?",
            "Does your organisation size - budget band, staff count - fall inside what this funder accepts?",
            "Is your program area inside this funder's stated priorities, not adjacent to them?",
            "Is your registration, charity status or licence current and verifiable today?",
            "Can you genuinely meet the reporting obligations you would be accepting, at the frequency stated?",
            "Is your ask inside the published award range?",
            "If a match or co-funding is required, can you document your share from a named source?",
            "Is the deadline realistic given how many required documents are already ready?",
            "Does the funder's decision timeline fit the dates your program actually needs?",
            "Is there one named person who will own this application to submission?",
            "If you had to reuse existing material with no rewrite at all, would you still apply?"]),
       (P, "The last question is the one people skip, and it is the most revealing. A genuine fit survives reuse with adaptation. A weak fit needs a bespoke case to be built from nothing, and that is the application that consumes three weeks and returns nothing. A NO there is not laziness; it is portfolio discipline."),
       (P, "<b>Write the answer down.</b> The Eligibility sheet has a row for each question with space for why it stops you and how to verify it. Recording the screen is what lets a colleague pick up the application, and what stops the same ineligible funder being re-added next quarter."),

       (H, "16. The standard document library, and what ready means"),
       (P, "The DocLibrary sheet lists twelve documents that cover most small-organisation applications. Treat it as a checklist to edit, not a rule to obey: some funders want a logic model, some want audited statements, some want none of it."),
       (B, ["<b>Mission statement, about 150 words.</b> Plain language, no jargon a reviewer has to decode. Refresh annually.",
            "<b>501(c)(3) determination letter.</b> The IRS letter naming the organisation and its status. Filed once, on receipt.",
            "<b>EIN confirmation letter.</b> The IRS letter showing the employer identification number. Filed once.",
            "<b>Board of directors list.</b> Names, roles, affiliations and the date the list was adopted. Updated on every board change - a stale board list is one of the most common verification failures.",
            "<b>Organisation budget.</b> The current financial-year operating budget, board approved. Refreshed whenever the budget is approved.",
            "<b>Project budget and narrative.</b> Every line justified in words as well as numbers. Prepared per application.",
            "<b>Most recent Form 990.</b> The return as filed, not a draft. Refreshed yearly once filed.",
            "<b>Financial statements.</b> Audited, reviewed or internally prepared - and say which, because a reviewer will ask.",
            "<b>Program narrative.</b> What you do, for whom, with what evidence. Reviewed each quarter so it does not drift from reality.",
            "<b>Logic model or outcomes table.</b> Inputs, activities, outputs and the outcomes you actually measure.",
            "<b>Letters of support.</b> Dated, specific, signed, one page each. Prepared per application, and they take weeks to obtain.",
            "<b>Project timeline.</b> Months, milestones and who delivers them."]),
       (P, "<b>What ready means.</b> Ready is not 'exists somewhere'. A document is ready when a reviewer could open it today and find it current, signed where signatures are needed, and consistent with the numbers in the rest of the application. That last test is the one that fails most often: the board list in the narrative, the budget in the attachment and the figures in the financial statements are three places for one number to disagree."),
       (P, "<b>Refresh discipline.</b> The DocLibrary sheet gives a cadence for each item. The practice that works is a single annual document review, one hour, before the busiest application season: open each document, confirm it is current, update where it is not, and set Last checked to that date. Everything after that is a checklist, not a project."),

       (H, "17. Writing the narrative from reusable blocks"),
       (P, "Most of a grant narrative is organisation-wide material that changes once a year, not per application. The parts that are genuinely bespoke are the sections that respond to this funder's stated priorities, this program's design, and this budget. Separating the two is the difference between two weeks and three days of writing."),
       (P, "<b>Blocks that should exist before any application is started</b>, each one paragraph, each one already reviewed: the organisation story, the problem statement, the approach and evidence, the team, the outcomes and how you measure them, and the sustainability answer. Each block should be written to be reused, which means avoiding sentences that are true only for one funder. Keep them somewhere you control, and keep a date on each."),
       (P, "<b>Blocks that must be written for each application:</b> the response to the funder's own priorities in their own language, the specific program design and timeline, and the budget narrative. That is a bounded piece of work, and it is where the thinking belongs."),
       (P, "<b>Three rules for reuse.</b> First, never reuse a sentence that names a different funder - a leftover name is the single fastest way to lose credibility. Second, never reuse a number that has changed; pull figures from the current budget, not from the last application. Third, always re-read a reused block aloud: prose written for a different program often sounds like it, and reviewers can hear it."),
       (P, "<b>On word limits.</b> Where a funder sets a limit, respect it exactly and spend the space on their priorities, not on your history. Where there is no limit, shorter is still the discipline: a reviewer reading forty applications rewards the one that answers the question in the first sentence."),

       (H, "18. The budget narrative that survives review"),
       (P, "Reviewers read the budget before they read the narrative in many small competitions, because a budget is hard to obscure. Five habits make a budget narrative defensible."),
       (B, ["<b>Every line has a unit and a count.</b> Staff weeks at a rate, sessions at a cost, equipment at a price. A round number with no unit invites a question you will have to answer later.",
            "<b>Administration is stated, not hidden.</b> If you are asking for a percentage to cover management, say so and say what it covers. A hidden overhead discovered late damages the whole application.",
            "<b>What you contribute is shown.</b> In-kind, volunteer time, existing staff, other funders: name them, with a value where you can defend one.",
            "<b>The totals agree everywhere.</b> The request total, the narrative total, the attachment total and the form field must be the same number. Prepare the budget in the workbook and copy, never retype.",
            "<b>Multi-year asks show the shape.</b> If the request spans years, show the split per year and what happens in each, rather than one total that implies even spending."]),
       (P, "The Budget sheet is deliberately simple: one row per line, requested and confirmed. That simplicity is the point. Complex spreadsheets are where totals disagree; a flat list with a computed total is where they stop disagreeing. Keep the detailed workbook your finance person uses, and keep the summary here for the application."),

       (H, "19. Worked example: ninety days, one fictional organisation"),
       (P, "The following is an illustration, not a real organisation, funder or result. It shows only the mechanics of the system."),
       (P, "A small arts organisation - call it a community arts collective with three staff and a volunteer board - starts a quarter with eleven funder rows in the register, most at Research. Over ninety days the following happens, and it is all ordinary."),
       (B, ["<b>Week 1.</b> The team screens all eleven against the twelve must-pass questions. Four are stopped immediately: two fund only organisations in a different service area, one requires a registration the collective does not hold, and one has an award range starting above the collective's whole programme budget. Seven remain. The four that stopped are marked Declined with the reason recorded in Next action, so nobody re-adds them next quarter - that is seventeen person-hours saved, not earned.",
            "<b>Week 2.</b> Documents are reviewed. The board list is two years old and names a director who left; the most recent Form 990 is missing from the folder. Both go on the Docs sheet as required and not ready for three applications at once, which is why the Docs sheet is per application rather than per organisation. The 990 is downloaded, the board list is updated and adopted, and both are marked ready with the date checked.",
            "<b>Weeks 3 to 6.</b> Three applications are drafted from the reusable blocks plus bespoke priority and budget sections. Two more go into Eligibility, where one is stopped on question 8 - a match requirement the collective cannot document - and one proceeds. Meanwhile a deadline on an already-drafted application moves from DUE IN 14 DAYS to DUE IN 7 DAYS on the Dashboard without anyone having to remember it.",
            "<b>Week 7.</b> The five live applications are submitted. Receipts are saved and the Submitted dates entered. The row check catches one row where the status had been set to Submitted a week earlier with no date, which turns out to be a submission that never completed - exactly the kind of error a memory-based system carries silently until the funder's portal closes.",
            "<b>Week 9.</b> Two decisions arrive. One award of 15,000 is recorded with the award letter on file; one decline is recorded with the funder's own reason copied into Next action. The award rate on the Dashboard now reads from two decisions rather than being blank. The awarded amount is entered against the budget lines that were actually funded, and the confirmed total differs from the requested total by the amount the funder trimmed - a figure that is now visible rather than surprising the finance meeting later.",
            "<b>Week 10.</b> The award letter specifies four quarterly reports and a final report. Each becomes a row on Timeline with its first due date and a 90-day interval. The next due date computes to the first report, which is 57 days away.",
            "<b>Week 13.</b> The monthly review takes forty minutes. Two new funders are added at Research, one duplicate is found and merged (the same funder had been entered under its acronym and its full name), and the Dashboard's single next instruction is to confirm eligibility on the two new rows. Nothing is overdue, one report is due in under 30 days, and the pipeline has 9 live rows, 5 submissions, 2 decisions, 1 award."]),
       (P, "Nothing in that quarter was clever. The value came from three ordinary behaviours: screening before writing, keeping documents current, and letting arithmetic hold the dates."),

       (H, "20. When you are declined: the four-line post-mortem"),
       (P, "A decline is data if you write it down and noise if you do not. Copy the funder's own reason into the row's Next action, then write four lines somewhere you will see them again."),
       (C, ["What the funder said, in their words, not your paraphrase.",
            "Which stage would have caught this if it had been run properly - eligibility, documents, budget, narrative or review?",
            "Whether this funder is worth a future application, and if so, what would have to change first.",
            "The one thing you will do differently on the next application, written as an action."]),
       (P, "Then close the row: set the status to Declined and record the decision date. A declined row keeps its history and stops appearing as live. What must not happen is the row being deleted. A pipeline of only live rows cannot tell you that you have applied to the same funder unsuccessfully three times, which is the single most useful thing a pipeline can tell you."),

       (H, "21. The monthly sixty-minute pipeline review"),
       (P, "The system works on a monthly rhythm, and the rhythm is short on purpose. Every item below is visible on the Dashboard or one of the sheets; nothing needs to be sought out."),
       (C, ["Read the Pipeline verdict first and do what it says. It is ordered by what costs least if ignored.",
            "Work the overdue deadlines, newest first: an overdue application either moves or dies this month.",
            "Check the rows due within 14 days and confirm each one is genuinely ready to submit - documents, budget, reviewer.",
            "Clear the MISSING count: obtain or request one blocking document this month, not all of them.",
            "Read the Timeline: anything overdue or due within 30 days gets a date and an owner in the calendar.",
            "Add new funders at Research only. Do not start writing anything new until the live list is under control.",
            "Log every decision received this month, with date, amount and the funder's reason.",
            "Sweep for duplicates and row problems: both counts should be zero when you finish.",
            "Write one sentence about what this month taught you. It takes thirty seconds and it is the only part that compounds."]),
       (P, "Sixty minutes a month, plus the annual document review, is the whole maintenance burden. A pipeline that needs more attention than that is usually a sign that too many rows are live at once: five or six well-worked applications beat twenty half-worked ones, and the eligibility screen is what keeps the number honest."),

       (H, "22. Twenty mistakes that cost applications and awards"),
       (B, ["Writing the narrative before screening eligibility. The most expensive mistake on this list, and the most common.",
            "Treating 'we could probably qualify' as a yes. A screen has no room for probably.",
            "Applying to funders whose award range does not overlap what you can deliver, because the money looks attractive.",
            "Ignoring the match requirement until the budget is written - the point at which it is no longer practical to withdraw.",
            "Submitting with a required document missing and promising it later. Many funders disqualify silently rather than ask.",
            "Using a board list that names people who have left. Reviewers check, and an inaccurate list casts doubt on everything else.",
            "Copying a reused narrative block that still names a different funder. It happens more often than anyone admits.",
            "Retyping the budget total instead of copying it, so the narrative, the attachment and the form disagree.",
            "Letting the deadline be remembered rather than computed, and discovering it on the closing day.",
            "One person writing and reviewing their own work, then submitting with their own assumptions intact.",
            "No named owner for an application, so every stage is everyone's job and therefore nobody's.",
            "Setting the status to Submitted when the work is merely finished. Submitted means a receipt exists.",
            "Recording a verbal 'we are likely to fund you' as an award. It can still be lost, and it must not be counted as money.",
            "Not recording declines, so the same ineligible funder is added again in six months.",
            "Not reading the award letter after a yes, and therefore not knowing what reports are now owed.",
            "Treating quarterly reports as a memory task, and discovering in an audit that two were never filed.",
            "Running the whole pipeline in one person's head and inbox while the workbook is left empty - the tool does not work unused.",
            "Keeping too many live applications at once, so every one of them is worked badly.",
            "Deleting declined rows. The history is the most useful part of a pipeline.",
            "Measuring activity - how many applications were sent - instead of outcomes: decisions, awards, and reports filed on time."]),

       (H, "23. Reporting after award: the calendar that protects the money"),
       (P, "An award is a contract with reporting obligations attached, and the obligations are usually stated in the same letter as the grant. The common cycle is: an interim report part-way through, a final narrative and financial report at the end, and for multi-year awards an annual report for each year. Some funders add site visits, outcomes data or a spend-down schedule."),
       (P, "Two habits prevent the failure that matters. The first is translating the schedule into a first due date and an interval on the day the award letter arrives, while the letter is open - not later, when it has gone into a folder. The second is checking the Timeline sheet weekly rather than monthly: a report due in three weeks is a task, a report due in three days is an emergency, and there is no reason to let the second state ever occur."),
       (P, "A missed report has a specific cost that is worse than embarrassment. It puts future funding from that funder at risk, it often triggers a closer look at the whole award, and it can require repaying an unspent or unjustified amount. The Timeline sheet exists because the cost is asymmetric: keeping it current takes two minutes a month, and a missed report can cost an award."),
       (P, "<b>Close the loop at the end of an award.</b> When the final report is filed, record the filing date in the Notes column rather than deleting the row, and set the award row's status honestly. A funder whose award is finished and reported well is the most likely source of the next award; a pipeline that keeps that history can prove it."),

       (H, "24. Compatibility, limitations and honest caveats"),
       (B, ["<b>Spreadsheet application.</b> The workbook is a standard .xlsx file, built for Excel and using only common functions - COUNTIF, COUNTIFS, SUM, SUMIF, MIN, ROUNDUP, TODAY, IF, SUMPRODUCT, INDEX and MATCH - plus data validation lists. It was not verified in every spreadsheet application. If your editor changes or drops a formula or a validation list, the affected cell will say so or show an error, and the fix is to re-enter it.",
            "<b>Dynamic dates.</b> Anything involving today's date recalculates on open, and a file left closed for months will show stale states until it is opened again. Nothing is emailed, nothing is scheduled, and no reminder exists outside the file.",
            "<b>Sample rows.</b> The workbook ships with four example rows, marked EXAMPLE, so the computed columns are visible immediately. They are fictional. Delete them before real use, or the Dashboard will count them.",
            "<b>No discovery, no submission, no integration.</b> Nothing here finds funders, files anything, or connects to a funder portal. There is no import from a funder's own template, and no export to one beyond copying and pasting your own text.",
            "<b>The formulas are transparent, and that is deliberate.</b> Every computed cell can be read, and this guide explains each rule in words. If you disagree with a rule, change the formula in your copy - but change it everywhere it is used, and note the change, because the Dashboard's counts depend on the state strings in the other sheets.",
            "<b>Not advice.</b> Nothing in this kit is legal, tax, accounting or fundraising advice, and nothing in it is specific to any funder's requirements. Eligibility, reporting and deductibility are governed by law and by the funder's own terms."]),

       (H, "25. Frequently asked questions"),
       (P, "<b>Do I need Excel, or does Google Sheets work?</b> The file is an .xlsx workbook, and the functions used are common to both. Google Sheets import is generally reliable for these functions but it has not been tested against every version of every editor, so check the computed columns after import before relying on them."),
       (P, "<b>Should I use one workbook per year, or one forever?</b> One per year is easier to read and to archive, and it keeps the Dashboard's totals meaningful. If you carry live applications across the new year, copy those rows over rather than starting clean."),
       (P, "<b>What if two people edit the workbook?</b> Then agree on one editor at a time, or use a file in shared storage that records who changed what. The computed columns rely on the data being consistent; simultaneous edits produce duplicates and contradictions, which is exactly what the Duplicate? column will then report."),
       (P, "<b>Can I add columns?</b> Yes, anywhere to the right of the existing ones. Do not insert a column in the middle: every formula refers to columns by letter, and inserting one silently shifts what they read."),
       (P, "<b>How many funders should be live at once?</b> As many as you can genuinely work. For a small team, five or six live applications is usually the honest ceiling; the eligibility screen is what keeps the number honest rather than aspirational."),
       (P, "<b>What if a deadline changes?</b> Update the Deadline field. Everything downstream - days, state, next deadline, the overdue count - recalculates immediately. Put the funder's new notice in the Source URL or Next action so the change is dated."),
       (P, "<b>What if a funder reopens the same program next year?</b> Keep the old row, set it to Declined or Withdrawn with the reason, and create a new row for the new cycle with a new deadline. The history is worth more than the tidiness."),
       (P, "<b>What if I apply for two programs at the same funder?</b> Two rows. They have different deadlines, different documents and different award ranges, and a single row will hide one of them."),
       (P, "<b>My award rate is low. What does that mean?</b> It means decisions are being received and not all are yes. It is not automatically a problem: funders fund on their own priorities, and a portfolio with a hundred per cent award rate usually means too few, too easy, too small applications. Read the reasons recorded against declines; that is where the information is."),
       (P, "<b>Why does the workbook ask whether a document is required?</b> Because documents fail in two different ways. A document marked required that nobody can find inflates the readiness figure, and a document marked optional that the funder actually requires hides a disqualifying omission. The two questions are kept separate so both failures are visible."),
       (P, "<b>The Timeline status says CHECK INPUTS. What is wrong?</b> Either the first due date is blank or not a real date, or the repeat interval is blank, zero, negative or not a number. Fill both and the status resolves."),
       (P, "<b>Can I use this for non-grant funding - sponsorship, contracts, donations?</b> The structure fits any funding relationship with a deadline and reporting obligations, so yes, with the caveat that the eligibility questions and document list are written for grants and would need adapting."),
       (P, "<b>Does it track spend against each award?</b> Not in detail. It records what was requested and what was confirmed per budget line, and it tracks report due dates. Detailed spend tracking belongs in accounting software, and duplicating it here would create a second set of books."),
       (P, "<b>What happens if I stop using it for three months?</b> Nothing breaks: the file shows the state as of the day it is opened. The next deadline may have passed and reports may be overdue, and the Dashboard will say so. Catching up takes one long session."),
       (P, "<b>Can I share it with a board member?</b> Yes, and a single page - the Dashboard, or the Opportunities sheet sorted by deadline - is usually what a board actually wants to see. Delete any rows containing personal contact details first if your policy requires it."),
       (P, "<b>Is any of my data sent anywhere?</b> No. The workbook is a local file with no macros, no external connections and no telemetry. Nothing leaves your machine or your storage unless you send it yourself."),

       (H, "26. Glossary"),
       (B, ["<b>Application to a funder</b>: a single request under a single program, with its own deadline, documents, budget and outcome. It is one row on the Opportunities sheet.",
            "<b>Award</b>: a confirmed commitment of money, recorded with its amount and date. A verbal indication is not an award.",
            "<b>Award rate</b>: awards divided by decisions received - not by applications submitted, because silence is not yet a decision.",
            "<b>Cadence</b>: the repeating interval between reports, expressed in days on the Timeline sheet.",
            "<b>Closed row</b>: an opportunity whose status is Awarded, Declined or Withdrawn. Closed rows keep their history and stop appearing as live work.",
            "<b>Co-funding / match</b>: the share of a project the applicant must fund from elsewhere, which may have to be documented rather than stated.",
            "<b>Determination letter</b>: the IRS letter recognising an organisation's tax-exempt status; the most commonly requested proof of eligibility in the United States.",
            "<b>DocLibrary</b>: the sheet listing the standard twelve documents and how often each needs refreshing.",
            "<b>Docs gap</b>: the computed state showing that at least one required document for an application is not ready.",
            "<b>Eligibility screen</b>: the twelve must-pass questions answered before any writing begins.",
            "<b>Exit gate</b>: the condition that must be true before a row moves to the next stage.",
            "<b>Form 990</b>: the annual information return most US tax-exempt organisations file with the IRS; funders routinely ask for the most recent filed version.",
            "<b>Fiscal sponsor</b>: an organisation that provides legal and financial cover to a project that is not itself incorporated. It changes the answers to several eligibility questions.",
            "<b>Logic model</b>: a one-page description of inputs, activities, outputs and outcomes; often requested instead of a long narrative.",
            "<b>Next due</b>: the computed date of the next report, derived from the first due date and the interval, and never in the past.",
            "<b>Program</b>: a specific funding stream or call within a funder. Two programs at one funder are two opportunities.",
            "<b>Row check</b>: the computed column naming concrete problems within a single row.",
            "<b>Service area</b>: the geographic area a funder serves, or the area your organisation serves; the mismatch between the two is one of the most common disqualifiers."]),

       (H, "27. First ninety minutes"),
       (C, ["Minutes 0-20: set up. Delete or ignore the EXAMPLE rows, add your own funders, one row per funder and program.",
            "Minutes 20-40: screen. Run the twelve eligibility questions against the two or three rows you most want to work on. Stop what fails, and write the reason down.",
            "Minutes 40-60: documents. Add the required documents for the surviving rows to the Docs sheet, and mark ready only what genuinely is.",
            "Minutes 60-80: money. Add the budget lines you intend to request for the application you will actually write.",
            "Minutes 80-90: dates. Put every live deadline in and confirm the state column reads sensibly. If you already hold an award, add its reports to Timeline now."]),
       (P, "At the end of ninety minutes you have a screen you trust, a document list that tells you the truth, and a deadline column that will still be correct in three weeks. That is the whole system."),

       ("break", ""),
       (H, "28. What this is not"),
       (P, "This is a workbook and a written method for organising your own grant applications. It does not submit applications, contact funders, monitor portals, provide legal or financial advice, or promise any funding outcome. Eligibility rules, award ranges, match requirements, reporting obligations and tax treatment are set by each funder and by law, and they change; the funder's own guidelines and your own professional advisers always take precedence over anything in this kit. Review and eligibility answers shown in the examples are fictional illustrations of how the mechanics work, not statements about any real funder. The formulas are provided as a working tool and should be verified in your own copy before you rely on them.")],
      disclaimers=["ORGANISING TOOL ONLY - NO FUNDING IS PROMISED OR IMPLIED. Nothing here submits an application, contacts a funder, or monitors a portal. Eligibility, reporting and tax rules are set by each funder and by law - always follow the funder's own guidelines. Not legal, tax, accounting or financial advice. Examples are fictional."])

print("PDF batch done.")
