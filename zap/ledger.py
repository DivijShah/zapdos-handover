"""Append-only promise ledger. State = replay of handover/*.jsonl. Everything is idempotent."""
import json
import os
from pathlib import Path

from .route import SLOTS, promise_id, route, slot_id, slug

ROOT = Path(__file__).resolve().parent.parent
H = ROOT / "handover"
PROMISES, ACTIONS, QUESTIONS = H / "promises.jsonl", H / "actions.jsonl", H / "questions.jsonl"


def append(path: Path, rec: dict):
    """One fsync'd O_APPEND write; heals a torn last line left by kill -9."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n"
    fd = os.open(path, os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        size = os.fstat(fd).st_size
        if size and os.pread(fd, 1, size - 1) != b"\n":
            line = "\n" + line
        os.write(fd, line.encode())
        os.fsync(fd)
    finally:
        os.close(fd)


def read_jsonl(path: Path) -> list[dict]:
    out = []
    if path.exists():
        for ln in path.read_text().splitlines():
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                pass  # torn write
    return out


def _fold(st: dict, ev: dict):
    op, pid = ev["op"], ev.get("id")
    if op == "create":
        st["promises"][pid] = {k: v for k, v in ev.items() if k != "op"}
    elif op == "ingest":
        st["ingested"].add(ev["source"])
    elif pid in st["promises"]:
        p = st["promises"][pid]
        if op in ("update", "done", "supersede"):
            for s in ev.get("add_sources", []):
                if s not in p["sources"]:
                    p["sources"].append(s)
            for n in ev.get("add_notes", []):
                if n not in p["notes"]:
                    p["notes"].append(n)
            for f in ev.get("add_flags", []):
                if f not in p["flags"]:
                    p["flags"].append(f)
            for k in ("status", "due", "due_at"):
                if k in ev:
                    p[k] = ev[k]
            if op == "done":
                p["status"] = "done"
            if op == "supersede":
                p["status"], p["superseded_by"] = "superseded", ev.get("by")


def materialize() -> dict:
    st = {"promises": {}, "ingested": set(), "n_events": 0}
    for ev in read_jsonl(PROMISES):
        _fold(st, ev)
        st["n_events"] += 1
    return st


def _emit(st: dict, ev: dict):
    append(PROMISES, ev)
    _fold(st, ev)
    st["n_events"] += 1


def stats(st: dict) -> dict:
    c = {"open": 0, "done": 0, "waiting_owner": 0, "superseded": 0}
    for p in st["promises"].values():
        c[p["status"]] = c.get(p["status"], 0) + 1
    qs = read_jsonl(QUESTIONS)
    acts = read_jsonl(ACTIONS)
    c["questions"] = sum(1 for q in qs if not q.get("answered"))
    c["last_action"] = acts[-1] if acts else None
    return c


def _mention_id(m: dict) -> tuple[str, str, str, str]:
    """(promise id, counterparty, kind, label) from canonical enums only."""
    if m["slot"] != "new":
        s = SLOTS[m["slot"]]
        return slot_id(m["slot"]), s["counterparty"], s["kind"], s["label"]
    return (promise_id(m["counterparty"], m["topic"]), slug(m["counterparty"]), m["kind"],
            m.get("deliverable") or f"{m['counterparty']}: {m['topic']}")


def apply_source(st: dict, src, mentions: list[dict]) -> int:
    """Fold one source's mentions into the ledger. Idempotent: re-applying emits nothing new."""
    n0 = st["n_events"]
    for m in mentions:
        pid, cp, kind, label = _mention_id(m)
        p = st["promises"].get(pid)
        note = m.get("note") or ""
        if p is None:
            owner, routed = route(kind, m["slot"])
            _emit(st, dict(op="create", id=pid, slot=m["slot"], deliverable=label, kind=kind, counterparty=cp,
                           owner=owner, due=m.get("due"), due_at=src.at if m.get("due") else None,
                           status="done" if m["state"] == "done" else "open", sources=[src.id],
                           created_from=src.id, notes=[note] if note else [],
                           flags=([f"duplicate:{src.id}"] if m["state"] == "duplicate" else []) +
                                 ([] if routed else ["unrouted"])))
            continue
        d = {}
        if src.id not in p["sources"]:
            d["add_sources"] = [src.id]
        if note and note not in p["notes"] and len(p["notes"]) < 4:
            d["add_notes"] = [note]
        if m["state"] == "duplicate" and f"duplicate:{src.id}" not in p["flags"]:
            d["add_flags"] = [f"duplicate:{src.id}"]
        if m["state"] == "done" and p["status"] != "done":
            d["status"] = "done"
        if m["state"] == "superseded" and p["status"] != "superseded":
            d["status"] = "superseded"
        if m.get("due") and m["due"] != p["due"] and src.at >= (p.get("due_at") or ""):
            d["due"], d["due_at"] = m["due"], src.at
        if d:
            _emit(st, dict(op="update", id=pid, **d))
    return st["n_events"] - n0


