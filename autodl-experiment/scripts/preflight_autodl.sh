#!/usr/bin/env bash
set -euo pipefail

HEALTH=0

echo "== GPU inventory =="
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader || HEALTH=1

echo "== Disk =="
(df -h / /root/autodl-tmp 2>/dev/null || df -h) || true

echo "== Python =="
if [[ -z "${PYTHON_BIN:-}" ]]; then
  CONDA_REQUESTED="${CONDA_SH:-${CONDA_ENV:-}}"
  CONDA_SH="${CONDA_SH:-/root/miniconda3/etc/profile.d/conda.sh}"
  if [[ -f "$CONDA_SH" ]]; then
    # A requested activation failure must never fall back to a different Python.
    source "$CONDA_SH" || { echo 'readiness=unready reason=conda_source_failed'; exit 1; }
    conda activate "${CONDA_ENV:-base}" || { echo 'readiness=unready reason=conda_activation_failed'; exit 1; }
  elif [[ -n "$CONDA_REQUESTED" ]]; then
    echo 'readiness=unready reason=requested_conda_unavailable'
    exit 1
  fi
  PYTHON_BIN=python
fi
command -v "$PYTHON_BIN" || { echo 'readiness=unready reason=python_not_found'; exit 1; }

echo "== Interpreter, optional package inventory, and CUDA smoke test =="
"$PYTHON_BIN" - <<'PY' || HEALTH=1
import importlib.util
import sys
print("python_executable=" + sys.executable)
print("python_version=" + sys.version.split()[0])
for name in ["transformers", "cv2", "sklearn", "pandas", "tqdm"]:
    try:
        available = importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        available = False
    print(f"optional_package={name} inventory={'present' if available else 'missing'}")
try:
    import torch
    print("torch_version=" + str(torch.__version__))
    print("torch_cuda_build=" + str(torch.version.cuda))
    available = torch.cuda.is_available()
    print("cuda_available=" + str(available).lower())
    if not available:
        raise RuntimeError("CUDA unavailable")
    print("cuda_device_count=" + str(torch.cuda.device_count()))
    print("cuda_device=" + str(torch.cuda.get_device_name(0)))
    torch.ones(1, device="cuda").sum().item()
    torch.cuda.synchronize()
    print("cuda_smoke=ok")
except Exception as exc:
    print("cuda_smoke=failed reason=" + type(exc).__name__)
    raise SystemExit(1)
PY

echo "== Background runner =="
(tmux -V || screen -v || true)

echo "== Proxy =="
while IFS= read -r name; do
  [[ "${name,,}" != *proxy* ]] || printf '%s=set (value hidden)\n' "$name"
done < <(compgen -e)

if (( HEALTH == 0 )); then
  echo 'readiness=ready scope=interpreter_and_cuda_smoke (dataset, model, and metrics require separate checks)'
else
  echo 'readiness=unready'
fi
exit "$HEALTH"
