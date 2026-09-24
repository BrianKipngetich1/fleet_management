import { expect, test, type Page } from "@playwright/test";
import { authenticate } from "../auth";
import { openNew } from "../desk";
import { QA_FIXTURES, USERS } from "../fixtures";

test.use({ storageState: USERS.primary.state });

type Resource = { name: string };

async function resourceData<T>(response: Awaited<ReturnType<Page["request"]["get"]>>, label: string) {
	const body = await response.text();
	if (!response.ok()) throw new Error(`${label} failed (${response.status()})`);
	return (JSON.parse(body) as { data: T }).data;
}

async function csrf(page: Page) {
	return page.evaluate(() => window.frappe.csrf_token as string);
}

async function clearBrowserHttpCache(page: Page) {
	const cdp = await page.context().newCDPSession(page);
	await cdp.send("Network.clearBrowserCache");
	await cdp.detach();
}

async function firstName(page: Page, doctype: string, exactName?: string, match?: RegExp) {
	const response = await page.request.get(`/api/resource/${encodeURIComponent(doctype)}`, {
		params: {
			fields: JSON.stringify(["name"]),
			filters: exactName ? JSON.stringify({ name: exactName }) : undefined,
			limit_page_length: "100",
		},
	});
	const rows = await resourceData<Resource[]>(response, `${doctype} lookup`);
	const row = exactName ? rows[0] : match ? rows.find(({ name }) => match.test(name)) : rows[0];
	expect(row, `Expected a ${doctype} fixture`).toBeTruthy();
	return row!.name;
}

async function nextOdometer(page: Page, asset: string) {
	const response = await page.request.get("/api/resource/Fueling Transaction", {
		params: {
			filters: JSON.stringify({ asset }),
			fields: JSON.stringify(["vehicle_odometer"]),
			order_by: "vehicle_odometer desc",
			limit_page_length: "100",
		},
	});
	const rows = await resourceData<{ vehicle_odometer?: number }[]>(response, "odometer lookup");
	const maximum = Math.max(0, ...rows.map((row) => Number(row.vehicle_odometer) || 0));
	return maximum + 1000;
}

async function createQaAsset(page: Page, fuelType: string, location: string, custodian: string) {
	const identifier = `Desk QA Vehicle ${Date.now()}`;
	await authenticate(page, USERS.admin.email, "/app/fuel-order");
	const response = await page.request.post("/api/resource/Fleet Asset", {
		data: {
			doctype: "Fleet Asset",
			asset_identifier: identifier,
			asset_type: "Vehicle",
			active: 1,
			fuel_type: fuelType,
			tank_capacity_litres: 60,
			target_km_per_litre: 10,
			assignments: [
				{
					doctype: "Asset Assignment",
					custodian,
					assigned_location: location,
					effective_from: "2026-01-01",
				}
			],
		},
		headers: { "X-Frappe-CSRF-Token": await csrf(page) },
	});
	const asset = await resourceData<Resource>(response, "QA asset creation");
	await authenticate(page, USERS.primary.email, "/app/fuel-order");
	return asset.name;
}

async function createApprovedOrder(page: Page, refs: Record<string, string>, meter: number) {
	const create = await page.request.post("/api/resource/Fuel Order", {
		data: {
			doctype: "Fuel Order",
			request_datetime: await page.evaluate(() => window.frappe.datetime.now_datetime()),
			actual_requester: refs.requester,
			driver: refs.driver,
			custodian: refs.custodian,
			company_representative: refs.representative,
			asset: refs.asset,
			operational_location: refs.location,
			planned_station: refs.station,
			fuel_type: refs.fuelType,
			request_meter_reading: meter,
			request_gauge_percent: 40,
		},
		headers: { "X-Frappe-CSRF-Token": await csrf(page) },
	});
	const order = await resourceData<Resource>(create, "Fuel Order creation");
	const submit = await page.request.post("/api/method/frappe.model.workflow.apply_workflow", {
		data: {
			doc: JSON.stringify({ doctype: "Fuel Order", name: order.name }),
			action: "Submit for Approval",
		},
		headers: { "X-Frappe-CSRF-Token": await csrf(page) },
	});
	await resourceData(submit, "Fuel Order submission");

	await authenticate(page, USERS.approver.email, `/app/fuel-order/${encodeURIComponent(order.name)}`);
	const approve = await page.request.post("/api/method/frappe.model.workflow.apply_workflow", {
		data: {
			doc: JSON.stringify({ doctype: "Fuel Order", name: order.name }),
			action: "Approve",
		},
		headers: { "X-Frappe-CSRF-Token": await csrf(page) },
	});
	await resourceData(approve, "Fuel Order approval");
	const print = await page.request.get(
		`/printview?doctype=${encodeURIComponent("Fuel Order")}&name=${encodeURIComponent(order.name)}&format=${encodeURIComponent("Fuel Order Approval Slip")}&no_letterhead=1`,
	);
	expect(print.ok(), "approved Fuel Order slip must be printed before fueling").toBeTruthy();
	await authenticate(page, USERS.primary.email, `/app/fuel-order/${encodeURIComponent(order.name)}`);
	return order.name;
}

