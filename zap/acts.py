"""File-backed tools (outbox, slack, linear working copy) + outbound-text verification (R7)."""
import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from . import ledger
from .route import slug

ROOT = Path(__file__).resolve().parent.parent
OUTBOX = ROOT / "outbox"
MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"


def _atomic(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


# ---------- provenance helpers ----------
def quote(srcmap: dict, ids: list[str], needle: str) -> tuple[str, str]:
    """First source line containing `needle` -> (verbatim line, source id). Raises if absent: no quote, no claim."""
    n = needle.lower()
    for i in ids:
        for ln in srcmap[i].text.splitlines():
            if n in ln.lower():
                return ln.strip().lstrip("- ").strip(), i
    raise KeyError(f"no source line with {needle!r} in {ids}")


def addr_for(srcmap: dict, fragment: str) -> str | None:
    for s in srcmap.values():
        if s.kind == "email":
            for a in re.findall(r"[\w.+-]+@[\w.-]+\.example", s.text):
                if fragment in a:
                    return a
    return None


# ---------- verify (R7) ----------
ISO = r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?(?:[+-]\d{2}:\d{2}|Z)?)?"


def verify_text(text: str, srcmap: dict, ids: list[str], no_money: bool = False) -> list[str]:
    """Return problems. Every number/time/$/day-month in outbound text must appear verbatim in the cited sources."""
    corpus = "\n".join(srcmap[i].text for i in ids if i in srcmap).lower()
    body = text
    for i in sorted(srcmap, key=len, reverse=True):  # strip citation ids like C01, L-ZAP-101
        if i in body:
            body = body.replace(i, " ")
    body = re.sub(r"\bZAP-\d+\b", " ", body)
    probs = []
    for iso in re.findall(ISO, body):
        if iso.lower() not in corpus:
            probs.append(f"timestamp {iso}")
    body = re.sub(ISO, " ", body)
    for ip in re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?", body):  # dotted addresses are one token
        if not re.search(rf"(?<![\d.]){re.escape(ip)}(?![\d])", corpus):
            probs.append(f"ip {ip}")
    body = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?", " ", body)
    for dot in re.findall(r"(?<![\w.])\.\d+", body):  # '.50 to .55': leading-dot octets, checked verbatim
        if dot not in corpus:
            probs.append(f"number {dot}")
    body = re.sub(r"(?<![\w.])\.\d+", " ", body)
    if no_money and "$" in body:
        probs.append("money not allowed in this message")
    if re.search(r"https?://|www\.", body):
        probs.append("url")
    for a in re.findall(r"[\w.+-]+@[\w.-]+", body):
        if not a.endswith(".example"):
            probs.append(f"address {a}")
    for d, m in re.findall(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTHS})[a-z]*", body.lower()):
        if not re.search(rf"\b0?{d}(?:st|nd|rd|th)?\s+{m}", corpus) and not re.search(rf"{m}[a-z]*\.?\s+0?{d}\b", corpus):
            probs.append(f"date {d} {m}")
    for t in re.findall(r"\d{1,2}:\d{2}|\$?\d[\d,]*(?:\.\d+)?", body):
        t = t.rstrip(".,").lower()
        if t and not re.search(rf"(?<![\d.,:]){re.escape(t)}(?![\d])", corpus):
            probs.append(f"number {t}")
    return sorted(set(probs))


# ---------- tools ----------
def email(now: datetime, persona: dict, slug_: str, to: str | None, subject: str, body: str, promise: dict,
          cite: list[str]) -> str:
    """Write an outbox email artifact (the file-backed 'send'). Returns repo-relative path. Deterministic name."""
    name = f"{now:%Y%m%d-%H%M}-{persona['id']}-{slug(slug_)}.md"
    foot = (f"\n\n--\nDrafted by {persona['name']}'s AI assistant (an AI, not a person). "
            f"Based on: {', '.join(cite)}.")
    head = (f"From: {persona['email']}\nTo: {to or 'UNKNOWN (ask owner)'}\nSubject: {subject}\n"
            f"Promise: {promise['id']} ({promise['deliverable']})\nSources: {', '.join(cite)}\n\n")
    _atomic(OUTBOX / name, head + body.strip() + foot + "\n")
    return f"outbox/{name}"


def document(now: datetime, persona: dict, slug_: str, title: str, md: str, promise: dict, cite: list[str]) -> str:
    name = f"{now:%Y%m%d-%H%M}-{persona['id']}-{slug(slug_)}.md"
    _atomic(OUTBOX / name, f"# {title}\n\n_{persona['name']}'s AI assistant · promise {promise['id']} · "
                           f"sources: {', '.join(cite)}_\n\n{md.strip()}\n")
    return f"outbox/{name}"


def doc_flat(name: str, md: str) -> str:
    _atomic(OUTBOX / name, md)
    return f"outbox/{name}"


def slack_post(channel: str, user: str, at: str, text: str, key: str) -> bool:
    p = ledger.H / "slack.jsonl"
    if any(m.get("key") == key for m in ledger.read_jsonl(p)):
        return False
    ledger.append(p, dict(channel=channel, user=user, at=at, text=text, key=key))
    return True


