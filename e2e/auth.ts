import { Page } from "@playwright/test";
import { mintSid } from "./sid";
import { assertTestBaseURL } from "./target";

export const BASE_URL = assertTestBaseURL(process.env.BASE_URL);

function safeUrl(value: string) {
	return value.replace(/([?&]sid=)[A-Za-z0-9]+/g, "$1[redacted]");
}

async function detectedUser(page: Page): Promise<string | null> {
	return page.evaluate(() => window.frappe?.session?.user || null).catch(() => null);
}

export async function authenticate(page: Page, expectedUser: string, path = "/app/fuel-order") {
	const sid = mintSid(expectedUser);
	await page.context().addCookies([
		{
			name: "sid",
			value: sid,
			url: `${BASE_URL}/`,
		},
	]);

	try {
		await page.goto(path, { waitUntil: "domcontentloaded" });
		await page.waitForFunction(
			(user) => window.frappe?.session?.user === user,
			expectedUser,
		);
	} catch (error) {
		throw new Error(
			`Authentication failed for ${expectedUser}; final URL ${safeUrl(page.url())}; ` +
			`detected session user ${await detectedUser(page) || "<none>"}`,
			{ cause: error },
		);
	}

	const actualUser = await detectedUser(page);
	if (actualUser !== expectedUser || /\/login(?:\/|\?|$)/.test(page.url())) {
		throw new Error(
			`Authentication failed for ${expectedUser}; final URL ${safeUrl(page.url())}; ` +
			`detected session user ${actualUser || "<none>"}`,
		);
	}
}

export async function setSessionCookie(page: Page, value: string) {
	await page.context().addCookies([
		{
			name: "sid",
			value,
			url: `${BASE_URL}/`,
		},
	]);
}
