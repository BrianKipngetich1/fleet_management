import { test as setup } from "@playwright/test";
import { authenticate } from "../auth";
import { USERS } from "../fixtures";
import { assertSampleData } from "../setup";

setup("the test site carries the sample data", async ({ page }) => {
	await assertSampleData(page);
});

for (const [name, user] of Object.entries(USERS)) {
	setup(`authenticate ${name}`, async ({ page }) => {
		await authenticate(page, user.email);
		await page.context().storageState({ path: user.state });
	});
}
