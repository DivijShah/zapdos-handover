"""Export for index.html: handover/site.js (deterministic, git-tracked) + handover/heartbeat.js (wall-clock, gitignored).
index.html is read-only and loads these with <script src>, so it opens from file:// with no server."""
import json
import os
import time
from datetime import datetime

from . import acts, audit, extract, ledger
from .render import LIVE, _due_label, _overdue, _sorted
from .route import team


VERB = {"email": "drafted", "send": "sent", "brief": "wrote brief", "doc": "wrote document", "ics": "drafted calendar proposal",
        "dependency": "handed off dependency", "slack-handover": "posted handover to #sales"}


def slug(path: str | None, fallback: str) -> str:
    import re
    m = re.match(r"^\d{8}-\d{4}-[a-z]+-(.+?)\.(?:md|ics)$", (path or "").rsplit("/", 1)[-1])
    return m.group(1) if m else (path.rsplit("/", 1)[-1] if path else fallback)


def describe(a: dict, st: dict) -> tuple[str, str, list[str]]:
    """(persona, one-line text, cited source ids) for an action record. Used by the terminal narration and the page's live feed."""
    t, p = a["type"], st["promises"].get(a["promise_id"], {})
    cites = list((a.get("cite") or p.get("sources") or [])[:3])
    if t == "drop":
        return "system", "drop landed: " + (a.get("path") or "").rsplit("/", 1)[-1], []
    if t == "audit":
        return "system", "audit tab on screen", []
    if t.startswith("inform-"):
        return a["persona"], f"told {a.get('to')}: heads-up", cites
    if t.startswith("linear-"):
        return a["persona"], f"updated Linear {t.split('linear-note-')[-1].split('linear-')[-1]}", cites
    return a["persona"], f"{VERB.get(t, t)} {slug(a.get('path'), p.get('deliverable', ''))[:48]}", cites


def _feed(st: dict, acts_: list, qs: list, rej: list) -> list[dict]:
    items = []
    for a in acts_:
        who, text, cites = describe(a, st)
        items.append((a.get("ts") or "", who, "sent" if a["type"] == "send" else "act", text, cites, "a:" + a["key"]))
    for q in qs:
        p = st["promises"].get(q.get("promise_id"), {})
        items.append((q.get("ts") or "", q["from"], "asked", f"asked {q['to']}: {q['question'][:84]}" + (" → answered" if q.get("answered") else ""), list(p.get("sources", []))[:3], "q:" + q["id"]))
    for ev in ledger.read_jsonl(ledger.PROMISES):
        if ev["op"] == "supersede":
            old = st["promises"].get(ev["id"], {})
            items.append((ev.get("ts") or "", old.get("owner", "system"), "sup", f"superseded: {old.get('deliverable', ev['id'])[:70]}",
                          [ev.get("source")] if ev.get("source") else [], "s:" + ev["id"] + str(ev.get("by"))))
        elif ev["op"] == "ingest" and str(ev.get("source", "")).startswith("D-"):
            items.append((ev.get("ts") or "", "system", "drop", "ingested a new drop", [ev["source"]], "i:" + ev["source"]))
    for r in rej:
        items.append((r.get("ts") or "", r["persona"], "caught", "caught itself: " + r["reason"][:90], [], "r:" + r["key"]))
    order = sorted(range(len(items)), key=lambda i: (items[i][0], i))
    out = []
    for i in order[-18:][::-1]:
        ts, who, kind, text, cites, key = items[i]
        out.append({"key": key, "time": ts[11:19], "persona": who, "kind": kind, "text": text, "cites": cites})
    return out


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
                        "sources": g("Sources"), "path": f"outbox/{'sent/' if sent else ''}{f.name}"})
    out.sort(key=lambda o: (o["file"].split("/")[-1][:13], o["mtime"]), reverse=True)
    for o in out:
        o.pop("mtime")
    return out


def footer_text(st: dict, n_sources: int, boot: float | None, since: float | None = None) -> str:
    u = extract.usage_totals(since)
    sent = sum(a["type"] == "send" for a in ledger.read_jsonl(ledger.ACTIONS))
    up = int(time.time() - boot) if boot else 0
    return (f"{n_sources} sources · {len(st['promises'])} promises · {sent} sent · {len(ledger.questions())} asked · "
            f"this session: {u['calls']} calls · ${u['cost']:.2f} · up {up // 3600}h{up % 3600 // 60:02d}m{up % 60:02d}s")


