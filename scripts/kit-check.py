#!/usr/bin/env python3
"""List where this app differs from how the kit works now, in words for the requester.

Usage: python3 scripts/kit-check.py [APP_PATH]
Read-only. Ids listed in KIT_CHECK_SKIP (comma-separated) in .kaysalt/project.conf are not shown.
Each check returns None or (what to tell the requester, what to do if they agree).
"""

import os
import pathlib
import sys

TABLE = ["site", "username", "role", "password"]
PRUNE = {".git", "node_modules", "graphify-out", "__pycache__"}


def read_conf(root):
	conf = {}
	for line in (root / ".kaysalt" / "project.conf").read_text().splitlines():
		key, _, value = line.partition("=")
		conf[key.strip()] = value.strip()
	return conf


def find(root, name):
	for folder, dirs, files in os.walk(root):
		dirs[:] = sorted(d for d in dirs if d not in PRUNE)
		if name in files:
			yield pathlib.Path(folder, name).relative_to(root)


def has_kit_table(path):
	for line in path.read_text().splitlines():
		cells = [cell.strip().lower() for cell in line.strip().strip("|").split("|")]
		if cells == TABLE:
			return True
	return False


def credentials_location(root, conf):
	if (root / "CREDENTIALS.md").exists():
		return None
	where = next(find(root, "CREDENTIALS.md"), None)
	if where is None:
		return None
	return (
		f"This app's list of sign-ins is kept in {where}. The kit now keeps it in one place, "
		"CREDENTIALS.md at the top of the app's folder, so that rebuilding the test site gives "
		"every test sign-in its password back. Nothing about the app itself changes.",
		f"Move {where} to CREDENTIALS.md at the repository root in the kit's "
		"| Site | Username | Role | Password | table (AGENTS.md, Credentials), keep its other "
		"sections below the table, chmod 600 it, and update anything that names the old path.",
	)


def credentials_table(root, conf):
	path = root / "CREDENTIALS.md"
	if not path.exists() or has_kit_table(path):
		return None
	return (
		"The list of sign-ins isn't laid out the way the kit reads it, so when the test site is "
		"rebuilt, the test sign-ins don't get their passwords back and people can't sign in "
		"by hand.",
		"Rewrite the logins in CREDENTIALS.md into the | Site | Username | Role | Password | "
		"table and keep any other notes below it. Never print or commit a password.",
	)


def credentials_private(root, conf):
	path = root / "CREDENTIALS.md"
	if not path.exists() or path.stat().st_mode & 0o777 == 0o600:
		return None
	return (
		"The list of sign-ins can be read by other accounts on this computer. The kit keeps it "
		"readable by you only.",
		"chmod 600 CREDENTIALS.md",
	)


def sample_data_location(root, conf):
	app = conf.get("APP_NAME", "")
	if not app or conf.get("TEST_SITE_BUILD"):
		return None
	seed = conf.get("SAMPLE_DATA_SEED") or f"{app}.tests.sample_data.seed"
	if (root / (seed.rpartition(".")[0].replace(".", "/") + ".py")).exists():
		return None
	where = next(find(root / app, "sample_data.py"), None) if (root / app).is_dir() else None
	if where is None:
		return None
	module = ".".join((app, *where.with_suffix("").parts))
	return (
		f"This app has sample data in {app}/{where}, but the kit looks for it somewhere else, "
		"so a rebuilt test site starts empty. One setting tells the kit where it is; the sample "
		"data itself doesn't change.",
		f"Check {module} has a seed() function, then set SAMPLE_DATA_SEED={module}.seed in "
		".kaysalt/project.conf.",
	)


def ci_workflow(root, conf):
	path = root / ".github" / "workflows" / "ci.yml"
	if not path.is_file() or ".kaysalt/project.conf" in path.read_text():
		return None
	return (
		"The automatic checks on GitHub won't pass because this CI file uses an older kit setup. "
		"The app's hand-edited file stays in place when the kit updates. The kit's current file "
		"reads the app's settings from .kaysalt/project.conf by itself.",
		"A person can replace the old CI file with the kit's current CI workflow, then move any "
		"app-specific steps over.",
	)


CHECKS = [credentials_location, credentials_table, credentials_private, sample_data_location, ci_workflow]


def main(argv):
	root = pathlib.Path(argv[0] if argv else pathlib.Path(__file__).resolve().parent.parent).resolve()
	if not (root / ".kaysalt" / "project.conf").is_file():
		print(f"kit-check: {root} has no .kaysalt/project.conf, so it is not a kit app", file=sys.stderr)
		return 1
	conf = read_conf(root)
	skip = {item.strip() for item in conf.get("KIT_CHECK_SKIP", "").split(",") if item.strip()}
	found = []
	for check in CHECKS:
		name = check.__name__.replace("_", "-")
		if name not in skip and (result := check(root, conf)):
			found.append((name, *result))
	if not found:
		print("No kit suggestions.")
	for number, (name, tell, fix) in enumerate(found, 1):
		print(f"Kit suggestion {number} of {len(found)} ({name})")
		print(f"  Tell the requester: {tell}")
		print(f"  If they agree: {fix}")
	return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
