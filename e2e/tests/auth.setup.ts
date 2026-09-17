import { test as setup } from "@playwright/test";
import { mintSid } from "../sid";
import { USERS } from "../fixtures";

for (const [name, user] of Object.entries(USERS)) {
	setup(`authenticate ${name}`, async ({ page }) => {
		await page.goto(`/app?sid=${mintSid(user.email)}`);
		await page.waitForFunction(() => (window as any).frappe?.session?.user);
		await page.context().storageState({ path: user.state });
	});
}
