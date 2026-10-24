"""Source -> promise mentions via claude-sonnet-5-5. Cached per source_id; never re-run for a cached source."""
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import anthropic

from .route import KINDS, SLOTS
from .sources import Source

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "handover" / "extract_cache"
MODEL, FALLBACK = "claude-sonnet-5-5", "claude-haiku-5-5"
STATES = ["open", "done", "duplicate", "superseded"]

CATALOG = "\n".join(f"- {k}: {v['desc']}" for k, v in SLOTS.items())
SYSTEM = f"""You extract commitments for Zapdemo Labs (4 people: Sam founder, Wei Lin engineer, Dana sales caller, Priya content).
Read ONE source and report every deliverable it mentions that Zapdemo owes (or must act on). You MUST answer by calling the record_mentions tool (empty list if none).

For each mention pick a `slot` from this fixed catalog. Use "new" only if nothing fits; then also give kind, counterparty (short name) and topic (2-3 word slug).
{CATALOG}

`state` of the deliverable according to THIS source:
- open: still owed / unresolved / asked-for / promised.
- done: this source shows it was completed, delivered, received or booked (per the slot description).
- duplicate: a ticket that merely duplicates another item.
- superseded: this source withdraws or replaces an earlier fact or request.

Rules:
- Nothing made up. Only what the source says. `due` = ISO date (YYYY-MM-DD) ONLY if that exact calendar date (day and month) is written in the source; never resolve a bare weekday or "before the weekend" yourself; otherwise null.
- `evidence` = a short VERBATIM quote (<= 160 chars) from the source supporting the mention.
- `note` = one short factual sentence from the source (<= 120 chars), or "".
- Newsletters, recovery notices, travel/out-of-office, stand-ups and other pure information produce NO mentions (empty list).
- One mention per slot per source."""

TOOL = {
    "name": "record_mentions",
    "description": "Record the commitments found in the source (empty list if none).",
    "input_schema": {
        "type": "object",
        "properties": {"mentions": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "slot": {"type": "string", "enum": list(SLOTS) + ["new"]},
                "state": {"type": "string", "enum": STATES},
                "due": {"type": ["string", "null"]},
                "evidence": {"type": "string"},
                "note": {"type": "string"},
                "kind": {"type": "string", "enum": KINDS},
                "counterparty": {"type": "string"},
                "topic": {"type": "string"},
                "deliverable": {"type": "string"},
            },
            "required": ["slot", "state", "due", "evidence", "note"],
        }}},
        "required": ["mentions"],
    },
}

_client = None
USAGE = ROOT / "handover" / "llm_usage.jsonl"
# first-party list price, $ per million tokens (input, output); prompts <= 100K tokens
PRICE = {"claude-sonnet-5-5": (2.00, 10.00), "claude-haiku-5-5": (0.10, 0.50)}


def client():
    global _client
    if _client is None:
        demo = bool(os.environ.get("ZAP_DEMO"))  # demo mode: fail fast (30 s, 1 retry) so the room never watches a stalled call
        _client = anthropic.Anthropic(max_retries=1 if demo else 5, timeout=30 if demo else 90)
    return _client


def create(purpose: str, **kw):
    """messages.create + one usage line (real SDK token counts) in handover/llm_usage.jsonl (gitignored)."""
    r = client().messages.create(**kw)
    u = r.usage
    line = json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "model": kw["model"], "purpose": purpose,
                       "in": u.input_tokens, "out": u.output_tokens,
                       "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
                       "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0}) + "\n"
    USAGE.parent.mkdir(exist_ok=True)
    fd = os.open(USAGE, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, line.encode())  # one small O_APPEND write: atomic across the extract threads
    finally:
        os.close(fd)
    return r


def usage_totals(since: float | None = None) -> dict:
    """Totals from the usage log; `since` (epoch seconds) limits it to the current session."""
    calls = tin = tout = 0
    cost = 0.0
    if USAGE.exists():
        for ln in USAGE.read_text().splitlines():
            try:
                u = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if since and datetime.fromisoformat(u["at"]).timestamp() < since:
                continue
            pi, po = PRICE.get(u["model"], (0, 0))
            calls += 1
            tin += u["in"] + u.get("cache_read", 0) + u.get("cache_write", 0)
            tout += u["out"]
            cost += (u["in"] * pi + u["out"] * po) / 1e6  # no caching is used, so cache fields are 0
    return {"calls": calls, "in": tin, "out": tout, "cost": round(cost, 4)}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


