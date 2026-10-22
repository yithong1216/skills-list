#!/usr/bin/env bash
set -Eeuo pipefail

if [ "$#" -lt 4 ]; then
  cat >&2 <<'USAGE'
Usage:
  wrap_existing_run.sh <existing_sh> <run_root> <project> <run_id> [notify_env] [thresholds] [-- payload_args...]

This wrapper does not edit the original shell script. It runs it, captures logs,
writes an exit code file, and records process identity. Email is off unless
NOTIFY_ENABLED=1. Use a fresh run root; existing logs/state are never reused.
USAGE
  exit 2
fi

EXISTING_SH="$1"
RUN_ROOT="$2"
PROJECT="$3"
RUN_ID="$4"
NOTIFY_ENV="${5:-}"
THRESHOLDS="${6:-50,75,100}"
PAYLOAD_ARGS=()
if (( $# > 6 )); then
  shift 6
  [[ "$1" == -- ]] || { echo 'Expected -- before payload arguments' >&2; exit 2; }
  shift
  PAYLOAD_ARGS=("$@")
fi
PYTHON_BIN="${PYTHON_BIN:-python}"
NOTIFY_ENABLED="${NOTIFY_ENABLED:-0}"
[[ "$NOTIFY_ENABLED" == 0 || "$NOTIFY_ENABLED" == 1 ]] || { echo 'NOTIFY_ENABLED must be 0 or 1' >&2; exit 2; }
[[ -n "$RUN_ROOT" && -n "$RUN_ID" && "$RUN_ID" != *$'\n'* && "$PROJECT" != *$'\n'* ]] || exit 2
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${RUN_ROOT}/logs/main.log"
EXIT_CODE_FILE="${RUN_ROOT}/exit_code.txt"

for evidence in "$LOG_FILE" "$EXIT_CODE_FILE" "${RUN_ROOT}/notify_state.json" "${RUN_ROOT}/run_metadata.txt"; do
  if [[ -e "$evidence" || -L "$evidence" ]]; then
    echo "Refusing to reuse run evidence: $evidence; choose a fresh run root" >&2
    exit 2
  fi
done
mkdir -p "$RUN_ROOT"
# This persistent, atomic claim also rejects concurrent launches and interrupted runs.
mkdir "${RUN_ROOT}/.run_claim" 2>/dev/null || { echo 'Run root already claimed; choose a fresh run root' >&2; exit 2; }
RUN_PID=''
WATCH_PID=''
stop_watcher() {
  local owned_pid
  # Only signal a job still owned by this shell; never search global processes.
  for owned_pid in $(jobs -pr); do
    [[ "$owned_pid" != "$WATCH_PID" ]] || kill -TERM "$WATCH_PID" 2>/dev/null || true
  done
  [[ -z "$WATCH_PID" ]] || wait "$WATCH_PID" 2>/dev/null || true
}
finalize() {
  local code=$?
  trap - EXIT INT TERM
  set +e
  if [[ -n "$RUN_PID" ]]; then
    # A shell PID does not account for all training descendants. Do not fabricate
    # terminal status, or signal a potentially reused PID, after interruption.
    printf 'wrapper_exit_code=%s\nstatus=unknown\n' "$code" > "${RUN_ROOT}/wrapper_interrupted.txt"
    echo 'status=unknown: wrapper interrupted; payload or descendants may still be running' >&2
    stop_watcher
    exit "$code"
  fi
  if ! { printf '%s\n' "$code" > "${EXIT_CODE_FILE}.tmp" && mv "${EXIT_CODE_FILE}.tmp" "$EXIT_CODE_FILE"; }; then
    echo 'status=unknown: terminal marker could not be written' >&2
    stop_watcher
    exit "$code"
  fi
  if [[ -n "$WATCH_PID" ]]; then
    wait "$WATCH_PID" || echo 'Notification watcher failed; inspect logs/notify.log' >&2
  fi
  exit "$code"
}
trap finalize EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
mkdir -p "${RUN_ROOT}/logs" "${RUN_ROOT}/results" "${RUN_ROOT}/checkpoints" "${RUN_ROOT}/configs"

start_ticks() {
  local stat
  local -a fields
  [[ -r "/proc/$1/stat" ]] || { printf 'unknown'; return; }
  { read -r stat < "/proc/$1/stat"; } 2>/dev/null || { printf 'unknown'; return; }
  read -ra fields <<< "${stat##*) }"
  printf '%s' "${fields[19]:-unknown}"
}
BOOT_ID=unknown
[[ ! -r /proc/sys/kernel/random/boot_id ]] || read -r BOOT_ID < /proc/sys/kernel/random/boot_id
SESSION_KIND="${SESSION_KIND:-}"
SESSION_NAME="${SESSION_NAME:-}"
if [[ -z "$SESSION_KIND" && -n "${TMUX:-}" ]]; then
  SESSION_KIND=tmux
  SESSION_NAME="$(tmux display-message -p '#S' 2>/dev/null || true)"
elif [[ -z "$SESSION_KIND" && -n "${STY:-}" ]]; then
  SESSION_KIND=screen
  SESSION_NAME="$STY"
fi
{
  printf 'metadata_version=1\nrun_id=%s\nproject=%s\nwrapper_pid=%s\nwrapper_start_ticks=%s\nboot_id=%s\n' \
    "$RUN_ID" "$PROJECT" "$$" "$(start_ticks "$$")" "$BOOT_ID"
  printf 'session_kind=%s\nsession_name=%s\n' "${SESSION_KIND:-}" "${SESSION_NAME:-${STY:-}}"
} > "${RUN_ROOT}/run_metadata.txt"

if [[ "$NOTIFY_ENABLED" == 1 ]]; then
  "$PYTHON_BIN" "${SCRIPT_DIR}/send_email_notify.py" \
    --event started --project "$PROJECT" --run-id "$RUN_ID" --run-root "$RUN_ROOT" \
    --summary 'Wrapped experiment started' --env-file "$NOTIFY_ENV" \
    >> "${RUN_ROOT}/logs/notify.log" 2>&1 || true
  "$PYTHON_BIN" "${SCRIPT_DIR}/watch_progress_notify.py" \
    --project "$PROJECT" --run-id "$RUN_ID" --run-root "$RUN_ROOT" \
    --log-file "$LOG_FILE" --thresholds "$THRESHOLDS" --env-file "$NOTIFY_ENV" \
    --exit-code-file "$EXIT_CODE_FILE" \
    >> "${RUN_ROOT}/logs/notify.log" 2>&1 &
  WATCH_PID=$!
fi

# Direct redirection makes RUN_PID the actual payload shell, not tee's PID.
# Follow logs/main.log (or use monitor_run.sh) while the payload runs.
bash "$EXISTING_SH" "${PAYLOAD_ARGS[@]}" >> "$LOG_FILE" 2>&1 &
RUN_PID=$!
printf 'worker_pid=%s\nworker_start_ticks=%s\n' "$RUN_PID" "$(start_ticks "$RUN_PID")" >> "${RUN_ROOT}/run_metadata.txt"
printf 'run_root=%s worker_pid=%s log=%s\n' "$RUN_ROOT" "$RUN_PID" "$LOG_FILE"

set +e
wait "${RUN_PID}"
EXIT_CODE=$?
RUN_PID=''
set -e

exit "${EXIT_CODE}"
