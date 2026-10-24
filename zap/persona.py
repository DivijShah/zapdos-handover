"""Persona(id).tick(): work my own open promises. Pack facts only; missing fact or rejected draft -> question to owner."""
import re
import sys
from datetime import datetime

from . import acts, extract, ledger
from .route import SLOTS, slot_id, team

DRAFT_TOOL = {
    "name": "record_draft",
    "description": "Return the email draft.",
    "input_schema": {"type": "object", "properties": {"subject": {"type": "string"}, "body": {"type": "string"}},
                     "required": ["subject", "body"]},
}


class Rejected(Exception):
    pass


def _lines(srcmap, ids, needle):
    n = needle.lower()
    out = []
    for i in ids:
        for ln in srcmap[i].text.splitlines():
            if n in ln.lower():
                out.append((ln.strip().lstrip("- ").strip(), i))
    return out


class Persona:
    def __init__(self, pid: str, st: dict, now: datetime, srcmap: dict):
        self.who = next(p for p in team() if p["id"] == pid)
        self.id, self.st, self.now, self.srcmap = pid, st, now, srcmap
        self.at = now.isoformat()

    # ---- plumbing ----
    def do(self, p, atype, fn, **extra):
        """Idempotent action: skip if key recorded; else run tool, then record."""
        if f"{p['id']}:{atype}" in ledger.action_keys():
            return None
        path = fn()
        ledger.record_action(p["id"], self.id, atype, path, self.at, **extra)
        return path

    def ask(self, p, to, qkey, text, cite):
        probs = acts.verify_text(text, self.srcmap, cite)
        if probs:
            text = f"[unverified facts removed: {', '.join(probs)}] " + re.sub(r"\$?\d[\d,]*(?:[.:]\d+)?", "#", text)
        return ledger.add_question(self.st, p["id"], to, self.id, qkey, text, self.at)

    def inform(self, p, to, key, text, cite):
        probs = acts.verify_text(text, self.srcmap, cite)
        if probs:
            raise Rejected(f"inform {key}: {probs}")
        self.do(p, f"inform-{key}-{to}", lambda: None, to=to, text=text, cite=cite)

    def sources_block(self, ids):
        return "\n\n".join(f"[{i}]\n{self.srcmap[i].text}" for i in ids)

    def draft(self, task: str, ids: list[str], no_money=False) -> tuple[str, str]:
        system = (f"You are the AI assistant of {self.who['name']} ({self.who['role']}) at Zapdemo Labs. Write a short plain-text "
                  "email on their behalf. Rules: say in the first sentence that you are their AI assistant; use ONLY facts from "
                  "SOURCES; do not state any number, date, time, price, name or address that is not written in SOURCES; never "
                  "promise a price or delivery date; no markdown; at most 110 words; sign off with the assistant's role only. Answer by calling the record_draft tool.")
        feedback, probs = "", ["no valid record_draft call (subject and body required)"]
        for _ in range(3):
            msg = f"TASK: {task}\n{feedback}\nSOURCES:\n{self.sources_block(ids)}"
            r = extract.client().messages.create(
                model=extract.MODEL, max_tokens=700, system=system, tools=[DRAFT_TOOL],
                tool_choice={"type": "auto"}, messages=[{"role": "user", "content": msg}])
            d = next((b.input for b in r.content if b.type == "tool_use"), None)
            if d is None or not d.get("subject") or not d.get("body"):
                probs = ["no valid record_draft call (subject and body required)"]
                feedback = "You must answer by calling record_draft with both subject and body."
                continue
            probs = acts.verify_text(d["subject"] + "\n" + d["body"], self.srcmap, ids, no_money)
            if not probs:
                return d["subject"].strip(), d["body"].strip()
            feedback = f"Your previous draft was rejected for unsupported facts: {probs}. Remove them."
        raise Rejected(probs)

    def email(self, p, atype, slug_, to_frag, task, ids, no_money=False) -> bool:
        """Draft+verify+write outbox email. On rejection files a question to the owner instead. True if written."""
        try:
            def go():
                subj, body = self.draft(task, ids, no_money)
                return acts.email(self.now, self.who, slug_, acts.addr_for(self.srcmap, to_frag), subj, body, p, ids)
            self.do(p, atype, go)
            return True
        except Rejected as e:
            self.ask(p, self.id, f"{atype}-rejected",
                     f"AI draft for '{p['deliverable']}' failed fact check and was NOT written ({e}). Please advise.", ids)
            return False

    def doc(self, p, atype, slug_, title, md, ids):
        probs = acts.verify_text(md, self.srcmap, ids)
        if probs:
            raise Rejected(f"{atype}: {probs}")
        self.do(p, atype, lambda: acts.document(self.now, self.who, slug_, title, md, p, ids))

    # ---- handlers (return desired status or None) ----
    def h_maria_reply(self, p):
        ids = ["E15", "E03", "C01", "L-ZAP-101"]
        ok = self.email(p, "email", "reply-maria-northwind", "maria.gomez",
                        "Reply to Maria's chase email E15. Acknowledge Thursday passed and her VP asked for the number. Do NOT "
                        "mention any price or amount. Say the camera layout for doors 1 to 12 is done (L-ZAP-101, C01). Say you are "
                        "flagging the price to Sam and that Dana will be in touch about the call with Tom. Do not say when.",
                        ids, no_money=True)
        return "done" if ok else "waiting_owner"

    def h_price(self, p):
        s = self.srcmap
        ask = [acts.quote(s, ["E03"], "what will this roughly cost"), acts.quote(s, ["E15"], "the number"),
               acts.quote(s, ["C01"], "layout for doors 1 to 12")]
        quote = [acts.quote(s, ["E10"], "12 x OX-4K"), acts.quote(s, ["C09"], "PO by"),
                 acts.quote(s, ["C09"], "has to match")]
        done = acts.quote(s, ["L-ZAP-101"], "Layout v2")
        md = "\n".join([
            "## What Maria asked for", *[f"- \"{q}\" ({i})" for q, i in ask], "",
            "## What is done", f"- \"{done[0]}\" ({done[1]}). Camera layout, doors 1 to 12, delivered.", "",
            "## Supplier cost (NOT a customer price)", *[f"- \"{q}\" ({i})" for q, i in quote], "",
            "## Dependencies",
            "- Wei Lin has not seen the Optix quote; the camera model must match his layout (C09). "
            "A confirmation task has been opened for Wei Lin.",
            "- Maria has been replied to without a number (draft in outbox) so she is not left silent.", "",
            "## Not in the pack (so not stated here)",
            "- No customer sell price, margin target or markup exists anywhere in the pack. The AI will not invent one.", "",
            "## Decision needed from Sam", "- What price should Northwind be quoted?"])
        ids = ["E03", "E15", "C01", "L-ZAP-101", "E10", "C09"]
        self.doc(p, "brief", "northwind-pricing-brief", "Northwind pricing brief", md, ids)
        dep = ledger.ensure_slot(self.st, "optix.model_check", ["C09", "E10"], self.at,
                                 "Dependency of Northwind price/Optix PO (C09)")
        self.do(p, "dependency", lambda: None, depends_on=dep, to="weilin")
        self.ask(p, "sam", "price",
                 "What customer price should Northwind (Maria) be quoted for the 12-door dock cameras? The pack only has supplier cost "
                 f"(\"{quote[0][0]}\", E10), not a sell price. Brief is in the outbox.", ids)
        return "waiting_owner"

    def h_model_check(self, p):
        s = self.srcmap
        q = acts.quote(s, ["E10"], "12 x OX-4K")
        self.ask(p, "weilin", "model-match",
                 f"Does the quoted camera match your layout? Optix quote Q-1182: \"{q[0]}\" (E10). You have not seen it (C09). "
                 "Sam needs to know before the PO (due Tue 27 Oct).", ["E10", "C09"])
        return "waiting_owner"

    def h_tom_call(self, p):
        ids = ["E03", "C01", "L-ZAP-104"]
        ok = self.email(p, "email", "tom-call-reask-maria", "maria.gomez",
                        "Ask Maria for new times for the next call that includes her site manager Tom Reyes (he signs off anything "
                        "mounted). Her earlier note said Tom was free Friday afternoon (E03) but that Friday has passed, so ask for "
                        "fresh availability. No prices.", ids, no_money=True)
        return None if ok else "waiting_owner"

    def h_onepager(self, p):
        s = self.srcmap
        ids = [i for i in p["sources"] + (["E05"] if p["slot"] == "crestline.onepager" else []) if i in s and not i.startswith("CAL")]
        hits = _lines(s, ids, "one-pager") or _lines(s, ids, "pager")
        ctx = _lines(s, ["C01"], "Pallets get damaged") if p["slot"] == "northwind.onepager" else []
        md = "\n".join([
            f"## Brief: {p['deliverable']}", "", "### What was asked (verbatim)",
            *[f"- \"{q}\" ({i})" for q, i in hits], "",
            *(["### Context", *[f"- \"{q}\" ({i})" for q, i in ctx], ""] if ctx else []),
            "### Open facts", "- Nothing beyond the quotes above is in the pack; ask the owner before adding claims.",
            "- Nothing goes public before the customer approves." if p["slot"] == "bayview.casestudy" else ""])
        self.doc(p, "brief", f"onepager-brief-{p['counterparty']}", f"One-pager brief: {p['deliverable']}", md, ids)
        return None

    def h_send_onepager(self, p):
        dep = slot_id("crestline.onepager")
        self.do(p, "dependency", lambda: None, depends_on=dep, to="priya",
                text="Send only after Priya's one-pager exists; no sent email is in the pack, so treat it as not sent.")
        return None

    def h_clash(self, p):
        s = self.srcmap
        evs = {i: s[i].meta["event"] for i in p["sources"] if i in s and s[i].kind == "calendar"}
        a, b = (evs[k] for k in sorted(evs))
        fmt = lambda e: f"{e['title']} {e['start'][:10]} {e['start'][11:16]}-{e['end'][11:16]}"
        ids = [i for i in ["C03", "E05", *sorted(evs)] if i in s]
        ok = self.email(p, "email", "reschedule-crestline-call", "farah.aziz",
                        "Draft a polite note to Farah: our engineer is booked on-site on Tue 3 Nov 14:00 to 16:30 SGT, which overlaps "
                        "the 15:00 call. Ask whether she can move the call to a time after 16:30 SGT that day, or another day that "
                        "suits her. Do not offer a specific new time. Do not mention internal details.", ids)
        if ok:
            self.ask(p, "dana", "send-reschedule",
                     f"Send the reschedule draft to Farah? Wei Lin is double-booked: {fmt(a)} vs {fmt(b)} (SGT). "
                     "Draft is in the outbox; nothing has been sent.", ids)
        self.inform(p, "weilin", "clash",
                    f"Heads-up: you are double-booked on 3 Nov. {fmt(a)} vs {fmt(b)} (SGT). Dana's AI drafted a reschedule note to "
                    "Farah and asked Dana whether to send it. Raj's 13:30 start request (WA02) is still waiting for your answer.",
                    ids + ["WA02"])
        return "waiting_owner" if ok else "waiting_owner"

    def h_demo(self, p):
        s = self.srcmap
        call = s["CAL02"].meta["event"]
        ask = acts.quote(s, ["WA03"], "floor by floor")
        self.inform(p, "weilin", "demo",
                    f"Crestline call {call['start'][:10]} {call['start'][11:16]}-{call['end'][11:16]} SGT (CAL02). "
                    f"Farah asked Dana by WhatsApp: \"{ask[0]}\" (WA03). You were not copied on the one-pager email either (E05).",
                    ["CAL02", "WA03", "E05"])
        return None

    def h_reimburse(self, p):
        s = self.srcmap
        q = acts.quote(s, ["C10"], "out of pocket")
        self.ask(p, "sam", "approve-640",
                 f"Approve reimbursing Wei Lin? \"{q[0]}\" (C10, ZAP-160). Nothing will be paid without your approval; test mode only.",
                 ["C10"])
        return "waiting_owner"

    def h_deploy_alerts(self, p):
        s = self.srcmap
        ids = ["E11", "E12", "C10"]
        facts = [acts.quote(s, ["E11"], "deploy-api is DOWN"), acts.quote(s, ["E11"], "Rule:"),
                 acts.quote(s, ["E12"], "recovered after"), acts.quote(s, ["C10"], "nobody knows how the alerts")]
        md = "\n".join(["Known facts only. Each line is a verbatim quote.", "",
                        f"- DOWN notice sent {s['E11'].at} (E11)", f"- RECOVERED notice sent {s['E12'].at} (E12)",
                        *[f"- \"{q}\" ({i})" for q, i in facts], "",
                        "## Not in the pack (do not guess)",
                        "- How the alerts are wired beyond the rule file named above, and who gets notified.",
                        "- Alex is on two weeks' leave (C10); Alex is not in team.json."])
        probs = acts.verify_text(md, s, ids)
        if probs:
            raise Rejected(probs)
        self.do(p, "doc", lambda: acts.doc_flat("deploy-alerts-known-facts.md",
                                                "# Deploy alerts: known facts\n\n" + md + "\n\nSources: E11, E12, C10. "
                                                "Written by Wei Lin's AI assistant (an AI).\n"))
        return None

    HANDLERS = {
        "northwind.maria_reply": h_maria_reply, "northwind.price": h_price, "optix.model_check": h_model_check,
        "northwind.tom_call": h_tom_call, "northwind.onepager": h_onepager, "crestline.onepager": h_onepager,
        "crestline.send_onepager": h_send_onepager, "crestline.clash": h_clash, "crestline.demo_progress": h_demo,
        "internal.reimburse_weilin": h_reimburse, "internal.deploy_alerts_doc": h_deploy_alerts,
    }

    def tick(self) -> int:
        mine = [p for p in self.st["promises"].values() if p["owner"] == self.id and p["status"] in ("open", "waiting_owner")]
        mine.sort(key=lambda p: (p["due"] or "9999", SLOTS.get(p["slot"], {}).get("prio", 99)))
        n = 0
        for p in mine:
            h = self.HANDLERS.get(p["slot"])
            if not h:
                continue
            try:
                want = h(self, p)
            except Exception as e:
                print(f"persona {self.id} {p['slot']}: {type(e).__name__}: {str(e)[:160]}", file=sys.stderr)
                continue
            if want and want != p["status"]:
                ledger.set_status(self.st, p["id"], want)
                n += 1
        return n


