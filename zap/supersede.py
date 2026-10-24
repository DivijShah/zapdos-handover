"""Does a dropped source contradict a live promise? One cached model verdict per (source, promise)."""
import json
import os

from . import extract, ledger

TOOL = {
    "name": "record_verdict",
    "description": "Say whether the NEW SOURCE changes a fact the existing promise rests on.",
    "input_schema": {"type": "object", "properties": {
        "verdict": {"type": "string", "enum": ["same", "changed", "unrelated"]},
        "quote": {"type": "string", "description": "VERBATIM line from the NEW SOURCE that states the new fact ('' if not changed)"},
        "reason": {"type": "string"}}, "required": ["verdict", "quote", "reason"]},
}
SYSTEM = ("You compare ONE existing promise (with its source texts) to ONE new source. Call record_verdict.\n"
          "- changed: the new source states a DIFFERENT scheduled time, date of an event, quantity, place, price figure or decision than the one the promise rests on "
          "(for example a new call time replacing the old one). `quote` must be copied verbatim from the new source.\n"
          "- A new or moved DEADLINE for the same deliverable (\"I need it by 30 Oct\") is `same`, not changed: it is a due-date update.\n"
          "- same: consistent, or only progress on the same fact.\n- unrelated: about something else.\n"
          "Never infer. If unsure, answer same.")


def _path(src_id: str, pid: str):
    return ledger.H / "judge_cache" / f"{extract.cache_path(src_id).stem}__{pid}.json"


def judge(src, p: dict, m: dict, srcmap: dict) -> dict:
    cp = _path(src.id, p["id"])
    if cp.exists():
        return json.loads(cp.read_text())
    old = "\n\n".join(f"[{i}]\n{srcmap[i].text[:1200]}" for i in p["sources"][:4] if i in srcmap)
    user = (f"EXISTING PROMISE: {p['deliverable']} (due {p['due'] or 'none'}; notes: {'; '.join(p['notes']) or 'none'})\n"
            f"ITS SOURCES:\n{old}\n\nNEW SOURCE [{src.id}]:\n{src.text}")
    r = extract.client().messages.create(model=extract.MODEL, max_tokens=500, system=SYSTEM, tools=[TOOL],
                                         tool_choice={"type": "auto"}, messages=[{"role": "user", "content": user}])
    v = next((b.input for b in r.content if b.type == "tool_use"), None)
    if v is None:
        raise RuntimeError("no record_verdict call")  # not cached: retried next tick
    if v.get("verdict") == "changed" and extract._norm(v.get("quote", "")) not in extract._norm(src.text):
        v = {**v, "verdict": "same", "reason": "quote not found in source; treated as same"}
    v = {"verdict": v["verdict"], "quote": v.get("quote", ""), "reason": v.get("reason", ""), "test": src.id.startswith("T-")}
    cp.parent.mkdir(exist_ok=True)
    tmp = cp.with_suffix(".tmp")
    with open(tmp, "w") as f:
        f.write(json.dumps(v, indent=1))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, cp)
    return v
