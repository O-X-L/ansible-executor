#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

PYTHONPATH=''

python3 -m pytest $@
