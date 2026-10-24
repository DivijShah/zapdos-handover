#!/bin/sh
# Hands-off demo launcher: whoever kills run.py (kill -9, kill, crash) sees it come back by itself, 0.3 s later.
# Ctrl-C stops both. The prepared drop lands DEMO_DROP_AT seconds (default 110) after the FIRST boot ever (handover/demo.json).
cd "$(dirname "$0")" || exit 1
trap 'exit 0' INT TERM
mkdir -p handover
exec 2>>handover/run.log   # shell job messages ("Killed: 9") and stderr go to the log, not the screen
while true; do
  .venv/bin/python run.py --demo-drop-at "${DEMO_DROP_AT:-110}" "$@"
  sleep 0.3
done
