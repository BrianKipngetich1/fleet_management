import { expect, test } from "@playwright/test";
import { apiPost, openList } from "../desk";
import { DENY_PROBE, USERS } from "../fixtures";

const doctype = DENY_PROBE.doctype as string;

test.describe(`${USERS.restricted.role}`, () => {
	test.use({ storageState: USERS.restricted.state });

	test(`may read the ${doctype} list`, async ({ page }) => {
		await openList(page, doctype);
		await expect(page.locator(".layout-main-section")).toBeVisible();
	});

	test(`is denied creating a ${doctype}`, async ({ page }) => {
		await page.goto("/app");

		// Prove the session can read first. On a site that denies everything — a broken
		// or half-provisioned one — the 403 below would otherwise pass for the wrong
		// reason and report a permission boundary that was never exercised.
		const readable = await page.request.get(
			`/api/resource/${doctype}?limit_page_length=1`
		);
		expect(readable.status()).toBe(200);

		const response = await apiPost(page, `/api/resource/${doctype}`, DENY_PROBE);
		expect(response.status()).toBe(403);
	});
});

// The matching allow path belongs in lifecycle.spec.ts, where a permitted user creates
// and submits the same DocType through Desk. Repeating it here as an API call would only
// add another record to the test site.
