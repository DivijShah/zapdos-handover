"""Export for index.html: handover/site.js (deterministic, git-tracked) + handover/heartbeat.js (wall-clock, gitignored).
index.html is read-only and loads these with <script src>, so it opens from file:// with no server."""
import json
import os
import time
from datetime import datetime

from . import acts, ledger
from .render import LIVE, _due_label, _overdue, _sorted
from .route import team


def _w(path, text: str) -> bool:
    if path.exists() and path.read_text() == text:
        return False
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return True


def _outbox() -> list[dict]:
    out = []
    for d, sent in ((ledger.ROOT / "outbox", False), (ledger.ROOT / "outbox" / "sent", True)):
        if not d.exists():
            continue
        for f in d.iterdir():
            if not f.is_file() or f.suffix == ".tmp":
                continue
            head = f.read_text().splitlines()[:8]
            g = lambda k: next((ln.split(": ", 1)[1] for ln in head if ln.startswith(k + ": ")), "")  # noqa: E731
            out.append({"file": f"outbox/{'sent/' if sent else ''}{f.name}", "sent": sent, "kind": f.suffix[1:],
                        "to": g("To"), "subject": g("Subject") or f.stem.split("-", 3)[-1], "mtime": f.stat().st_mtime,
                        "sources": g("Sources")})
    out.sort(key=lambda o: (o["file"].split("/")[-1][:13], o["mtime"]), reverse=True)
    for o in out:
        o.pop("mtime")
    return out


def export(st: dict, now: datetime, banner: str | None = None, last_tick: dict | None = None) -> bool:
    qs = ledger.questions()
    acts_ = ledger.read_jsonl(ledger.ACTIONS)
    s = ledger.stats(st)
    item = lambda p, **k: {"id": p["id"], "title": p["deliverable"], "due": _due_label(p["due"]) if p["due"] else "",  # noqa: E731
                          "overdue": _overdue(p, now), "status": p["status"], "sources": p["sources"][:7],
                          "notes": p["notes"][-1:], "flags": [f for f in p["flags"] if not f.startswith("duplicate")], **k}
    people = []
    for who in team():
        me = who["id"]
        mine = [p for p in _sorted(st, now) if p["owner"] == me]
        asked = {q["promise_id"] for q in qs if q.get("to") == me and not q.get("answered")}
        owed = [item(p, updated=bool(p.get("supersedes")), new_fact=p.get("new_fact"), due_src=p.get("due_src"))
                for p in mine if p["status"] in ("open", "in_progress")]
        waiting = [{"id": q["id"], "text": q["question"], "from": q["from"], "re": q["promise_id"],
                    "due": _due_label(st["promises"][q["promise_id"]]["due"]) if st["promises"].get(q["promise_id"], {}).get("due") else "",
                    "due_src": st["promises"].get(q["promise_id"], {}).get("due_src")}
                   for q in qs if q.get("to") == me and not q.get("answered")]
        handed = [{"text": a["text"], "cite": a.get("cite", []), "from": a["persona"]}
                  for a in acts_ if a["type"].startswith("inform-") and a.get("to") == me]
        handed += [item(p, handed="dependency") for p in mine if "dependency" in p["flags"] and p["status"] in LIVE]
        sent_pids = {a["promise_id"] for a in acts_ if a["type"] == "send"}
        done = [item(p) for p in mine if p["status"] == "done" and p["id"] not in sent_pids]
        done += [{"id": a["key"], "title": f"SENT: {a.get('subject', '')}", "due": "", "overdue": False, "status": "sent",
                  "sources": a.get("cite", [])[:7], "notes": [f"→ {a.get('to', '')}  ·  {a['path']}"], "flags": []}
                 for a in acts_ if a["type"] == "send" and a["persona"] == me]
        sup = [{"id": p["id"], "title": p["deliverable"], "sources": p["sources"][:3],
                "by": (st["promises"].get(p.get("superseded_by")) or {}).get("created_from"),
                "fact": (st["promises"].get(p.get("superseded_by")) or {}).get("new_fact")}
               for p in mine if p["status"] == "superseded"]
        people.append({"id": me, "name": who["name"], "role": who["role"], "owed": owed, "waiting": waiting,
                       "handed": handed, "done": done, "superseded": sup, "asked": len(asked)})
    site = {"stats": {k: v for k, v in s.items() if k != "last_action"},
            "last_action": s["last_action"] and {k: s["last_action"].get(k) for k in ("type", "persona", "at", "path")},
            "clock": now.isoformat(), "people": people, "outbox": _outbox()[:24],
            "questions": [{"to": q["to"], "from": q["from"], "text": q["question"]} for q in qs if not q.get("answered")]}
    ch = _w(ledger.H / "site.js", "window.SITE = " + json.dumps(site, ensure_ascii=False, indent=1) + ";\n")
    hb = {"tick_at": time.strftime("%H:%M:%S"), "banner": banner, "last_tick": last_tick}
    _w(ledger.H / "heartbeat.js", "window.HEARTBEAT = " + json.dumps(hb, ensure_ascii=False) + ";\n")
    return ch
