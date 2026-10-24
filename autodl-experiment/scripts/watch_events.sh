#!/usr/bin/env bash
# Local event watcher. Launch it with the agent's run_in_background so that its exit
# re-invokes the agent; never poll with foreground `sleep N; ssh ...` loops.
#
# Usage: watch_events.sh <ssh_alias> <remote_status_cmd> [interval_s] [heartbeat_s] [state_file]
#   remote_status_cmd  e.g. "bash /root/autodl-tmp/status.sh" (see assets/status.sh.template);
#                      it prints KEY=VALUE facts plus lines starting with ALERT or EVENT.
#   interval_s         seconds between checks (default 120)
#   heartbeat_s        exit with a progress snapshot after this long even if quiet (default 3600)
#   state_file         remembers ALERT/EVENT lines already reported (default: per alias in $TMPDIR)
#
# Exits 0 and prints the snapshot when a NEW ALERT/EVENT line appears, the heartbeat elapses,
# or ssh fails twice in a row. A line is reported once while it persists; it re-arms after it
# disappears from the snapshot. Re-launch the watcher after handling its output.
set -uo pipefail

ALIAS="${1:?ssh alias}"
STATUS_CMD="${2:?remote status command}"
INTERVAL="${3:-120}"
HEARTBEAT="${4:-3600}"
STATE="${5:-${TMPDIR:-/tmp}/watch_events_${ALIAS//[^A-Za-z0-9_.-]/_}.state}"
touch "$STATE"

start=$(date +%s)
fails=0
while true; do
  snap=$(ssh -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=15 "$ALIAS" "$STATUS_CMD" 2>&1)
  rc=$?
  if [ $rc -ne 0 ] && [ -z "$(printf '%s\n' "$snap" | grep -E '^(ALERT|EVENT|now=)')" ]; then
    fails=$((fails + 1))
    if [ $fails -ge 2 ]; then
      echo "$(date +%T) ALERT ssh $ALIAS failed twice (rc=$rc); connection state UNKNOWN, run state not inferred"
      printf '%s\n' "$snap" | tail -n 5
      exit 0
    fi
    sleep 30
    continue
  fi
  fails=0
  current=$(printf '%s\n' "$snap" | grep -E '^(ALERT|EVENT)' | sort -u)
  new=$(comm -13 <(sort -u "$STATE") <(printf '%s\n' "$current" | sed '/^$/d'))
  printf '%s\n' "$current" | sed '/^$/d' > "$STATE"
  if [ -n "$new" ]; then
    echo "$(date +%T) NEW:"
    printf '%s\n' "$new"
    echo "--- snapshot"
    printf '%s\n' "$snap"
    exit 0
  fi
  if [ $(( $(date +%s) - start )) -ge "$HEARTBEAT" ]; then
    echo "$(date +%T) HEARTBEAT (no new ALERT/EVENT)"
    printf '%s\n' "$snap"
    exit 0
  fi
  sleep "$INTERVAL"
done