_MON = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def valid_due(src: Source, due) -> str | None:
    """A due date survives only if its day+month are written in the source (R7: no resolved-by-guess dates)."""
    if not (isinstance(due, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", due)):
        return None
    d, mon = int(due[8:]), _MON[int(due[5:7]) - 1]
    t = src.text.lower()
    if due in t or re.search(rf"\b0?{d}\s*(st|nd|rd|th)?\s+{mon}", t) or re.search(rf"{mon}[a-z]*\.?\s+0?{d}\b", t):
        return due
    return None


def revalidate(src: Source, mentions: list[dict]) -> list[dict]:
    return [{**m, "due": valid_due(src, m.get("due"))} for m in mentions]


def _call(model: str, src: Source, now: datetime) -> list[dict]:
    wd = datetime.fromisoformat(src.at).strftime("%A %d %b %Y")
    user = f"Source id {src.id} ({src.kind}); source timestamp {src.at} ({wd}); today is {now.strftime('%A %d %b %Y')}.\n---\n{src.text}"
    r = create(
        "extract", model=model, max_tokens=1500, system=SYSTEM, tools=[TOOL],
        tool_choice={"type": "auto"},
        messages=[{"role": "user", "content": user}])
    for b in r.content:
        if b.type == "tool_use":
            return b.input.get("mentions", [])
    return []


def _clean(src: Source, raw: list[dict]) -> list[dict]:
    out, seen, body = [], set(), _norm(src.text)
    for m in raw:
        slot = m.get("slot")
        if slot != "new" and slot not in SLOTS:
            continue
        if slot == "new" and not (m.get("kind") in KINDS and m.get("counterparty") and m.get("topic")):
            continue
        key = slot if slot != "new" else f"new:{m['counterparty']}|{m['topic']}"
        if key in seen or m.get("state") not in STATES:
            continue
        seen.add(key)
        due = valid_due(src, m.get("due"))
        ev = (m.get("evidence") or "").strip()
        out.append({**{k: m[k] for k in ("slot", "state", "kind", "counterparty", "topic", "deliverable") if k in m},
                    "due": due, "evidence": ev, "note": (m.get("note") or "").strip()[:140],
                    "ev_ok": bool(ev) and _norm(ev) in body})
    return out


def cache_path(source_id: str) -> Path:
    return CACHE / f"{re.sub(r'[^A-Za-z0-9._-]', '_', source_id)}.json"


def cached(source_id: str) -> dict | None:
    p = cache_path(source_id)
    try:
        return json.loads(p.read_text()) if p.exists() else None
    except json.JSONDecodeError:
        return None


def _write_cache(source_id: str, rec: dict):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = cache_path(source_id)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w") as f:
        f.write(json.dumps(rec, indent=1, ensure_ascii=False))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)


def extract_one(src: Source, now: datetime) -> dict:
    model = MODEL
    try:
        raw = _call(model, src, now)
    except (anthropic.RateLimitError, anthropic.InternalServerError):  # not BadRequest: that is a bug, surface it
        model = FALLBACK
        raw = _call(model, src, now)
    rec = {"source_id": src.id, "model": model, "test": src.id.startswith("T-"), "mentions": _clean(src, raw)}
    _write_cache(src.id, rec)
    return rec


def extract_missing(sources: list[Source], now: datetime, workers: int = 6) -> tuple[int, list[str]]:
    """Extract every uncached source. Returns (n_extracted, failed_ids). Cached sources cost zero calls."""
    todo = [s for s in sources if s.kind != "team" and cached(s.id) is None]
    failed = []

    def run(s):
        try:
            extract_one(s, now)
            return None
        except Exception as e:  # leave uncached; retried next tick
            return f"{s.id}: {type(e).__name__}"

    with ThreadPoolExecutor(workers) as ex:
        for r in ex.map(run, todo):
            if r:
                failed.append(r)
    return len(todo) - len(failed), failed
