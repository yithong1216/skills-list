#!/usr/bin/env bash
set -euo pipefail

RUN_ROOT="${1:-}"
if [ -z "${RUN_ROOT}" ]; then
  echo "Usage: monitor_run.sh <RUN_ROOT>" >&2
  exit 2
fi

LOG_FILE="${RUN_ROOT}/logs/main.log"

echo "== Run status =="
MONITOR_CODE=3
STATUS=unknown
REASON='no terminal marker or verified process identity'
RUN_ID=''
PROJECT=''
METADATA_VERSION=''
WRAPPER_PID=''
WRAPPER_TICKS=''
BOOT_ID=''
SESSION_KIND=''
SESSION_NAME=''
if [[ -r "${RUN_ROOT}/run_metadata.txt" ]]; then
  while IFS='=' read -r key value; do
    case "$key" in
      metadata_version) METADATA_VERSION="$value" ;;
      run_id) RUN_ID="$value" ;;
      project) PROJECT="$value" ;;
      wrapper_pid) WRAPPER_PID="$value" ;;
      wrapper_start_ticks) WRAPPER_TICKS="$value" ;;
      boot_id) BOOT_ID="$value" ;;
      session_kind) SESSION_KIND="$value" ;;
      session_name) SESSION_NAME="$value" ;;
    esac
  done < "${RUN_ROOT}/run_metadata.txt"
fi
IDENTITY_VALID=0
if [[ "$METADATA_VERSION" == 1 && -n "$RUN_ID" && -n "$PROJECT" && "$WRAPPER_PID" =~ ^[1-9][0-9]*$ ]]; then
  IDENTITY_VALID=1
fi
if [[ -e "${RUN_ROOT}/exit_code.txt" ]]; then
  EXIT_CODE="$(cat "${RUN_ROOT}/exit_code.txt" 2>/dev/null || true)"
  if (( IDENTITY_VALID == 0 )); then
    REASON="observed_exit_code=$EXIT_CODE (unverified; run identity is missing or invalid)"
  elif [[ "$EXIT_CODE" =~ ^[0-9]+$ && ${#EXIT_CODE} -le 3 ]] && (( 10#$EXIT_CODE <= 255 )); then
    if (( 10#$EXIT_CODE == 0 )); then STATUS=succeeded; MONITOR_CODE=0; else STATUS=failed; MONITOR_CODE=1; fi
    REASON="exit_code=$EXIT_CODE (process status; validate artifacts separately)"
  else
    REASON='invalid terminal marker'
  fi
elif (( IDENTITY_VALID == 1 )) && [[ "$WRAPPER_TICKS" =~ ^[0-9]+$ && "$BOOT_ID" != unknown && -n "$BOOT_ID" ]]; then
  # Linux boot ID + start ticks prevent a reused PID from impersonating this run.
  CURRENT_BOOT=''
  [[ ! -r /proc/sys/kernel/random/boot_id ]] || read -r CURRENT_BOOT < /proc/sys/kernel/random/boot_id
  if [[ "$CURRENT_BOOT" == "$BOOT_ID" && -r "/proc/${WRAPPER_PID}/stat" ]]; then
    if read -r STAT < "/proc/${WRAPPER_PID}/stat"; then
      read -ra FIELDS <<< "${STAT##*) }"
      if [[ "${FIELDS[19]:-}" == "$WRAPPER_TICKS" && "${FIELDS[0]:-Z}" != Z ]] && kill -0 "$WRAPPER_PID" 2>/dev/null; then
        STATUS=running
        MONITOR_CODE=0
        REASON="verified wrapper_pid=$WRAPPER_PID"
      fi
    fi
  fi
fi
printf 'run_id=%s status=%s %s\n' "${RUN_ID:-unknown}" "$STATUS" "$REASON"
printf 'session_kind=%s session_name=%s (inventory only)\n' "${SESSION_KIND:-unknown}" "${SESSION_NAME:-unknown}"

echo "== GPU inventory (not run identity) =="
nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader || true

echo "== Disk =="
(df -h / /root/autodl-tmp 2>/dev/null || df -h) || true

echo "== Latest log =="
tail -80 "${LOG_FILE}" 2>/dev/null || true

echo "== Artifacts =="
bash "$(dirname "$0")/find_artifacts.sh" "${RUN_ROOT}" || true

echo "== Notify state =="
cat "${RUN_ROOT}/notify_state.json" 2>/dev/null || true
exit "$MONITOR_CODE"
