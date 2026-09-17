import { Page, expect } from "@playwright/test";

// Frappe Desk mechanics. Nothing here is project-specific — project facts live in
// e2e/fixtures.ts. Each helper encodes a Desk behaviour that costs time when forgotten;
// see CLAUDE.md "Desk quirks that cost time when forgotten".

declare global {
	interface Window {
		frappe: any;
		cur_frm: any;
		cur_list: any;
	}
}

const slug = (doctype: string) => doctype.toLowerCase().replace(/ /g, "-");

export async function openList(page: Page, doctype: string) {
	await page.goto(`/app/${slug(doctype)}`);
	await page.waitForFunction(
		(dt) => window.cur_list?.doctype === dt && !window.cur_list.loading,
		doctype
	);
}

export async function openNew(page: Page, doctype: string) {
	await page.goto(`/app/${slug(doctype)}/new`);
	await waitForForm(page, doctype);
}

async function waitForForm(page: Page, doctype: string) {
	await page.waitForFunction((dt) => window.cur_frm?.doc?.doctype === dt, doctype);
}

// cur_list.loading clears before the first fetch populates cur_list.data. Wait for the
// data, then assert once on that first loaded state — polling until an assertion passes
// would tolerate a list that briefly showed unpermitted rows and then settled.
export async function listRows(page: Page): Promise<string[]> {
	await page.waitForFunction(() => ((window.cur_list?.data as unknown[])?.length ?? 0) > 0);
	return page.evaluate(() => (window.cur_list.data as { name: string }[]).map((r) => r.name));
}

const control = (page: Page, fieldname: string) =>
	page
		.locator(
			`.frappe-control[data-fieldname="${fieldname}"] input:visible, ` +
				`.frappe-control[data-fieldname="${fieldname}"] textarea:visible, ` +
				`.frappe-control[data-fieldname="${fieldname}"] select:visible`
		)
		.first();

// Focus rather than click: a neighbouring field's open autocomplete overlays the
// target input often enough that hit-testing is not worth the flake.
async function focusField(page: Page, fieldname: string) {
	await page.keyboard.press("Escape");
	const input = control(page, fieldname);
	await input.scrollIntoViewIfNeeded();
	await input.focus();
	return input;
}

// A currency or data field only reaches the model on blur — Frappe commits the typed
// value in the change handler, not on keystroke. Tab, then read the model back.
export async function setValue(page: Page, fieldname: string, value: string) {
	const input = await focusField(page, fieldname);
	await input.fill(value);
	await input.press("Tab");
	await page.waitForFunction(
		([f]) =>
			window.cur_frm.doc[f] !== undefined &&
			window.cur_frm.doc[f] !== null &&
			window.cur_frm.doc[f] !== "",
		[fieldname]
	);
}

// A link field must have its autocomplete option clicked. Typing and blurring leaves
// the model value undefined even though the input shows the text.
export async function setLink(page: Page, fieldname: string, value: string) {
	const input = await focusField(page, fieldname);
	await input.fill(value);
	await optionsFor(page, fieldname).filter({ hasText: value }).first().click();
	await page.waitForFunction(([f, v]) => window.cur_frm.doc[f] === v, [fieldname, value]);
}

// Frappe's link autocomplete renders each entry as div[role="option"], never as an li.
const optionsFor = (page: Page, fieldname: string) =>
	page.locator(`.frappe-control[data-fieldname="${fieldname}"] .awesomplete [role="option"]`);

const PSEUDO_OPTIONS = /^(Create a new |Advanced Search$)/;

// `query` should be a separator or prefix shared by every permitted value, so the live
// link search returns the full permitted set rather than a guessed subset.
export async function linkOptions(page: Page, fieldname: string, query: string): Promise<string[]> {
	const input = await focusField(page, fieldname);
	await input.fill(query);
	const options = optionsFor(page, fieldname);
	await expect(options.first()).toBeVisible();
	const titles = await options
		.locator("p")
		.evaluateAll((nodes) => nodes.map((n) => n.getAttribute("title") || ""));
	return titles.filter((t) => t && !PSEUDO_OPTIONS.test(t));
}

// The site's date format follows its locale, which complete_setup_wizard sets to US.
// Never type a hard-coded ISO date into a Desk date field.
export function userDate(page: Page, iso: string): Promise<string> {
	return page.evaluate((d) => window.frappe.datetime.str_to_user(d) as string, iso);
}

export async function save(page: Page) {
	await page.keyboard.press("Control+s");
	await page.waitForFunction(
		() => window.cur_frm && !window.cur_frm.doc.__unsaved && !window.cur_frm.doc.__islocal
	);
	return page.evaluate(() => window.cur_frm.doc.name as string);
}

// Submit is a primary page action; Cancel is a plain .page-actions button on a
// submitted document — it is not a menu dropdown item.
async function pageAction(page: Page, label: string) {
	await page
		.locator(".page-actions button", { hasText: new RegExp(`^\\s*${label}\\s*$`) })
		.first()
		.click();
	await page.locator(".modal.show .btn-primary:visible").first().click();
}

export async function submitDoc(page: Page) {
	await pageAction(page, "Submit");
	await page.waitForFunction(() => window.cur_frm.doc.docstatus === 1);
}

export async function cancelDoc(page: Page) {
	await pageAction(page, "Cancel");
	await page.waitForFunction(() => window.cur_frm.doc.docstatus === 2);
}

export async function apiPost(page: Page, path: string, data: object) {
	const csrf = await page.evaluate(() => window.frappe.csrf_token);
	return page.request.post(path, { data, headers: { "X-Frappe-CSRF-Token": csrf } });
}
