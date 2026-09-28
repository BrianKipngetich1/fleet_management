# Site provisioning

Read when creating or rebuilding a site, or when a site's time zone, currency, country, or date
format looks wrong.

## Sites

- `[app-name].localhost` is the main site, for the requester's own checks. `scripts/migrate.sh`
  migrates it after each task and reports Locale drift.
- `[app-name]-test.localhost` is the test site, for every functional test. Rebuild it before a
  PR with `scripts/rebuild-test-site.sh`. By default it runs the kit build, which:
  1. drops and recreates the site and installs the app;
  2. completes the setup wizard with the Locale from `.kaysalt/project.conf`;
  3. turns on `developer_mode`;
  4. seeds `SAMPLE_DATA_SEED` (default `[app_name].tests.sample_data.seed`) when that module
     exists;
  5. fails if System Settings still differ from the Locale.

  The kit build needs `KAYSALT_DB_ROOT_PASSWORD` and `KAYSALT_TEST_ADMIN_PASSWORD` (containing
  the word `test`) in the environment. Neither is stored in the repository.

  An app that already builds its own test site names that command in `TEST_SITE_BUILD`, for
  example `bench [app-name]-test-site up --replace`. The script then runs it instead of steps 1-4,
  needs neither password, turns on `developer_mode`, and still fails on Locale drift. The
  command must start with `bench`, may name only the test site, and must not run `drop-site`,
  `reinstall`, or `restore`.

- A blank Locale value fails `scripts/migrate.sh` and the rebuild and names the key. A kit
  update fills a blank Locale from the main site's System Settings and says so in its pull
  request; when the main site cannot be read, the pull request says which keys to fill.

Every script runs bench through `BENCH_EXEC` from `.kaysalt/project.conf`: empty on a host
bench, or a prefix such as `docker compose exec -w /home/frappe/frappe-bench backend` for a
Docker bench. Paths relative to the bench root are the same in both.

## Why the setup wizard matters

A site that never completed the setup wizard fails misleadingly: Desk re-routes everything to
the wizard, so every DocType route resolves as a Page and returns `403 Not permitted` — for
every user and DocType — while roles and `can_read` in the boot payload look perfectly correct.
Never use `frappe.utils.install.complete_setup_wizard`: it hard-codes a United States locale
(`America/New_York`, USD, `mm-dd-yyyy`), which shifts every datetime rule by the time-zone
difference. Complete it with the project's Locale instead (verified against Frappe 16.22.0):

```bash
bench --site [site] execute frappe.desk.page.setup_wizard.setup_wizard.setup_complete \
  --kwargs "{'args': {'country': '[Country]', 'timezone': '[Area/City]', 'currency': '[CUR]', 'language': '[Language name]'}}"
```

The wizard takes the date format from the country, so the scripts then save the Locale's date
format in System Settings (`frappe.client.set_value`); the app's Locale hook below keeps it.
A site also needs `bench --site [site] set-config developer_mode 1`, without which `bench
browse --user` refuses to mint a session for a non-Administrator — and it prints the refusal
while exiting `0`, so check the output for `?sid=`, never the exit code.

## Enforcing the Locale in the app

Every app enforces its Locale on install, after the setup wizard, and after every migrate, so no
site drifts. Frappe-first: System Settings already holds these values and these three hooks are
native, so the only custom code is the one function below. It is a recipe rather than kit code
because the kit ships no Python package and the hook belongs to each app.

```python
# hooks.py
after_install = "[app_name].site_defaults.apply_locale"
setup_wizard_complete = "[app_name].site_defaults.apply_locale"
after_migrate = "[app_name].site_defaults.apply_locale"

# site_defaults.py: the same values as the LOCALE_* keys in .kaysalt/project.conf
import frappe

LOCALE = {
	"country": "[Country]",
	"time_zone": "[Area/City]",
	"currency": "[CUR]",
	"date_format": "[dd/mm/yyyy]",
}


def apply_locale(*args, **kwargs):
	settings = frappe.get_single("System Settings")
	changed = {key: value for key, value in LOCALE.items() if settings.get(key) != value}
	if not changed:
		return
	settings.update(changed)
	# Saving (not set_single_value) also refreshes the site default that Desk boots from.
	settings.save(ignore_permissions=True)
```

Add a backend test asserting each value after migrate. Never type a hard-coded ISO date into a
Desk date field; convert through `frappe.datetime.str_to_user` (`userDate()` in `e2e/desk.ts`).
