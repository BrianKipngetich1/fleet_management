#!/usr/bin/env python3
"""Check specs/NNN-name folders against the requirements or bugfix, design and tasks templates.

Usage: python3 scripts/spec-check.py [specs/NNN-name ...]
With no arguments every numbered spec folder is checked. Exit 1 on errors; warnings only
print.
"""

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HEADING = re.compile(r"^#{1,6} ")
REQUIREMENT = re.compile(r"^### Requirement (\d+)\b")
BUG_SECTIONS = {"## Current behaviour": 1, "## Expected behaviour": 2, "## Unchanged behaviour": 3}
CRITERION = re.compile(r"^(\d+)\. (.*)$")
PROPERTY = re.compile(r"^### Property (\d+)\b")
TASK = re.compile(r"^\s*- \[[ xX]\] ")
IDS = re.compile(r"\d+\.\d+")
CITES = re.compile(r"_Requirements: ([\d., ]+)_")
VALIDATES = re.compile(r"\*\*Validates: Requirements ([\d., ]+)\*\*")
EARS = re.compile(r"^(THE|WHEN|WHILE|IF|WHERE)\b.*\bSHALL\b")
SNAKE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
VAGUE = re.compile(
	r"\b(fast|quickly|easy|easily|user-friendly|intuitive|appropriate|appropriately|"
	r"properly|adequate|reasonable|efficient|efficiently|robust|flexible|seamless|"
	r"as needed|if possible|etc|some|several|tbd)\b",
	re.IGNORECASE,
)
APPROVAL = re.compile(
	r"^Approved by: (pending|\S.* \(@[A-Za-z0-9-]+\) · \d{2}/\d{2}/\d{4} · "
	r"revision ([0-9a-f]{7,40})( \(explained by agent\))?)$",
	re.MULTILINE,
)


def strip_comments(text):
	return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def criteria(text, bugfix, errors, name):
	"""Return {id: (section, text)} for every numbered acceptance criterion."""
	found, group, expected_k, current = {}, None, 1, None
	last_requirement = 0
	for line in text.splitlines():
		if HEADING.match(line):
			current = None
			requirement = REQUIREMENT.match(line)
			if bugfix and line.strip() in BUG_SECTIONS:
				group, expected_k = BUG_SECTIONS[line.strip()], 1
			elif not bugfix and requirement:
				group, expected_k = int(requirement.group(1)), 1
				if group != last_requirement + 1:
					errors.append(f"{name}: Requirement {group} is out of sequence")
				last_requirement = group
			elif not bugfix and line.startswith("#### Acceptance Criteria"):
				continue
			elif bugfix or not line.startswith("#### "):
				group = None
			continue
		match = CRITERION.match(line)
		if group and match:
			k = int(match.group(1))
			if k != expected_k:
				errors.append(f"{name}: criterion {group}.{k} should be {group}.{expected_k}")
			expected_k = k + 1
			current = f"{group}.{k}"
			found[current] = [group, match.group(2)]
		elif current and line.startswith("   ") and line.strip():
			found[current][1] += " " + line.strip()
		else:
			current = None
	return {key: tuple(value) for key, value in found.items()}


def check_ears(name, cid, group, body, bugfix, errors):
	if bugfix and group == 1:
		ok = re.match(r"^WHEN\b.*\bTHEN\b", body)
	elif bugfix and group == 3:
		ok = EARS.match(body) and "SHALL CONTINUE TO" in body
	else:
		ok = EARS.match(body) and (not body.startswith("IF") or " THEN " in body)
	if not ok:
		errors.append(f"{name}: {cid} is not in EARS form")
	for word in sorted({m.group(0).lower() for m in VAGUE.finditer(body)}):
		errors.append(f"{name}: {cid} uses vague word '{word}'")


def check_approval(spec, name, raw, errors, warnings):
	lines = [line for line in raw.splitlines() if line.startswith("Approved by:")]
	if len(lines) != 1:
		errors.append(f"{name}: expected one 'Approved by:' line, found {len(lines)}")
		return
	match = APPROVAL.match(lines[0])
	if not match:
		errors.append(f"{name}: malformed approval line: {lines[0]}")
		return
	sha = match.group(2)
	if not sha:
		return
	known = subprocess.run(
		["git", "-C", str(spec), "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}"],
		capture_output=True,
	)
	if known.returncode:
		warnings.append(f"{name}: approved revision {sha} is not in this repository")
		return
	approved = subprocess.run(
		["git", "-C", str(spec), "show", f"{sha}:./{name}"], capture_output=True, text=True
	)
	if approved.returncode:
		errors.append(f"{name}: not present in approved revision {sha}")
		return

	def pending(text):
		return APPROVAL.sub("Approved by: pending", text)

	if pending(approved.stdout) != pending(raw):
		errors.append(f"{name}: changed since approval at {sha}; reset it to 'Approved by: pending'")


