# Remote operation reference

Use only the section needed for the current stage. Resolve example paths from
the actual project before execution. Commands here are Linux-side unless marked
local; supplying an example does not authorize a transfer, notification, or kill.

## Exact interpreter and entrypoint

Inventory the running project's interpreter before installing anything. An
absolute interpreter path is preferable to assumptions about python/python3 or
shell startup files. For example, after verifying the path:

```bash
PYTHON_BIN=/root/miniconda3/envs/research/bin/python bash scripts/preflight_autodl.sh
```

Alternatively supply the verified `CONDA_SH` and `CONDA_ENV`. Activation failure
must stop preflight rather than fall through to base. The helper's readiness
scope is interpreter/CUDA operation; optional package inventory is informational.
Separately run the actual project CLI/import/custom-operator/model/data smoke,
including its output write and parse step. Capture exact interpreter and versions
with the run's config/code/data identifiers.

From Windows, inspect commands using the Windows shell, and send Linux commands
through SSH deliberately. For complex remote logic, prefer a small reviewed LF
script and its hash to nested PowerShell/SSH/Bash quoting. A local spawn failure
is not a remote task exit. Fix the failing layer before changing the experiment.

## Cache and network

Check which cache/model snapshot the working process actually uses. Do not copy
tokens or dump full environment values. Keep existing cache settings when they
are correct; if migrating storage, verify the copied files and model loader
before launching. A cache directory's existence alone is not enough.

For a verified, fully cached model, set `HF_HUB_OFFLINE=1` in the launch process
before library import. This avoids the Hub metadata request that may occur even
when files are cached. Use `HF_HUB_CACHE` for current Hub cache configuration;
`HUGGINGFACE_HUB_CACHE` is a deprecated alias. Match the installed loader/version,
including Torch Hub/timm caches where applicable.
[Hugging Face environment-variable documentation](https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables)
was checked for these behaviors on 2026-09-06.

If downloads are required, test access, size, storage and measured transfer speed,
then reserve time for training/evaluation/pullback. A retry budget includes the
library's internal timeouts. Do not wait through repeated long HEAD requests
without checking a known cached alternative. Enable provider network setup only
when it exists and is appropriate for that host; persist required exports inside
the launcher rather than relying on an interactive session.

