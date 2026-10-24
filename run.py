"""The process they kill. Boot -> banner -> ingest -> render -> commit -> sleep 20 s -> repeat."""
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

from zap import drops, extract, ledger, persona, render, route, shiftnote, sources, supersede  # noqa: E402

TICK = 20
console = Console(width=None if sys.stdout.isatty() else 140)
stop = False


def _sig(*_):
    global stop
    stop = True


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
        import json
        tmp = sl.with_suffix(".tmp")
        tmp.write_text("".join(json.dumps(m) + "\n" for m in json.loads((sources.PACK / "slack/messages.json").read_text())))
        os.replace(tmp, sl)


def banner(st: dict, n_cached: int, n_total: int):
    s = ledger.stats(st)
    if not st["promises"]:
        head = f"FRESH START — ingesting pack  (cache {n_cached}/{n_total} sources)"
    else:
        la = s["last_action"]
        last = f"{la['type']} by {la['persona']} at {la['at']}" if la else "none"
        head = (f"RESUMED  open={s['open']} in_progress={s['in_progress']} done={s['done']} "
                f"waiting_owner={s['waiting_owner']} superseded={s['superseded']} questions={s['questions']}  last_action={last}  (cache {n_cached}/{n_total} sources)")
    console.print(f"[bold cyan]{head}[/]")
    return head


def git_commit(msg: str):
    try:
        subprocess.run(["git", "-C", str(ROOT), "add", "handover", "outbox"], check=True, capture_output=True)
        if subprocess.run(["git", "-C", str(ROOT), "diff", "--cached", "--quiet"]).returncode:
            subprocess.run(["git", "-C", str(ROOT), "commit", "-q", "-m", msg], check=True, capture_output=True)
    except Exception as e:
        console.print(f"[dim]git: {type(e).__name__}[/]")


def tick(first: bool) -> None:
    now = now_clock()
    n_norm, norm_failed = drops.normalise_missing(now)
    pack = sources.load_pack(now) + sources.load_drops(now)
    srcmap = {s.id: s for s in pack}
    st = ledger.materialize()
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
    ledger.apply_clashes(st, route.detect_clashes([s for s in pack if s.kind == "calendar"]))
    for who in route.team():
        persona.Persona(who["id"], st, now, srcmap).tick()
    persona.sync_linear(st, now.isoformat(), srcmap)
    persona.handover_post(st, now, srcmap)
    changed = shiftnote.render_handovers(st, now) or st["n_events"] != n0
    if first or changed:
        console.print(render.status_table(st, now))
    if failed:
        console.print(f"[red]extract failed (retry next tick): {', '.join(failed[:5])}[/]")
    if changed:
        git_commit(f"ai(system): ingested {new_sources} sources, {len(st['promises'])} promises")
        if not first:
            console.print("\a", end="")
    console.print(f"[dim]tick: drops={n_norm} extracted={n_extracted} ingested={new_sources} events+={st['n_events'] - n0} "
                  f"promises={len(st['promises'])}[/]")


def purge_drops():
    import json
    now = now_clock()
    res = drops.purge(now)
    st = ledger.materialize()
    shiftnote.render_handovers(st, now)
    git_commit(f"ai(system): purged TEST drops ({res['sources']} sources)")
    console.print("purged TEST drops: " + json.dumps(res))


def main():
    once = "--once" in sys.argv
    if "--drops-dir" in sys.argv:
        sources.set_drops_dir(sys.argv[sys.argv.index("--drops-dir") + 1])
    if "--purge-drops" in sys.argv:
        return purge_drops()
    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)
    ensure_working_copies()
    now = now_clock()
    pack = sources.load_pack(now) + sources.load_drops(now)
    st = ledger.materialize()
    banner(st, sum(extract.cached(s.id) is not None for s in pack), len(pack))
    first = True
    while not stop:
        tick(first)
        first = False
        if once:
            break
        for _ in range(TICK):
            if stop:
                break
            time.sleep(1)
    console.print("[dim]flushed, exit 0[/]")


if __name__ == "__main__":
    main()
