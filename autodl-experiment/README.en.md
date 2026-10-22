# AutoDL Experiment Runner

A Codex skill for launching, recovering, and completing AutoDL / SeetaCloud SSH
GPU experiments. [中文](README.md) · [Workflow](SKILL.md) · [Reference](references/autodl-reference.md)

## Use

```text
Use $autodl-experiment to finish this remote evaluation and pull back its results.
Recover the existing run state and reuse the verified interpreter and model cache.
Check every required sample and metric, reserving time for validation and transfer.
```

Launch-only, status-only, sidecar notifications, and complete experiments have
different acceptance criteria. Reconcile an uncertain SSH launch before retrying.
Freeze code/config/data identity per attempt; preserve logs and checkpoints.

## Helpers

- `preflight_autodl.sh`: interpreter, CUDA and an actual CUDA operation; a separate project CLI smoke is still required.
- `wrap_existing_run.sh`: preserves the original entrypoint, rejects reused run directories, and records identity, logs and atomic exit state.
- `monitor_run.sh`: a one-shot process snapshot; UNKNOWN remains possible and process exit is separate from experiment acceptance.
- `watch_progress_notify.py`: explicit overall progress and exit-code notifications, with run-bound atomic deduplication state.
- `find_artifacts.sh` / `append_autodl_note.py`: locate candidate outputs and record lessons; review scope and contents before use.

Preserve verified cache locations instead of inventing an empty default. If an
interrupted wrapper cannot establish whether descendants remain, retain UNKNOWN
and recovery evidence rather than publishing a false terminal marker.

## Email

Notifications default off. Enable `NOTIFY_ENABLED=1` only with recipient/event
authorization. Existing SMTP settings do not grant that authorization. Overall
progress comes from a single-value progress file or `AUTODL_PROGRESS=37.5`;
arbitrary percentages, accuracy and batch bars are ignored. Exit markers describe
process status, not scientific success.

Raw log tails default off. Regex redaction is best effort; review selected content
before opting in. Supply secrets through protected runtime configuration, never
command-line arguments, skills, chat or runbooks. Dry runs do not send or consume
production deduplication state.

Legacy unscoped state is rejected: retain it and follow the reference's fresh-state
procedure. SMTP timeout/crash ambiguity prevents an exactly-once delivery guarantee.

## Offline checks

```powershell
python -m unittest discover -s evals -p "test_*.py" -v
```

Requires Python 3 and Bash. Windows can set `BASH_BIN` to Git Bash.
Fixtures are local and do not connect to GPU hosts or SMTP. Linux process identity,
real CUDA, tmux/screen and mail transport still need deployment validation.

## Installation and license

This directory contains a local revision. Copy the reviewed complete package to
the personal skills directory and retain a backup. The
[upstream project](https://github.com/handsomeZR-netizen/autodl-experiment-skill)
may not include these local changes.

MIT; see [LICENSE](LICENSE).