def check_spec(spec, tests):
	errors, warnings = [], []
	bugfix = (spec / "bugfix.md").is_file()
	if bugfix and (spec / "requirements.md").is_file():
		return ["has both bugfix.md and requirements.md; keep one"], warnings
	first = "bugfix.md" if bugfix else "requirements.md"
	missing = [n for n in (first, "design.md", "tasks.md") if not (spec / n).is_file()]
	if missing:
		hint = " (old single-file format: convert spec.md)" if (spec / "spec.md").exists() else ""
		return [f"missing {', '.join(missing)}{hint}"], warnings

	raw = {n: (spec / n).read_text() for n in (first, "design.md", "tasks.md")}
	text = {n: strip_comments(t) for n, t in raw.items()}
	for n in (first, "design.md"):
		check_approval(spec, n, raw[n], errors, warnings)

	for token in sorted(set(SNAKE.findall(text[first]))):
		errors.append(f"{first}: technical name '{token}' (use business language)")

	found = criteria(text[first], bugfix, errors, first)
	if not found:
		errors.append(f"{first}: no acceptance criteria found")
	live = []
	for cid, (group, body) in found.items():
		if body.startswith("Removed:"):
			continue
		live.append(cid)
		check_ears(first, cid, group, body, bugfix, errors)

	properties = []
	blocks = re.split(r"^(?=#{1,6} )", text["design.md"], flags=re.MULTILINE)
	for block in blocks:
		match = PROPERTY.match(block)
		if not match:
			continue
		pid = f"Property {match.group(1)}"
		if pid in properties:
			errors.append(f"design.md: duplicate {pid}")
		properties.append(pid)
		validates = VALIDATES.search(block)
		if not validates:
			errors.append(f"design.md: {pid} has no '**Validates: Requirements N.k**' line")
			continue
		for cid in IDS.findall(validates.group(1)):
			if cid not in found:
				errors.append(f"design.md: {pid} validates unknown {cid}")

	cited = set()
	task_line, task_cites = None, None

	def close_task():
		if task_line and task_cites is None:
			errors.append(f"tasks.md: task has no '_Requirements: N.k_' line: {task_line}")

	for line in text["tasks.md"].splitlines():
		if TASK.match(line) or HEADING.match(line):
			close_task()
			task_line, task_cites = (line.strip(), None) if TASK.match(line) else (None, None)
		match = CITES.search(line)
		if match and task_line:
			task_cites = IDS.findall(match.group(1))
			for cid in task_cites:
				if cid not in found:
					errors.append(f"tasks.md: unknown requirement {cid}")
			cited |= set(task_cites)
	close_task()
	for cid in live:
		if cid not in cited:
			errors.append(f"tasks.md: no task cites requirement {cid}")

	tested = " ".join(t for t in tests if spec.name in t)
	tested_ids = {
		cid for group in re.findall(r"Requirements? ([\d., ]+)", tested) for cid in IDS.findall(group)
	}
	for cid in live:
		if cid not in tested_ids:
			warnings.append(f"no test_*.py naming {spec.name} cites requirement {cid}")
	for pid in properties:
		if pid not in tested:
			warnings.append(f"no test_*.py naming {spec.name} cites {pid}")
	return errors, warnings


def test_files():
	return [
		path.read_text(errors="ignore")
		for path in ROOT.rglob("test_*.py")
		if not {"node_modules", ".git"} & set(path.parts)
	]


def main(argv):
	specs = [pathlib.Path(a) for a in argv] or sorted(
		p for p in (ROOT / "specs").glob("[0-9][0-9][0-9]-*") if p.is_dir()
	)
	tests = test_files()
	failed = False
	for spec in specs:
		errors, warnings = check_spec(spec.resolve(), tests)
		for message in errors:
			print(f"ERROR {spec.name}: {message}")
		for message in warnings:
			print(f"warning {spec.name}: {message}")
		failed = failed or bool(errors)
		if not errors:
			print(f"ok {spec.name}")
	return 1 if failed else 0


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
