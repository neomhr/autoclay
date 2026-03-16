---
name: autoclay
description: Use this skill when the user wants to search for people at companies, build lead lists, or do people search via Clay. Triggers on mentions of Clay CLI, people search, lead enrichment, headcount analysis, or finding contacts at companies.
user-invocable: true
---

# AutoClay CLI Skill

AutoClay is a local CLI wrapper around Clay's People Search API. Use it to find people at companies by title/function/seniority, export to CSV/JSON/SQLite, and build lead lists.

**Editable install:** source changes are immediately live — no reinstall needed.
**Auth:** credentials stored in `~/.autoclay/credentials.json`, session cached in `~/.autoclay/session.json` (23h TTL, shared across parallel processes).

---

## When to use this skill

Use `clay` when:
- The user explicitly says "use Clay CLI", "use AutoClay", or "use the clay command"
- Searching for people at a known list of domains (headcount, contact discovery, lead enrichment)
- Running batch domain searches in parallel sub-agents
- Building sales team headcount analysis

Do NOT use this skill for:
- Enrichment tasks that don't start from a domain list (use other GTM tools instead)
- Email validation
- Tasks where the user hasn't specified Clay as the tool

---

## Core command: `clay people search`

### Minimal form
```bash
clay people search --domains "domain1.com,domain2.com" --title-keywords "AE,SDR,Account Executive" --output csv -f /tmp/results.csv
```

### No domains (search all)
```bash
clay people search --title-keywords "CEO" --countries "United States" --company-sizes "11-50" --mode full
```
Omitting `--domains` searches across all companies matching the filters.

### Full flag reference

| Flag | Type | Notes |
|------|------|-------|
| `--domains` | string | Comma-separated domains. Optional — omit to search all |
| `--domains-file` | path | CSV file, reads first column |
| `--title-keywords` | string | Comma-separated keywords matched against titles |
| `--exclude-titles` | string | Comma-separated exclusion keywords |
| `--title-mode` | smart/contain/exact | Default: smart. Use `contain` for broad recall |
| `--functions` | string | Job function filter — see valid values below. Often unreliable; prefer `--title-keywords` |
| `--seniority` | string | See valid values below |
| `--countries` | string | e.g. `"United States,Germany"` |
| `--countries-exclude` | string | Countries to exclude |
| `--states` | string | States to include |
| `--states-exclude` | string | States to exclude |
| `--cities` | string | Cities to include |
| `--cities-exclude` | string | Cities to exclude |
| `--regions` | string | Regions to include (e.g. EMEA, APAC) |
| `--regions-exclude` | string | Regions to exclude |
| `--company-sizes` | string | e.g. `"51-200,201-500,501-1000"` |
| `--industries` | string | Comma-separated Clay industry names |
| `--industries-exclude` | string | Industries to exclude |
| `--company-keywords` | string | Company description keywords |
| `--company-keywords-exclude` | string | Company description exclusions |
| `--headline-keywords` | string | LinkedIn headline keywords |
| `--about-keywords` | string | LinkedIn about section keywords |
| `--profile-keywords` | string | General profile keywords |
| `--job-description-keywords` | string | Job description keywords |
| `--certification-keywords` | string | Certification keywords |
| `--school-names` | string | School/university names |
| `--min-connections` | int | Minimum LinkedIn connections |
| `--max-connections` | int | Maximum LinkedIn connections |
| `--min-followers` | int | Minimum LinkedIn followers |
| `--max-followers` | int | Maximum LinkedIn followers |
| `--min-experience` | int | Minimum experience entries |
| `--max-experience` | int | Maximum experience entries |
| `--min-role-months` | int | Min months in current role |
| `--max-role-months` | int | Max months in current role |
| `--role-range-start-month` | int | Role start date filter (months ago) |
| `--role-range-end-month` | int | Role end date filter (months ago) |
| `--languages` | string | Comma-separated languages |
| `--names` | string | Person names to filter |
| `--include-past` | flag | Include past job experiences |
| `--mode` | preview/full/auto | Default: auto. **Use `full` for all production searches.** Preview is <=50 results, only useful for quick filter validation |
| `--output` | csv/sqlite/json | Output format (default: csv) |
| `--output-file` / `-f` | path | Output file path |
| `--limit` | int | Total max results across all companies. Default: plan cap (~25k). Only set when deliberately sampling |
| `--limit-per-company` | int | Max results per company. Default: no per-company cap |
| `--batch-size` | int | Domains per Clay table in full mode (default: 1). Set to 25-50 for large runs to cut API calls. |
| `--cleanup` | flag | Delete Clay table after extraction |
| `--quiet` / `-q` | flag | Suppress progress output |

