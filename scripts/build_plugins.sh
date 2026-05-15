#!/bin/bash

set -e

if [ -z "$1" ]
then
  echo "ERROR: Version required"
  exit 1
fi

VERSION="$1"

cd "$(dirname "$0")/../plugins_module"
echo "$VERSION" > VERSION
rm -rf dist/*

# bash scripts/update_version.sh
python3 -m pip install -r ../requirements_build.txt >/dev/null
python3 -m build
# python3 -m twine upload --repository pypi dist/*
