#!/usr/bin/env bash
# Drops and recreates the test site with the app, the Locale, developer mode and sample data.
# Needs KAYSALT_DB_ROOT_PASSWORD and KAYSALT_TEST_ADMIN_PASSWORD in the environment.
set -euo pipefail
source "$(dirname "$0")/project-env.sh"

require_conf TEST_SITE LOCALE_COUNTRY LOCALE_TIME_ZONE LOCALE_CURRENCY LOCALE_DATE_FORMAT LOCALE_LANGUAGE
: "${KAYSALT_DB_ROOT_PASSWORD:?set KAYSALT_DB_ROOT_PASSWORD}"
: "${KAYSALT_TEST_ADMIN_PASSWORD:?set KAYSALT_TEST_ADMIN_PASSWORD (it must contain the word test)}"
[[ $KAYSALT_TEST_ADMIN_PASSWORD == *test* ]] || die "KAYSALT_TEST_ADMIN_PASSWORD must contain the word test"
[[ $TEST_SITE == *-test.* ]] || die "TEST_SITE must be the -test site, never the main site: $TEST_SITE"

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
if [[ -f $BENCH_ROOT/apps/$APP_NAME/$APP_NAME/tests/sample_data.py ]]; then
	bench_run --site "$TEST_SITE" execute "$APP_NAME.tests.sample_data.seed"
else
	printf 'No %s/tests/sample_data.py yet; ask the requester for sample data before the first PR.\n' "$APP_NAME"
fi
drift=$(locale_drift "$TEST_SITE")
[[ -z $drift ]] || die "Locale drift after rebuild (add the app's Locale hooks, see docs/agents/site-provisioning.md):
$drift"
printf 'Rebuilt %s with the Locale in project.conf.\n' "$TEST_SITE"
