"""The process they kill. Boot -> banner -> ingest -> render -> commit -> sleep 20 s -> repeat.
Terminal prints only: the RESUMED banner, one line per action, one line per tick. Everything else goes to handover/run.log."""
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

from rich.console import Console  # noqa: E402

from zap import audit, drops, extract, ledger, persona, render, route, shiftnote, site, sources, supersede  # noqa: E402

TICK = 20
BOOT = time.time()
LOG = ROOT / "handover" / "run.log"
console = Console(width=None if sys.stdout.isatty() else 140, highlight=False)
stop = False


def _sig(*_):
    global stop
    stop = True


def log(msg: str):
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")


def say(line: str):
    console.print(line, markup=False)


def now_clock() -> datetime:
    raw = os.environ.get("NOW")
    if not raw:
        sys.exit("NOW missing from .env")
    return datetime.fromisoformat(raw)


def ensure_working_copies():
    ledger.H.mkdir(exist_ok=True)
    for name, src in (("linear.json", "linear/issues.json"), ("calendar.json", "calendar/events.json")):
        if not (ledger.H / name).exists():
            shutil.copy(sources.PACK / src, ledger.H / name)
    sl = ledger.H / "slack.jsonl"
    if not sl.exists():
        tmp = sl.with_suffix(".tmp")
        tmp.write_text("".join(json.dumps(m) + "\n" for m in json.loads((sources.PACK / "slack/messages.json").read_text())))
        os.replace(tmp, sl)


BANNER = {"text": None}


def banner(st: dict, n_cached: int, n_total: int):
    s = ledger.stats(st)
    if not st["promises"]:
        head = f"FRESH START — ingesting pack  (cache {n_cached}/{n_total} sources)"
    else:
        la = s["last_action"]
        last = f"{la['type']} by {la['persona']} at {la['at']}" if la else "none"
        head = (f"RESUMED  open={s['open']} in_progress={s['in_progress']} done={s['done']} "
                f"waiting_owner={s['waiting_owner']} superseded={s['superseded']} questions={s['questions']}  last_action={last}  "
                f"(cache {n_cached}/{n_total} sources)")
    console.print(f"[bold cyan]{head}[/]")
    BANNER["text"] = head
    return head


def git_commit(msg: str):
    try:
        subprocess.run(["git", "-C", str(ROOT), "add", "handover", "outbox"], check=True, capture_output=True)
        if subprocess.run(["git", "-C", str(ROOT), "diff", "--cached", "--quiet"], capture_output=True).returncode:
            subprocess.run(["git", "-C", str(ROOT), "commit", "-q", "-m", msg], check=True, capture_output=True)
    except Exception as e:
        log(f"git: {type(e).__name__} {getattr(e, 'stderr', b'')[:200]!r}")


# ---- demo drop: zero keyboard ----
DEMO = ledger.H / "demo.json"


def demo_drop_check(after: float):
    """Once, `after` seconds past the FIRST boot ever: copy the prepared drop into inbox/drops/. Key demo:drop survives restarts."""
    if not DEMO.exists():
        tmp = DEMO.with_suffix(".tmp")
        tmp.write_text(json.dumps({"first_boot": time.time()}))
        os.replace(tmp, DEMO)
    if time.time() - json.loads(DEMO.read_text())["first_boot"] < after or "demo:drop" in ledger.action_keys():
        return
    dst = ROOT / "inbox" / "drops" / "demo-2030.txt"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "tests" / "drops" / "demo-2030.txt", dst)  # same bytes every time: re-copy after a crash is a no-op
    ledger.record_action("demo", "system", "drop", "inbox/drops/demo-2030.txt", now_clock().isoformat(), after_s=after)
    say(f"drop landed: inbox/drops/demo-2030.txt (T+{int(after)}s after first boot)")


# ---- narration: one line per action ----
def narrate(st: dict, a0: int, q0: set, ev0: int):
    for a in ledger.read_jsonl(ledger.ACTIONS)[a0:]:
        who, text, cites = site.describe(a, st)
        if a["type"] != "drop":  # the 'drop landed' line is printed where the drop is copied
            say(f"{who}-ai {text} ({','.join(cites)})")
    for q in ledger.questions():
        if q["id"] not in q0:
            say(f"{q['from']}-ai asked {q['to']}: {q['question'][:90]}")
    for ev in ledger.read_jsonl(ledger.PROMISES)[ev0:]:
        if ev["op"] == "supersede":
            old = st["promises"].get(ev["id"], {})
            say(f"ledger: superseded '{old.get('deliverable', ev['id'])}' per {ev.get('source')}")


