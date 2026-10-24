"""Drops: any .txt/.md/.json saved in the drops folder -> model-normalised source records (kind, at, from, to, text).
Cached per file content hash in handover/drop_cache/. TEST drops (any folder other than inbox/drops) are marked and purgeable."""
import hashlib
import json
import os
from datetime import datetime

import anthropic

from . import extract, ledger, sources
from .sources import Source

KINDS = ["email", "slack", "whatsapp", "call", "note"]
TOOL = {
    "name": "record_sources",
    "description": "Record the messages or notes contained in the dropped file.",
    "input_schema": {"type": "object", "properties": {"sources": {"type": "array", "items": {
        "type": "object",
        "properties": {"kind": {"type": "string", "enum": KINDS},
                       "at": {"type": ["string", "null"]},
                       "frm": {"type": "string"}, "to": {"type": "string"},
                       "text": {"type": "string"}},
        "required": ["kind", "at", "frm", "to", "text"]}}}, "required": ["sources"]},
}
SYSTEM = ("A file was dropped into the Zapdemo Labs inbox. It may be an email, a Slack or WhatsApp message, call notes, "
          "a transcript or JSON. Split it into one record per message or note and call record_sources.\n"
          "- `text` = the message body copied VERBATIM from the file (no paraphrase, no summary, no added words). Keep headers out of it.\n"
          "- `at` = ISO 8601 timestamp with UTC offset ONLY if the file states both date and time; otherwise null. Never guess a date.\n"
          "- `frm` / `to` = sender / recipients exactly as written in the file, or \"\" if absent.\n"
          "Never add facts that are not in the file.")


def _write(path, rec: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        f.write(json.dumps(rec, indent=1, ensure_ascii=False))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _squash(s: str) -> str:
    return " ".join(s.split())


def _validate(raw: str, items: list[dict], tzinfo) -> list[dict]:
    """Keep only what the file supports: body verbatim, timestamp only if its day+month is written in the file."""
    probe = Source("x", "drop", "", raw)
    out = []
    for it in items:
        text = (it.get("text") or "").strip()
        if not text or _squash(text) not in _squash(raw):
            continue
        at = it.get("at")
        try:
            dt = datetime.fromisoformat(at) if at else None
            if dt and dt.tzinfo is None:
                dt = dt.replace(tzinfo=tzinfo)
            at = dt.isoformat() if dt and extract.valid_due(probe, dt.date().isoformat()) else None
        except (ValueError, TypeError):
            at = None
        out.append({"kind": it.get("kind") if it.get("kind") in KINDS else "note", "at": at,
                    "frm": (it.get("frm") or "").strip(), "to": (it.get("to") or "").strip(), "text": text})
    return out or [{"kind": "note", "at": None, "frm": "", "to": "", "text": raw.strip()}]


def _call(model: str, name: str, raw: str) -> list[dict]:
    r = extract.create(
        "drop-normalise", model=model, max_tokens=3000, system=SYSTEM, tools=[TOOL], tool_choice={"type": "auto"},
        messages=[{"role": "user", "content": f"File name: {name}\n---\n{raw}"}])
    for b in r.content:
        if b.type == "tool_use":
            return b.input.get("sources", [])
    raise RuntimeError("no record_sources call")


def normalise_missing(now: datetime) -> tuple[int, list[str]]:
    """One model call per never-seen drop file; zero calls for cached ones. Failures retry next tick."""
    n, failed = 0, []
    for p in sources.drop_files():
        sha = sources.file_sha(p)
        cp = sources.drop_cache_dir() / f"{sha}.json"
        if cp.exists():
            continue
        raw = p.read_text(errors="replace")
        model = extract.MODEL
        try:
            try:
                items = _call(model, p.name, raw)
            except (anthropic.RateLimitError, anthropic.InternalServerError):
                model = extract.FALLBACK
                items = _call(model, p.name, raw)
            seq = len(list(sources.drop_cache_dir().glob("*.json")))
            _write(cp, {"file": p.name, "sha": sha, "test": sources.is_test_dir(), "seq": seq, "model": model,
                        "sources": _validate(raw, items, now.tzinfo)})
            n += 1
        except Exception as e:
            failed.append(f"{p.name}: {type(e).__name__}")
    return n, failed


def purge(now: datetime) -> dict:
    """Remove every TEST drop and everything derived from it, so state equals a run that never saw it."""
    tcache = [p for p in sources.drop_cache_dir().glob("*.json") if json.loads(p.read_text()).get("test")]
    test_sids = {p.stem for p in extract.CACHE.glob("T-*.json")} if extract.CACHE.exists() else set()
    evs = ledger.read_jsonl(ledger.PROMISES)
    test_sids |= {e.get("by_src") for e in evs if str(e.get("by_src", "")).startswith("T-")}
    test_sids |= {e.get("source") for e in evs if str(e.get("source", "")).startswith("T-")}
    dead = {e["id"] for e in evs if e["op"] == "create" and e.get("by_src") in test_sids}
    keep = [e for e in evs if e.get("by_src") not in test_sids and e.get("source") not in test_sids and e.get("id") not in dead]
    acts_ = ledger.read_jsonl(ledger.ACTIONS)
    gone_acts = [a for a in acts_ if a["promise_id"] in dead]
    qs = ledger.read_jsonl(ledger.QUESTIONS)
    gone_q = {q["id"] for q in qs if q.get("promise_id") in dead}
    slack = ledger.read_jsonl(ledger.H / "slack.jsonl")
    keep_slack = [m for m in slack if m.get("key") not in gone_q and not str(m.get("key", "")).split(":")[0] in dead]

    def rewrite(path, recs):
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            f.write("".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in recs))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)

    rewrite(ledger.PROMISES, keep)
    rewrite(ledger.ACTIONS, [a for a in acts_ if a["promise_id"] not in dead])
    rewrite(ledger.QUESTIONS, [q for q in qs if q["id"] not in gone_q])
    rewrite(ledger.H / "slack.jsonl", keep_slack)
    files = 0
    for a in gone_acts:
        if a.get("path", "") and a["path"].startswith("outbox/"):
            from . import acts
            f = ledger.ROOT / acts.resolve(a["path"])
            if f.exists():
                f.unlink()
                files += 1
    for sid in test_sids:
        for d in (extract.CACHE, ledger.H / "judge_cache"):
            for f in d.glob(f"{extract.cache_path(sid).stem}*.json") if d.exists() else []:
                f.unlink()
    for p in tcache:
        p.unlink()
    return {"drop_cache": len(tcache), "sources": len(test_sids), "events_removed": len(evs) - len(keep),
            "promises_removed": len(dead), "actions_removed": len(gone_acts), "questions_removed": len(gone_q),
            "outbox_files_removed": files}
