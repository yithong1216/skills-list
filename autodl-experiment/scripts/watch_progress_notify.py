#!/usr/bin/env python3
"""Watch explicit overall progress and authoritative process exit status.

Use a dedicated progress file containing one percentage (e.g. 37.5 or 37.5%),
or emit a standalone AUTODL_PROGRESS=37.5 log line. Ordinary epoch, tqdm, and
accuracy text is not an overall progress contract. Write inputs atomically.

State locking prevents concurrent local sends; it cannot provide exactly-once
SMTP delivery. A server may accept a message before a timeout or state-write
failure, so a later retry can duplicate it. Use unique run IDs and fresh run
directories. Missing/malformed exit markers are unknown, not process failure.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path


PROGRESS_VALUE = r"(\d+(?:\.\d+)?)\s*%?"


def read_text(path: str | None) -> str:
    if not path:
        return ""
    file_path = Path(path)
    if not file_path.exists():
        return ""
    return file_path.read_text(encoding="utf-8", errors="replace")


def parse_thresholds(value: str) -> list[float]:
    thresholds: list[float] = []
    for part in value.split(","):
        part = part.strip().rstrip("%")
        if not part:
            continue
        number = float(part)
        if 0 <= number <= 100:
            thresholds.append(number)
    return sorted(set(thresholds))


def parse_progress_from_text(text: str) -> float | None:
    progress = None
    for line in text.splitlines():
        match = re.fullmatch(r"\s*AUTODL_PROGRESS\s*=\s*" + PROGRESS_VALUE + r"\s*", line)
        if match:
            value = float(match.group(1))
            progress = value if 0 <= value <= 100 else None
    return progress


def parse_progress(progress_file: str | None, log_text: str) -> float | None:
    if progress_file:
        match = re.fullmatch(r"\s*" + PROGRESS_VALUE + r"\s*", read_text(progress_file))
        if match:
            value = float(match.group(1))
            return value if 0 <= value <= 100 else None
        return None
    return parse_progress_from_text(log_text)


def detect_failure(log_text: str, exit_code_file: str | None) -> tuple[bool, str]:
    raw = read_text(exit_code_file).strip()
    if not re.fullmatch(r"[+-]?\d+", raw):
        return False, ""
    code = int(raw)
    return code != 0, f"exit_code={code}"


def load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"schema_version": 2, "runs": {}}
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or state.get("schema_version") != 2 or not isinstance(state.get("runs"), dict):
        raise ValueError("Invalid or legacy notification state; preserve it and use a fresh --state-file")
    return state


def save_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".tmp-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def state_lock(path: Path):
    """OS-managed lock releases on process exit; retain its inode for other waiters."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_name(path.name + ".lock").open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            if os.fstat(handle.fileno()).st_size == 0:
                handle.write(b"\0")
                handle.flush()
            lock = lambda: msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            unlock = lambda: msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            lock = lambda: fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            unlock = lambda: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        deadline = time.monotonic() + 10
        while True:
            handle.seek(0)
            try:
                lock()
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Another watcher holds the notification state lock")
                time.sleep(0.05)
        try:
            yield
        finally:
            handle.seek(0)
            unlock()


def state_path(args: argparse.Namespace) -> Path:
    if args.state_file:
        return Path(args.state_file)
    if args.run_root:
        return Path(args.run_root) / "notify_state.json"
    if args.log_file:
        return Path(args.log_file).parent / "notify_state.json"
    return Path("notify_state.json")


def send_alert(args: argparse.Namespace, event: str, progress: float | None, summary: str) -> bool:
    script = Path(__file__).with_name("send_email_notify.py")
    command = [
        sys.executable,
        str(script),
        "--event",
        event,
        "--project",
        args.project,
        "--run-id",
        args.run_id,
        "--summary",
        summary,
    ]
    if progress is not None:
        command += ["--progress", f"{progress:g}"]
    if args.run_root:
        command += ["--run-root", args.run_root]
    if args.log_file:
        command += ["--log-file", args.log_file]
    command += ["--tail-lines", str(getattr(args, "tail_lines", 0))]
    if args.env_file:
        command += ["--env-file", args.env_file]
    if args.dry_run:
        command.append("--dry-run")

    try:
        result = subprocess.run(command, check=False, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"notification transport failed: {type(exc).__name__}", file=sys.stderr)
        return False
    return result.returncode == 0


