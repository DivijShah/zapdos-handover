"""Audit: every number / date / $ / name in outbox/, outbox/sent/ and Linear changes -> source id + the verbatim source line.
Independent of verify_text: it re-derives facts from the finished artifacts and looks each one up in the cited sources."""
import re
from pathlib import Path

from . import acts, ledger
from .route import team

MONTHS = acts.MONTHS
STOP = set("""a an the and or but if so as at by for from in into of on onto to with without about after before then than that this these those
it its is are was were be been am i we our us you your yours he she they them their his her hi hello dear thanks thank best regards kind sincerely
please also sorry since while when where which who whom what how not no yes ok can could will would shall should may might must do does did done
have has had just only still yet already new now today tomorrow sent drafted draft based sources source subject status promise note notes
ai assistant monday tuesday wednesday thursday friday saturday sunday
january february march april may june july august september october november december jan feb mar apr jun jul aug sep sept oct nov dec
sales caller engineer founder content investors investor team email message messages reply replying wrote writing writes write
proposed tentative published request calendar invite call meeting camera cameras dock doors door layout case study photos photo list
first day details logins login monday morning forklifts forklift start voice note range mask gateway vlan install installation
confirm confirmed confirming received receive thank you""".split())
WORD = re.compile(r"\b[A-Z][a-zA-Z'’\-]*\b")
NUM = re.compile(rf"\b\d{{4}}-\d{{2}}-\d{{2}}(?:T[\d:+\-Z]+)?|\b\d{{1,3}}(?:\.\d{{1,3}}){{3}}(?:/\d{{1,2}})?|(?<![\w.])\.\d+|\b\d{{1,2}}:\d{{2}}\b|"
                 rf"\b\d{{1,2}}\s?(?:am|pm)\b|\$\d[\d,]*(?:\.\d+)?|\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{MONTHS})[a-z]*|\b(?:{MONTHS})[a-z]*\.?\s+\d{{1,2}}\b|"
                 r"\b\d[\d,]*(?:\.\d+)?\b")


def _team_text() -> str:
    return "\n".join(f"{t['name']} ({t['id']}), {t['role']}, {t['city']}, {t['email']}, owns: {', '.join(t['owns'])}" for t in team())


def _find(token: str, ids: list[str], srcmap: dict, kind: str):
    """First (source id, verbatim line) in the cited sources containing the token, else None."""
    esc = re.escape(token)
    pat = (re.compile(rf"(?<![\w]){esc}(?![\w])", re.I) if kind == "name"
           else re.compile(rf"(?<![\d.,:]){esc}(?!\d)", re.I) if kind == "num" else re.compile(esc, re.I))
    weak = None  # a match on a From:/To:/Cc: header line only counts if no prose line matches
    for i in ids:
        txt = _team_text() if i == "T" else srcmap[i].text if i in srcmap else ""
        for ln in txt.splitlines():
            if pat.search(ln):
                if ln.startswith(("From:", "To:", "Cc:")):
                    weak = weak or (i, ln.strip())
                else:
                    return i, ln.strip()
    return weak


_LEX = None


def _initial(text: str, i: int) -> bool:
    j = i - 1
    while j >= 0 and text[j] in " \t\"'-*#(_>":
        j -= 1
    return j < 0 or text[j] in ".!?:\n"


def lexicon(srcmap: dict) -> set[str]:
    """Words the pack itself capitalises mid-sentence (people, orgs, places): only these count as names at a sentence start."""
    global _LEX
    if _LEX is None:
        _LEX = set()
        for txt in [_team_text()] + [s.text for s in srcmap.values()]:
            for m in WORD.finditer(txt):
                if not _initial(txt, m.start()):
                    _LEX.add(m.group(0).lower().split("'")[0].split("’")[0])
    return _LEX


def facts_in(text: str, srcmap: dict | None = None, strip_ids=()) -> list[tuple[str, str]]:
    out, seen = [], set()
    for i in sorted(strip_ids, key=len, reverse=True):
        text = text.replace(i, " ")
    text = re.sub(r"\b(?:L-)?ZAP-\d+\b|\bCAL\d+\b", " ", text)  # issue / calendar ids are citations, not facts
    text = re.sub(r"^#+ .*$", " ", text, flags=re.M)  # markdown headings are template, not facts
    lex = lexicon(srcmap) if srcmap else set()
    scrub = text
    for m in NUM.finditer(text):
        t = m.group(0)
        if t.lower() not in seen:
            seen.add(t.lower())
            out.append(("num", t))
    scrub = NUM.sub(" ", scrub)
    for m in WORD.finditer(scrub):
        t = re.split(r"['’]", m.group(0).strip("'’-"))[0]  # "Rivera's" -> Rivera, "I'm" -> I
        if t.lower() in STOP or len(t) < 2 or t.lower() in seen:
            continue
        if _initial(scrub, m.start()) and t.lower() not in lex:
            continue
        seen.add(t.lower())
        out.append(("name", t))
    return out


