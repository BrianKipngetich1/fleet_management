#!/usr/bin/env bash
set -euo pipefail

SCRIPT=$(cd "$(dirname "$0")" && pwd)/git-preflight.sh
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
git init --bare -q "$TMP/remote.git"
git clone -q "$TMP/remote.git" "$TMP/app"
git -C "$TMP/app" config user.name Test
git -C "$TMP/app" config user.email test@example.com
printf 'starter\n' > "$TMP/app/README.md"
git -C "$TMP/app" add README.md
git -C "$TMP/app" commit -qm bootstrap
git -C "$TMP/app" branch -M main
git -C "$TMP/app" push -qu origin main
git -C "$TMP/app" switch -qc develop
git -C "$TMP/app" push -qu origin develop
git -C "$TMP/app" switch -qc feature/test
mkdir -p "$TMP/app/.kaysalt"
cat > "$TMP/app/.kaysalt/project.conf" <<EOF
REPOSITORY_URL=$TMP/remote.git
MAIN_BRANCH=main
DEVELOP_BRANCH=develop
WORKING_BRANCH_PREFIXES=feature,fix,refactor,chore
EOF
git -C "$TMP/app" add .kaysalt/project.conf
git -C "$TMP/app" commit -qm config
git -C "$TMP/app" push -qu origin feature/test
export KAYSALT_AGENT_HOME=$TMP/agent
mkdir -p "$TMP/agent/policy"
printf '# Kaysalt workflow\n\nStep one.\n' > "$TMP/agent/policy/KAYSALT_WORKFLOW.md"
(cd "$TMP/app" && "$SCRIPT" "$TMP/app")

mkdir -p "$TMP/elsewhere"
if (cd "$TMP/elsewhere" && "$SCRIPT" "$TMP/app") 2>/dev/null; then
	printf 'preflight passed outside the repository\n' >&2
	exit 1
fi

mkdir -p "$TMP/bench/apps" "$TMP/bench/sites"
bench_output=$(cd "$TMP/bench" && "$SCRIPT" "$TMP/app" 2>&1)
[[ $bench_output == *'started at a bench root'* ]]

stale_output=$(cd "$TMP/app" && "$SCRIPT" "$TMP/app" 2>&1)
[[ $stale_output == *'workflow in AGENTS.md is missing or stale'* ]]
{
	printf '# Rules\n\n<!-- kaysalt:workflow:begin -->\n'
	cat "$TMP/agent/policy/KAYSALT_WORKFLOW.md"
	printf '<!-- kaysalt:workflow:end -->\n'
} > "$TMP/app/AGENTS.md"
git -C "$TMP/app" add AGENTS.md
git -C "$TMP/app" commit -qm agents
current_output=$(cd "$TMP/app" && "$SCRIPT" "$TMP/app" 2>&1)
[[ $current_output != *'stale'* ]]

git clone -q "$TMP/remote.git" "$TMP/other"
git -C "$TMP/other" switch -q develop
git -C "$TMP/other" -c user.name=Test -c user.email=test@example.com commit -q --allow-empty -m moved
git -C "$TMP/other" push -q origin develop
git -C "$TMP/app" fetch -q origin develop:develop
moved_output=$(cd "$TMP/app" && "$SCRIPT" "$TMP/app" 2>&1)
[[ $moved_output == *'has moved on'* && $moved_output == *'Preflight passed'* ]]
printf 'git-preflight self-check passed\n'
