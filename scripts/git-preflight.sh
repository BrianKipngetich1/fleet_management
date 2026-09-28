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

grep -q "^REPOSITORY_URL=" "$CFG" || die "missing REPOSITORY_URL"
: "${MAIN_BRANCH:?missing MAIN_BRANCH}"
: "${DEVELOP_BRANCH:?missing DEVELOP_BRANCH}"
: "${WORKING_BRANCH_PREFIXES:?missing WORKING_BRANCH_PREFIXES}"
git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1 || die "not a Git repository"
warn() { printf 'Preflight warning: %s\n' "$*" >&2; }
ROOT_REAL=$(cd "$ROOT" && pwd -P)
HERE=$(pwd -P)
if [[ -d $HERE/apps && -d $HERE/sites ]]; then
	warn "started at a bench root; start agents from the app repository ($ROOT_REAL) except to create a new app"
elif [[ $HERE != "$ROOT_REAL" && $HERE != "$ROOT_REAL"/* ]]; then
	die "working directory $HERE is outside the repository; start the agent from $ROOT_REAL"
fi
WORKFLOW=${KAYSALT_AGENT_HOME:-$HOME/.kaysalt-agent}/policy/KAYSALT_WORKFLOW.md
if [[ -f $WORKFLOW ]]; then
	rendered=$(awk '/^<!-- kaysalt:workflow:begin/ { on = 1; next } /^<!-- kaysalt:workflow:end/ { on = 0 } on' "$ROOT/AGENTS.md" 2>/dev/null || true)
	[[ $rendered == "$(cat "$WORKFLOW")" ]] ||
		warn "the Kaysalt workflow in AGENTS.md is missing or stale; re-run the project installer"
fi
# An empty REPOSITORY_URL means the app is local only until repository-bootstrap.sh --publish.
LOCAL_ONLY=false
if [[ -z ${REPOSITORY_URL:-} ]]; then
	LOCAL_ONLY=true
	git -C "$ROOT" remote get-url origin >/dev/null 2>&1 && die "origin is set but REPOSITORY_URL is empty in $CFG"
	warn "no repository yet; work stays local until the requester asks for one"
else
	ACTUAL=$(git -C "$ROOT" remote get-url origin 2>/dev/null) || die "origin is missing"
	[[ $ACTUAL == "$REPOSITORY_URL" ]] || die "origin mismatch: expected $REPOSITORY_URL, found $ACTUAL"
fi
[[ -z $(git -C "$ROOT" status --porcelain) ]] || die "working tree is not clean"

$LOCAL_ONLY || git -C "$ROOT" fetch origin --prune
BRANCH=$(git -C "$ROOT" branch --show-current)
[[ -n $BRANCH && $BRANCH != "$MAIN_BRANCH" && $BRANCH != "$DEVELOP_BRANCH" ]] || die "current branch must be a working branch"
valid=false
IFS=',' read -ra prefixes <<< "$WORKING_BRANCH_PREFIXES"
for prefix in "${prefixes[@]}"; do
	[[ $BRANCH == "$prefix/"* ]] && valid=true
done
$valid || die "branch $BRANCH does not use an allowed prefix"
git -C "$ROOT" show-ref --verify --quiet "refs/heads/$DEVELOP_BRANCH" || die "local $DEVELOP_BRANCH is missing"
if $LOCAL_ONLY; then
	printf 'Preflight passed for %s (local only).\n' "$BRANCH"
	exit 0
fi
git -C "$ROOT" show-ref --verify --quiet "refs/remotes/origin/$DEVELOP_BRANCH" || die "origin/$DEVELOP_BRANCH is missing"
[[ $(git -C "$ROOT" rev-list --left-right --count "$DEVELOP_BRANCH...origin/$DEVELOP_BRANCH") == $'0\t0' ]] || die "$DEVELOP_BRANCH and origin/$DEVELOP_BRANCH differ"
git -C "$ROOT" merge-base --is-ancestor "origin/$DEVELOP_BRANCH" HEAD ||
	warn "$DEVELOP_BRANCH has moved on since $BRANCH started; merge it in if needed, never rebase a pushed branch"
printf 'Preflight passed for %s.\n' "$BRANCH"