def write_heartbeat(banner, last_tick, boot, since, demo, processing) -> None:
    """handover/heartbeat.js (wall-clock, gitignored). `processing`="drop" while a drop is being ingested: the page shows it."""
    u = extract.usage_totals(since)
    hb = {"tick_at": time.strftime("%H:%M:%S"), "banner": banner, "last_tick": last_tick, "boot": boot, "demo": demo,
          "processing": processing, "llm": {"calls": u["calls"], "tokens": u["in"] + u["out"], "cost": u["cost"]}}
    _w(ledger.H / "heartbeat.js", "window.HEARTBEAT = " + json.dumps(hb, ensure_ascii=False) + ";\n")


def write_sources(srcmap: dict | None) -> None:
    """handover/sources/<id>.txt: the verbatim source record behind every citation chip (write-if-changed)."""
    if not srcmap:
        return
    d = ledger.H / "sources"
    d.mkdir(exist_ok=True)
    for sid, s in srcmap.items():
        _w(d / f"{sid}.txt", f"[{sid} · {s.kind} · {s.at}]\n\n{s.text}\n")


def export(st: dict, now: datetime, banner: str | None = None, last_tick: dict | None = None, srcmap: dict | None = None,
           boot: float | None = None, since: float | None = None, demo: dict | None = None) -> bool:
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
                    "overdue": bool(st["promises"].get(q["promise_id"])) and _overdue({**st["promises"][q["promise_id"]], "status": "open"}, now),
                    "due_src": st["promises"].get(q["promise_id"], {}).get("due_src")}
                   for q in qs if q.get("to") == me and not q.get("answered")]
        # questions on promises a drop just touched (new due date, supersede) go first: they are what changed
        touched = lambda w: bool((st["promises"].get(w["re"]) or {}).get("supersedes")) or str((st["promises"].get(w["re"]) or {}).get("due_src", "")).startswith(("D-", "T-"))  # noqa: E731
        waiting.sort(key=lambda w: not touched(w))
        handed = [{"text": a["text"], "cite": a.get("cite", []), "from": a["persona"]}
                  for a in acts_ if a["type"].startswith("inform-") and a.get("to") == me]
        handed += [item(p, handed="dependency") for p in mine if "dependency" in p["flags"] and p["status"] in LIVE]
        sent_pids = {a["promise_id"] for a in acts_ if a["type"] == "send"}
        done = [item(p) for p in mine if p["status"] == "done" and p["id"] not in sent_pids]
        done += [{"id": a["key"], "title": f"SENT: {a.get('subject', '')}", "due": "", "overdue": False, "status": "sent",
                  "sources": a.get("cite", [])[:7], "notes": [f"→ {a.get('to', '')}  ·  {a['path']}"], "flags": [], "path": a["path"]}
                 for a in acts_ if a["type"] == "send" and a["persona"] == me]
        sup = [{"id": p["id"], "title": p["deliverable"], "sources": p["sources"][:3],
                "by": (st["promises"].get(p.get("superseded_by")) or {}).get("created_from"),
                "fact": (st["promises"].get(p.get("superseded_by")) or {}).get("new_fact")}
               for p in mine if p["status"] == "superseded"]
        people.append({"id": me, "name": who["name"], "role": who["role"], "owed": owed, "waiting": waiting,
                       "handed": handed, "done": done, "superseded": sup, "asked": len(asked)})
    au = audit.run(srcmap, st) if srcmap else {"groups": [], "checked": 0, "unsourced": 0, "uncited": 0}
    rej = ledger.read_jsonl(ledger.REJECTED)
    sent_n = sum(a["type"] == "send" for a in acts_)
    site = {"feed": _feed(st, acts_, qs, rej), "audit": au, "rejected": rej[-14:][::-1], "rejected_total": len(rej),
            "footer": {"sources": len([s for s in (srcmap or {}).values() if s.kind != "team"]), "promises": len(st["promises"]), "sent": sent_n, "asked": len(qs)},
            "stats": {k: v for k, v in s.items() if k != "last_action"},
            "last_action": s["last_action"] and {k: s["last_action"].get(k) for k in ("type", "persona", "at", "path")},
            "clock": now.isoformat(), "people": people, "outbox": _outbox()[:24],
            "questions": [{"to": q["to"], "from": q["from"], "text": q["question"]} for q in qs if not q.get("answered")]}
    ch = _w(ledger.H / "site.js", "window.SITE = " + json.dumps(site, ensure_ascii=False, indent=1) + ";\n")
    write_heartbeat(banner, last_tick, boot, since, demo, None)
    write_sources(srcmap)
    return ch
