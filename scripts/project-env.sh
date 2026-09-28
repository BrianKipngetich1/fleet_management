# Sourced by the kit scripts: loads .kaysalt/project.conf and runs bench through BENCH_EXEC.
PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CFG=$PROJECT_ROOT/.kaysalt/project.conf

die() { printf '%s: %s\n' "$(basename "$0")" "$*" >&2; exit 1; }

[[ -f $CFG ]] || die "missing $CFG"
while IFS='=' read -r key value; do
	case $key in
		APP_NAME|MAIN_SITE|TEST_SITE|TEST_SITE_URL|TEST_SITE_BUILD|SAMPLE_DATA_SEED|BENCH_ROOT|BENCH_EXEC|LOCALE_*) printf -v "$key" '%s' "$value" ;;
	esac
done < "$CFG"

require_conf() {
	local key
	for key in "$@"; do
		[[ -n ${!key:-} ]] || die "set $key in .kaysalt/project.conf (ask the requester if it is a business fact)"
	done
}

require_locale() {
	require_conf LOCALE_COUNTRY LOCALE_TIME_ZONE LOCALE_CURRENCY LOCALE_DATE_FORMAT LOCALE_LANGUAGE
}

require_conf APP_NAME BENCH_ROOT
[[ $BENCH_ROOT == /* ]] || BENCH_ROOT=$PROJECT_ROOT/$BENCH_ROOT
[[ -d $BENCH_ROOT/sites ]] || die "BENCH_ROOT has no sites/ folder: $BENCH_ROOT"
read -ra BENCH_PREFIX <<< "${BENCH_EXEC:-}"

bench_run() {
	(cd "$BENCH_ROOT" && "${BENCH_PREFIX[@]}" bench "$@")
}

# Prints mismatches between the site's System Settings and the Locale in project.conf.
# Language is left out: the site stores a code, the Locale holds the wizard's language name.
# It runs inside $(...), where a die would be lost, so a blank Locale value is reported as drift.
locale_drift() {
	bench_run --site "$1" execute frappe.db.get_singles_dict --args "['System Settings']" |
		python3 -c '
import json, sys
settings = json.loads(sys.stdin.read().strip().splitlines()[-1])
wanted = dict(zip(("country", "time_zone", "currency", "date_format"), sys.argv[1:]))
for field, value in wanted.items():
    if not value:
        print(f"{field}: site has {settings.get(field)!r}, Locale is blank in .kaysalt/project.conf")
    elif str(settings.get(field) or "") != value:
        print(f"{field}: site has {settings.get(field)!r}, Locale says {value!r}")
' "${LOCALE_COUNTRY:-}" "${LOCALE_TIME_ZONE:-}" "${LOCALE_CURRENCY:-}" "${LOCALE_DATE_FORMAT:-}"
}
