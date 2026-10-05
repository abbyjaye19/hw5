# Dashboard Design: Campus Customs Operations Desk

**Concept: a formal boardroom, not a chat app.** The agents are a management team, so the desk is designed like the room where a board meets. Cases sit on a docket, the team convenes around a table, a secretary keeps minutes, and a treasurer holds the chequebook. A human sits at the head of all of it with the pen. Every visual choice serves that metaphor, so someone sitting at the desk can tell at a glance what's open, who is talking, what was decided and where the money went.

## Palette and type: navy, white, gold, silver

| Element | Choice | Why |
|---|---|---|
| Navy `#0b1f3a` | Masthead, boardroom, balance card, matter strip | Authority and trust; the colour of banks, law firms and Yale |
| White / ivory paper | Panels and page background with faint vertical "ledger" rules | Reads as paper and documents, calm for long sessions |
| Gold `#c9a54b` | Accents only: the chair, live delegations, resolved seals, the balance figure, primary buttons | Gold means *important or decided*. Rationing it keeps the eye on what matters |
| Silver `#c3c9d2` | Specialists' nameplates, borders, inactive states, secondary buttons | Brushed-metal nameplates feel formal; silver is the "supporting" colour next to gold |
| Type | Cormorant Garamond (display), Cinzel (engraved small caps), Inter (UI), IBM Plex Mono (figures) | Serif headings and engraved capitals give the formal, institutional feel; Inter and Plex keep data crisp |

There's no black-and-pink anywhere. Red appears only as a muted crimson for refusals and errors, so it stands out when it matters.

## Layout: three columns, read left to right like the workflow

1. **The Docket (left):** each ticket is a **manila case folder** with a navy file tab ("No. 101"), its type, requester and SKU or lease details. You pick a matter by clicking its folder.
2. **The Boardroom (centre):** the matter strip on top shows the selected case and the **"Convene the team"** button. Below it is an **oval boardroom table seen from above**. The Boss sits at the head on a **gold nameplate**, and the four specialists sit around the table on **silver nameplates**. Under it are the **Minutes** (live proceedings) and the **Resolution** (outcome).
3. **The Treasury (right, sticky):** the checking balance, a cash-flow ledger, and the cheques waiting for your signature. It stays visible while you scroll, because money is always in view at a real desk.

## How the agents read differently

**On the table:**
- **Who's working:** a nameplate lifts and glows gold while its agent works. It dims when idle, shows a tick when the report is filed, and gets a red ring if a guardrail blocked something.
- **Speech:** each seat shows a small speech card with that agent's latest words or the tool it's consulting.
- **Delegations:** these draw **gold lines between seats**. A line stays bright and animated (flowing dashes) while the delegated agent is still working, then fades to a silver dashed trace, so after a run you can see the delegation map at a glance. Specialist-to-specialist hand-offs show up as two live lines at once (e.g. Boss → Facilities → Accounting).

**In the minutes, each agent has its own typographic voice:**
- **Boss:** larger, bold Garamond, the chair's voice
- **Inventory:** monospaced, like a stock printout; it's all counts and SKUs
- **Accounting:** clean sans with tabular numerals, like a spreadsheet
- **Facilities:** engraved small caps, like a property deed
- **Customer Service:** italic serif, like a handwritten letter

Delegated work is **indented** under the agent that asked for it, so the minutes read as a nested conversation. Tool calls appear as small grey **chips with their arguments**, and tool results as one-line `↳` notes in mono, so you can audit exactly which MCP tools were used. Internal plumbing (the structured-output step) is hidden.

## How resolved tickets show up

- **Docket seals:** each folder carries a seal. **Open** is a dashed silver ring. **In session** is a pulsing gold ring. **Resolved** is a **gold wax seal with a check mark** that "stamps" down with a small animation, a satisfying and unmistakable signal of closure. Resolved folders turn a slightly aged-paper colour.
- **Resolution card:** after a run, the panel titled **"The Board Has Decided"** shows the Boss's decision as a pull-quote, the status filed, cheque and draft numbers, and **"For your signature"**: the ordered steps the human must take.
- **Agent briefs:** below that, one card per agent involved, with its summary, the tools it used (with counts), and whom it briefed. Agents that weren't needed don't get a card, which shows the Boss didn't call everyone.
- **Draft letters:** customer drafts render on **Campus Customs letterhead** with a red **"Draft · not sent"** stamp, reinforcing that agents never email anyone.

## How cash flow shows up

- **Balance card:** the checking balance in large gold figures on navy. After you sign a cheque, the number **counts down** to the new balance and the card flashes a gold ring, so you *see* the money leave.
- **Pending:** under the figure, the total awaiting signature and "balance if all signed" warn before you approve something unaffordable.
- **Cash-flow line:** a small line that only ever steps down (there's no revenue in this shop).
- **Ledger:** an opening balance, then one debit row per approved payment, with **who signed it** and the running balance, like a bank register.
- **Cheques:** every payment or purchase order the agents prepared appears as a **cheque**: "Pay to the order of…", the amount in numerals **and in words** ("Eight Hundred Forty and 00/100 Dollars"), a memo with the reason and ticket, and "Prepared by Accounting". You type your name once as the **authorised signatory**; it appears on the signature line, and you click **Sign & approve** or **Decline**. If the backend refuses (insufficient cash, or a vendor still blocked by an open invoice), the refusal is written right on the cheque and the balance doesn't move.

## Creative touches that make it feel special

- **The cheque metaphor** makes human approval feel weighty and deliberate. You literally sign before money moves, which is exactly the guardrail the assignment requires.
- **The table itself:** the CC crest sits at the centre with the current matter number. A "Recording ●" indicator on the minutes and a session light on the boardroom pulse while the team is in session.
- **Wax-seal resolution stamp** and **letterhead drafts** turn abstract states into familiar office objects.
- **Engraved small caps** for section eyebrows ("The Docket", "The Boardroom", "Minutes of the Meeting", "The Treasury") give it a formal, institutional voice.
- **Fine detail:** a double inner border on every panel (like a framed document), a gold underline on each panel title, a guilloché-style diagonal pattern on cheques, and a gold/silver double rule under the masthead.
- **The colophon:** the footer reads *"Agents prepare · humans sign · every step recorded in the audit trail"*, which sums up the operating principle of the desk.

## Behaviour notes

- The board polls the backend every 1.2 s while a team is in session (events, run status, cash and approvals), then refreshes everything when the run ends.
- One matter runs at a time, because every ticket shares one checking account. "Convene" is disabled during a session, and resolved matters must be reset before running again.
- **Reset the books** (masthead) restores the original database after a confirmation. The audit trail is kept, and the board shows only events since the last reset.
- It's responsive: three columns on wide screens, two on laptops (the Treasury moves below), one on narrow screens.