def _split(text: str, rel: str) -> tuple[list[str], str, list[tuple[str, str]]]:
    """(cited ids, body to audit, extra literal facts like the To: address)."""
    extra = []
    if rel.endswith(".ics"):
        t = text.replace("\r\n", "\n")
        cite = re.search(r"Sources: ([A-Za-z0-9,\- ]+?)\.?$", t, re.M)
        ids = [c.strip() for c in cite.group(1).split(",")] if cite else []
        m = re.search(r"DTSTART;TZID=[\w/]+:(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})", t)
        if m:
            y, mo, d, h, mi = map(int, m.groups())
            mon = MONTHS.split("|")[mo - 1]
            extra += [("date", f"{d} {mon}"), ("time", f"{h % 12 or 12}{'pm' if h >= 12 else 'am'}" if mi == 0 else f"{h:02d}:{mi:02d}")]
        body = "\n".join(ln.split(":", 1)[1] for ln in t.splitlines() if ln.startswith(("SUMMARY:", "DESCRIPTION:")))
        extra += [("addr", a) for a in re.findall(r"mailto:([\w.+-]+@[\w.-]+)", t)]
        return ids, body, extra
    head, _, rest = text.partition("\n\n")
    if "Sources: " in head and "From: " in head:  # email
        cite = next(ln[9:] for ln in head.splitlines() if ln.startswith("Sources: "))
        subj = next((ln[9:] for ln in head.splitlines() if ln.startswith("Subject: ")), "")
        to = next((ln[4:] for ln in head.splitlines() if ln.startswith("To: ")), "")
        if "@" in to:
            extra.append(("addr", to.strip()))
        body = subj + "\n" + rest.split("\n\n--\nDrafted by")[0]
        return [c.strip() for c in cite.split(",")], body, extra
    m = re.search(r"sources: ([A-Za-z0-9,\- ]+)", text) or re.search(r"Sources: ([A-Za-z0-9,\- ]+)", text)
    ids = [c.strip() for c in m.group(1).split(",")] if m else []
    body = re.sub(r"^_.*_$", "", text, flags=re.M)
    body = re.sub(r"\n\nSources:.*$", "", body, flags=re.S)
    return ids, body, extra


def run(srcmap: dict, st: dict) -> dict:
    acts_ = ledger.read_jsonl(ledger.ACTIONS)
    who = {}
    for a in acts_:
        if a.get("path"):
            who[a["path"].rsplit("/", 1)[-1]] = a["persona"]
    people = {t["id"]: t["name"] for t in team()}
    groups = {pid: {"persona": pid, "name": people[pid], "files": []} for pid in people}
    checked = unsourced = uncited_n = 0

    def audit_one(label, state, ids, body, extra, persona):
        nonlocal checked, unsourced, uncited_n
        ids = [i for i in ids if i in srcmap or i == "T"] + ["T"]
        facts = []
        for kind, tok in extra + facts_in(body):
            k = "num" if kind in ("num", "time", "date") else "name" if kind == "name" else "lit"
            hit = _find(tok, ids, srcmap, k)
            uncited = False
            if hit is None:  # not in the cited sources: is it anywhere in the pack?
                hit = _find(tok, list(srcmap), srcmap, k)
                uncited = hit is not None
            facts.append({"fact": tok, "src": hit[0] if hit else None, "line": hit[1][:140] if hit else None, "uncited": uncited})
            checked += 1
            unsourced += hit is None
            uncited_n += uncited
        groups[persona]["files"].append({"file": label, "state": state, "cites": [i for i in ids if i != "T"], "facts": facts})

    root = ledger.ROOT / "outbox"
    for d, state in ((root, "draft"), (root / "sent", "sent")):
        if not d.exists():
            continue
        for f in sorted(d.iterdir()):
            if not f.is_file() or f.suffix not in (".md", ".ics"):
                continue
            text = f.read_text()
            persona = who.get(f.name) or (re.match(r"\d{8}-\d{4}-([a-z]+)-", f.name) or [None, None])[1]
            if persona not in groups:
                persona = "weilin" if "Wei Lin" in text else "sam"
            ids, body, extra = _split(text, f.name)
            if f.suffix == ".md" and not extra and "Sources:" not in text and "sources:" not in text:
                continue
            audit_one(f"outbox/{'sent/' if state == 'sent' else ''}{f.name}", state, ids, body, extra, persona)
    for a in acts_:
        if a["type"].startswith("linear-") and a.get("changes"):
            p = st["promises"].get(a["promise_id"], {})
            body = "\n".join(c.split(": ", 1)[1].split(" -> ", 1)[-1] if ": " in c else c for c in a["changes"])
            issue = a["type"].split("linear-note-")[-1].split("linear-")[-1]
            persona = a["persona"] if a["persona"] in groups else "sam"
            new_assignee = [c.split(" -> ", 1)[1].strip("'") for c in a["changes"] if ".assignee:" in c]
            extra = [("lit", issue)] + [("lit", v) for v in new_assignee]  # assignee is a routing result: found in team.json's `owns`
            audit_one(f"linear {issue}: {'; '.join(a['changes'])[:90]}", "linear", list(a.get("cite", [])) + list(p.get("sources", [])),
                      "" if new_assignee else body, extra, persona)
    return {"groups": [g for g in groups.values() if g["files"]], "checked": checked, "unsourced": unsourced, "uncited": uncited_n}


def render_text(res: dict, delay: float = 0.0) -> list[str]:
    import time
    out = []
    for g in res["groups"]:
        out.append(f"\n== {g['persona'].upper()}  ({g['name']})  {sum(len(f['facts']) for f in g['files'])} facts")
        for f in g["files"]:
            out.append(f"  {f['file']}  [{f['state']}]  cites {', '.join(f['cites']) or '-'}")
            for x in f["facts"]:
                mark = "  (not in a cited source; found in pack)" if x.get("uncited") else ""
                out.append(f"    {x['fact']:<26} <- {x['src']}: \"{x['line']}\"{mark}" if x["src"] else f"    {x['fact']:<26} <- NOT FOUND anywhere in the pack")
    out.append(f"\n{res['checked']} facts checked · {res['unsourced']} unsourced"
               + (f" · {res['uncited']} found in the pack but not in the cited sources" if res.get("uncited") else ""))
    return out
