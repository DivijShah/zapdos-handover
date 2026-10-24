"""File-backed tools (outbox, slack, linear working copy) + outbound-text verification (R7)."""
import json
import os
import re
from datetime import datetime
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