Provider reference links retained from the original package:
[network acceleration](https://www.autodl.com/docs/network_turbo/),
[background execution](https://www.autodl.com/docs/daemon/),
[SCP](https://www.autodl.com/docs/scp/),
[downloads](https://www.autodl.com/docs/down/),
[disk FAQ](https://www.autodl.com/docs/qa1/).
The first two could not be fetched during the 2026-09-06 audit; their availability
is not a preflight result for the user's instance.

## Wrapper and new-run template

The wrapper keeps the original positional interface and defaults notifications
off. Use a fresh attempt directory; configs/scripts may be staged there before
launch, but logs, exit state, metadata, or `.run_claim` mean it is already used.

```bash
bash scripts/wrap_existing_run.sh /verified/project/train.sh /verified/runs/run01 project run01
```

With explicitly authorized email, a verified notification interpreter and private
SMTP configuration:

```bash
NOTIFY_ENABLED=1 PYTHON_BIN=/verified/env/bin/python \
  bash scripts/wrap_existing_run.sh /verified/project/train.sh /verified/runs/run02 \
  project run02 /private/notify.env 50,75,100
```

Pass extra payload arguments after the optional positions and `--`:

```bash
bash scripts/wrap_existing_run.sh /verified/project/train.sh /verified/runs/run03 \
  project run03 '' 50,75,100 -- --config /verified/frozen/config.py
```

The wrapper logs directly to `logs/main.log`, writes `run_metadata.txt` and an
atomic `exit_code.txt`, and owns one watcher when enabled. Follow the log rather
than expecting live tee output. Existing `.run_claim` is retained after exit so
accidental reruns cannot erase evidence. Choose a new attempt or a project-defined
verified checkpoint-resume path; do not delete the claim to bypass this check.

If interrupted before the payload is reaped, the wrapper records
`wrapper_interrupted.txt` and UNKNOWN, stops its owned watcher, and does not write
a terminal exit marker or assume training descendants stopped. Reconcile the
recorded worker and actual descendants before an authorized stop or recovery.
An enabled watcher may take its default 60-second interval to notice terminal
state; notification transport/retries can add time after the marker is written.

Render `assets/run.sh.template` with the real project, run ID, script directory,
environment, thresholds, and command. Verify no placeholders remain and run
`bash -n`. Its setup executes inside the wrapper so setup failures are recorded.
Set interpreter/workdir/cache explicitly as needed; use the same snapshot in
smoke and formal runs. Background this wrapper using the available tmux/screen
or project job manager and verify first useful work after dispatch.

## One-shot monitoring

```bash
bash scripts/monitor_run.sh /verified/runs/run01
```

This prints a snapshot. Exit 0 means a verified running process or normal process
exit, 1 means nonzero process exit, 3 means UNKNOWN, and 2 is usage error. The
printed status disambiguates running from exited. Completion of the user's
experiment still requires result verification. Linux boot ID and `/proc` start
ticks protect against PID reuse; missing identity is UNKNOWN, not evidence of a
clean finish. GPU information is inventory, not run ownership.

For a preexisting process without wrapper metadata, inspect its actual command,
start identity, log and artifacts without restarting it. Do not manufacture
terminal state. If persistent monitoring is requested, register the appropriate
watcher/host automation and verify it exists before promising future checks.

## Notification contract and migration

Calling the notification helpers is an external-message action: do so only with
the user's recipient/event authorization. `--dry-run` previews locally and does
not contact SMTP or alter production notification state.

```bash
python scripts/watch_progress_notify.py --project project --run-id run01 \
  --run-root /verified/runs/run01 --log-file /verified/runs/run01/logs/main.log \
  --exit-code-file /verified/runs/run01/exit_code.txt \
  --thresholds 50,75,100 --env-file /private/notify.env --once --dry-run
```

Overall progress must be a single number in a dedicated `--progress-file` (e.g.
`37.5` or `37.5%`) or a standalone `AUTODL_PROGRESS=37.5` log line. Keep it scoped
to the whole declared run and update files atomically. Ordinary epoch/step text,
validation accuracy, download bars and batch percentages are ignored. If needed,
adapt the project's known total-work counter to the explicit progress protocol.
No reliable source means terminal-only notifications.

The watcher treats an integer exit marker as process status, sends terminal
events before progress events, and exits after terminal delivery. Missing or
malformed markers remain unknown. `--terminal-attempts` defaults to 3 and
`--retry-interval` to 5 seconds; transport timeout also counts toward elapsed
time. Delivery exhaustion returns nonzero while preserving unsent state, so a
later watcher invocation can retry. Notification failure does not fail training.

State schema version 2 contains separate project/run entries. Legacy unscoped
`{"sent": [...]}` or corrupt files are rejected rather than silently reset.
Preserve old state and use a new `--state-file`; explicitly account for which
events were already sent before opting into a new watcher. This is not automatic
migration and may replay milestones. All watchers for one attempt must share
the same state file for locking/deduplication to work.

Sender and watcher default `--tail-lines 0`: no logs are attached, including when
zero is passed explicitly. A positive value is opt-in after reviewing the selected
content. Regex redaction is best effort only. SMTP acceptance followed by a client
timeout/crash can still cause a duplicate on retry; no exactly-once claim is made.
Use `assets/notify.env.example` only as a private configuration template, with
restricted access and no committed secrets. A dry-run proves formatting, not
SMTP reachability or inbox delivery.

## Transfer and finish

Run SCP locally; use uppercase `-P`. Precreate only the exact authorized target
directory when needed, keep outputs separate, and verify transferred size/hash.
For still-running jobs copy completed snapshots rather than actively written
artifacts. For many files an explicit archive/manifest can simplify checking;
do not change transfer scope or upload a replacement snapshot without applicable
authorization. A missing remote parser can be replaced by the verified interpreter
or a local parser for hash-identical content, with the evidence stated accurately.

Before releasing an instance, recover the required metrics, logs, manifests,
configs and requested models. Verify expected output IDs, parseability, finite
values, evaluator/protocol and artifact provenance. If incomplete, report the
missing stage and recovery route. Do not treat a copy command, exit 0, or a
success email as proof of the requested research result.

## Failure routing

| Symptom | First discriminating check |
| --- | --- |
| Local approval/Windows helper failure | Did any SSH process actually start? Preserve remote-state uncertainty |
| SSH timeout after launch | Inspect the same run/session/process identity before sending another launch |
| python3 missing | Locate the project's actual interpreter; do not reinstall speculatively |
| Cached weights trigger network retries | Compare working cache paths and loader settings; validate local/offline load |
| Config/remote source drift | Freeze matching inputs, isolate invalid rows, rerun under a coherent snapshot |
| Empty logs | Check buffering, expected phase duration, process identity and counters |
| OOM/NaN recurs after a fix | Reproduce the first failing batch and changed condition before another long run |
| Exit 0 but missing outputs | Reconcile expected IDs/stages and validate before marking experiment complete |
| Email failure | Keep training status separate; inspect notification state/config without exposing secrets |
