import { expect, test } from "@playwright/test";
import { BASE_URL, setSessionCookie } from "../auth";
import { DATE_FORMAT, DOCTYPES, USERS } from "../fixtures";

test.use({ storageState: USERS.primary.state });

test("the minted session lands on Desk as the intended user", async ({ page }) => {
	await page.goto("/app");
	expect(page.url()).not.toContain("/login");
	expect(await page.evaluate(() => window.frappe.session.user)).toBe(USERS.primary.email);
});

test("the session carries the intended role", async ({ page }) => {
	await page.goto("/app");
	const roles = await page.evaluate(() => window.frappe.boot.user.roles as string[]);
	expect(roles).toContain(USERS.primary.role);
});

test("Desk shows and accepts dates as dd/mm/yyyy", async ({ page }) => {
	await page.goto("/app");
	expect(await page.evaluate(() => window.frappe.boot.sysdefaults.date_format)).toBe(DATE_FORMAT);
	expect(await page.evaluate(() => window.frappe.datetime.str_to_user("2026-09-24"))).toBe("24/09/2026");
	expect(await page.evaluate(() => window.frappe.datetime.user_to_str("24/09/2026"))).toBe("2026-09-24");
});

test("Desk connects to the realtime service", async ({ page }) => {
	await page.goto("/app");
	await page.waitForFunction(() => window.frappe.realtime?.socket?.connected === true);
});

test("an unauthenticated visitor is sent to login", async ({ browser }) => {
	const context = await browser.newContext({ baseURL: BASE_URL, storageState: { cookies: [], origins: [] } });
	const page = await context.newPage();
	await page.goto(`/app/${DOCTYPES[0].toLowerCase().replace(/ /g, "-")}`);
	await expect(page).toHaveURL(/\/login/);
	await context.close();
});

test("anonymous root and login pages do not expose a debugger", async ({ browser }) => {
	const context = await browser.newContext({ baseURL: BASE_URL, storageState: { cookies: [], origins: [] } });
	const page = await context.newPage();

	await page.goto("/");
	await expect(page).toHaveURL(/\/$/);
	await expect(page.getByRole("heading", { name: "Login to Frappe" })).toBeVisible();
	await expect(page.locator("body")).not.toContainText(/Werkzeug Debugger|Traceback|Interactive debugger/i);

	await page.goto("/login");
	await expect(page).toHaveURL(/\/login/);
	await expect(page.locator("body")).not.toContainText(/Werkzeug Debugger|Traceback|Interactive debugger/i);
	await context.close();
});

test("an expired session is sent to login without a debugger page", async ({ browser }) => {
	const context = await browser.newContext({ baseURL: BASE_URL });
	const page = await context.newPage();
	await setSessionCookie(page, "expired-test-session");
	await page.goto("/app");
	await expect(page).toHaveURL(/\/login/);
	await expect(page.locator("body")).not.toContainText(/Werkzeug Debugger|Traceback|Interactive debugger/i);
	await context.close();
});

test("invalid API requests return controlled errors", async ({ page }) => {
	for (const method of [
		"fleet_management.missing.not_whitelisted",
		"missing_app.missing.not_whitelisted",
	]) {
		const response = await page.request.get(`/api/method/${method}`, {
			headers: { Accept: "application/json" },
		});
		const body = await response.text();
		expect([403, 405]).toContain(response.status());
		expect(body).not.toMatch(/Werkzeug Debugger|Traceback|Interactive debugger|sid=/i);
	}
});
