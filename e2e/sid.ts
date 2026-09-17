import { execSync } from "node:child_process";

// Passwordless Desk authentication. `bench browse --user` runs Frappe's own
// LoginManager.login_as, which mints a server-side session id and prints it as a
// ?sid= query parameter. No credential is ever typed into a login form.
//
// This is a user-impersonation primitive and is permitted only against the dedicated
// test site. See CLAUDE.md "Authentication for UI tests".
//
// PC_SID_CMD overrides the command for other environments — a containerised bench, or
// CI, where bench runs directly. The acting user is passed in as $PC_USER.
const DEFAULT_SID_CMD =
	'BROWSER=echo bench browse [test site] --user "$PC_USER"';

export function mintSid(user: string): string {
	const command = process.env.PC_SID_CMD || DEFAULT_SID_CMD;
	const output = execSync(command, {
		encoding: "utf8",
		env: { ...process.env, PC_USER: user },
	});
	// bench prints its refusal and exits 0 when developer_mode is off, so the sid — not
	// the exit code — is what proves the session was minted.
	const sid = output.match(/[?&]sid=([A-Za-z0-9]+)/)?.[1];
	if (!sid) {
		throw new Error(`No sid in PC_SID_CMD output for ${user}:\n${output}`);
	}
	return sid;
}
