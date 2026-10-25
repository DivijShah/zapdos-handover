# Demo: The 24/7 Handover (3 minutes, zero keyboard)

Nobody types during the demo. A judge kills the process, `demo.sh` brings it back, and the prepared drop lands by itself. After the 3 minutes judges may click any card on the page: it opens a detail sheet with the sources and the file.

## Setup (before 20:30): run from the REAL folder, not a copy
The git-log pane needs `.git`, so the demo runs in `/Users/divij/PersonalProjects/hackday` itself.
- **Primary screen: the browser, full screen at 1080p.** `open index.html` (file://), Handover tab. Austin on the left, Singapore on the right, the handover lane between them. It re-reads the ledger every 3 s: new items slide in and glow for 2 s, superseded items strike through, the live feed runs down the middle lane. The pill top-right shows the heartbeat: green "RUNNING · tick Ns ago", amber "PROCESSING DROP…" while a drop is ingested, red "NOT RUNNING" after 60 s without a tick. Citation chips and sent items are links to the verbatim source record or the outbox file. Light/dark toggle top-right.
- **Terminal A, small, in a corner:** `cd /Users/divij/PersonalProjects/hackday && ./demo.sh` (loops `run.py`). `DEMO_DROP_AT` seconds after the FIRST boot (default 110) the prepared drop is copied into `inbox/drops/`. `DEMO_AUDIT_AT` seconds after the first boot (default 140) the page switches itself to the Audit tab for 30 s, then back to Handover. In demo mode model calls time out after 30 s with one retry.
- **Pane B, tiny:** `watch -n 5 'git log --oneline | head -12'`
- **Before starting, in the real folder:** `handover/demo.json` and `inbox/drops/demo-2030.txt` must NOT exist, and `inbox/drops/` must be empty. The drop is ingested once, for good, so there is no second run in the same folder. Rehearse only in a copy: `rsync -a --exclude .git ./ /tmp/demo-copy/`, then `./demo.sh` there.
- Stop at the end with Ctrl-C in Terminal A. A `demo.sh` launched in the background ignores SIGINT; use `kill` on it.
- What the judge runs: `kill -9 $(pgrep -f "run.py --demo-drop-at")`. Nobody relaunches.

## Measured
See the table at the bottom of this file.

## Narration
**0:00 (the Handover tab is on screen; Terminal A small in the corner)**
"Four AIs, one per person. Austin on this side: Sam and Dana. Singapore on that side: Wei Lin and Priya. It is Saturday afternoon here and Sunday morning there, and the work crosses the middle lane. Each person has three things: what they owe, what the AI already did for them, and the decisions waiting for them, one tap each. Every item shows its sources, and the chips open the source text."

**0:20 (point at Austin, the lane, Singapore)**
"Northwind's price is Sam's. The camera layout is done. The Tom call is Dana's. The Crestline double-booking was found from the calendar and handed to Dana, and the heads-up crosses to Wei Lin in Singapore here in the lane. Owners come from a lookup on who owns what, never from a guess."

**0:50 (the "Done by the AI" rows, then the decisions)**
"The AIs finish what they can. The emails to Maria, Ken, Raj, Jordan, Lisa and Omar were sent by the AI on its own, because they promise nothing new: no price, no time, no money. Sam's price and the Farah reschedule were not sent: they commit us, so they are decisions in the owner's column, one tap each. The Optix PO is on Sam's Owed list; no decision has been filed for it. And this box logs what the AI caught itself doing wrong: right now zero, nothing has been rejected yet."

**1:20 (the judge kills it; point at the corner terminal, not the pill)**
"Kill it. Look at the terminal: it comes back by itself in under a second with RESUMED and the same counts. No model calls to get there, nothing duplicated. All state is on disk and the git log is the feed."

**1:50 (the drop lands on its own, T+110 s; the pill turns amber: PROCESSING DROP…)**
"A new message just arrived: Maria says Tom can do Friday 30 October at 2pm Dallas and wants the number by then." Wait 15 to 25 s. Watch the lane: new lines slide in and glow. Point at Dana: "The old Tom-call item strikes through as superseded. There is a new decision for Dana: book the call, with a calendar proposal and a confirmation ready; it waits because booking commits her. And in Sam's column the price decision now carries a due date, Friday 30 October, with the drop as its source."

**2:20 to 2:50 (the page shows the audit on its own; nobody touches anything)**
"This is an automated token audit: numbers, dates, dollar amounts and names in outbound text, each matched verbatim against the sources it cites." The page flips itself to the Audit tab at T+140 s and back after 30 s. Point at `$4,680 <- E10` and `2pm <- D-demo-2030-…`, and at the headline "token audit: N checked · 0 unsourced". "If it finds a token with no source, a draft is withheld before it is sent; a file that was already sent is flagged, not recalled." It checks tokens, not whether a sentence is true.

**2:50 (the close; docs/SCENARIOS.md, "Lines for the demo close", his words)**
- "Your sheet says the AI removes the waiting, not the deciding. That's the send policy: it sent five things that commit nothing, and queued the five that do."
- "Your four boxes: one AI per person — yes. One shared record — the ledger plus a handover note per person. Two handovers a day — tonight the restart is the handover. One decision queue, one tap each — Sam's column, five items, brief attached. The tap-to-execute is Monday's first build."
(The page footer shows the live counts, currently 7 sent with the Omar acknowledgement; say the live number if it differs from "five".)
Stop. Judges may now click any card.

## If something goes wrong
- No supersede after 40 s: look in `handover/run.log` and `handover/judge_cache/`. The drop is retried every tick.
- Pill red "NOT RUNNING": no heartbeat for 60 s; `demo.sh` restarts the process by itself, nothing to type. The pill does not prove a restart happened: check the terminal's RESUMED line.
- The header banner is recomputed on every tick, so it can lag by up to one tick (about 20 s).

## Measured (live check, promoted v4 page)
Fresh copy, `DEMO_DROP_AT=60 DEMO_AUDIT_AT=90`, `kill -9` at T+65 (mid drop processing), one browser page open throughout, viewport 1920x1080:

| Step | Result |
|---|---|
| `kill -9` to RESUMED line in the terminal | 0.75 s (0.86 s in the first run of this page) |
| Drop lands (from first boot) | T+60 |
| Drop lands to the Tom card struck through and both due dates on the page (includes the kill and restart) | 20.5 s |
| Page switches to Audit by itself, then back on the same page, no reload | T+90.7 to T+120.7 |
| Rejections / withheld files | 0 / none |
| Token audit at the end | 133 checked, 0 unsourced |
| Clipping at 1920x1080 (container overflow, child overflow) | none |
| Card click opens the sheet; it stays open through the data updates underneath (samples T+71 to T+107) | yes |
| Citation chip click opens `handover/sources/C09.txt` | yes |

Without a kill in the middle, drop to visible was about 14 s in earlier runs. The first run of this page found Dana's decision card cut off at the bottom and the sent-chip row cut at the edge; fixed by showing no Owed card beside a superseded one (the "+N more" line carries the count) and two sent chips plus "+N more"; the run above is the re-run after that fix.
