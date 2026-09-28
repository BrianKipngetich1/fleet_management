#!/usr/bin/env bash
# Migrates the main site (or the sites given) and reports any Locale drift.
set -euo pipefail
source "$(dirname "$0")/project-env.sh"

sites=("$@")
((${#sites[@]})) || { require_conf MAIN_SITE; sites=("$MAIN_SITE"); }
status=0
for site in "${sites[@]}"; do
	bench_run --site "$site" migrate
	drift=$(locale_drift "$site")
	if [[ -n $drift ]]; then
		printf 'Locale drift on %s:\n%s\n' "$site" "$drift" >&2
		status=1
	else
		printf 'Migrated %s; Locale matches.\n' "$site"
	fi
done
exit "$status"
