#!/usr/bin/env bash
# Drops and recreates the test site with the app, the Locale, developer mode and sample data.
# An app with its own test-site command names it in TEST_SITE_BUILD; otherwise the kit builds the
# site, which needs KAYSALT_DB_ROOT_PASSWORD and KAYSALT_TEST_ADMIN_PASSWORD in the environment.
set -euo pipefail
source "$(dirname "$0")/project-env.sh"

require_conf TEST_SITE
require_locale
[[ $TEST_SITE == *-test.* ]] || die "TEST_SITE must be the -test site, never the main site: $TEST_SITE"

# The app's own build runs only as a bench command aimed at the test site.
check_app_build() {
	local word prev=
	[[ ${1-} == bench ]] || die "TEST_SITE_BUILD must be a bench command: $TEST_SITE_BUILD"
	for word in "${@:2}"; do
		case $word in
			drop-site|reinstall|restore|partial-restore)
				die "TEST_SITE_BUILD must not run bench $word: $TEST_SITE_BUILD" ;;
			--site=*) [[ ${word#--site=} == "$TEST_SITE" ]] || die "TEST_SITE_BUILD may only name $TEST_SITE: $TEST_SITE_BUILD" ;;
		esac
		[[ $prev != --site || $word == "$TEST_SITE" ]] || die "TEST_SITE_BUILD may only name $TEST_SITE: $TEST_SITE_BUILD"
		[[ -z ${MAIN_SITE:-} || $word != "$MAIN_SITE" ]] || die "TEST_SITE_BUILD must not name the main site: $TEST_SITE_BUILD"
		prev=$word
	done
}

if [[ -n ${TEST_SITE_BUILD:-} ]]; then
	read -ra build <<< "$TEST_SITE_BUILD"
	check_app_build "${build[@]}"
	bench_run "${build[@]:1}"
	bench_run --site "$TEST_SITE" set-config developer_mode 1
else
	: "${KAYSALT_DB_ROOT_PASSWORD:?set KAYSALT_DB_ROOT_PASSWORD}"
	: "${KAYSALT_TEST_ADMIN_PASSWORD:?set KAYSALT_TEST_ADMIN_PASSWORD (it must contain the word test)}"
	[[ $KAYSALT_TEST_ADMIN_PASSWORD == *test* ]] || die "KAYSALT_TEST_ADMIN_PASSWORD must contain the word test"
	seed=${SAMPLE_DATA_SEED:-$APP_NAME.tests.sample_data.seed}
	[[ $seed =~ ^$APP_NAME(\.[A-Za-z_][A-Za-z0-9_]*)+$ ]] || die "SAMPLE_DATA_SEED must be a function in the $APP_NAME package: $seed"
	module=${seed%.*}

	if [[ -d $BENCH_ROOT/sites/$TEST_SITE ]]; then
		bench_run drop-site "$TEST_SITE" --force --no-backup --db-root-password "$KAYSALT_DB_ROOT_PASSWORD"
	fi
	bench_run new-site "$TEST_SITE" --db-root-password "$KAYSALT_DB_ROOT_PASSWORD" \
		--admin-password "$KAYSALT_TEST_ADMIN_PASSWORD" --install-app "$APP_NAME"
	bench_run --site "$TEST_SITE" execute frappe.desk.page.setup_wizard.setup_wizard.setup_complete \
		--kwargs "$(python3 -c 'import sys; print(repr({"args": dict(zip(("country", "timezone", "currency", "language"), sys.argv[1:]), enable_telemetry=0)}))' \
			"$LOCALE_COUNTRY" "$LOCALE_TIME_ZONE" "$LOCALE_CURRENCY" "$LOCALE_LANGUAGE")"
	# The wizard takes the date format from the country; saving System Settings sets the Locale's.
	bench_run --site "$TEST_SITE" execute frappe.client.set_value \
		--args "$(python3 -c 'import sys; print(repr(["System Settings", "System Settings", "date_format", sys.argv[1]]))' "$LOCALE_DATE_FORMAT")" >/dev/null
	bench_run --site "$TEST_SITE" set-config developer_mode 1
	if [[ -f $BENCH_ROOT/apps/$APP_NAME/${module//.//}.py ]]; then
		bench_run --site "$TEST_SITE" execute "$seed"
	else
		printf 'No %s.py yet; ask the requester for sample data before the first PR.\n' "${module//.//}"
	fi
fi
drift=$(locale_drift "$TEST_SITE")
[[ -z $drift ]] || die "Locale drift after rebuild (add the app's Locale hooks, see docs/agents/site-provisioning.md):
$drift"
printf 'Rebuilt %s with the Locale in project.conf.\n' "$TEST_SITE"
