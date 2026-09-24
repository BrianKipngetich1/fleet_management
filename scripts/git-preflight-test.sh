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
"$SCRIPT" "$TMP/app"
printf 'git-preflight self-check passed\n'
