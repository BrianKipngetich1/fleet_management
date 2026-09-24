import { test as setup } from "@playwright/test";
import { authenticate } from "../auth";
import { USERS } from "../fixtures";
import { ensureQaLocationPermissions } from "../setup";

setup("bootstrap QA location permissions", async ({ page }) => {
	await ensureQaLocationPermissions(page);
});

for (const [name, user] of Object.entries(USERS)) {
	setup(`authenticate ${name}`, async ({ page }) => {
		await authenticate(page, user.email);
		await page.context().storageState({ path: user.state });
	});
}
