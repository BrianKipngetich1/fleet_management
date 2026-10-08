import { execFileSync, execSync } from "node:child_process";
import { assertTestSite, TEST_SITE } from "./target.ts";

const BENCH_ROOT = process.env.BENCH_ROOT || "/home/kayadmin/frappe-bench";
const SITE = assertTestSite(process.env.E2E_SITE || TEST_SITE);
const BENCH_PATH =
	process.env.PC_BENCH_PATH ||
	"/home/kayadmin/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin";

function benchEnv() {
	return {
		...process.env,
		PATH: BENCH_PATH,
		GIT_PYTHON_GIT_EXECUTABLE: process.env.GIT_PYTHON_GIT_EXECUTABLE || "/usr/bin/git",
		BROWSER: "true",
	};
}

function runBench(args: string[]) {
	try {
		return execFileSync("bench", args, {
			cwd: BENCH_ROOT,
			encoding: "utf8",
			env: benchEnv(),
		});
	} catch (error: any) {
		const output = `${error.stdout || ""}${error.stderr || ""}`.replace(
			/([?&]sid=|["']sid["']\s*:\s*["'])[A-Za-z0-9]+/g,
			"$1[redacted]",
		);
		throw new Error(`Frappe session command failed: ${args[0]} ${args[1] || ""}\n${output}`, {
			cause: error,
		});
	}
}

// Passwordless Desk authentication. The default path runs the app's own
// `bench fleet-test-site session` command, which uses Frappe's LoginManager.login_as
// to persist a server-side session and never opens a browser. The SID is read only
// inside this process and is installed as a cookie by auth.ts; it never goes into a
// browser URL, log, or screenshot. Playwright's temporary local auth state is
// ignored and removed after verification.
//
// This is a user-impersonation primitive and is permitted only against the dedicated
// test site. See CLAUDE.md "UI verification".
//
// CI (the kit's ci.yml) sets PC_SID_CMD, because bench runs directly there. The
// command prints the ?sid= URL for $PC_USER, and that replaces the session command below.
export function mintSid(user: string): string {
	if (!user || user === "Guest") {
		throw new Error(`A named QA user is required to mint a test session; received ${user || "<empty>"}`);
	}

	if (process.env.PC_SID_CMD) {
		const output = execSync(process.env.PC_SID_CMD, {
			encoding: "utf8",
			env: { ...process.env, PC_USER: user },
		});
		const sid = output.match(/[?&]sid=([A-Za-z0-9]+)/)?.[1];
		if (!sid) {
			throw new Error(`No sid was printed by PC_SID_CMD for ${user}`);
		}
		return sid;
	}

	const sid = runBench(["--site", SITE, "fleet-test-site", "session", user]).match(
		/[?&]sid=([A-Za-z0-9]+)/,
	)?.[1];
	if (!sid) {
		throw new Error(`No sid was printed by the session command for ${user}`);
	}
	return sid;
}
