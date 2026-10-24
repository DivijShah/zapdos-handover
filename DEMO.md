# Demo: The 24/7 Handover (3 minutes, hands off)

Timings below are measured in two stopwatch rehearsals on fresh copies with cold caches (real LLM latency).

## Setup (before 20:30)
- Terminal A (left): `cd /Users/divij/PersonalProjects/hackday && .venv/bin/python run.py`
- Terminal B (right): `cd /Users/divij/PersonalProjects/hackday && watch -n 5 'git log --oneline | head -12'`
- Browser: `open index.html` (file://, refreshes every 10 s), full screen at 1080p.
- `inbox/drops/` must be empty. Do NOT run `make demo-drop` before the demo: a dropped file is ingested once, for good. To re-run the demo, rehearse in a copy: `rsync -a --exclude .git ./ /tmp/demo-copy/` and run there.
- Kill command, ready to paste: `kill -9 $(pgrep -f "python run.py")`

## Measured timings (seconds)
| Step | Rehearsal 1 | Rehearsal 2 |
|---|---|---|
| Boot to RESUMED banner | 0.71 | 0.69 |
| `kill -9`, relaunch, RESUMED banner | 0.35 | 0.35 |
| Drop lands to drop file normalised | 3.2 | 2.3 |
| Drop lands to supersede in the ledger | 13.4 | 11.8 |
| Drop lands to everything visible in index.html (supersede, price due Fri 30 Oct, .ics, confirmation draft) | 16.7 | 13.8 |
Both rehearsals: zero duplicate actions, questions or outbox files after the kill, SIGTERM exits 0.

## Narration
**0:00 (A and the browser are already up)**
"Four AIs, one per person: Sam, Wei Lin, Dana, Priya. They have read a week of calls, email, Slack, Linear, calendar and WhatsApp. This table is what the team owes, to whom, by when. Every row has an owner picked by a lookup on who owns what, and every row cites its source."

**0:20 (point at the columns in the browser)**
"Each person has four lists: owed, waiting on me, handed to me, done. Northwind's price is Sam's. The camera layout is done. The one-pager is Priya's. The Tom call is Dana's. The Crestline double-booking was found from the calendar and handed to Dana."

**0:50 (right rail and `outbox/sent/`)**
"The AIs finish what they can. Maria's holding reply, Ken's IP acknowledgement, Raj, Jordan and Lisa have already been sent: those drafts promise nothing new, no price, no time, no money. Sam's price, the Optix PO and the Farah reschedule are not sent: they commit us, so they are questions to the owner, in that person's list."

**1:20 (paste the kill command in A, then relaunch with up-arrow)**
"I kill it with kill -9. Relaunch. It prints RESUMED with the same counts in under a second. Nothing re-read, no model call, no duplicate drafts. All state is on disk and the git log is the feed."

**1:50 (in A's directory, or a third pane: `make demo-drop`)**
"A new message arrives: Maria says Tom can do Friday 30 October at 2pm Dallas, and asks for the number by then." Keep talking while it works; allow 15 to 20 s.
"Dana's old Tom-call item is struck through as superseded. There is a new booking with a calendar proposal and a confirmation draft, held for Dana because booking commits her. And Sam's price question now has a due date, Friday 30 October, citing the drop."

**2:30**
"Everything a person promised has an owner, a source and a next step, and when the process dies it picks up where it left off without asking anyone."
Stop.

## If something goes wrong
- No supersede after 30 s: check `handover/judge_cache/` for the verdict file and the Terminal A log line `extract failed`. It retries every tick.
- Browser shows a red "NOT RUNNING": the heartbeat is more than 60 s old; relaunch run.py.