def sync_linear(st: dict, at: str) -> int:
    """Working-copy Linear: assign unassigned issues to the routed owner; close duplicates. Idempotent."""
    import json
    cur = {t["id"]: t for t in json.loads((ledger.H / "linear.json").read_text())}
    n = 0
    for p in st["promises"].values():
        dups = {f.split(":", 1)[1] for f in p["flags"] if f.startswith("duplicate:")}
        for sid in p["sources"]:
            if not sid.startswith("L-"):
                continue
            issue, t = sid[2:], cur.get(sid[2:])
            if not t:
                continue
            if sid in dups:
                ch = acts.linear_update(issue, status="Done", note=f"Duplicate of {next((s[2:] for s in p['sources'] if s.startswith('L-') and s not in dups), 'original')}")
            elif t["assignee"] is None:
                ch = acts.linear_update(issue, assignee=p["owner"])
            else:
                continue
            if ch:
                n += 1
                ledger.record_action(p["id"], p["owner"], f"linear-{issue}", None, at, changes=ch)
    return n


def handover_post(st: dict, now: datetime, srcmap: dict) -> bool:
    """Slack post summarising Northwind once its four pieces have acted. Key-idempotent."""
    ks = ledger.action_keys()
    by = {p["slot"]: p for p in st["promises"].values()}
    need = [("northwind.maria_reply", "email"), ("northwind.price", "brief"), ("northwind.tom_call", "email"),
            ("northwind.onepager", "brief")]
    if not all(f"{by[s]['id']}:{a}" in ks for s, a in need if s in by) or not all(s in by for s, _ in need):
        return False
    lay = by["northwind.layout"]
    text = (f"Northwind handover (posted by Sam's AI assistant, an AI). Camera layout, doors 1 to 12: {lay['status']} "
            f"({', '.join(lay['sources'][:2])}). Price: owner sam, {by['northwind.price']['status']}, question filed. "
            f"Tom call: owner dana, re-ask drafted. One-pager: owner priya, brief handed over from C01. "
            "Reply to Maria drafted with no number (E15).")
    ids = ["C01", "L-ZAP-101", "E15"]
    probs = acts.verify_text(text, srcmap, ids)
    if probs:
        print(f"handover_post rejected: {probs}", file=sys.stderr)
        return False
    if acts.slack_post("#sales", "ai-sam", now.isoformat(), text, "northwind:slack_handover"):
        ledger.record_action(by["northwind.price"]["id"], "sam", "slack-handover", "handover/slack.jsonl", now.isoformat())
        return True
    return False
