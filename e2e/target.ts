export const TEST_SITE = "fleet_management-test.localhost";
export const TEST_BASE_URL = "http://fleet_management-test.localhost:8000";

export function assertTestBaseURL(value = TEST_BASE_URL): string {
	const url = new URL(value);
	if (
		url.protocol !== "http:" ||
		url.hostname !== "fleet_management-test.localhost" ||
		url.port !== "8000" ||
		url.pathname !== "/" ||
		url.search ||
		url.hash
	) {
		throw new Error(
			`UI automation is fail-closed to ${TEST_BASE_URL}; received ${value}`
		);
	}
	return value.replace(/\/$/, "");
}

export function assertTestSite(value = TEST_SITE): string {
	if (value !== TEST_SITE) {
		throw new Error(`UI automation is fail-closed to ${TEST_SITE}; received ${value}`);
	}
	return value;
}
