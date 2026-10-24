"""Load the work pack and any drops into a flat list of Source records."""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "work_pack"
DEFAULT_DROPS = ROOT / "inbox" / "drops"
DROPS = DEFAULT_DROPS
DROP_EXT = {".txt", ".md", ".json"}


@dataclass
class Source:
    id: str
    kind: str  # call|email|slack|whatsapp|linear|calendar|drop
    at: str  # ISO timestamp
    text: str
    meta: dict = field(default_factory=dict)


def _j(name):
    return json.loads((PACK / name).read_text())


def load_pack(now: datetime) -> list[Source]:
    now_iso = now.isoformat()
    out = []
    for c in _j("calls/calls.json"):
        text = (f"Call: {c['title']}\nWhen: {c['start']}\nAttendees: {', '.join(c['attendees'])}\n\n{c['notes']}")
        out.append(Source(c["id"], "call", c["start"], text))
    for e in _j("inbox/emails.json"):
        text = (f"Email ({e['folder']}) {e['at']}\nFrom: {e['frm']}\nTo: {', '.join(e['to'])}\n"
                f"Cc: {', '.join(e.get('cc') or [])}\nSubject: {e['subject']}\n\n{e['body']}")
        out.append(Source(e["id"], "email", e["at"], text))
    for i, m in enumerate(_j("slack/messages.json"), 1):
        text = f"Slack {m['channel']} {m['at']}\n{m['user']}: {m['text']}"
        out.append(Source(f"S{i:03d}", "slack", m["at"], text, {"channel": m["channel"], "user": m["user"]}))
    for i, m in enumerate(_j("whatsapp/messages.json"), 1):
        text = f"WhatsApp {m['chat']} -> {m['to']} {m['at']}\n{m['text']}"
        out.append(Source(f"WA{i:02d}", "whatsapp", m["at"], text))
    for t in _j("linear/issues.json"):
        text = (f"Linear {t['id']}: {t['title']}\nAssignee: {t['assignee'] or 'unassigned'}\n"
                f"Status: {t['status']}\nDue: {t['due'] or 'none'}\nNote: {t['note'] or 'none'}")
        out.append(Source(f"L-{t['id']}", "linear", now_iso, text, {"issue": t["id"]}))
    for i, ev in enumerate(_j("calendar/events.json"), 1):
        text = (f"Calendar event: {ev['title']}\nStart: {ev['start']}\nEnd: {ev['end']}\n"
                f"Attendees: {', '.join(ev['attendees'])}\nWhere: {ev['where'] or 'n/a'}")
        out.append(Source(f"CAL{i:02d}", "calendar", now_iso, text, {"event": ev}))
    from .route import team
    out.append(Source("T", "team", now_iso, "team.json\n" + "\n".join(
        f"{t['name']} ({t['id']}), {t['role']}, {t['city']}, {t['email']}, owns: {', '.join(t['owns'])}" for t in team())))
    return out


def drop_cache_dir() -> Path:
    return ROOT / "handover" / "drop_cache"


def is_test_dir() -> bool:
    return DROPS.resolve() != DEFAULT_DROPS.resolve()


def set_drops_dir(path: str | Path):
    """Point ingestion at another folder (tests/drops). Sources from it are id-prefixed T- and purgeable."""
    global DROPS
    DROPS = Path(path).resolve()


def drop_files() -> list[Path]:
    if not DROPS.exists():
        return []
    return [p for p in sorted(DROPS.iterdir())
            if p.is_file() and p.suffix.lower() in DROP_EXT and not p.name.startswith(".")]


def file_sha(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()[:12]


def load_drops(now: datetime) -> list[Source]:
    """Cache-only: turns each normalised drop file into Sources. Never calls the model (see drops.normalise_missing)."""
    out = []
    for p in drop_files():
        sha = file_sha(p)
        cp = drop_cache_dir() / f"{sha}.json"
        try:
            rec = json.loads(cp.read_text()) if cp.exists() else None
        except json.JSONDecodeError:
            rec = None
        if not rec:
            continue
        items = rec["sources"]
        for n, it in enumerate(items, 1):
            sid = f"{'T' if rec.get('test') else 'D'}-{p.stem[:24].replace(' ', '_')}-{sha[:6]}" + (f"-{n}" if len(items) > 1 else "")
            head = f"Drop {it['kind']} ({p.name})\nFrom: {it.get('frm') or 'unknown'}\nTo: {it.get('to') or 'unknown'}"
            at = it.get("at") or (now + timedelta(minutes=1 + rec.get("seq", 0))).isoformat()
            out.append(Source(sid, "drop", at, f"{head}\n\n{it['text']}", {"file": p.name, "test": bool(rec.get("test"))}))
    return out
