import { APIResponse, Page } from "@playwright/test";
import { authenticate } from "./auth";
import { QA_FIXTURES, USER_LOCATIONS, USERS } from "./fixtures";

// The suite runs on a test site built from the sample data (`bench fleet-test-site up`). It
// never creates users, permissions, or master data: that would let the suite and the sample
// data drift apart. It only proves the site is the one it expects, and stops early if not.

const REBUILD = "Build the test site first: bench fleet-test-site up --replace";

type UserPermission = { for_value: string; apply_to_all_doctypes: number | string };
type UserDoc = { enabled: number; roles: { role: string }[] };

async function resourceData<T>(response: APIResponse, label: string): Promise<T> {
	const body = await response.text();
	if (!response.ok()) {
		throw new Error(`${label} failed (${response.status()}). ${REBUILD}`);
	}
	return (JSON.parse(body) as { data: T }).data;
}

async function assertExists(page: Page, doctype: string, name: string) {
	const response = await page.request.get(`/api/resource/${encodeURIComponent(doctype)}`, {
		params: {
			fields: JSON.stringify(["name"]),
			filters: JSON.stringify({ name }),
			limit_page_length: "1",
		},
	});
	const rows = await resourceData<{ name: string }[]>(response, `${doctype} lookup for ${name}`);
	if (!rows[0]?.name) throw new Error(`Sample data is missing ${doctype} "${name}". ${REBUILD}`);
}

async function assertUser(page: Page, key: keyof typeof USER_LOCATIONS) {
	const { email, role } = USERS[key];
	const user = await resourceData<UserDoc>(
		await page.request.get(`/api/resource/User/${encodeURIComponent(email)}`),
		`User lookup for ${email}`,
	);
	if (!user.enabled || !user.roles.some((row) => row.role === role)) {
		throw new Error(`${email} must be an enabled ${role}. ${REBUILD}`);
	}

	const permissions = await resourceData<UserPermission[]>(
		await page.request.get("/api/resource/User Permission", {
			params: {
				fields: JSON.stringify(["for_value", "apply_to_all_doctypes"]),
				filters: JSON.stringify({ user: email, allow: "Fleet Location" }),
				limit_page_length: "50",
			},
		}),
		`User Permission lookup for ${email}`,
	);
	const granted = permissions.map((permission) => permission.for_value).sort();
	const expected = USER_LOCATIONS[key];
	if (
		granted.length !== 1 ||
		granted[0] !== expected ||
		Number(permissions[0].apply_to_all_doctypes) !== 1
	) {
		throw new Error(`${email} must hold exactly Fleet Location = ${expected}, found [${granted}]. ${REBUILD}`);
	}
}

export async function assertSampleData(page: Page) {
	await authenticate(page, USERS.admin.email);
	for (const key of Object.keys(USER_LOCATIONS) as (keyof typeof USER_LOCATIONS)[]) {
		await assertUser(page, key);
	}
	for (const location of QA_FIXTURES.locations) await assertExists(page, "Fleet Location", location);
	for (const fuelType of QA_FIXTURES.fuelTypes) await assertExists(page, "Fuel Type", fuelType);
	await assertExists(page, "Fuel Station", QA_FIXTURES.station);
	await assertExists(page, "Vehicle Model", QA_FIXTURES.vehicleModel);
	await assertExists(page, "Fleet Asset", QA_FIXTURES.asset);
	for (const person of [
		QA_FIXTURES.requester,
		QA_FIXTURES.driver,
		QA_FIXTURES.custodian,
		QA_FIXTURES.representative,
	]) {
		await assertExists(page, "Fleet Person", person);
	}
}
