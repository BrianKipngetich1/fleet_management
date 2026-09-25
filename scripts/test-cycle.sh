#!/usr/bin/env bash
# One full local test session on a disposable test site:
#   build it from the sample data → backend tests → Playwright Desk suite → throw it away.
#
#   scripts/test-cycle.sh          # the whole cycle; the site is removed even when a check fails
#   scripts/test-cycle.sh --keep   # leave the site up afterwards, e.g. for an agent-browser walkthrough
#
# An agent-browser walkthrough runs between `bench fleet-test-site up` and `down` by hand; this
# script is the automated part. See CLAUDE.md "UI verification".
set -euo pipefail

APP_DIR=$(cd "$(dirname "$0")/.." && pwd)
BENCH_ROOT=${BENCH_ROOT:-$(cd "$APP_DIR/../.." && pwd)}
SITE=fleet_management-test.localhost
KEEP=0
[[ ${1:-} == --keep ]] && KEEP=1

cd "$BENCH_ROOT"
bench fleet-test-site up --replace
if (( ! KEEP )); then
	trap 'cd "$BENCH_ROOT" && bench fleet-test-site down' EXIT
fi

bench --site "$SITE" run-tests --app fleet_management
(cd "$APP_DIR" && npx playwright test)
