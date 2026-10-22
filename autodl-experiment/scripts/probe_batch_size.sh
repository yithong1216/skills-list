#!/usr/bin/env bash
# Find the batch size that keeps the GPU busy without OOM — by measurement.
#
# Guessing batch size costs restarts. This runs the REAL training command briefly
# at each candidate size and reports mean GPU utilisation, peak VRAM and whether
# it OOM'd, so the choice is made on data.
#
# Bigger is NOT always faster: once VRAM nears the card limit the allocator
# overhead dominates. A measured example (RF-DETR-Medium 800px on a 24 GB card):
#
#     batch  GPU mean  peak VRAM   verdict
#       2      40%      7.3 GiB    under-utilised
#       4      58%     12.2 GiB    best
#       8      42%     22.8 GiB    slower AND 0.7 GiB from OOM
#      12       —          —       OOM
#
# Usage:
#   TRAIN_CMD='python train.py --data ... --epochs 1' \
#   BATCH_FLAG='--batch-size' ACCUM_FLAG='--grad-accum-steps' EFFECTIVE=16 \
#   PROC_PAT='train.py' \
#   bash probe_batch_size.sh 4 8 12
#
# TRAIN_CMD must run in the foreground and accept the batch flag appended.
set -uo pipefail

TRAIN_CMD="${TRAIN_CMD:?set TRAIN_CMD to the training command}"
BATCH_FLAG="${BATCH_FLAG:---batch-size}"
ACCUM_FLAG="${ACCUM_FLAG:-}"
EFFECTIVE="${EFFECTIVE:-0}"          # 0 = don't adjust accumulation
PROC_PAT="${PROC_PAT:-python}"
WARMUP="${WARMUP:-45}"               # seconds to let training reach steady state
SAMPLES="${SAMPLES:-25}"             # 1s GPU samples per candidate
PROBE_DIR="${PROBE_DIR:-/root/autodl-tmp/runs/_probe}"

# Many-core boxes starve the GPU without a thread cap — see SKILL.md GPU Throughput.
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-8}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

[ $# -gt 0 ] || set -- 2 4 8
echo "cores=$(nproc)  OMP_NUM_THREADS=$OMP_NUM_THREADS  candidates: $*"
echo

for B in "$@"; do
  OUT="${PROBE_DIR}_b$B"; rm -rf "$OUT"; mkdir -p "$OUT"
  CMD="$TRAIN_CMD $BATCH_FLAG $B"
  if [ -n "$ACCUM_FLAG" ] && [ "$EFFECTIVE" -gt 0 ]; then
    ACC=$(( EFFECTIVE / B )); [ "$ACC" -lt 1 ] && ACC=1
    CMD="$CMD $ACCUM_FLAG $ACC"
  else
    ACC="-"
  fi

  eval "$CMD" > "$OUT/probe.log" 2>&1 &
  PID=$!

  # wait for the training loop to actually start before sampling: sampling during
  # startup or validation gives a false "GPU is idle" reading
  for _ in $(seq 1 40); do
    grep -qaE "Epoch|Start training|it/s|step" "$OUT/probe.log" 2>/dev/null && break
    kill -0 $PID 2>/dev/null || break
    sleep 5
  done
  sleep "$WARMUP"

  MAXV=0; SUM=0; N=0
  for _ in $(seq 1 "$SAMPLES"); do
    read -r U V <<< "$(nvidia-smi --query-gpu=utilization.gpu,memory.used \
                        --format=csv,noheader,nounits | head -1 | tr ',' ' ')"
    [ -n "${U:-}" ] || continue
    SUM=$((SUM + U)); N=$((N + 1)); [ "$V" -gt "$MAXV" ] && MAXV=$V
    sleep 1                          # 1s: 5s intervals alias past GPU bursts
  done

  OOM=$(grep -ac "OutOfMemory\|out of memory" "$OUT/probe.log" 2>/dev/null || echo 0)
  MEAN=$([ "$N" -gt 0 ] && echo $((SUM / N)) || echo 0)
  if [ "$OOM" -gt 0 ]; then
    printf "batch=%-3s accum=%-3s  ->  OOM\n" "$B" "$ACC"
  else
    printf "batch=%-3s accum=%-3s  ->  GPU mean %3s%%   peak VRAM %6s MiB\n" \
           "$B" "$ACC" "$MEAN" "$MAXV"
  fi

  kill -9 $PID 2>/dev/null
  pkill -9 -f "$PROC_PAT" 2>/dev/null
  sleep 10
done

echo
echo "Pick the highest GPU mean with comfortable VRAM headroom (>=20% of the card)."
echo "Do NOT pick the largest batch that merely fits — near the limit it runs slower."
