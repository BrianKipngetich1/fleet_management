import { APIResponse, Page } from "@playwright/test";
import { authenticate } from "./auth";
import { QA_FIXTURES, USERS } from "./fixtures";

const QA_LOCATION = "Nairobi";
const RESTRICTED_LOCATION = "Mombasa";
const APPROVED_LOCATIONS = QA_FIXTURES.locations;
const APPROVED_FUEL_TYPES = QA_FIXTURES.fuelTypes;

type UserPermission = {
	name: string;
	for_value: string;
	apply_to_all_doctypes: number | string;
};

const QA_USERS = [
	{ email: USERS.primary.email, first_name: "Desk QA Requester", roles: ["Fleet User"] },
	{ email: USERS.restricted.email, first_name: "Desk QA Restricted", roles: ["Fleet Approver"] },
	{ email: USERS.approver.email, first_name: "Desk QA Approver", roles: ["Fleet Approver"] },
] as const;

async function resourceData<T>(response: APIResponse, label: string): Promise<T> {
	const body = await response.text();
	if (!response.ok()) {
		throw new Error(`${label} failed (${response.status()})`);
	}
	return (JSON.parse(body) as { data: T }).data;
}

export async function ensureQaLocationPermissions(page: Page) {
	await authenticate(page, USERS.admin.email);
	await ensureQaUsers(page);
	for (const location of APPROVED_LOCATIONS) await ensureLocation(page, location);
	for (const fuelType of APPROVED_FUEL_TYPES) await ensureFuelType(page, fuelType);
	await ensureFleetMasterData(page);

	const csrfToken = await page.evaluate(() => (window as any).frappe.csrf_token as string);
	const headers = { "X-Frappe-CSRF-Token": csrfToken };
	const grants = new Map([
		[USERS.primary.email, QA_LOCATION],
		[USERS.restricted.email, RESTRICTED_LOCATION],
		[USERS.approver.email, QA_LOCATION],
	]);

	for (const [user, location] of grants) {
		const permissionsResponse = await page.request.get("/api/resource/User Permission", {
			params: {
				fields: JSON.stringify(["name", "for_value", "apply_to_all_doctypes"]),
				filters: JSON.stringify({ user, allow: "Fleet Location" }),
				limit_page_length: "50",
			},
		});
		const permissions = await resourceData<UserPermission[]>(
			permissionsResponse,
			`User Permission lookup for ${user}`
		);
		const existing = permissions.find((permission) => permission.for_value === location);

		for (const permission of permissions.filter((permission) => permission.for_value !== location)) {
			const deleteResponse = await page.request.delete(
				`/api/resource/User Permission/${encodeURIComponent(permission.name)}`,
				{ headers },
			);
			if (!deleteResponse.ok()) {
				throw new Error(`Stale User Permission removal for ${user} failed (${deleteResponse.status()})`);
			}
		}

		if (existing) {
			if (Number(existing.apply_to_all_doctypes) !== 1) {
				const updateResponse = await page.request.put(
					`/api/resource/User Permission/${encodeURIComponent(existing.name)}`,
					{ data: { apply_to_all_doctypes: 1 }, headers }
				);
				await resourceData<UserPermission>(updateResponse, `User Permission update for ${user}`);
			}
			continue;
		}

		const createResponse = await page.request.post("/api/resource/User Permission", {
			data: {
				doctype: "User Permission",
				user,
				allow: "Fleet Location",
				for_value: location,
				apply_to_all_doctypes: 1,
			},
			headers,
		});
		await resourceData<UserPermission>(createResponse, `User Permission creation for ${user}`);
	}
}

async function ensureLocation(page: Page, location: string) {
	const response = await page.request.get("/api/resource/Fleet Location", {
		params: {
			fields: JSON.stringify(["name"]),
			filters: JSON.stringify({ name: location }),
			limit_page_length: "1",
		},
	});
	const locations = await resourceData<{ name: string }[]>(response, `Fleet Location lookup for ${location}`);
	if (locations[0]?.name) return;

	const createResponse = await page.request.post("/api/resource/Fleet Location", {
		data: { doctype: "Fleet Location", location_name: location, active: 1 },
		headers: { "X-Frappe-CSRF-Token": await csrfToken(page) },
	});
	await resourceData(createResponse, `Fleet Location creation for ${location}`);
}

async function ensureFuelType(page: Page, fuelType: string) {
	const response = await page.request.get("/api/resource/Fuel Type", {
		params: {
			fields: JSON.stringify(["name"]),
			filters: JSON.stringify({ name: fuelType }),
			limit_page_length: "1",
		},
	});
	const fuelTypes = await resourceData<{ name: string }[]>(response, `Fuel Type lookup for ${fuelType}`);
	if (fuelTypes[0]?.name) return;

	const createResponse = await page.request.post("/api/resource/Fuel Type", {
		data: { doctype: "Fuel Type", fuel_type_name: fuelType, active: 1 },
		headers: { "X-Frappe-CSRF-Token": await csrfToken(page) },
	});
	await resourceData(createResponse, `Fuel Type creation for ${fuelType}`);
}

