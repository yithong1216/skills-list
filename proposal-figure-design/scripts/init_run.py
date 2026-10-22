#!/usr/bin/env python3
"""Create a non-destructive proposal-figure run from bundled Markdown templates."""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path


TEMPLATES = (
    "01-content-spec.md",
    "02-reference-selection.md",
    "03-image-prompt.md",
    "04-feedback-log.md",
)


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "-", value.strip()).strip("-_")
    return slug or "proposal-figure"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="task name used for the run folder")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument(
        "--templates",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "assets" / "templates",
    )
    args = parser.parse_args()

    for filename in TEMPLATES:
        if not (args.templates / filename).is_file():
            parser.error(f"missing template: {args.templates / filename}")

    base = args.workspace / "proposal-figure-runs"
    requested = base / safe_slug(args.name)
    run_dir = requested
    if run_dir.exists():
        run_dir = base / f"{safe_slug(args.name)}-{datetime.now():%Y%m%d-%H%M%S}"

    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "images").mkdir()
    (run_dir / "editable").mkdir()
    for filename in TEMPLATES:
        shutil.copy2(args.templates / filename, run_dir / filename)

    print(run_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
