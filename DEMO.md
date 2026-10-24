# Demo: The 24/7 Handover (3 minutes, zero keyboard)

Nobody types during the demo. A judge kills the process, `demo.sh` brings it back, and the prepared drop lands by itself.

## Setup (before 20:30)
- **Primary screen: the browser, full screen at 1080p.** `open index.html` (file://), Board tab. It re-reads the ledger every 3 s: live activity feed on the right, new items slide in and glow for 2 s, superseded items strike through. The pill top-right shows the heartbeat: green "RUNNING · tick Ns ago", amber "PROCESSING DROP…" while a drop is being ingested, red "NOT RUNNING" if no tick for 60 s. Citation chips and sent/outbox items are links: they open the verbatim source record (`handover/sources/<id>.txt`) or the outbox file. The footer shows the counts and the audit result.
- **Terminal A, small, in a corner of the screen:** `cd /Users/divij/PersonalProjects/hackday && ./demo.sh` (loops `run.py`). `DEMO_DROP_AT` seconds after the FIRST boot (default 110) the prepared drop is copied into `inbox/drops/`. `DEMO_AUDIT_AT` seconds after the first boot (default 150) the page switches itself to the Audit tab for 30 s and then back to Board. In demo mode model calls time out after 30 s with one retry.
- Pane B (optional, tiny): `watch -n 5 'git log --oneline | head -12'`
- The real repo must be untouched: `handover/demo.json` and `inbox/drops/demo-2030.txt` must NOT exist. The drop is ingested once, for good. To rehearse, always copy: `rsync -a --exclude .git ./ /tmp/demo-copy/` and run `./demo.sh` there.
- Stop at the end with Ctrl-C in Terminal A (it stops the loop and the process). A `demo.sh` launched in the background ignores SIGINT; use `kill` on it instead.
- What the judge runs: `kill -9 $(pgrep -f "run.py --demo-drop-at")`. Nobody relaunches.

## Measured
Live check on a fresh copy with `DEMO_DROP_AT=60 DEMO_AUDIT_AT=90`, `kill -9` at T+65 (mid drop processing), one browser page open throughout on `index-v2.html` (now `index.html`):

| Step | Seconds |
|---|---|
| `kill -9` to RESUMED line in the terminal | 0.67 |
| Drop lands (from first boot) | 60.2 |
| Drop lands to the Tom card struck through and Sam's due date on the page (includes the kill and restart) | 20.5 |
| Page switches to Audit by itself | T+90.7 |
| Page back on Board, same page, no reload | T+120.8 |

Three earlier runs (same setup, before the last fixes): kill to RESUMED 0.9 / 0.9 / 0.66 s; drop to visible 23.5 / 26.2 / 20.6 s; audit switch at T+90.5 to 90.8 and back at T+120.6 to 120.9 each time. Without a kill in the middle, drop to visible was about 14 s. Every run: one supersede, one ingest, no duplicate actions or questions, 0 rejections, 0 withheld files, about 5 to 7 model calls, about $0.03 to $0.04.

## Narration
**0:00 (the browser Board is on screen; Terminal A is small in the corner)**
"Four AIs, one per person: Sam, Wei Lin, Dana, Priya. They read a week of calls, email, Slack, Linear, calendar and WhatsApp. Each person has four lists: what's owed, what's waiting on them, what was handed to them, what's done. Every item shows its sources, and the chips open the source text."

**0:20 (point at the Board and the live activity feed)**
"Northwind's price is Sam's. The camera layout is done. The one-pager is Priya's. The Tom call is Dana's. The Crestline double-booking was found from the calendar and handed to Dana. Owners come from a lookup on who owns what, never from a guess."

**0:50 (right rail, then the Done lists)**
"The AIs finish what they can. These emails to Maria, Ken, Raj, Jordan and Lisa were sent by the AI on its own, because they promise nothing new: no price, no time, no money. Sam's price question and the Farah reschedule were not sent: they commit us, so they are questions in the owner's list. The Optix PO is on Sam's Owed list; no question has been filed for it. And this panel logs what the AI caught itself doing wrong: right now zero, nothing has been rejected yet."

**1:20 (the judge kills it; point at the corner terminal, not the pill)**
"Kill it. Look at the terminal: it comes back by itself in under a second with RESUMED and the same counts. No model calls to get there, nothing duplicated. All state is on disk and the git log is the feed."

**1:50 (the drop lands on its own, T+110 s; the pill turns amber: PROCESSING DROP…)**
"A new message just arrived: Maria says Tom can do Friday 30 October at 2pm Dallas and wants the number by then." Wait about 15 to 25 s. Watch the feed: new lines slide in and glow. Point at Dana: "The old Tom-call item strikes through as superseded. There is a new booking with a calendar proposal and a confirmation, held for Dana because booking commits her. And Sam's price question now carries a due date, Friday 30 October, with the drop as its source."

**2:30 to 3:00 (the page shows the audit on its own; nobody touches anything)**
"This is an automated token audit: numbers, dates, dollar amounts and names in outbound text, each matched verbatim against the sources it cites." The page flips itself to the Audit tab at T+150 s and back to Board after 30 s. Point at `$4,680 <- E10` and `2pm <- D-demo-2030-…`, and at the headline "token audit: N checked · 0 unsourced". "If it finds a token with no source, a draft is withheld before it is sent; a file that was already sent is flagged, not recalled." (Optional: `python run.py --audit` prints the same thing.) It checks tokens, not whether a sentence is true.

**3:00**
"Everything a person promised has an owner, a source and a next step, and when the process dies it picks up where it left off without asking anyone."
Stop.

## If something goes wrong
- No supersede after 40 s: look in `handover/run.log` and `handover/judge_cache/`. The drop is retried every tick.
- Pill red "NOT RUNNING": no heartbeat for 60 s; `demo.sh` restarts the process by itself, nothing to type. The pill does not prove a restart happened: check the terminal's RESUMED line.
- If the page shows an old banner: the header is recomputed on every tick, so it can lag by up to one tick (about 20 s).
