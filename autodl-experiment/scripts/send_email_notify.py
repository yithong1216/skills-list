#!/usr/bin/env python3
"""Send SMTP notifications for AutoDL process events after user authorization.

Log content is excluded unless --tail-lines is positive. Redaction recognizes
only common secret patterns; it cannot safely sanitize arbitrary logs. Review
any opted-in log export and keep credentials and sensitive data out of logs.
SMTP acceptance is not proof of recipient delivery or experiment validation.
"""

from __future__ import annotations

import argparse
import os
import re
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path


SECRET_PATTERNS = [
    re.compile(r"github_pat_[A-Za-z0-9_]+"),
    re.compile(r"gho_[A-Za-z0-9_]+"),
    re.compile(r"hf_[A-Za-z0-9_\-]+"),
    re.compile(r"sk-[A-Za-z0-9_\-]+"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"BEGIN OPENSSH PRIVATE KEY"),
    re.compile(r"(?i)(password|passwd|token|api[_-]?key|secret)\s*=\s*\S+"),
]


EVENT_LABELS = {
    "started": "started",
    "progress": "progress",
    "progress_25": "25%",
    "progress_50": "50%",
    "progress_75": "75%",
    "progress_90": "90%",
    "progress_100": "100%",
    "success": "success",
    "failed": "failed",
    "heartbeat": "heartbeat",
}


def load_env_file(path: str | None) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path:
        return values
    env_path = Path(path)
    if not env_path.exists():
        return values
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def env_value(name: str, env_file_values: dict[str, str], default: str = "") -> str:
    return os.environ.get(name) or env_file_values.get(name) or default


def as_bool(value: str) -> bool:
    return value.strip().lower() not in {"0", "false", "no", "off"}


def redact(text: str) -> str:
    """Best-effort masking of common patterns, not a secure log sanitizer."""
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def read_tail(path: str | None, lines: int) -> str:
    if not path or lines <= 0:
        return ""
    log_path = Path(path)
    if not log_path.exists():
        return ""
    content = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:])


def build_message(args: argparse.Namespace, env_values: dict[str, str]) -> EmailMessage:
    mail_from = env_value("MAIL_FROM", env_values) or env_value("SMTP_USER", env_values)
    mail_to = env_value("MAIL_TO", env_values)
    event_label = EVENT_LABELS.get(args.event, args.event)
    subject = f"[AutoDL][{args.project}][{args.run_id}] {event_label}"

    body_parts = [
        f"Project: {args.project}",
        f"Run ID: {args.run_id}",
        f"Event: {args.event}",
    ]
    if args.progress is not None:
        body_parts.append(f"Progress: {args.progress:g}%")
    if args.run_root:
        body_parts.append(f"Run root: {args.run_root}")
    if args.summary:
        body_parts.append(f"Summary: {args.summary}")
    if args.next_command:
        body_parts.append(f"Next command: {args.next_command}")
    tail = read_tail(args.log_file, args.tail_lines)
    if tail:
        body_parts.extend(["", "Latest log tail (best-effort redaction only):", redact(tail)])

    msg = EmailMessage()
    msg["Subject"] = redact(subject)
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg.set_content(redact("\n".join(body_parts)))
    return msg


def validate_config(env_values: dict[str, str]) -> None:
    required = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "MAIL_TO"]
    missing = [name for name in required if not env_value(name, env_values)]
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(f"Missing SMTP configuration: {joined}")


def send_message(msg: EmailMessage, env_values: dict[str, str]) -> None:
    host = env_value("SMTP_HOST", env_values)
    port = int(env_value("SMTP_PORT", env_values, "587"))
    user = env_value("SMTP_USER", env_values)
    password = env_value("SMTP_PASSWORD", env_values)
    use_tls = as_bool(env_value("SMTP_TLS", env_values, "true"))

    if use_tls and port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
            server.login(user, password)
            refused = server.send_message(msg)
            if refused:
                raise smtplib.SMTPRecipientsRefused(refused)
        return

    with smtplib.SMTP(host, port, timeout=30) as server:
        server.ehlo()
        if use_tls:
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
        server.login(user, password)
        refused = server.send_message(msg)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--progress", type=float)
    parser.add_argument("--summary", default="")
    parser.add_argument("--run-root", default="")
    parser.add_argument("--log-file", default="")
    parser.add_argument("--tail-lines", type=int, default=0, help="Opt in to N log lines; redaction is best effort only")
    parser.add_argument("--next-command", default="")
    parser.add_argument("--env-file", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.tail_lines < 0:
        parser.error("tail-lines must be nonnegative")

    env_values = load_env_file(args.env_file)
    if not args.dry_run:
        validate_config(env_values)
    msg = build_message(args, env_values)

    if args.dry_run:
        print("DRY RUN: email would be sent")
        print(f"Subject: {msg['Subject']}")
        print(f"From: {msg['From'] or '<missing>'}")
        print(f"To: {msg['To'] or '<missing>'}")
        print("")
        print(msg.get_content())
        return 0

    try:
        send_message(msg, env_values)
    except (OSError, smtplib.SMTPException, ValueError) as exc:
        # Do not echo SMTP server responses, which may contain message details.
        print(f"SMTP delivery not confirmed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(f"SMTP accepted: {msg['Subject']} -> {msg['To']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