### Valid seniority values
`owner`, `partner`, `c-suite`, `vp`, `director`, `head`, `manager`, `senior`, `entry`, `assistant`, `intern`, `freelance`, `certified`

### Valid --functions values (exact strings required)
`Sales`, `Business Development`, `Marketing and Public Relations`, `Customer Success and Support`,
`Engineering`, `Finance`, `Human Resources and Recruiting`, `Information Technology (IT) and Computer Science`,
`Administrative`, and others. See `autoclay/enums.py` for the full list.

### Valid company sizes
`1`, `2-10`, `11-50`, `51-200`, `201-500`, `501-1000`, `1001-5000`, `5001-10000`, `10001+`

---

## Filter validation (mandatory before any significant run)

Before running a full search at scale, validate that your filters actually work in practice.

### The core problem: provider taxonomy is unreliable

Providers like Clay expose department/function filters that look precise but are mapped inconsistently. The **raw data** (title, headline, company name) is reliable. The **inferred taxonomy** (department, function, seniority bucket) is often wrong or missing.

**Example:** `--functions Sales` on Clay returns 0 results on many companies even when dozens of AEs and SDRs exist.

### The correct approach: broad search -> title filter

1. **Start broad** — use minimal filters, no function/department tags
2. **Pull on raw text** — filter by `--title-keywords` or `--headline-keywords`
3. **Post-process** — do your own classification on the returned data
4. **Validate on a 1-3 domain pilot** — before running at scale, spot-check results

### When to use preview vs full mode

| Scenario | Mode |
|----------|------|
| Validating filter keywords on 1 company, expecting <50 results | `--mode preview` |
| Any headcount or qualification work | `--mode full` |
| Any multi-domain batch | `--mode full` |
| Anything going into a database or decision | `--mode full` |

### What filters are reliable vs. fragile

| Filter | Reliability | Notes |
|--------|-------------|-------|
| `--title-keywords` | **High** | Matches raw title text. Use as primary filter |
| `--exclude-titles` | **High** | Matches raw title text. Reliable for cutting false positives |
| `--seniority` | **Medium** | Inferred from title. Useful as secondary cut |
| `--functions` | **Low** | Often unmapped. Avoid as primary filter |
| `--company-sizes` | **Medium** | Data freshness varies |
| `--industries` | **Low** | Same unmapped problem |
| `--headline-keywords` | **High** | Raw LinkedIn headline text |
| `--countries` / `--cities` | **High** | Geo is well-mapped |

---

## Other commands

### Auth
```bash
clay auth status     # check session
clay auth login      # force fresh login
clay setup           # interactive credential setup
```

### Table management
```bash
clay table list          # list tables in workspace
clay table info <id>     # get table details
clay table count <id>    # get record count
clay table delete <id>   # delete table
```

### Keyword expansion
```bash
clay keywords expand --terms "AE,SDR,Account Executive" --output json
```

### Update
```bash
clay update              # pull latest changes from git
```

---

## Output handling

### JSON (recommended for programmatic use)
```bash
clay people search --domains "..." --output json -f /tmp/results.json
```
Each record has: `first_name`, `last_name`, `full_name`, `job_title`, `location`, `company_domain`, `linkedin_url`.

### CSV
```bash
clay people search --domains "..." --output csv -f /tmp/results.csv
```

### SQLite (deduplicates on LinkedIn URL)
```bash
clay people search --domains "..." --output sqlite -f /tmp/results.db
```

---

## Known issues

1. **`--functions Sales` returns 0 results** — Use `--title-keywords` instead.
2. **Always use `--cleanup`** — each full search creates a table in the Clay workspace. Use `--cleanup` to auto-delete after extraction, or clean up manually via `clay table list` + `clay table delete`.
3. **Preview mode caps at 50 results total** — shared across all domains in a batch. For headcount accuracy, use `--mode full`.
4. **`--mode auto` is unreliable for headcount** — it only upgrades to full if preview hits exactly 50. Use `--mode full` explicitly.
