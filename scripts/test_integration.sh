#!/usr/bin/env bash

set -euo pipefail

ANSIBLE_CORE_VERSION='2.18'
PYTHONPATH=''

cd "$(dirname "$0")/.."
PATH_REPO="$(pwd)"

echo '### CREATING TMP VENV ###'
tmp_venv="/tmp/ar_venv_$(date +%s)"
python3 -m virtualenv "$tmp_venv" >/dev/null
source "${tmp_venv}/bin/activate"

echo '### INSTALLING DEPENDENCIES ###'
pip install "ansible-core==${ANSIBLE_CORE_VERSION}.*"

echo '### INSTALLING MODULE ###'
python3 -m pip install -e "$PATH_REPO" >/dev/null

echo '### RUNNING TESTS ###'
python3 "${PATH_REPO}/test/integration.py"

echo '### CLEANUP ###'
deactivate
rm -rf "$tmp_venv"
