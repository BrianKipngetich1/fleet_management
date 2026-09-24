import { expect, test } from "@playwright/test";
import { linkOptions, listRows, openList, openNew } from "../desk";
import {
	SCOPED_VALUES,
	SCOPE_DOCTYPE,
	SCOPE_FIELD,
	SCOPE_HOST_DOCTYPE,
	SCOPE_QUERY,
	USERS,
} from "../fixtures";

test.use({ storageState: USERS.primary.state });

test("the scoped list shows only the user's permitted records", async ({ page }) => {
	const errors: string[] = [];
	page.on("pageerror", (error) => errors.push(error.message));
	await openList(page, SCOPE_DOCTYPE);
	const names = await listRows(page);
	expect(names.sort()).toEqual([...SCOPED_VALUES].sort());
	expect(errors).toEqual([]);
});

test("the Fueling Transaction list finishes loading, including with no rows", async ({ page }) => {
	const errors: string[] = [];
	page.on("pageerror", (error) => errors.push(error.message));
	await openList(page, "Fueling Transaction");
	await expect(page.locator(".layout-main-section")).toBeVisible();
	const names = await listRows(page);
	await expect(page.locator(".layout-main-section")).not.toContainText("Object");
	if (names.length === 0) await expect(page.locator(".no-result")).toBeVisible();
	expect(errors).toEqual([]);
});

test("a scoping link field offers only permitted values", async ({ page }) => {
	await openNew(page, SCOPE_HOST_DOCTYPE);
	const options = await linkOptions(page, SCOPE_FIELD, SCOPE_QUERY);
	expect(options.sort()).toEqual([...SCOPED_VALUES].sort());
});
