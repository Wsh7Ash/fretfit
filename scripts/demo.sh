#!/usr/bin/env bash
# Demo gate for fretfit: exercises the documented behaviour end to end.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

tmp=".demo-tmp"
rm -rf "$tmp"
mkdir -p "$tmp"
fail=0

check() {
  if [ "$1" -eq "$2" ]; then
    echo "ok: $3"
  else
    echo "FAIL: $3 (exit $1, expected $2)"
    fail=1
  fi
}

python -m fretfit fit --input examples/six-string.json --json "$tmp/report.json" >"$tmp/six.txt" 2>&1
check $? 0 "individual fit meets the tolerance"

grep -q "status: within-tolerance" "$tmp/six.txt"
check $? 0 "reports the tolerance verdict"

grep -q "single-point rule" "$tmp/six.txt"
check $? 0 "shows the single-point comparison"

python -m fretfit fit --input examples/straight-saddle.json >"$tmp/straight.txt" 2>&1
check $? 0 "a true straight saddle meets the tolerance"

grep -q "one straight saddle line meets the tolerance" "$tmp/straight.txt"
check $? 0 "prints the straight-saddle verdict"

python -m fretfit fit --input examples/straight-mismatch.json >"$tmp/mismatch.txt" 2>&1
check $? 1 "independent offsets fail a straight saddle"

grep -q "individual" "$tmp/mismatch.txt"
check $? 0 "explains that individual saddles are needed"

python -m fretfit verify "$tmp/report.json" >"$tmp/verify.txt" 2>&1
check $? 0 "verifier accepts the fresh report"

grep -q "verify: ok" "$tmp/verify.txt"
check $? 0 "verifier prints its verdict"

python - "$tmp/report.json" "$tmp/tampered.json" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
payload["result"]["strings"][0]["nut_mm"] += 0.5
json.dump(payload, open(sys.argv[2], "w", encoding="utf-8"))
PY

python -m fretfit verify "$tmp/tampered.json" >"$tmp/tampered.txt" 2>&1
check $? 1 "verifier rejects a tampered offset"

grep -q "verify: FAILED" "$tmp/tampered.txt"
check $? 0 "verifier explains the rejection"

if [ "$fail" -ne 0 ]; then
  echo "demo: FAILED"
  exit 1
fi
echo "demo: all checks passed"