def linear_update(issue: str, **fields) -> list[str]:
    """Mutate handover/linear.json only (pack original untouched). Returns list of changes made."""
    p = ledger.H / "linear.json"
    data = json.loads(p.read_text())
    changed = []
    for t in data:
        if t["id"] == issue:
            for k, v in fields.items():
                if t.get(k) != v:
                    changed.append(f"{issue}.{k}: {t.get(k)!r} -> {v!r}")
                    t[k] = v
    if changed:
        _atomic(p, json.dumps(data, indent=1))
    return changed


# ---------- send policy ----------
WEEKDAYS = r"monday|tuesday|wednesday|thursday|friday|saturday|sunday"
_SCHED = (rf"\b\d{{1,2}}:\d{{2}}\b|\b\d{{1,2}}\s?(?:am|pm)\b|\b(?:{WEEKDAYS})\b|\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{MONTHS})[a-z]*|"
          rf"\b(?:{MONTHS})[a-z]*\.?\s+\d{{1,2}}\b")
_COMMIT = r"\b(will attend|will be attending|will be there|will join|is attending|are attending|will deliver|quote|estimate|discount|invoice)\b"


def commitment_problems(text: str, inbound_ids: list[str], srcmap: dict) -> list[str]:
    """A draft may go out unasked only if it commits the company to nothing new: no money, no schedule token (time, day,
    date) that the counterparty's own message did not already contain, no attendee or delivery promise."""
    inbound = "\n".join(srcmap[i].text for i in inbound_ids if i in srcmap).lower()
    probs = []
    if "$" in text or re.search(r"\b(usd|dollars?|euros?)\b", text.lower()):
        probs.append("money or price")
    for m in re.finditer(_SCHED, text.lower()):
        if m.group(0) not in inbound:
            probs.append(f"offers schedule '{m.group(0)}'")
    for m in re.finditer(_COMMIT, text.lower()):
        probs.append(f"commitment '{m.group(0)}'")
    return sorted(set(probs))


def sent_path(rel: str) -> str:
    return "outbox/sent/" + rel.rsplit("/", 1)[-1]


def resolve(rel: str) -> str:
    """Path of an outbox artifact wherever it lives now (outbox/ or outbox/sent/)."""
    if rel and not (ROOT / rel).exists():
        for alt in (sent_path(rel), "outbox/withheld/" + rel.rsplit("/", 1)[-1]):
            if (ROOT / alt).exists():
                return alt
    return rel


def send(rel: str, persona: dict, at: str) -> str:
    """The file-backed 'send': move outbox/x.md -> outbox/sent/x.md with a Status line. Idempotent across a crash."""
    src, dst = ROOT / rel, ROOT / sent_path(rel)
    if not src.exists():
        return sent_path(rel)
    stamp = f"Status: SENT by {persona['name']}'s AI assistant at {at} (file-backed outbox: nothing leaves this machine)\n"
    _atomic(dst, stamp + src.read_text())
    src.unlink()
    return sent_path(rel)


def parse_when(quote_: str, year: int):
    """(date, hour, minute, tzid) from 'Friday 30 Oct, 2pm Dallas' style text; None unless date, time AND zone are all written."""
    q = quote_.lower()
    md = re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTHS})", q)
    dm = re.search(rf"\b({MONTHS})[a-z]*\.?\s+(\d{{1,2}})\b", q)
    tm = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s?(am|pm)\b", q)
    tz = "America/Chicago" if re.search(r"\b(dallas|cdt|ct|central|texas)\b", q) else None
    if not ((md or dm) and tm and tz):
        return None
    day, mon = (int(md.group(1)), md.group(2)) if md else (int(dm.group(2)), dm.group(1))
    h = int(tm.group(1)) % 12 + (12 if tm.group(3) == "pm" else 0)
    from datetime import date
    return date(year, MONTHS.split("|").index(mon[:3]) + 1, day), h, int(tm.group(2) or 0), tz


def ics(now: datetime, persona: dict, slug_: str, summary: str, when, attendees: list[str], promise: dict, cite: list[str],
        note: str) -> str:
    """Proposal .ics (METHOD:PUBLISH, TENTATIVE). No DTEND: the pack gives no duration, so none is invented."""
    d, h, m, tz = when
    name = f"{now:%Y%m%d-%H%M}-{persona['id']}-{slug(slug_)}.ics"
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Zapdemo AI//handover//EN", "METHOD:PUBLISH", "BEGIN:VEVENT",
             f"UID:{promise['id']}@zapdemo.example", f"DTSTAMP:{now.astimezone(ZoneInfo('UTC')):%Y%m%dT%H%M%SZ}",
             f"DTSTART;TZID={tz}:{d:%Y%m%d}T{h:02d}{m:02d}00", f"SUMMARY:{summary}", "STATUS:TENTATIVE",
             f"ORGANIZER:mailto:{persona['email']}", *[f"ATTENDEE:mailto:{a}" for a in attendees],
             f"DESCRIPTION:{note} Proposed by {persona['name']}'s AI assistant (an AI); not sent. Sources: {', '.join(cite)}.",
             "END:VEVENT", "END:VCALENDAR"]
    _atomic(OUTBOX / name, "\r\n".join(lines) + "\r\n")
    return f"outbox/{name}"


def withhold(rel: str) -> str:
    """Pull an unsent draft out of outbox/ into outbox/withheld/ (audit found an unsourced fact in it)."""
    src, dst = ROOT / rel, ROOT / "outbox" / "withheld" / rel.rsplit("/", 1)[-1]
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.replace(src, dst)
    return "outbox/withheld/" + dst.name
