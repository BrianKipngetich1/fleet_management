import { expect, test } from "@playwright/test";
import { DOCTYPES, USERS } from "../fixtures";

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

test("an unauthenticated visitor is sent to login", async ({ browser }) => {
	const context = await browser.newContext({ storageState: { cookies: [], origins: [] } });
	const page = await context.newPage();
	await page.goto(`/app/${DOCTYPES[0].toLowerCase().replace(/ /g, "-")}`);
	await expect(page).toHaveURL(/\/login/);
	await context.close();
});
