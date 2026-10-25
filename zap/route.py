"""Slot catalog + deterministic routing (team.json.owns lookup) + calendar clash detection.

The extractor picks a slot from this fixed list, so kind, label and id never depend on LLM free text.
"""
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent / "work_pack"

KINDS = ["price", "layout", "install", "server", "pilot", "onboarding", "booking", "followup",
         "onepager", "post", "clip", "casestudy", "approval", "payment", "investor", "reply"]

# kind -> exact phrase in team.json owns
KIND_PHRASE = {
    "price": "pricing", "layout": "camera layouts", "install": "installs", "server": "deploys and servers",
    "pilot": "pilot delivery", "onboarding": "onboarding new engineers", "booking": "booking meetings",
    "followup": "lead follow-ups", "onepager": "one-pagers", "post": "LinkedIn posts", "clip": "videos",
    "casestudy": "case studies", "approval": "approvals and payments", "payment": "approvals and payments",
    "investor": "investors", "reply": "sales",
}

# slot -> (counterparty, topic, kind, label, description, owner-phrase override or None)
# Order = priority (WORKPACK priority order).
_S = [
    ("jordan_lee.onboarding", "onboarding", "Onboard Jordan: accounts, laptop, first task, buddy",
     "Slack/Linear/email accounts, laptop, first task and buddy for new hire Jordan Lee (starts Mon 26 Oct)", None),
    ("jordan_lee.reply", "reply", "Reply to Jordan: where to go Mon 09:00",
     "Answer Jordan's email (logins, where to go at 9)", "hiring decisions"),
    ("northwind.price", "price", "Northwind price for Maria",
     "Customer price/quote Zapdemo owes Northwind (Maria), including a deadline for it. A supplier quote (Optix) is NOT this", None),
    ("northwind.maria_reply", "reply", "Reply to Maria's chase (Northwind)", "Answer Maria's chase email", None),
    ("optix.po", "payment", "Optix PO by Tue 27 Oct 17:00 (50% upfront)",
     "Supplier purchase order / upfront payment for Optix cameras", None),
    ("optix.model_check", "layout", "Confirm Optix OX-4K matches the Northwind layout",
     "Wei Lin must confirm the quoted camera model matches the layout before the PO (he has not seen the quote)", None),
    ("cedar.numbers_refs", "investor", "Cedar Fund: pilot numbers + 2 references",
     "Updated pilot numbers and customer references owed to Cedar Fund (Rachel Kim)", None),
    ("cedar.engineer_call", "booking", "Book Cedar call: Rachel with an engineer",
     "20-minute investor call with an engineer; done once it is booked", None),
    ("ridgeline.price", "price", "Ridgeline ballpark price range for Omar", "Price range owed to Ridgeline (Omar)", None),
    ("ridgeline.reply", "reply", "Reply to Omar: acknowledge his site-visit and price request",
     "Holding acknowledgement to Omar Haddad (Ridgeline); not a visit time and not a price", "lead follow-ups"),
    ("ridgeline.site_visit", "booking", "Ridgeline site visit Tue 27 / Wed 28 AM",
     "Book the Ridgeline site visit and reply to Omar; done once booked", None),
    ("bayview.glare", "pilot", "Bayview night glare false alerts (cams 2, 5)",
     "Fix night glare false alerts at Bayview", None),
    ("bayview.pass_bar", "approval", "Bayview pilot pass bar (signed)",
     "Written pilot pass bar, signed, before pilot review", None),
    ("bayview.weekly_report", "pilot", "Bayview weekly Friday report", "Weekly report to Chris at Bayview", None),
    ("bayview.clip", "clip", "30s night-shift clip for Monday post",
     "Short night-shift video clip for the Monday LinkedIn post (footage comes from pilot delivery)", "pilot delivery"),
    ("bayview.casestudy", "casestudy", "Bayview case study: draft + photos to Lisa",
     "Case study draft and photos for Lisa Park to review/approve", None),
    ("harbor_point.start_time_reply", "reply", "Answer Raj: start 13:30 instead of 14:00?",
     "Reply to Raj about starting the install earlier", "installs"),
    ("harbor_point.cam3_relocation", "layout", "Harbor Point: relocate cam 3 (rack in bay C)",
     "Move camera 3 because a rack blocks the spot", None),
    ("harbor_point.vlan_reply", "reply", "Answer Ken: is a VLAN needed?",
     "Reply to Ken Ong's VLAN question", "installs"),
    ("harbor_point.ip_range", "install", "Harbor Point camera IP range from Ken",
     "IP range for the 6 cameras; done once received", None),
    ("harbor_point.install", "install", "Harbor Point install: 6 cams, paint shop",
     "The on-site install itself (open until physically installed)", None),
    ("crestline.clash", "booking", "Resolve clash: Crestline call vs Harbor Point install (3 Nov)",
     "Double-booking of Wei Lin on 3 Nov", None),
    ("crestline.engineer_call", "booking", "Crestline engineer call (3 Nov 15:00 SGT)",
     "Engineer call with Farah; done once it is on the calendar", None),
    ("crestline.onepager", "onepager", "Crestline one-pager", "Make the Crestline one-pager", None),
    ("crestline.send_onepager", "followup", "Send Crestline one-pager to Farah",
     "Send the finished one-pager to Farah (not sent unless a sent email exists)", None),
    ("crestline.demo_progress", "pilot", "Demo floor-by-floor progress tracking on Crestline call",
     "Farah asked for a floor-by-floor progress demo on the call", None),
    ("northwind.tom_call", "booking", "Book next call with Tom Reyes (Northwind)",
     "Next call including Tom Reyes; done once booked", None),
    ("northwind.onepager", "onepager", "Northwind pallet-damage one-pager for Maria's VP",
     "One-pager on pallet-damage tracking Maria can forward", None),
    ("northwind.layout", "layout", "Northwind dock camera layout (doors 1-12)",
     "Camera layout deliverable; done once delivered. A duplicate ticket is state=duplicate", None),
    ("internal.reimburse_weilin", "approval", "Approve $640 reimbursement to Wei Lin",
     "Reimburse Wei Lin for taxi + hotel (needs approval; payment test mode only)", None),
    ("internal.deploy_alerts_doc", "server", "Document how deploy alerts are wired",
     "Write down how deploy-api alerts are set up (alex is on leave)", None),
]
SLOTS = {}
for _slot, _kind, _label, _desc, _phr in _S:
    _cp, _topic = _slot.split(".")
    SLOTS[_slot] = dict(counterparty=_cp, topic=_topic, kind=_kind, label=_label, desc=_desc, phrase=_phr,
                        prio=len(SLOTS))

