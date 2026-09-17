import { expect, test } from "@playwright/test";
import { cancelDoc, openNew, save, setLink, setValue, submitDoc, userDate } from "../desk";
import { USERS } from "../fixtures";

// The one spec in this suite that must be written per project: it drives the
// application's central submittable document from draft to submitted to cancelled.
// Keep it to that lifecycle. Anything that proves a single phase's acceptance criterion
// belongs in the agent-browser walkthrough and in an IntegrationTestCase instead — see
// CLAUDE.md "What the regression suite is not".

test.use({ storageState: USERS.primary.state });

test.skip(true, "Replace with this application's central submittable document.");

test("a document goes draft -> submitted -> cancelled", async ({ page }) => {
	await openNew(page, "[Submittable DocType]");

	await setLink(page, "[link_fieldname]", "[value]");
	await setValue(page, "[data_fieldname]", "[value]");
	await setValue(page, "[date_fieldname]", await userDate(page, "2026-01-31"));

	const name = await save(page);
	expect(name).toBeTruthy();

	await submitDoc(page);
	expect(await page.evaluate(() => window.cur_frm.doc.docstatus)).toBe(1);

	await cancelDoc(page);
	expect(await page.evaluate(() => window.cur_frm.doc.docstatus)).toBe(2);
});
