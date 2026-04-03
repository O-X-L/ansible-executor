#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

PYTHONPATH=''
export AR_TEST=1

python3 -m pytest $@
