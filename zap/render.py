"""Ledger -> HANDOVER-<persona>.md (per-persona shift notes) + TV-sized rich status table."""
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

from rich import box
from rich.table import Table
from rich.text import Text

from . import ledger
from .route import SLOTS, team

MAX_ROWS = 22
STATUS_STYLE = {"open": "yellow", "waiting_owner": "magenta", "done": "green", "superseded": "dim"}


def _due_label(due: str | None) -> str:
    return datetime.fromisoformat(due).strftime("%a %d %b") if due else "-"


def _overdue(p: dict, now: datetime) -> bool:
    return bool(p["due"]) and p["status"] in ("open", "waiting_owner") and \
        date.fromisoformat(p["due"]) < now.astimezone(ZoneInfo("America/Chicago")).date()


def _sorted(st: dict, now: datetime) -> list[dict]:
    def key(p):
        live = p["status"] in ("open", "waiting_owner")
        prio = SLOTS.get(p["slot"], {}).get("prio", 99)
        return (not live, not _overdue(p, now), p["due"] or "9999", prio, p["id"])
    return sorted(st["promises"].values(), key=key)


def _write_if_changed(path, text: str) -> bool:
    if path.exists() and path.read_text() == text:
        return False
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return True


def render_handovers(st: dict, now: datetime) -> bool:
    qs = ledger.read_jsonl(ledger.QUESTIONS)
    changed = False
    for who in team():
        pid_, tz = who["id"], ZoneInfo(who["tz"])
        mine = [p for p in _sorted(st, now) if p["owner"] == pid_]
        live = [p for p in mine if p["status"] in ("open", "waiting_owner")]
        lines = [f"# Handover: {who['name']} ({pid_})",
                 f"_AI shift note, written by the Zapdemo AI for {who['name']}. "
                 f"Clock: {now.astimezone(tz).strftime('%a %d %b %Y %H:%M %Z')}._", "",
                 f"Open: {len(live)} · Done: {sum(p['status'] == 'done' for p in mine)}", "", "## Open"]
        for p in live:
            flag = " **OVERDUE**" if _overdue(p, now) else ""
            lines.append(f"- **{p['deliverable']}**{flag} · due {_due_label(p['due'])} · {p['status']} "
                         f"· sources: {', '.join(p['sources'])}")
            lines += [f"  - {n}" for n in p["notes"]]
            lines += [f"  - flag: {f}" for f in p["flags"]]
        mq = [q for q in qs if q.get("to") == pid_ and not q.get("answered")]
        lines += ["", "## Questions for you"] + ([f"- {q['question']} (re {q['promise_id']})" for q in mq] or ["- none"])
        lines += ["", "## Done"] + ([f"- {p['deliverable']} · sources: {', '.join(p['sources'])}"
                                     for p in mine if p["status"] == "done"] or ["- none"])
        changed |= _write_if_changed(ledger.H / f"HANDOVER-{pid_}.md", "\n".join(lines) + "\n")
    return changed


def status_table(st: dict, now: datetime) -> Table:
    rows = _sorted(st, now)
    live = [p for p in rows if p["status"] in ("open", "waiting_owner")]
    shown = rows[:MAX_ROWS]
    t = Table(box=box.SIMPLE_HEAD, pad_edge=False, expand=False,
              title=f"Promises · {len(live)} open / {len(rows)} total · {now.strftime('%a %d %b %H:%M %Z')}")
    for c, kw in (("Owner", {}), ("Promise", {"max_width": 58, "overflow": "ellipsis", "no_wrap": True}),
                  ("Due", {}), ("Status", {}), ("Sources", {"max_width": 26, "overflow": "ellipsis", "no_wrap": True})):
        t.add_column(c, **kw)
    for p in shown:
        status = Text(p["status"], style=STATUS_STYLE.get(p["status"], ""))
        due = Text(_due_label(p["due"]), style="bold red" if _overdue(p, now) else "")
        mark = " [dup]" if any(f.startswith("duplicate") for f in p["flags"]) else ""
        t.add_row(p["owner"], p["deliverable"] + mark, due, status, ",".join(p["sources"]))
    if len(rows) > len(shown):
        t.caption = f"+{len(rows) - len(shown)} more (see handover/HANDOVER-*.md)"
    return t