async function ensureFleetMasterData(page: Page) {
	const personNames = [
		QA_FIXTURES.requester,
		QA_FIXTURES.driver,
		QA_FIXTURES.custodian,
		QA_FIXTURES.representative,
	];
	for (const personName of personNames) {
		const lookup = await page.request.get("/api/resource/Fleet Person", {
			params: {
				fields: JSON.stringify(["name"]),
				filters: JSON.stringify({ name: personName }),
				limit_page_length: "1",
			},
		});
		const people = await resourceData<{ name: string }[]>(lookup, `Fleet Person lookup for ${personName}`);
		if (people[0]?.name) continue;
		const create = await page.request.post("/api/resource/Fleet Person", {
			data: { doctype: "Fleet Person", person_name: personName, active: 1 },
			headers: { "X-Frappe-CSRF-Token": await csrfToken(page) },
		});
		await resourceData(create, `Fleet Person creation for ${personName}`);
	}

	const stationName = QA_FIXTURES.station;
	const stationLookup = await page.request.get("/api/resource/Fuel Station", {
		params: {
			fields: JSON.stringify(["name"]),
			filters: JSON.stringify({ name: stationName }),
			limit_page_length: "1",
		},
	});
	const stations = await resourceData<{ name: string }[]>(stationLookup, "Fuel Station lookup");
	if (!stations[0]?.name) {
		const create = await page.request.post("/api/resource/Fuel Station", {
			data: {
				doctype: "Fuel Station",
				station_name: stationName,
				operational_location: QA_LOCATION,
				active: 1,
				approved: 1,
			},
			headers: { "X-Frappe-CSRF-Token": await csrfToken(page) },
		});
		await resourceData(create, "Fuel Station creation");
	}

	const assetName = QA_FIXTURES.asset;
	const assetData = {
		doctype: "Fleet Asset",
		asset_identifier: assetName,
		asset_type: "Vehicle",
		active: 1,
		fuel_type: QA_FIXTURES.fuelTypes[0],
		tank_capacity_litres: 60,
		target_km_per_litre: 10,
		assignments: [
			{
				doctype: "Asset Assignment",
				custodian: QA_FIXTURES.custodian,
				assigned_location: QA_LOCATION,
				effective_from: "2026-01-01",
			}
		],
	};
	const assetLookup = await page.request.get("/api/resource/Fleet Asset", {
		params: {
			fields: JSON.stringify(["name"]),
			filters: JSON.stringify({ name: assetName }),
			limit_page_length: "1",
		},
	});
	const assets = await resourceData<{ name: string }[]>(assetLookup, "Fleet Asset lookup");
	const assetResponse = assets[0]?.name
		? await page.request.put(`/api/resource/Fleet Asset/${encodeURIComponent(assetName)}`, {
				data: assetData,
				headers: { "X-Frappe-CSRF-Token": await csrfToken(page) },
		  })
		: await page.request.post("/api/resource/Fleet Asset", {
				data: assetData,
				headers: { "X-Frappe-CSRF-Token": await csrfToken(page) },
		  });
	await resourceData(assetResponse, "Fleet Asset configuration");
}

async function ensureQaUsers(page: Page) {
	for (const user of QA_USERS) {
		const lookup = await page.request.get("/api/resource/User", {
			params: {
				fields: JSON.stringify(["name"]),
				filters: JSON.stringify({ name: user.email }),
				limit_page_length: "1",
			},
		});
		const users = await resourceData<{ name: string }[]>(lookup, `User lookup for ${user.email}`);
		const roles = user.roles.map((role) => ({ doctype: "Has Role", role }));
		const data = {
			first_name: user.first_name,
			enabled: 1,
			user_type: "System User",
			send_welcome_email: 0,
			roles,
		};

		if (users[0]?.name) {
			const update = await page.request.put(
				`/api/resource/User/${encodeURIComponent(user.email)}`,
				{ data, headers: { "X-Frappe-CSRF-Token": await csrfToken(page) } },
			);
			await resourceData(update, `User update for ${user.email}`);
		} else {
			const create = await page.request.post("/api/resource/User", {
				data: { doctype: "User", email: user.email, ...data },
				headers: { "X-Frappe-CSRF-Token": await csrfToken(page) },
			});
			await resourceData(create, `User creation for ${user.email}`);
		}
	}
}

async function csrfToken(page: Page) {
	return page.evaluate(() => (window as any).frappe.csrf_token as string);
}
