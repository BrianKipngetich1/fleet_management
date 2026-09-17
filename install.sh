#!/usr/bin/env bash
# Copy the starter kit into a Frappe app repository. Never overwrites an existing file.
set -euo pipefail

REPO=krystallinesalt/Frappe-Starter-Kit
ITEMS=(AGENTS.md CLAUDE.md PROGRESS.md README.md specs .github e2e playwright.config.ts package.json)
GITIGNORE_MARKER='specs/*/verification/screenshots/'

die() { printf '%s\n' "$*" >&2; exit 1; }

find_bench() {
	local d=$PWD
	while [[ $d != / ]]; do
		[[ -d $d/apps && -d $d/sites ]] && { printf '%s' "$d"; return; }
		d=$(dirname "$d")
	done
}

DEST=${1:-}
if [[ -z $DEST ]]; then
	bench=$(find_bench)
	[[ -n $bench ]] && printf 'Bench root: %s\n' "$bench"
	read -rp "App folder name${bench:+ under $bench/apps}: " name
	[[ -n $name ]] || die "No name given."
	DEST=${bench:+$bench/apps/}$name
fi

[[ -d $DEST ]] || die "Not a directory: $DEST
Create the app first (bench new-app), then re-run."
DEST=$(cd "$DEST" && pwd)

SRC=$(mktemp -d)
trap 'rm -rf "$SRC"' EXIT
if command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
	gh repo clone "$REPO" "$SRC/kit" -- --depth 1 --quiet
else
	git clone --depth 1 --quiet "git@github.com:$REPO.git" "$SRC/kit"
fi
cd "$SRC/kit"

copied=() skipped=()
while IFS= read -r f; do
	if [[ -e $DEST/$f ]]; then skipped+=("$f"); else
		install -Dm644 "$f" "$DEST/$f"
		copied+=("$f")
	fi
done < <(find "${ITEMS[@]}" -type f | sort)

if grep -qF "$GITIGNORE_MARKER" "$DEST/.gitignore" 2>/dev/null; then
	ignore="already present"
else
	cat gitignore-additions.txt >> "$DEST/.gitignore"
	ignore="appended to .gitignore"
fi

printf '\nInstalled into %s\n' "$DEST"
printf '  %d file(s) copied, .gitignore rules %s\n' "${#copied[@]}" "$ignore"
if ((${#skipped[@]})); then
	printf '\nKept your existing file(s) — merge by hand if the kit version is wanted:\n'
	printf '  %s\n' "${skipped[@]}"
fi
printf '\nNext: fill the bracketed values in %s/CLAUDE.md\n' "$DEST"
