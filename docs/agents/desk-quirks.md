# Desk quirks that cost time when forgotten

Read when driving Desk from agent-browser or Playwright.

- A currency or data field needs a `Tab` blur before Frappe commits the typed value. Reading
  `cur_frm.doc` straight back after typing returns the stale value.
- A link field needs its autocomplete option **clicked**. Typing the exact value and blurring
  leaves the model field undefined even though the input shows the text.
- Frappe renders autocomplete entries as `div[role="option"]`, never `li`. Scanning for `li`
  finds nothing and reads as "no options returned".
- `Cancel` on a submitted document is a `.page-actions` button, not a menu dropdown item.
