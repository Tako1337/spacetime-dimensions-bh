#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m src.benchmark --config configs/config.yaml "${1:---sample}"