const PDF_CONTENT = Buffer.from(
	"%PDF-1.4\n" +
		"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n" +
		"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n" +
		"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n" +
		"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n" +
		"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n186\n%%EOF\n",
	"utf8",
);
const PNG_CONTENT = Buffer.from(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
	"base64",
);

async function uploadEvidence(page: Page, transaction: string, fieldname: string, extension: "pdf" | "png") {
	const content = extension === "pdf" ? PDF_CONTENT : PNG_CONTENT;
	const response = await page.request.post("/api/method/upload_file", {
		multipart: {
			file: {
				name: `desk-qa-${transaction}-${fieldname}.${extension}`,
				mimeType: extension === "pdf" ? "application/pdf" : "image/png",
				buffer: content,
			},
			doctype: "Fueling Transaction",
			docname: transaction,
			fieldname,
			is_private: "1",
		},
		headers: { "X-Frappe-CSRF-Token": await csrf(page) },
	});
	const body = await response.text();
	if (!response.ok()) throw new Error(`${fieldname} upload failed (${response.status()})`);
	const payload = JSON.parse(body) as { message?: { file_url?: string } | string };
	const message = payload.message;
	const fileUrl = typeof message === "string" ? message : message?.file_url;
	expect(fileUrl, `${fieldname} upload did not return a file URL`).toBeTruthy();
	return { file_url: fileUrl! };
}

async function submitTransaction(
	page: Page,
	order: string,
	values: { invoice: string; cu: string; litres: number; odometer: number; full: number },
) {
	const create = await page.request.post("/api/resource/Fueling Transaction", {
		data: {
			doctype: "Fueling Transaction",
			fuel_order: order,
			actual_fueling_datetime: await page.evaluate(() => window.frappe.datetime.now_datetime()),
			fueling_time_source: "Printed on invoice",
			invoice_number: values.invoice,
			cu_number: values.cu,
			invoice_litres: values.litres,
			vehicle_odometer: values.odometer,
			full_tank_confirmed: values.full,
			attendant_name: "Playwright Attendant",
		},
		headers: { "X-Frappe-CSRF-Token": await csrf(page) },
	});
	const transaction = await resourceData<Resource>(create, "Fueling Transaction creation");
	const invoice = await uploadEvidence(page, transaction.name, "signed_invoice", "pdf");
	const signedOrder = await uploadEvidence(page, transaction.name, "signed_order", "png");
	const saved = await page.request.get(
		`/api/resource/Fueling Transaction/${encodeURIComponent(transaction.name)}`,
	);
	const document = await resourceData<Record<string, unknown>>(saved, "Fueling Transaction reload");
	document.signed_invoice = invoice.file_url;
	document.signed_order = signedOrder.file_url;

	const submit = await page.request.post("/api/method/frappe.client.submit", {
		data: { doc: JSON.stringify(document) },
		headers: { "X-Frappe-CSRF-Token": await csrf(page) },
	});
	await resourceData(submit, "Fueling Transaction submission");
	await page.goto(`/app/fueling-transaction/${encodeURIComponent(transaction.name)}`);
	await page.waitForFunction((name) => window.cur_frm?.doc?.name === name, transaction.name);
	return transaction.name;
}

