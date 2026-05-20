# Clay CPL CLI CPJ Parity Plan

## Summary

Build Clay CPL CLI around Clay's "Companies, People, Jobs" source primitives, with neutral agent-friendly commands for company, people, and job search. Support `clay-cpl companies search`, `clay-cpl people search`, and `clay-cpl jobs search`, plus both typed CLI filters and exact raw Clay input payloads.

## Key Changes

- Refactor the current people-only search stack into a generic CPJ source engine.
- Add neutral entity commands:
  - `clay-cpl companies search`
  - `clay-cpl people search`
  - `clay-cpl jobs search`
- Shared flags: `--mode`, `--limit`, `--output csv|json|sqlite`, `--output-file/-f`, `--cleanup`, `--quiet`, `--inputs-json`, `--inputs-file`.
- Raw inputs replace typed filter construction. Output, mode, cleanup, and client-side limit behavior remain CLI-controlled.
- Full-mode runs persist resumable workbook, table, view, and source IDs under `~/.clay-cpl/runs/`. `--wait-timeout` returns pending instead of failing when Clay is still queued/running, and `--detach` creates the table without waiting.
- Completed full-mode tables can be exported later:
  - `clay-cpl table export <table_id> --entity companies --output csv`
  - `clay-cpl table export <table_id> --entity people --output sqlite`
  - `clay-cpl table export <table_id> --entity jobs --output json`
- Add typed filter parity for the current Clay UI action schemas from `actions?workspaceId=<workspace_id>`:
  - Companies: 37 source inputs.
  - People: 48 source inputs, including `job_title_include_past_experiences`, `job_description_include_past_experiences`, and v2 seniority controls.
  - Jobs: 12 source inputs.
- Replace person-shaped output with entity-shaped output:
  - Companies JSON: `{ "count": n, "companies": [...] }`
  - People JSON: `{ "count": n, "people": [...] }`
  - Jobs JSON: `{ "count": n, "jobs": [...] }`
  - SQLite tables: `clay_companies`, `clay_people`, `clay_jobs`.
- Add join primitives:
  - `clay-cpl jobs search --from-company-table <table_id> --company-domain-field <field name>`
  - `clay-cpl people search --from-company-table <table_id> --company-domain-field <field name>`

## Validation Notes

Implementation should validate live behavior with an explicit `CLAY_WORKSPACE_ID`, preserve public-safe tests that skip live Clay calls when credentials are unavailable, and avoid committing credentials, cookies, local session values, or personal workspace IDs into tracked code.
