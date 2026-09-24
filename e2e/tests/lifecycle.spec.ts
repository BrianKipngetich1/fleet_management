import { expect, test } from "@playwright/test";
import { authenticate } from "../auth";
import { cancelDoc, openNew, save, setLink, setValue, userDate } from "../desk";
import { QA_FIXTURES, USERS } from "../fixtures";

// The one spec in this suite that must be written per project: it drives the
// application's central submittable document from draft to submitted to cancelled.
// Keep it to that lifecycle. Anything that proves a single phase's acceptance criterion
// belongs in the agent-browser walkthrough and in an IntegrationTestCase instead — see
// CLAUDE.md "What the regression suite is not".

test.use({ storageState: USERS.primary.state });

async function firstName(
	page: Parameters<typeof openNew>[0],
	doctype: string,
	exactName?: string,
	match?: RegExp,
) {
	const response = await page.request.get(`/api/resource/${encodeURIComponent(doctype)}`, {
		params: {
			fields: JSON.stringify(["name"]),
			filters: exactName ? JSON.stringify({ name: exactName }) : undefined,
			limit_page_length: "100",
		},
	});
	const body = await response.text();
	expect(response.ok(), `${doctype} lookup failed (${response.status()})`).toBeTruthy();
	const rows = JSON.parse(body).data as { name: string }[];
	const row = exactName ? rows[0] : match ? rows.find(({ name }) => match.test(name)) : rows[0];
	expect(row, `Expected a ${doctype} fixture${match ? ` matching ${match}` : ""}`).toBeTruthy();
	return row!.name;
}

async function loginAs(page: Parameters<typeof openNew>[0], email: string) {
	await authenticate(page, email);
}

test("a Fuel Order goes draft -> approved -> cancelled", async ({ page }) => {
	const location = await firstName(page, "Fleet Location", "Nairobi");
	const station = await firstName(page, "Fuel Station", QA_FIXTURES.station);
	const fuelType = await firstName(page, "Fuel Type", QA_FIXTURES.fuelTypes[0]);
	const asset = await firstName(page, "Fleet Asset", QA_FIXTURES.asset);
	const requester = await firstName(page, "Fleet Person", QA_FIXTURES.requester);
	const driver = await firstName(page, "Fleet Person", QA_FIXTURES.driver);
	const custodian = await firstName(page, "Fleet Person", QA_FIXTURES.custodian);
	const representative = await firstName(page, "Fleet Person", QA_FIXTURES.representative);

	await openNew(page, "Fuel Order");

	await setLink(page, "actual_requester", requester);
	await setLink(page, "driver", driver);
	await setLink(page, "custodian", custodian);
	await setLink(page, "company_representative", representative);
	await setLink(page, "asset", asset);
	await setLink(page, "operational_location", location);
	await setLink(page, "planned_station", station);
	await setLink(page, "fuel_type", fuelType);
	await setValue(page, "request_meter_reading", "1000");
	await setValue(page, "request_gauge_percent", "40");

	const name = await save(page);
	expect(name).toBeTruthy();

	await page.getByRole("button", { name: "Actions", exact: true }).click();
	await page.locator(".actions-btn-group .dropdown-menu").getByText("Submit for Approval", { exact: true }).click();
	await page.waitForFunction(() => window.cur_frm?.doc?.workflow_state === "Pending Approval");
	expect(await page.evaluate(() => window.cur_frm.doc.docstatus)).toBe(0);

	await loginAs(page, USERS.approver.email);
	await page.goto(`/app/fuel-order/${encodeURIComponent(name)}`);
	await page.waitForFunction((docname) => window.cur_frm?.doc?.name === docname, name);
	await page.getByRole("button", { name: "Actions", exact: true }).click();
	await page.locator(".actions-btn-group .dropdown-menu").getByText("Approve", { exact: true }).click();
	await page.waitForFunction(() => window.cur_frm?.doc?.workflow_state === "Approved");
	expect(await page.evaluate(() => window.cur_frm.doc.docstatus)).toBe(1);

	// The app's own "Actions" button group, not Frappe's workflow-actions button of the same
	// name, which can be present at the same time once the approved form refreshes.
	const appActions = page.locator('.inner-group-button[data-label="Actions"]');
	await appActions.locator("button").click();
	await appActions.locator(".dropdown-menu").getByText("Extend Validity", { exact: true }).click();
	const extendedUntil = await page.evaluate(() =>
		window.moment(window.cur_frm.doc.valid_until).add(1, "days").format("YYYY-MM-DD HH:mm:ss"),
	);
	// Type, never fill: an instant fill while the date picker is open lets the picker
	// replace the typed time with the current time.
	const validUntilInput = page.locator('.modal.show [data-fieldname="new_valid_until"] input');
	// Keys sent before the field's date picker has opened are lost.
	await validUntilInput.click();
	await expect(page.locator(".datepicker.active")).toBeVisible();
	await validUntilInput.pressSequentially(await userDate(page, extendedUntil));
	await validUntilInput.press("Tab");
	await expect
		.poll(() => page.evaluate(() => window.cur_dialog.get_value("new_valid_until")))
		.toBe(extendedUntil);
	await page.locator('.modal.show [data-fieldname="reason"] textarea').fill("Desk QA pre-fueling extension");
	await page.locator('.modal.show .btn-primary').getByText("Extend", { exact: true }).click();
	await page.waitForFunction(() => window.cur_frm?.doc?.reprint_required === 1);

	await page.goto(
		`/printview?doctype=${encodeURIComponent("Fuel Order")}&name=${encodeURIComponent(name)}&format=${encodeURIComponent("Fuel Order Approval Slip")}&no_letterhead=1`,
	);
	await expect(page.locator("body")).toContainText("Do not dispense after the valid-until timestamp");

	await loginAs(page, USERS.admin.email);
	await page.goto(`/app/fuel-order/${encodeURIComponent(name)}`);
	await page.waitForFunction((docname) => window.cur_frm?.doc?.name === docname, name);
	await cancelDoc(page);
	expect(await page.evaluate(() => window.cur_frm.doc.docstatus)).toBe(2);
});
