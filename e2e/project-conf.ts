import { readFileSync } from "node:fs";
import { resolve } from "node:path";

export function projectConf(key: string): string {
	const path = resolve(__dirname, "../.kaysalt/project.conf");
	let contents: string;
	try {
		contents = readFileSync(path, "utf8");
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === "ENOENT") {
			throw new Error(`set ${key} in .kaysalt/project.conf`);
		}
		throw error;
	}

	const value = contents
		.split(/\r?\n/)
		.find((line) => line.startsWith(`${key}=`))
		?.slice(key.length + 1)
		.trim();
	if (!value) {
		throw new Error(`set ${key} in .kaysalt/project.conf`);
	}
	return value;
}
