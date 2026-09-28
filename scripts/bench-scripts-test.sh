#!/usr/bin/env bash
# Self-check for migrate.sh and rebuild-test-site.sh against a stub bench behind BENCH_EXEC.
set -euo pipefail

SCRIPTS=$(cd "$(dirname "$0")" && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bench/sites/shop-test.localhost" "$TMP/bench/apps/shop" "$TMP/app/.kaysalt" "$TMP/bin"
cp "$SCRIPTS"/project-env.sh "$SCRIPTS"/migrate.sh "$SCRIPTS"/rebuild-test-site.sh "$TMP/app/"
mkdir -p "$TMP/app/scripts"
mv "$TMP/app"/*.sh "$TMP/app/scripts/"

cat > "$TMP/bin/exec-prefix" <<'EOF'
#!/usr/bin/env bash
printf 'via-prefix %s\n' "$*" >> "$BENCH_LOG"
exec "$@"
EOF
cat > "$TMP/bin/bench" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$BENCH_LOG"
if [[ $* == *get_singles_dict* ]]; then
	printf '{"country": "Portugal", "time_zone": "%s", "currency": "EUR", "date_format": "dd/mm/yyyy"}\n' "$STUB_TZ"
fi
EOF
chmod 755 "$TMP/bin/exec-prefix" "$TMP/bin/bench"
export PATH=$TMP/bin:$PATH BENCH_LOG=$TMP/bench.log STUB_TZ=Europe/Lisbon

cat > "$TMP/app/.kaysalt/project.conf" <<EOF
APP_NAME=shop
MAIN_SITE=shop.localhost
TEST_SITE=shop-test.localhost
BENCH_ROOT=$TMP/bench
BENCH_EXEC=exec-prefix
LOCALE_COUNTRY=Portugal
LOCALE_TIME_ZONE=Europe/Lisbon
LOCALE_CURRENCY=EUR
LOCALE_DATE_FORMAT=dd/mm/yyyy
LOCALE_LANGUAGE=Portuguese
EOF

"$TMP/app/scripts/migrate.sh" | grep -q 'Migrated shop.localhost; Locale matches.'
grep -qxF -- '--site shop.localhost migrate' "$BENCH_LOG"
grep -q '^via-prefix bench --site shop.localhost migrate$' "$BENCH_LOG"

if STUB_TZ=America/New_York "$TMP/app/scripts/migrate.sh" >/dev/null 2>"$TMP/drift.err"; then
	printf 'migrate.sh passed with a wrong time zone\n' >&2
	exit 1
fi
grep -q "time_zone: site has 'America/New_York', Locale says 'Europe/Lisbon'" "$TMP/drift.err"

if KAYSALT_DB_ROOT_PASSWORD=root KAYSALT_TEST_ADMIN_PASSWORD=secret \
	"$TMP/app/scripts/rebuild-test-site.sh" >/dev/null 2>&1; then
	printf 'rebuild-test-site.sh accepted a password without "test"\n' >&2
	exit 1
fi

: > "$BENCH_LOG"
KAYSALT_DB_ROOT_PASSWORD=root KAYSALT_TEST_ADMIN_PASSWORD=admin-test \
	"$TMP/app/scripts/rebuild-test-site.sh" >/dev/null
grep -q '^drop-site shop-test.localhost --force --no-backup' "$BENCH_LOG"
grep -q '^new-site shop-test.localhost .*--install-app shop$' "$BENCH_LOG"
grep -qF "'country': 'Portugal', 'timezone': 'Europe/Lisbon', 'currency': 'EUR', 'language': 'Portuguese'" "$BENCH_LOG"
grep -qxF -- '--site shop-test.localhost set-config developer_mode 1' "$BENCH_LOG"

if command -v node >/dev/null; then
	cp "$SCRIPTS/ab-login.sh" "$TMP/app/scripts/"
	mkdir -p "$TMP/app/e2e"
	cp "$SCRIPTS/../e2e/sid.ts" "$TMP/app/e2e/"
	printf 'TEST_SITE_URL=http://shop-test.localhost:8000\n' >> "$TMP/app/.kaysalt/project.conf"
	cat > "$TMP/bin/agent-browser" <<'EOF'
#!/usr/bin/env bash
printf 'agent-browser %s\n' "$*" >> "$BENCH_LOG"
EOF
	sed -i 's|^if \[\[ \$\* == \*get_singles_dict\* \]\]; then$|[[ $1 == browse ]] \&\& echo "http://x/app?sid=s3cr3t"\n&|' "$TMP/bin/bench"
	chmod 755 "$TMP/bin/agent-browser"
	login_output=$("$TMP/app/scripts/ab-login.sh" jane.test@example.com)
	[[ $login_output != *s3cr3t* ]]
	grep -qxF 'agent-browser cookies set sid s3cr3t --url http://shop-test.localhost:8000' "$BENCH_LOG"
	grep -q '^via-prefix bench browse shop-test.localhost --user jane.test@example.com$' "$BENCH_LOG"
fi

sed -i 's/^TEST_SITE=.*/TEST_SITE=shop.localhost/' "$TMP/app/.kaysalt/project.conf"
if KAYSALT_DB_ROOT_PASSWORD=root KAYSALT_TEST_ADMIN_PASSWORD=admin-test \
	"$TMP/app/scripts/rebuild-test-site.sh" >/dev/null 2>&1; then
	printf 'rebuild-test-site.sh would have dropped the main site\n' >&2
	exit 1
fi
printf 'bench scripts self-check passed\n'