_team = None


def team() -> list[dict]:
    global _team
    if _team is None:
        _team = json.loads((PACK / "team.json").read_text())
    return _team


def owner_for_phrase(phrase: str) -> str | None:
    for p in team():
        if phrase in p["owns"]:
            return p["id"]
    return None


def route(kind: str, slot: str | None = None) -> tuple[str, bool]:
    """(owner_id, routed). Deterministic lookup on team.json.owns; unrouted falls to the founder."""
    phrase = (SLOTS.get(slot or "", {}).get("phrase")) or KIND_PHRASE.get(kind)
    owner = owner_for_phrase(phrase) if phrase else None
    return (owner, True) if owner else ("sam", False)


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def promise_id(counterparty: str, topic: str) -> str:
    return hashlib.sha1(f"{slug(counterparty)}|{slug(topic)}".encode()).hexdigest()[:10]


def slot_id(slot: str) -> str:
    s = SLOTS[slot]
    return promise_id(s["counterparty"], s["topic"])


def detect_clashes(cal_sources) -> list[dict]:
    """Per persona, overlapping calendar events -> booking promise for dana. Pure function of the calendar."""
    evs = []
    for s in cal_sources:
        e = s.meta["event"]
        evs.append((s.id, e, datetime.fromisoformat(e["start"]), datetime.fromisoformat(e["end"])))
    out, seen = [], set()
    for i, (ida, a, a0, a1) in enumerate(evs):
        for idb, b, b0, b1 in evs[i + 1:]:
            shared = set(a["attendees"]) & set(b["attendees"])
            if not shared or not (a0 < b1 and b0 < a1) or (ida, idb) in seen:
                continue
            seen.add((ida, idb))
            text = (a["title"] + " " + b["title"]).lower()
            if "crestline" in text and "harbor" in text:
                slot, pid, label = "crestline.clash", slot_id("crestline.clash"), SLOTS["crestline.clash"]["label"]
            else:
                slot = None
                pid = promise_id("internal", "clash-" + "-".join(sorted([ida, idb])))
                label = f"Resolve clash: {a['title']} vs {b['title']}"
            out.append(dict(id=pid, slot=slot, deliverable=label, sources=sorted([ida, idb]),
                            due=min(a["start"], b["start"])[:10], who=sorted(shared)))
    return out
