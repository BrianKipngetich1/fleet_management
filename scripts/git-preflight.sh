#!/usr/bin/env bash
set -euo pipefail

die() { printf 'Preflight failed: %s\n' "$*" >&2; exit 1; }
ROOT=${1:-$PWD}
CFG=$ROOT/.kaysalt/project.conf
[[ -f $CFG ]] || die "missing $CFG"

while IFS='=' read -r key value; do
	case $key in
		REPOSITORY_URL|MAIN_BRANCH|DEVELOP_BRANCH|WORKING_BRANCH_PREFIXES) printf -v "$key" '%s' "$value" ;;
	esac
done < "$CFG"

: "${REPOSITORY_URL:?missing REPOSITORY_URL}"
: "${MAIN_BRANCH:?missing MAIN_BRANCH}"
: "${DEVELOP_BRANCH:?missing DEVELOP_BRANCH}"
: "${WORKING_BRANCH_PREFIXES:?missing WORKING_BRANCH_PREFIXES}"
git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1 || die "not a Git repository"
ACTUAL=$(git -C "$ROOT" remote get-url origin 2>/dev/null) || die "origin is missing"
[[ $ACTUAL == "$REPOSITORY_URL" ]] || die "origin mismatch: expected $REPOSITORY_URL, found $ACTUAL"
[[ -z $(git -C "$ROOT" status --porcelain) ]] || die "working tree is not clean"

git -C "$ROOT" fetch origin --prune
BRANCH=$(git -C "$ROOT" branch --show-current)
[[ -n $BRANCH && $BRANCH != "$MAIN_BRANCH" && $BRANCH != "$DEVELOP_BRANCH" ]] || die "current branch must be a working branch"
valid=false
IFS=',' read -ra prefixes <<< "$WORKING_BRANCH_PREFIXES"
for prefix in "${prefixes[@]}"; do
	[[ $BRANCH == "$prefix/"* ]] && valid=true
done
$valid || die "branch $BRANCH does not use an allowed prefix"
git -C "$ROOT" show-ref --verify --quiet "refs/heads/$DEVELOP_BRANCH" || die "local $DEVELOP_BRANCH is missing"
git -C "$ROOT" show-ref --verify --quiet "refs/remotes/origin/$DEVELOP_BRANCH" || die "origin/$DEVELOP_BRANCH is missing"
[[ $(git -C "$ROOT" rev-list --left-right --count "$DEVELOP_BRANCH...origin/$DEVELOP_BRANCH") == $'0\t0' ]] || die "$DEVELOP_BRANCH and origin/$DEVELOP_BRANCH differ"
git -C "$ROOT" merge-base --is-ancestor "origin/$DEVELOP_BRANCH" HEAD || die "$BRANCH does not descend from origin/$DEVELOP_BRANCH"
printf 'Preflight passed for %s.\n' "$BRANCH"
