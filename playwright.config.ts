import { defineConfig, devices } from "@playwright/test";
import { assertTestBaseURL } from "./e2e/target";

// Root UI regression suite. It guards the application's core Desk behaviour and is
// deliberately not tied to any spec phase — per-phase evidence is recorded in the
// verification record alongside this live browser suite.

const baseURL = assertTestBaseURL(process.env.BASE_URL);

export default defineConfig({
	testDir: "./e2e/tests",
	fullyParallel: false,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 0,
	workers: 1,
	reporter: process.env.CI
		? [["github"], ["html", { open: "never" }]]
		: [["list"], ["html", { open: "never" }]],
	timeout: 90_000,
	expect: { timeout: 15_000 },
	use: {
		baseURL,
		trace: "on-first-retry",
		video: "retain-on-failure",
		screenshot: "only-on-failure",
		actionTimeout: 20_000,
		navigationTimeout: 45_000,
	},
	// Frappe convention: the bench's own web server (:8000) serves every site
	// by Host header, with Socket.IO, workers and the scheduler alongside it. The suite
	// reuses that server and never starts a partial one of its own.
	webServer: {
		// A missing test site answers 404, so it lands here too: the site is disposable and is
		// built for each test session from the sample data.
		command: "echo 'Test site not reachable on :8000. Build it with: bench fleet-test-site up --replace (and start the bench if needed: systemctl --user start frappe-bench.target).' >&2; exit 1",
		url: `${baseURL}/api/method/ping`,
		reuseExistingServer: true,
		timeout: 10_000,
	},
	projects: [
		{ name: "setup", testMatch: /auth\.setup\.ts/ },
		{
			name: "desk",
			use: { ...devices["Desktop Chrome"] },
			dependencies: ["setup"],
		},
	],
});
