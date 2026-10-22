#!/usr/bin/env python3
"""Append a sanitized AutoDL experiment lesson to a project runbook."""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path


MARKER = "## 经验日志"
SECRET_PATTERNS = [
    re.compile(r"github_pat_[A-Za-z0-9_]+"),
    re.compile(r"gho_[A-Za-z0-9_]+"),
    re.compile(r"hf_[A-Za-z0-9_\-]+"),
    re.compile(r"sk-[A-Za-z0-9_\-]+"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"BEGIN OPENSSH PRIVATE KEY"),
    re.compile(r"(?i)(password|passwd|token|api[_-]?key|secret)\s*=\s*\S+"),
]


def clean(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip()
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default="docs/AUTODL_EXPERIMENT_RUNBOOK.md")
    parser.add_argument("--event", required=True)
    parser.add_argument("--problem", default="")
    parser.add_argument("--cause", default="")
    parser.add_argument("--fix", default="")
    parser.add_argument("--evidence", default="")
    parser.add_argument("--next", default="")
    args = parser.parse_args()

    path = Path(args.file)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        text = "# AutoDL 实验运行手册\n\n## 经验日志\n"

    if MARKER not in text:
        text = text.rstrip() + f"\n\n{MARKER}\n"

    timestamp = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    lines = ["", f"### {timestamp} - {clean(args.event)}"]
    for label, value in [
        ("问题", args.problem),
        ("原因", args.cause),
        ("解决方式", args.fix),
        ("证据", args.evidence),
        ("后续动作", args.next),
    ]:
        cleaned = clean(value)
        if cleaned:
            lines.append(f"- {label}: {cleaned}")

    path.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
