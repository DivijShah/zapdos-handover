"""Load the work pack and any drops into a flat list of Source records."""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "work_pack"
DROPS = ROOT / "inbox" / "drops"
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
    return out


def _drop_items(path: Path):
    raw = path.read_text(errors="replace")
    if path.suffix == ".json":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return [raw]
        items = data if isinstance(data, list) else data.get("messages", [data]) if isinstance(data, dict) else [data]
        return items
    return [raw]


def _render_item(item) -> tuple[str, str | None]:
    if isinstance(item, dict):
        at = next((item[k] for k in ("at", "date", "time", "timestamp", "start") if isinstance(item.get(k), str)), None)
        return "\n".join(f"{k}: {v}" for k, v in item.items()), at
    return str(item), None


def load_drops(now: datetime) -> list[Source]:
    out = []
    if not DROPS.exists():
        return out
    for p in sorted(DROPS.iterdir()):
        if p.suffix.lower() not in DROP_EXT or p.name.startswith("."):
            continue
        items = _drop_items(p)
        for n, item in enumerate(items, 1):
            text, at = _render_item(item)
            if not text.strip():
                continue
            h = hashlib.sha1(text.encode()).hexdigest()[:6]
            sid = f"D-{p.stem[:24].replace(' ', '_')}-{h}" + (f"-{n}" if len(items) > 1 else "")
            out.append(Source(sid, "drop", at or (now + timedelta(minutes=1)).isoformat(),
                              f"Drop ({p.name})\n{text}"))
    return out