test("live Desk transaction acceptance covers evidence, KPI, integrity, and scope", async ({ page }) => {
	await openNew(page, "Fueling Transaction");
	await expect(page.locator(".form-layout")).toBeVisible();
	await expect(page.locator("body")).toContainText("Signed Evidence");
	await expect(page.locator("body")).toContainText("Vehicle Efficiency");
	const explanationField = page.locator('.frappe-control[data-fieldname="fueling_time_explanation"]');
	const timeSourceField = page.locator('.frappe-control[data-fieldname="fueling_time_source"] select');
	await expect(explanationField).toBeHidden();
	await timeSourceField.selectOption({ label: "Not printed on invoice" });
	await expect(explanationField).toBeVisible();
	await timeSourceField.selectOption({ label: "Printed on invoice" });
	await expect(explanationField).toBeHidden();

	const refs = {
		location: await firstName(page, "Fleet Location", "Nairobi"),
		station: await firstName(page, "Fuel Station", QA_FIXTURES.station),
		fuelType: await firstName(page, "Fuel Type", QA_FIXTURES.fuelTypes[0]),
		asset: "",
		requester: await firstName(page, "Fleet Person", QA_FIXTURES.requester),
		driver: await firstName(page, "Fleet Person", QA_FIXTURES.driver),
		custodian: await firstName(page, "Fleet Person", QA_FIXTURES.custodian),
		representative: await firstName(page, "Fleet Person", QA_FIXTURES.representative),
	};
	const asset = await createQaAsset(page, refs.fuelType, refs.location, refs.custodian);
	refs.asset = asset;
	const run = `${Date.now()}`;
	const baseOdometer = await nextOdometer(page, refs.asset);

	const timeSourceOrder = await createApprovedOrder(page, refs, baseOdometer);
	const missingExplanation = await page.request.post("/api/resource/Fueling Transaction", {
		data: {
			doctype: "Fueling Transaction",
			fuel_order: timeSourceOrder,
			fueling_time_source: "Not printed on invoice",
		},
		headers: { "X-Frappe-CSRF-Token": await csrf(page) },
	});
	const timeSourceDraft = await resourceData<Resource>(missingExplanation, "time-source draft creation");
	await page.goto(`/app/fueling-transaction/${encodeURIComponent(timeSourceDraft.name)}`);
	await page.waitForFunction((name) => window.cur_frm?.doc?.name === name, timeSourceDraft.name);
	await expect(explanationField).toBeVisible();
	await page
		.locator(".page-actions button")
		.filter({ hasText: /^\s*Submit\s*$/ })
		.first()
		.click();
	const confirmation = page.locator(".modal.show").filter({
		hasText: /Permanently Submit|Are you sure/,
	});
	await expect(confirmation).toBeVisible();
	await confirmation.locator(".btn-primary:visible").first().click();
	await expect(
		page.locator(".modal.show").filter({
			hasText: /Please fill the following mandatory fields before saving/,
		}),
	).toContainText("Station Time Explanation is required.");

	const firstOrder = await createApprovedOrder(page, refs, baseOdometer);
	await expect.poll(() => page.evaluate(() => window.frappe.session.user)).toBe(USERS.primary.email);
	// The test switches `sid` cookies across roles in one browser context; flush the
	// browser's per-URL HTTP cache so Desk fetches this user's notification list.
	await clearBrowserHttpCache(page);
	await page.reload({ waitUntil: "domcontentloaded" });
	// Ask the server directly as this user: a body captured from Desk's own request is lost
	// whenever the page navigates again before it is read.
	const notificationResponse = await page.request.get(
		"/api/method/frappe.desk.doctype.notification_log.notification_log.get_notification_logs"
	);
	expect(notificationResponse.ok()).toBeTruthy();
	const notificationBody = await notificationResponse.json();
	expect(notificationBody.message.notification_logs).toEqual(
		expect.arrayContaining([
			expect.objectContaining({
				subject: `Fuel Order ${firstOrder} was approved`,
				link: `/app/fuel-order/${encodeURIComponent(firstOrder)}`,
			}),
		])
	);
	await page.locator(".sidebar-notification").click();
	const approvalNotice = page
		.locator(".dropdown-notifications .notification-item")
		.filter({ hasText: `Fuel Order ${firstOrder} was approved` });
	await expect(approvalNotice).toBeVisible();
	await expect(approvalNotice).toHaveAttribute(
		"href",
		`/app/fuel-order/${encodeURIComponent(firstOrder)}`
	);
	const firstTransaction = await submitTransaction(page, firstOrder, {
		invoice: `E2E-${run}-1`,
		cu: `E2E-CU-${run}-1`,
		litres: 60,
		odometer: baseOdometer,
		full: 1,
	});
	const first = await page.evaluate(() => window.cur_frm.doc);
	expect(first.docstatus).toBe(1);
	expect(first.signed_invoice).toContain("/private/files/");
	expect(first.signed_order).toContain("/private/files/");
	expect(first.is_efficiency_baseline).toBe(1);
	expect(first.km_per_litre).toBeFalsy();

	const partialOrder = await createApprovedOrder(page, refs, baseOdometer + 200);
	await submitTransaction(page, partialOrder, {
		invoice: `E2E-${run}-2`,
		cu: `E2E-CU-${run}-2`,
		litres: 10,
		odometer: baseOdometer + 200,
		full: 0,
	});

	const closingOrder = await createApprovedOrder(page, refs, baseOdometer + 500);
	const closingTransaction = await submitTransaction(page, closingOrder, {
		invoice: `E2E-${run}-3`,
		cu: `E2E-CU-${run}-3`,
		litres: 40,
		odometer: baseOdometer + 500,
		full: 1,
	});
	const closing = await page.evaluate(() => window.cur_frm.doc);
	expect(closing.name).toBe(closingTransaction);
	expect(Number(closing.distance_km)).toBe(500);
	expect(Number(closing.qualifying_litres)).toBe(50);
	expect(Number(closing.km_per_litre)).toBe(10);
	expect(closing.previous_full_fill).toBe(firstTransaction);

	// The same order cannot be submitted twice, even when the second attempt carries valid evidence.
	const duplicateCreate = await page.request.post("/api/resource/Fueling Transaction", {
		data: { doctype: "Fueling Transaction", fuel_order: firstOrder, invoice_litres: 1 },
		headers: { "X-Frappe-CSRF-Token": await csrf(page) },
	});
	const duplicate = await resourceData<Resource>(duplicateCreate, "duplicate transaction creation");
	await uploadEvidence(page, duplicate.name, "signed_invoice", "pdf");
	await uploadEvidence(page, duplicate.name, "signed_order", "png");
	const duplicateSubmit = await page.request.post("/api/method/frappe.client.submit", {
		data: { doc: JSON.stringify({ doctype: "Fueling Transaction", name: duplicate.name }) },
		headers: { "X-Frappe-CSRF-Token": await csrf(page) },
	});
	expect(duplicateSubmit.ok()).toBeFalsy();
	expect(await duplicateSubmit.text()).not.toMatch(/Werkzeug Debugger|Traceback|Interactive debugger|sid=/i);

	// The other-location user cannot list, read, print, or invoke the extension action on North records.
	await authenticate(page, USERS.restricted.email, "/app/fuel-order");
	// Session-cookie role switches reuse this test browser's URL cache; force Desk to
	// reload the restricted user's own notification response before scope assertions.
	await clearBrowserHttpCache(page);
	await page.reload({ waitUntil: "domcontentloaded" });
	await page.waitForFunction((user) => window.frappe.session.user === user, USERS.restricted.email);
	const restrictedOrders = await page.request.get("/api/resource/Fuel Order", {
		params: { filters: JSON.stringify({ name: firstOrder }), fields: JSON.stringify(["name"]) },
	});
	expect(restrictedOrders.ok()).toBeTruthy();
	expect((await restrictedOrders.json()).data).toEqual([]);
	const restrictedReportView = await page.request.get("/api/method/frappe.desk.reportview.get", {
		params: {
			doctype: "Fuel Order",
			fields: JSON.stringify(["name"]),
			filters: JSON.stringify([["Fuel Order", "name", "=", firstOrder]]),
			limit_page_length: "20",
		},
	});
	expect(restrictedReportView.ok()).toBeTruthy();
	expect(await restrictedReportView.text()).not.toContain(firstOrder);

	for (const [doctype, name] of [
		["Fuel Order", firstOrder],
		["Fueling Transaction", firstTransaction],
	] as const) {
		const response = await page.request.get(
			`/api/resource/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`,
		);
		expect([403, 404]).toContain(response.status());
	}
	await page.goto(`/app/fuel-order/${encodeURIComponent(firstOrder)}`);
	// Frappe's own denial dialog repeats the name typed in the URL, so wait for the denial
	// and then prove that no part of the order itself reached the page.
	await expect(page.locator(".modal.show")).toContainText("Not permitted");
	expect(await page.evaluate((name) => window.cur_frm?.doc?.name === name, firstOrder)).toBeFalsy();
	await expect(page.locator(".form-layout:visible")).toHaveCount(0);
	await expect(page.locator("body")).not.toContainText(refs.asset);
	await expect(page.locator("body")).not.toContainText(/Werkzeug Debugger|Traceback|Interactive debugger/i);

	const print = await page.request.get(
		`/printview?doctype=${encodeURIComponent("Fuel Order")}&name=${encodeURIComponent(firstOrder)}&format=${encodeURIComponent("Fuel Order Approval Slip")}&no_letterhead=1`,
	);
	expect([403, 404]).toContain(print.status());

	const extension = await page.request.post("/api/method/run_doc_method", {
		data: {
			dt: "Fuel Order",
			dn: firstOrder,
			method: "extend_validity",
			args: JSON.stringify({ new_valid_until: "2099-01-01 00:00:00", reason: "denied" }),
		},
		headers: { "X-Frappe-CSRF-Token": await csrf(page) },
	});
	expect([403, 404, 417]).toContain(extension.status());
	expect(await extension.text()).not.toMatch(/Werkzeug Debugger|Traceback|Interactive debugger|sid=/i);
});
