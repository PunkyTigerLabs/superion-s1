#!/usr/bin/env bash
# Runs every snippet against the real API (4 requests). Needs SUPERION_API_KEY.
# Before the SDKs are on PyPI/npm: PYTHONPATH/NODE_PATH must point at local builds (see README).
set -euo pipefail
cd "$(dirname "$0")/.."
: "${SUPERION_API_KEY:?set SUPERION_API_KEY}"
PY=${PYTHON:-python3}
out=$(bash -c "$(sed -e 's/^export SUPERION_API_KEY=.*//' -e 's/^curl /curl -s /' quickstart.sh)"); echo "$out" | grep -q '"neg"' && echo "ok curl"
$PY quickstart.py | grep -q "neg" && echo "ok python sdk"
$PY quickstart_requests.py | grep -Eq "^0\.9" && echo "ok python requests"
node quickstart_fetch.mjs | grep -Eq "^0\.9" && echo "ok js fetch"
if [ -n "${SDK_JS_DIR:-}" ]; then
  tmp=$(mktemp -d); sed "s#@punkytigerlabs/superion-s1#$SDK_JS_DIR/dist/index.js#" quickstart.mjs > "$tmp/q.mjs"
  node "$tmp/q.mjs" | grep -q "neg" && echo "ok js sdk"; rm -rf "$tmp"
fi
