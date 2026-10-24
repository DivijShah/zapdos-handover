"""HANDOVER-<persona>.md: the human-readable shift note. Deterministic (clock = NOW), write-if-changed."""
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from . import ledger
from .render import LIVE, _due_label, _overdue, _sorted
from .route import team


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


def _attending(who_id: str, tz: ZoneInfo) -> list[str]:
    evs = json.loads((ledger.H / "calendar.json").read_text())
    mine = sorted((e for e in evs if who_id in e["attendees"]), key=lambda e: datetime.fromisoformat(e["start"]))
    out = []
    for e in mine:
        s, f = datetime.fromisoformat(e["start"]), datetime.fromisoformat(e["end"])
        clash = [o["title"] for o in mine if o is not e and datetime.fromisoformat(o["start"]) < f
                 and s < datetime.fromisoformat(o["end"])]
        out.append(f"- {e['title']} · {s.strftime('%a %d %b %H:%M')}-{f.strftime('%H:%M')} {s.tzname() or ''}".rstrip()
                   + (f" · **CLASH with {', '.join(clash)}**" if clash else ""))
    return out


def render_handovers(st: dict, now: datetime) -> bool:
    qs = ledger.read_jsonl(ledger.QUESTIONS)
    acts_ = ledger.read_jsonl(ledger.ACTIONS)
    changed = False
    for who in team():
        me, tz = who["id"], ZoneInfo(who["tz"])
        mine = [p for p in _sorted(st, now) if p["owner"] == me]
        live = [p for p in mine if p["status"] in LIVE]
        arts = {}
        for a in acts_:
            if a.get("path") and a["persona"] == me:
                arts.setdefault(a["promise_id"], []).append(a["path"])
        lines = [f"# Handover: {who['name']} ({me})",
                 f"_AI shift note, written by the Zapdemo AI for {who['name']}. "
                 f"Clock: {now.astimezone(tz).strftime('%a %d %b %Y %H:%M %Z')}._", "",
                 f"Open: {len(live)} · Done: {sum(p['status'] == 'done' for p in mine)}", ""]
        mq = [q for q in qs if q.get("to") == me and not q.get("answered")]
        lines += ["## Questions for you"] + ([f"- {q['question']} _(from {q['from']}'s AI; re {q['promise_id']})_" for q in mq]
                                             or ["- none"]) + [""]
        hu = [a for a in acts_ if a["type"].startswith("inform-") and a.get("to") == me]
        lines += ["## Heads-up"] + ([f"- {a['text']} _(sources: {', '.join(a.get('cite', []))})_" for a in hu] or ["- none"]) + [""]
        att = _attending(me, tz)
        lines += ["## Calendar you attend"] + (att or ["- none"]) + [""]
        lines += ["## Open"]
        for p in live:
            flag = " **OVERDUE**" if _overdue(p, now) else ""
            lines.append(f"- **{p['deliverable']}**{flag} · due {_due_label(p['due'])} · {p['status']} "
                         f"· sources: {', '.join(p['sources'])}")
            lines += [f"  - {n}" for n in p["notes"]]
            lines += [f"  - flag: {f}" for f in p["flags"]]
            if p.get("supersedes"):
                lines.append(f"  - **supersedes** the earlier version ({p['supersedes']}) per {p['created_from']}: \"{p['new_fact']}\"")
            lines += [f"  - artifact: `{a}`" for a in arts.get(p["id"], [])]
        done = []
        for p in mine:
            if p["status"] == "done":
                done.append(f"- {p['deliverable']} · sources: {', '.join(p['sources'])}"
                            + (f" · {', '.join(arts[p['id']])}" if p["id"] in arts else ""))
                done += [f"  - {n}" for n in p["notes"]]
        lines += ["", "## Done"] + (done or ["- none"])
        sup = []
        for p in mine:
            if p["status"] == "superseded":
                new = st["promises"].get(p.get("superseded_by"))
                stale = [a["path"] for a in acts_ if a["promise_id"] == p["id"] and (a.get("path") or "").startswith("outbox/")]
                sup.append(f"- ~~{p['deliverable']}~~ · **superseded by** {new['deliverable'] if new else p.get('superseded_by')} "
                           f"({new['created_from'] if new else '?'}): \"{new['new_fact'] if new else ''}\""
                           + (f" · stale artifacts: {', '.join(stale)}" if stale else ""))
        lines += ["", "## Superseded"] + (sup or ["- none"])
        changed |= _write_if_changed(ledger.H / f"HANDOVER-{me}.md", "\n".join(lines) + "\n")
    return changed
