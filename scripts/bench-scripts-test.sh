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

CONF=$TMP/app/.kaysalt/project.conf
set_conf() { sed -i "/^$1=/d" "$CONF"; printf '%s=%s\n' "$1" "$2" >> "$CONF"; }
rebuild_fails() { # rebuild_fails <what went wrong> <expected error>; the rebuild stops before bench runs
	: > "$BENCH_LOG"
	if "$TMP/app/scripts/rebuild-test-site.sh" >/dev/null 2>"$TMP/rebuild.err"; then
		printf 'rebuild-test-site.sh %s\n' "$1" >&2
		exit 1
	fi
	grep -qF -- "$2" "$TMP/rebuild.err"
	[[ ! -s $BENCH_LOG ]]
}

# The kit build seeds the module SAMPLE_DATA_SEED names, when the app has it.
mkdir -p "$TMP/bench/apps/shop/shop"
touch "$TMP/bench/apps/shop/shop/sample_data.py"
set_conf SAMPLE_DATA_SEED shop.sample_data.seed
: > "$BENCH_LOG"
KAYSALT_DB_ROOT_PASSWORD=root KAYSALT_TEST_ADMIN_PASSWORD=admin-test \
	"$TMP/app/scripts/rebuild-test-site.sh" >/dev/null
grep -qxF -- '--site shop-test.localhost execute shop.sample_data.seed' "$BENCH_LOG"
set_conf SAMPLE_DATA_SEED os.system
KAYSALT_DB_ROOT_PASSWORD=root KAYSALT_TEST_ADMIN_PASSWORD=admin-test \
	rebuild_fails 'seeded a function outside the app' 'SAMPLE_DATA_SEED must be a function in the shop package'
set_conf SAMPLE_DATA_SEED ''

# An app with its own test-site command: no passwords, no kit drop-site or new-site.
set_conf TEST_SITE_BUILD 'bench shop-test-site up --replace'
: > "$BENCH_LOG"
env -u KAYSALT_DB_ROOT_PASSWORD -u KAYSALT_TEST_ADMIN_PASSWORD "$TMP/app/scripts/rebuild-test-site.sh" >/dev/null
grep -qxF 'via-prefix bench shop-test-site up --replace' "$BENCH_LOG"
grep -qxF -- '--site shop-test.localhost set-config developer_mode 1' "$BENCH_LOG"
! grep -qE 'drop-site|new-site' "$BENCH_LOG" || exit 1
set_conf TEST_SITE_BUILD 'make site'
rebuild_fails 'ran a build that is not a bench command' 'must be a bench command'
set_conf TEST_SITE_BUILD 'bench --site shop-test.localhost reinstall --yes'
rebuild_fails 'let the build reinstall a site' 'must not run bench reinstall'
set_conf TEST_SITE_BUILD 'bench --site all migrate'
rebuild_fails 'let the build reach every site' 'may only name shop-test.localhost'
set_conf TEST_SITE_BUILD 'bench shop-test-site up --from shop.localhost'
rebuild_fails 'let the build name the main site' 'must not name the main site'
set_conf TEST_SITE_BUILD ''

# A blank Locale stops migrate.sh and the rebuild before bench runs, and names the key.
set_conf LOCALE_COUNTRY ''
: > "$BENCH_LOG"
if "$TMP/app/scripts/migrate.sh" >/dev/null 2>"$TMP/blank.err"; then
	printf 'migrate.sh passed with a blank Locale\n' >&2
	exit 1
fi
grep -qF 'set LOCALE_COUNTRY in .kaysalt/project.conf' "$TMP/blank.err"
[[ ! -s $BENCH_LOG ]]
KAYSALT_DB_ROOT_PASSWORD=root KAYSALT_TEST_ADMIN_PASSWORD=admin-test \
	rebuild_fails 'ran with a blank Locale' 'set LOCALE_COUNTRY'
set_conf LOCALE_COUNTRY Portugal

sed -i 's/^TEST_SITE=.*/TEST_SITE=shop.localhost/' "$CONF"
KAYSALT_DB_ROOT_PASSWORD=root KAYSALT_TEST_ADMIN_PASSWORD=admin-test \
	rebuild_fails 'would have dropped the main site' 'never the main site'
set_conf TEST_SITE_BUILD 'bench shop-test-site up --replace'
rebuild_fails 'ran the app build on the main site' 'never the main site'
printf 'bench scripts self-check passed\n'