def apply_clashes(st: dict, clashes: list[dict]) -> int:
    n0 = st["n_events"]
    for c in clashes:
        p = st["promises"].get(c["id"])
        if p is None:
            owner, _ = route("booking", c["slot"])
            _emit(st, dict(op="create", id=c["id"], slot=c["slot"] or "new", deliverable=c["deliverable"],
                           kind="booking", counterparty="internal", owner=owner, due=c["due"], due_at=None,
                           status="open", sources=list(c["sources"]), created_from="calendar-clash",
                           notes=[f"Overlapping calendar events for {', '.join(c['who'])}"], flags=["clash"]))
        else:
            add = [s for s in c["sources"] if s not in p["sources"]]
            fl = [] if "clash" in p["flags"] else ["clash"]
            if add or fl:
                _emit(st, dict(op="update", id=c["id"], add_sources=add, add_flags=fl))
    return st["n_events"] - n0


def mark_ingested(st: dict, source_id: str):
    if source_id not in st["ingested"]:
        _emit(st, dict(op="ingest", source=source_id))


# ---- actions / questions / dependency helpers (persona layer) ----
def action_keys() -> set[str]:
    return {a["key"] for a in read_jsonl(ACTIONS)}


def record_action(promise_id: str, persona: str, atype: str, path: str | None, at: str, **extra) -> bool:
    """Append an action once per key f"{promise_id}:{atype}". Returns False if it already existed."""
    key = f"{promise_id}:{atype}"
    if key in action_keys():
        return False
    append(ACTIONS, dict(key=key, promise_id=promise_id, persona=persona, type=atype, path=path, at=at, **extra))
    return True


def set_status(st: dict, pid: str, status: str, note: str | None = None):
    p = st["promises"][pid]
    d = {}
    if p["status"] != status:
        d["status"] = status
    if note and note not in p["notes"]:
        d["add_notes"] = [note]
    if d:
        _emit(st, dict(op="update", id=pid, **d))


def add_question(st: dict, pid: str, to: str, frm: str, qkey: str, question: str, at: str) -> bool:
    """Question for an owner persona. Idempotent on (promise, to, qkey); also posted as a DM record."""
    import hashlib
    qid = hashlib.sha1(f"{pid}|{to}|{qkey}".encode()).hexdigest()[:10]
    if any(q["id"] == qid for q in read_jsonl(QUESTIONS)):
        return False
    append(QUESTIONS, dict(id=qid, promise_id=pid, to=to, **{"from": frm}, question=question, at=at, answered=False))
    append(H / "slack.jsonl", dict(channel=f"dm:ai-{to}", user=f"ai-{frm}", at=at, text=question, key=qid))
    return True


def ensure_slot(st: dict, slot: str, src_ids: list[str], at: str, note: str) -> str:
    """Create the dependency promise for a catalog slot if missing (idempotent). Returns its id."""
    pid = slot_id(slot)
    if pid not in st["promises"]:
        s = SLOTS[slot]
        owner, _ = route(s["kind"], slot)
        _emit(st, dict(op="create", id=pid, slot=slot, deliverable=s["label"], kind=s["kind"],
                       counterparty=s["counterparty"], owner=owner, due=None, due_at=None, status="open",
                       sources=list(src_ids), created_from="dependency", notes=[note], flags=["dependency"]))
    return pid
