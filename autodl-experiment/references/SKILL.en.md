# AutoDL Experiment: English workflow

The canonical entrypoint is [SKILL.md](../SKILL.md). Recover state, freeze inputs,
test the actual entrypoint, launch once, monitor or repair from evidence, then
validate and pull back. SSH acknowledgement, process termination, and experiment
acceptance are separate facts.

## Scope and state

Infer configuration from the user, current runbook, scripts, and artifacts. Keep
existing authorization; ask only for missing information that changes the next
action. Launch-only finishes after verified startup. Read-only queries do not
authorize environment changes, downloads, restarts, or signals. End-to-end work
requires the requested validation and artifact recovery.

Record exact host/port, run/attempt, workdir, interpreter, source/config/data/model
identities, cache, session/PID and start identity, log/exit/artifact paths, last
observation time, stage dependencies, deadline/timezone, budget, and next action.
Memory locates evidence; it does not establish current remote state.

## Preflight and launch

Compare local and remote source first. Freeze inputs read during a run; do not
edit live configs and mix incompatible rows. Without Git use a scoped inventory
and hashes. Use the actual interpreter; never silently fall back to base. Check
CUDA operation and required imports/operators, then smoke the actual CLI, workdir,
loader and save path. Package discovery alone is not readiness. Match data IDs
and protocol. Measure real-compute memory and throughput with explicit units and
respect project constraints without ballast. Budget concurrency across resources.

Reuse verified cache/model snapshots. An empty new cache can trigger needless
network retries; test the exact loader. Use offline mode only with the required
assets locally verified. Count preparation, training, evaluation and pullback
against the same deadline, reserving time for the final checks.

Use tmux/screen or the existing job manager. Scripts set their own workdir and
environment. New attempts have separate state/logs. The wrapper refuses existing
run state and records process identity and an atomic exit code. Verify first
useful work after dispatch. Reconcile a timed-out launch against that same run
before retrying. Stage chaining needs the complete result and declared gate.

## Monitoring and recovery

Distinguish local tool/approval failure, SSH failure, shell/runtime, cache/data,
training, and evaluator problems. A failed observation does not establish job
failure. Empty logs may be buffered. A matching PID proves process liveness, not
progress. Shared GPU activity is weaker still. Missing session/PID without a
terminal record means interrupted or UNKNOWN.

Observe at a useful cadence and back off unchanged checks. After repeated failure,
change the diagnosis or repair the demonstrated boundary before another run.
Preserve logs, downloads, caches and checkpoints; verify checkpoint/protocol before
resume. Signal only an identified owned process within scope, never broad Python
groups. Continue independent authorized work while blocked.

`monitor_run.sh` is one snapshot. Future monitoring needs an authorized remote
watcher or host automation actually registered and checked; a chat promise does
not create one.

## Notifications and completion

Email is opt-in, with wrapper default off. Existing SMTP settings do not authorize
messages. Use declared overall progress rather than arbitrary accuracy/batch bars.
Terminal process status comes from an exit code, not error-looking log text.
Failed delivery remains retryable; dry-run leaves production state unchanged.
SMTP retry ambiguity prevents an exactly-once external delivery guarantee.

Raw log tails are off by default. Redaction is best effort; review authorized
content before sending. Never expose credentials in commands, records, full
environment dumps, or public artifacts.

Pull back scoped completed files early and verify hashes and local parsing.
Process exit zero does not prove coverage, official evaluation, or metric
acceptance. Preserve the target and report unmet requirements. Do not implicitly
clean up or shut down the server. Final status separates process state, experiment
acceptance, notification delivery, recovered files and remaining work.
