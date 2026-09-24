// The only file in e2e/ that carries project facts. Fill it once; every spec in
// e2e/tests/ is driven from it. See CLAUDE.md "UI verification workflow".

export const USERS = {
	primary: {
		email: "desk.qa.requester.20260919@example.com",
		role: "Fleet User",
		state: "e2e/.auth/primary.json",
	},
	restricted: {
		email: "desk.qa.restricted.20260919@example.com",
		role: "Fleet Approver",
		state: "e2e/.auth/restricted.json",
	},
	approver: {
		email: "desk.qa.approver.20260919@example.com",
		role: "Fleet Approver",
		state: "e2e/.auth/approver.json",
	},
	admin: { email: "Administrator", role: "Administrator", state: "e2e/.auth/admin.json" },
} as const;

export const QA_FIXTURES = {
	locations: ["Gongoni", "Marereni", "Mombasa", "Nairobi"],
	fuelTypes: ["Diesel", "Petrol"],
	station: "Synthetic Nairobi Station",
	asset: "Synthetic Nairobi Vehicle",
	requester: "Synthetic Requester",
	driver: "Synthetic Driver",
	custodian: "Synthetic Custodian",
	representative: "Synthetic Company Representative",
} as const;

// Every site uses Frappe's dd/mm/yyyy date format (CLAUDE.md "Dates"). Checks and typed dates
// assume it; never type an ISO date into a Desk field, convert with userDate() in desk.ts.
export const DATE_FORMAT = "dd/mm/yyyy";

// DocTypes whose list view and new form must render without a page error.
export const DOCTYPES: string[] = ["Fuel Order", "Fueling Transaction"];

// Of the above, those written only by controllers — they have no meaningful new form.
export const NO_NEW_FORM: string[] = [];

// Row-level scoping. SCOPE_DOCTYPE is the DocType whose list is restricted; SCOPE_FIELD
// is the link field that scopes other records by it; SCOPED_VALUES is the exact set the
// primary user may see. Leave SCOPE_DOCTYPE empty when the app has no row-level scoping.
export const SCOPE_DOCTYPE = "Fleet Location";
export const SCOPE_FIELD = "operational_location";
export const SCOPE_HOST_DOCTYPE = "Fuel Order";
export const SCOPED_VALUES: string[] = ["Nairobi"];

// The shared separator or prefix that makes the link search return the full permitted
// set rather than a guessed subset.
export const SCOPE_QUERY = "Nai";

// A minimal valid draft the restricted user must be denied from creating. Its doctype
// must be one the restricted user may read, so the deny is proved against a live session.
export const DENY_PROBE: Record<string, unknown> = {
	doctype: "Fuel Order",
};
