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
test.skip(!SCOPE_DOCTYPE, "This application has no row-level scoping — see e2e/fixtures.ts.");

test("the scoped list shows only the user's permitted records", async ({ page }) => {
	await openList(page, SCOPE_DOCTYPE);
	const names = await listRows(page);
	expect(names.sort()).toEqual([...SCOPED_VALUES].sort());
});

test("a scoping link field offers only permitted values", async ({ page }) => {
	await openNew(page, SCOPE_HOST_DOCTYPE);
	const options = await linkOptions(page, SCOPE_FIELD, SCOPE_QUERY);
	expect(options.sort()).toEqual([...SCOPED_VALUES].sort());
});
