# Demo: The 24/7 Handover (3 minutes, zero keyboard)

Nobody types during the demo. A judge kills the process, `demo.sh` brings it back, and the prepared drop lands by itself.

## Setup (before 20:30)
- Pane A: `cd /Users/divij/PersonalProjects/hackday && ./demo.sh` (loops `run.py`; `DEMO_DROP_AT` seconds after the FIRST boot, default 110, the prepared drop is copied into `inbox/drops/`).
- Pane B: `cd /Users/divij/PersonalProjects/hackday && watch -n 5 'git log --oneline | head -12'`
- Browser: `open index.html` (file://, refreshes every 3 s, Board and Audit tabs), full screen at 1080p.
- Pane C (empty prompt, used at 2:20): `cd /Users/divij/PersonalProjects/hackday`
- The real repo must be untouched: `handover/demo.json` and `inbox/drops/demo-2030.txt` must NOT exist. The drop is ingested once, for good. To rehearse, always copy: `rsync -a --exclude .git ./ /tmp/demo-copy/` and run `./demo.sh` there.
- Stop at the end with Ctrl-C in pane A (it stops the loop and the process).
- What the judge runs: `kill -9 $(pgrep -f "run.py --demo-drop-at")`. Nobody relaunches.

## Measured (two rehearsals on fresh copies, cold caches, `demo.sh`, kill at T+80 s; seconds)
| Step | Rehearsal 1 | Rehearsal 2 |
|---|---|---|
| Launch to RESUMED banner | 0.84 | 0.84 |
| `kill -9` to RESUMED again (no one relaunches) | 0.71 | 0.68 |
| Drop lands, from first boot | 111.2 | 111.2 |
| Drop lands to "ingested drop" | 12.1 | 12.3 |
| Drop lands to supersede line, `.ics` and confirmation draft, and the page showing them | 13.7 to 13.8 | 13.9 |
| `python run.py --audit` | 0.4 | 0.4 |
Both rehearsals: no duplicate actions, questions or Slack records after the kill, exactly one `demo:drop` key, 7 LLM calls, about $0.04. The audit line in those runs read "1 unsourced" because of a bug in the audit (it read a drop id as a name); it is fixed and a re-run on a copy ended "129 facts checked · 0 unsourced". The fix and the rest of the hands-off path were re-checked once in a copy (kill, automatic restart, drop, audit), not stopwatch-timed again.

## Narration
**0:00 (pane A and the Board are already up)**
"Four AIs, one per person: Sam, Wei Lin, Dana, Priya. They read a week of calls, email, Slack, Linear, calendar and WhatsApp. Each person has four lists: what's owed, what's waiting on them, what was handed to them, what's done. Every item names its sources."

**0:20 (point at the Board)**
"Northwind's price is Sam's. The camera layout is done. The one-pager is Priya's. The Tom call is Dana's. The Crestline double-booking was found from the calendar and handed to Dana. Owners come from a lookup on who owns what, never from a guess."

**0:50 (right rail, then pane A)**
"The AIs finish what they can. These emails to Maria, Ken, Raj, Jordan and Lisa were sent by the AI on its own, because they promise nothing new: no price, no time, no money. Sam's price, the Optix PO and the Farah reschedule were not sent. They commit us, so they are questions in the owner's list. And this panel is where the AI logs what it caught itself doing wrong. Right now: zero, nothing has been rejected yet."

**1:20 (the judge kills it; say nothing until the banner is back)**
"Kill it. It comes back by itself in under a second: RESUMED, same counts, nothing re-read, nothing duplicated. All state is on disk and the git log is the feed."

**1:50 (the drop lands on its own, T+110 s)**
"A new message just arrived: Maria says Tom can do Friday 30 October at 2pm Dallas and wants the number by then." Wait about 14 s. Point at Dana: "The old Tom-call item is struck through as superseded. There is a new booking with a calendar proposal and a confirmation, held for Dana because booking commits her. And Sam's price question now carries a due date, Friday 30 October, with the drop as its source."

**2:20 to 2:50 (pane C: `python run.py --audit`)**
"Every number, date, dollar amount and name in everything the AI wrote, with the source line it came from." Let it scroll; point at `$4,680 <- E10` and `2pm <- D-demo-2030-…`. The last line reads "N facts checked · 0 unsourced". "If it ever can't find one, that line says so."

**2:50**
"Everything a person promised has an owner, a source and a next step, and when the process dies it picks up where it left off without asking anyone."
Stop.

## If something goes wrong
- No supersede after 30 s: look in `handover/run.log` and `handover/judge_cache/`. The drop is retried every tick.
- Page header turns red "NOT RUNNING": the heartbeat is older than 45 s; `demo.sh` restarts the process by itself, nothing to type.
- `kill -INT` sent only to `demo.sh` does not stop it (the shell waits for python); Ctrl-C in the pane does.