def tick(first: bool, table: bool = False) -> None:
    now = now_clock()
    n_norm, norm_failed = drops.normalise_missing(now)
    pack = sources.load_pack(now) + sources.load_drops(now)
    srcmap = {s.id: s for s in pack}
    st = ledger.materialize()
    a0, q0, ev0 = len(ledger.read_jsonl(ledger.ACTIONS)), {q["id"] for q in ledger.questions()}, st["n_events"]
    n_extracted, failed = extract.extract_missing(pack, now)
    failed += norm_failed
    n0 = st["n_events"]
    new_sources = 0
    judge = lambda src, p, m: supersede.judge(src, p, m, srcmap)  # noqa: E731
    for src in sorted(pack, key=lambda s: (s.at, s.id)):
        if src.id in st["ingested"]:
            continue
        rec = extract.cached(src.id)
        if rec is None:
            continue
        try:
            ledger.apply_source(st, src, extract.revalidate(src, rec["mentions"]), judge)
        except Exception as e:  # e.g. judge API error: leave un-ingested, retry next tick (apply is idempotent)
            failed.append(f"{src.id}: {type(e).__name__}")
            continue
        ledger.mark_ingested(st, src.id)
        new_sources += 1
        if src.kind == "drop":
            say(f"ingested drop {src.meta.get('file')} as {src.id}")
    ledger.apply_clashes(st, route.detect_clashes([s for s in pack if s.kind == "calendar"]))
    for who in route.team():
        persona.Persona(who["id"], st, now, srcmap).tick()
    persona.sync_linear(st, now.isoformat(), srcmap)
    persona.handover_post(st, now, srcmap)
    if audit.gate(st, now.isoformat(), srcmap):  # runtime audit: findings go to rejected.jsonl, unsent drafts are withheld
        say("audit: caught an unsourced fact - see 'Caught itself'")
    narrate(st, a0, q0, ev0)
    changed = shiftnote.render_handovers(st, now) or st["n_events"] != n0
    changed = site.export(st, now, BANNER["text"], {"ingested": new_sources, "events": st["n_events"] - n0}, srcmap, BOOT) or changed
    if table:
        console.print(render.status_table(st, now))
    if failed:
        log(f"retry next tick: {', '.join(failed[:8])}")
    if changed:
        git_commit(f"ai(system): ingested {new_sources} sources, {len(st['promises'])} promises")
        if not first:
            console.print("\a", end="")
    note = f" · {len(failed)} retry pending (run.log)" if failed else ""
    say(f"tick {time.strftime('%H:%M:%S')} · +{st['n_events'] - n0} events · {site.footer_text(st, len(pack), BOOT)}{note}")


def purge_drops():
    now = now_clock()
    res = drops.purge(now)
    st = ledger.materialize()
    shiftnote.render_handovers(st, now)
    site.export(st, now, "purged TEST drops")
    git_commit(f"ai(system): purged TEST drops ({res['sources']} sources)")
    console.print("purged TEST drops: " + json.dumps(res))


def _srcmap():
    now = now_clock()
    return {s.id: s for s in sources.load_pack(now) + sources.load_drops(now)}


def show_audit():
    res = audit.run(_srcmap(), ledger.materialize())
    for ln in audit.render_text(res):
        print(ln, flush=True)
        if sys.stdout.isatty() and "<-" in ln:
            time.sleep(0.02)


def show_rejections():
    rows = ledger.read_jsonl(ledger.REJECTED)
    if not rows:
        return print("0 — nothing rejected yet")
    for r in rows:
        print(f"{r['at']}  {r['persona']:<7} re {r['promise_id']}  {r['reason']}\n    offending: {', '.join(r['offending'])}\n    text: {r['excerpt']}")
    print(f"\n{len(rows)} caught")


def show_as(who_id: str, at: str | None):
    now = datetime.fromisoformat(at) if at else now_clock()
    who = next((p for p in route.team() if p["id"] == who_id), None)
    if not who:
        sys.exit(f"unknown persona {who_id}")
    from zoneinfo import ZoneInfo
    local = now.astimezone(ZoneInfo(who["tz"]))
    header = f"# {local:%A %H:%M} {who['city']} — prepared overnight by {who['name']}'s AI"
    print(shiftnote.note_text(ledger.materialize(), now, who, ledger.questions(), ledger.read_jsonl(ledger.ACTIONS), header))


def _arg(name: str):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


def main():
    once = "--once" in sys.argv
    if "--drops-dir" in sys.argv:
        sources.set_drops_dir(_arg("--drops-dir"))
    if "--audit" in sys.argv:
        return show_audit()
    if "--rejections" in sys.argv:
        return show_rejections()
    if "--as" in sys.argv:
        return show_as(_arg("--as"), _arg("--at"))
    if "--export" in sys.argv:
        st = ledger.materialize()
        site.export(st, now_clock(), "export only", srcmap=_srcmap(), boot=BOOT)
        return console.print("exported handover/site.js")
    if "--purge-drops" in sys.argv:
        return purge_drops()
    ledger.H.mkdir(exist_ok=True)
    os.dup2(os.open(LOG, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644), 2)  # warnings, tracebacks, git noise -> run.log
    sys.stderr = open(2, "w", closefd=False)
    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)
    demo_after = float(_arg("--demo-drop-at")) if "--demo-drop-at" in sys.argv else None
    table = "--table" in sys.argv
    ensure_working_copies()
    now = now_clock()
    pack = sources.load_pack(now) + sources.load_drops(now)
    st = ledger.materialize()
    banner(st, sum(extract.cached(s.id) is not None for s in pack), len(pack))
    first = True
    while not stop:
        if demo_after is not None:
            demo_drop_check(demo_after)
        tick(first, table)
        first = False
        if once:
            break
        seen = [(f.name, f.stat().st_mtime) for f in sources.drop_files()]
        for _ in range(TICK * 2):
            if stop:
                break
            time.sleep(0.5)
            if demo_after is not None:
                demo_drop_check(demo_after)
            if [(f.name, f.stat().st_mtime) for f in sources.drop_files()] != seen:
                break  # a new drop landed: ingest now, don't wait out the tick
    log("flushed, exit 0")
    say("flushed, exit 0")


if __name__ == "__main__":
    main()
