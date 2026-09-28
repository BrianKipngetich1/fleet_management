#!/usr/bin/env bash
# Opens agent-browser on the test site signed in as USER, through e2e/sid.ts. Prints no secret.
set -euo pipefail
source "$(dirname "$0")/project-env.sh"

user=${1:?Usage: ab-login.sh USER_EMAIL [PATH]}
path=${2:-/app}
require_conf TEST_SITE TEST_SITE_URL
printf -v PC_SID_CMD 'cd %q && BROWSER=echo %s bench browse %q --user "$PC_USER"' \
	"$BENCH_ROOT" "${BENCH_EXEC:-}" "$TEST_SITE"
export PC_SID_CMD
sid=$(cd "$PROJECT_ROOT" && node --experimental-strip-types --no-warnings -e \
	'import("./e2e/sid.ts").then((m) => console.log(m.mintSid(process.argv[1])))' "$user")
agent-browser cookies set sid "$sid" --url "$TEST_SITE_URL" >/dev/null
agent-browser open "$TEST_SITE_URL$path" >/dev/null
printf 'agent-browser is signed in to %s as %s.\n' "$TEST_SITE" "$user"
