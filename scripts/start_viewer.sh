#!/bin/sh
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_root"
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi
if ! .venv/bin/python -c 'import trimesh, numpy' >/dev/null 2>&1; then
    .venv/bin/python -m pip install -r requirements.txt
fi
cd viewer
if [ ! -f node_modules/.processor-lock ] || ! cmp -s package-lock.json node_modules/.processor-lock; then
    npm ci
    cp package-lock.json node_modules/.processor-lock
fi
npm run build
cd "$project_root"
exec .venv/bin/python scripts/viewer_server.py "$@"
