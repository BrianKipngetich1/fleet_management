import { defineConfig, devices } from "@playwright/test";

// Root UI regression suite. It guards the application's core Desk behaviour and is
// deliberately not tied to any spec phase — per-phase evidence comes from agent-browser.
// See CLAUDE.md "UI verification workflow".

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
		baseURL: process.env.BASE_URL || "http://[test site]:8000",
		trace: "on-first-retry",
		video: "retain-on-failure",
		screenshot: "only-on-failure",
		actionTimeout: 20_000,
		navigationTimeout: 45_000,
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