def check_once(args: argparse.Namespace) -> tuple[bool, bool]:
    """Return (terminal status observed, all due notifications delivered)."""
    path = state_path(args)
    # A preview neither reads nor writes production deduplication state.
    if args.dry_run:
        return check_locked(args, path, {"schema_version": 2, "runs": {}})
    with state_lock(path):
        return check_locked(args, path, load_state(path))


def check_locked(args: argparse.Namespace, path: Path, state: dict) -> tuple[bool, bool]:
    key = json.dumps([args.project, args.run_id])
    run = state["runs"].setdefault(key, {"project": args.project, "run_id": args.run_id, "sent": []})
    if (not isinstance(run, dict) or run.get("project") != args.project or run.get("run_id") != args.run_id
            or not isinstance(run.get("sent"), list) or not all(isinstance(item, str) for item in run["sent"])):
        raise ValueError("Notification state project/run identity or sent list is invalid")
    sent = set(run["sent"])
    log_text = read_text(args.log_file)
    progress = parse_progress(args.progress_file, log_text)
    failed, reason = detect_failure(log_text, args.exit_code_file)
    terminal = bool(reason)
    due = []
    if terminal:
        event = "failed" if failed else "success"
        if event not in sent:
            summary = (f"Process exited with {reason}; experiment results require separate validation")
            due.append((event, event, summary))
    elif not sent.intersection({"failed", "success"}) and progress is not None:
        for threshold in parse_thresholds(args.thresholds):
            event_key = f"progress_{threshold:g}"
            if progress >= threshold and event_key not in sent:
                event = f"progress_{int(threshold)}" if threshold.is_integer() else "progress"
                due.append((event_key, event, f"Overall progress reached {progress:.1f}%"))
    delivered = True
    for event_key, event, summary in due:
        if not send_alert(args, event, progress, summary):
            delivered = False
            continue
        if not args.dry_run:
            sent.add(event_key)
            run["sent"] = sorted(sent)
            # Commit each accepted send before attempting the next event.
            save_state(path, state)
    if not args.dry_run:
        run["last_progress"] = progress
        run["updated_at"] = int(time.time())
        save_state(path, state)
    print(f"state={path} progress={progress} sent={','.join(sorted(sent))} delivered={delivered}")
    return terminal, delivered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-root", default="")
    parser.add_argument("--log-file", default="")
    parser.add_argument("--progress-file", default="", help="Dedicated file with one percentage, 0..100, optional %%")
    parser.add_argument("--exit-code-file", default="", help="Atomic integer process status: 0 success, nonzero failure")
    parser.add_argument("--state-file", default="")
    parser.add_argument("--thresholds", default="50,75,100")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--env-file", default="")
    parser.add_argument("--tail-lines", type=int, default=0, help="Opt in to exporting N log lines; redaction is best effort only")
    parser.add_argument("--terminal-attempts", type=int, default=3)
    parser.add_argument("--retry-interval", type=int, default=5)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.terminal_attempts < 1 or args.retry_interval < 0 or args.tail_lines < 0:
        parser.error("terminal-attempts must be positive; retry-interval and tail-lines must be nonnegative")
    terminal_attempts = 0
    while True:
        try:
            terminal, delivered = check_once(args)
        except (OSError, ValueError) as exc:
            print(f"notification state/input error: {exc}", file=sys.stderr)
            return 1
        if args.once or args.dry_run:
            return 0 if delivered else 1
        if terminal:
            terminal_attempts += 1
            if delivered:
                return 0
            if terminal_attempts >= args.terminal_attempts:
                print("terminal notification remains unsent; rerun watcher to retry", file=sys.stderr)
                return 1
        time.sleep(args.retry_interval if terminal else max(5, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
