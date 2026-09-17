import { expect, test } from "@playwright/test";
import { openList, openNew } from "../desk";
import { DOCTYPES, NO_NEW_FORM, USERS } from "../fixtures";

test.use({ storageState: USERS.primary.state });

for (const doctype of DOCTYPES) {
	test(`${doctype} list view renders`, async ({ page }) => {
		const errors: string[] = [];
		page.on("pageerror", (e) => errors.push(e.message));
		await openList(page, doctype);
		await expect(page.locator(".layout-main-section")).toBeVisible();
		expect(errors).toEqual([]);
	});
}

for (const doctype of DOCTYPES.filter((d) => !NO_NEW_FORM.includes(d))) {
	test(`${doctype} form renders its fields`, async ({ page }) => {
		await openNew(page, doctype);
		await expect(page.locator(".form-layout .frappe-control:visible").first()).toBeVisible();
	});
}
