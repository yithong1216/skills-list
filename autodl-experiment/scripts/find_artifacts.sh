#!/usr/bin/env bash
set -euo pipefail

RUN_ROOT="${1:-.}"

find "${RUN_ROOT}" -maxdepth 5 \( \
  -name '*.csv' -o \
  -name '*.json' -o \
  -name '*.md' -o \
  -name '*.txt' -o \
  -name '*.yaml' -o \
  -name '*.yml' -o \
  -name '*.png' -o \
  -name '*.jpg' -o \
  -name '*.jpeg' -o \
  -name '*.pdf' -o \
  -name '*.pt' -o \
  -name '*.pth' -o \
  -name '*.ckpt' -o \
  -name '*.log' \
\) -type f -print 2>/dev/null | sort
