import { execFileSync } from "node:child_process";
import { assertTestSite, TEST_SITE } from "./target";

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

function parseJsonLine(output: string) {
	for (const line of output.trim().split(/\r?\n/).reverse()) {
		try {
			return JSON.parse(line) as unknown;
		} catch {
			// Bench may write non-JSON status lines before its result.
		}
	}
	return null;
}

// Passwordless Desk authentication. `bench browse --user` runs Frappe's own
// LoginManager.login_as and persists a server-side session. The SID is read back
// only inside this process and is installed as a cookie by auth.ts; it never goes
// into a browser URL, log, or screenshot. Playwright's temporary local auth state
// is ignored and removed after verification.
//
// This is a user-impersonation primitive and is permitted only against the dedicated
// test site. See CLAUDE.md "Authentication for UI tests".
//
export function mintSid(user: string): string {
	if (!user || user === "Guest") {
		throw new Error(`A named QA user is required to mint a test session; received ${user || "<empty>"}`);
	}

	runBench(["--site", SITE, "browse", "--user", user]);
	const query =
		`frappe.db.sql(${JSON.stringify(
			`select sid, user from tabSessions where user = ${JSON.stringify(user)} order by lastupdate desc limit 1`,
		)}, as_dict=True)`;
	const rows = parseJsonLine(runBench(["--site", SITE, "execute", query]));
	const session = Array.isArray(rows) ? (rows[0] as { sid?: string; user?: string } | undefined) : undefined;

	if (!session?.sid || session.user !== user) {
		throw new Error(
			`Frappe did not persist a session for ${user}; detected session user ${session?.user || "<none>"}`,
		);
	}

	return session.sid;
}
