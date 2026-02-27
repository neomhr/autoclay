# autoclay

Python SDK and CLI for Clay's People Search API. Stdlib only — zero external dependencies.

## Install

```bash
pip install .
```

Or editable for development:

```bash
pip install -e .
```

## Setup

```bash
clay setup
```

This prompts for your Clay email/password, verifies authentication, and stores credentials in `.env` in the current directory.

Alternatively, set environment variables directly:

```bash
export CLAY_EMAIL=you@example.com
export CLAY_PASSWORD=yourpassword
export CLAY_WORKSPACE_ID=123456
```

Verify auth:

```bash
clay auth login
```

The session cookie is obtained via email/password login and auto-refreshes every 23 hours. No browser or manual cookie copying needed.

## CLI Reference

### People Search

```bash
# Basic search (auto mode: preview if limit <= 50, else full)
clay people search --domains acme.com

# Multi-domain
clay people search --domains "acme.com,example.com,startup.io"

# From CSV file (first column = domains)
clay people search --domains-file companies.csv

# Full mode (creates Clay table, polls, extracts all records)
clay people search --domains acme.com --mode full --limit 2000

# Preview mode (max 50 results, no table creation)
clay people search --domains acme.com --mode preview

# Output formats
clay people search --domains acme.com --output csv          # default
clay people search --domains acme.com --output json
clay people search --domains acme.com --output sqlite
clay people search --domains acme.com -f results.csv

# Delete Clay table after extraction
clay people search --domains acme.com --mode full --cleanup

# Quiet mode
clay people search --domains acme.com -q
```

### Filter Flags

#### Seniority & Job Function

```bash
--seniority owner,partner,c-suite,vp,director,head,manager,senior,entry,assistant,intern,freelance,certified
--functions "Engineering,Sales,Human Resources and Recruiting"
```

#### Title Filters

```bash
--title-keywords "CEO,CTO,VP Engineering"
--exclude-titles "Intern,Assistant"
--title-mode smart|contain|exact     # default: smart
```

#### Location Filters

```bash
--countries "United States,Germany"
--countries-exclude "China"
--states "California,New York"
--states-exclude "Texas"
--cities "San Francisco,Berlin"
--cities-exclude "Houston"
--regions "EMEA,APAC"
--regions-exclude "LATAM"
```

#### Company Filters

```bash
--company-sizes "1,2-10,11-50,51-200,201-500,501-1000,1001-5000,5001-10000,10001+"
--industries "Software Development,Accounting"
--industries-exclude "Mining"
--company-keywords "SaaS,AI"
--company-keywords-exclude "nonprofit"
```

#### Profile & Keyword Filters

```bash
--headline-keywords "growth,scaling"
--about-keywords "entrepreneur"
--profile-keywords "python,machine learning"
--job-description-keywords "team lead"
--certification-keywords "PMP,AWS"
--school-names "MIT,Stanford"
```

#### LinkedIn Activity Filters

```bash
--min-connections 500
--max-connections 5000
--min-followers 1000
--max-followers 50000
--min-experience 3
--max-experience 10
```

#### Role Tenure

```bash
--min-role-months 6      # at least 6 months in current role
--max-role-months 24     # at most 24 months in current role
```

#### Other

```bash
--languages "English,German"
--names "John,Jane"
--include-past            # include people who previously worked at company
```

### Full Example

```bash
clay people search \
  --domains github.com \
  --seniority vp,director \
  --countries "United States" \
  --company-sizes "51-200,201-500" \
  --industries "Software Development" \
  --title-keywords "Engineering,Product" \
  --headline-keywords "growth" \
  --min-connections 500 \
  --mode full \
  --limit 500 \
  -f github_leaders.csv \
  --cleanup
```

### Keyword Expansion

```bash
# Expand seed terms with related keywords from Clay
clay keywords expand --terms "director,leader"
clay keywords expand --terms "machine learning,AI" --output json
```

### Table Management

```bash
clay table list                    # list all tables
clay table info <table_id>         # table details
clay table count <table_id>        # record count
clay table delete <table_id>       # delete table
```

### Authentication

```bash
clay auth login     # login and verify session
clay auth status    # show current auth status
```

## SDK Usage (Python)

```python
from autoclay import ClayClient, PeopleSearch, SearchFilters, KeywordExpander

# Initialize
client = ClayClient()
ps = PeopleSearch(client)

# Simple search
result = ps.search(["acme.com"])

# With filters
filters = SearchFilters(
    seniority_levels=["vp", "director"],
    job_functions=["Engineering", "Sales"],
    countries_include=["United States"],
    company_sizes=["51-200", "201-500"],
    job_title_keywords=["VP", "Director"],
    headline_keywords=["growth"],
    connection_count=500,
    current_role_min_months=6,
)
result = ps.search(
    ["github.com"],
    filters=filters,
    limit=500,
    mode="full",
    cleanup=True,
)

for person in result.people:
    print(f"{person.full_name} — {person.job_title} @ {person.company_domain}")

# Output writers
from autoclay.output import write_csv, write_sqlite, write_json

write_csv(result.people, "output.csv")
write_sqlite(result.people, "contacts.db")     # dedupes on linkedin_url
json_str = write_json(result.people)            # returns JSON string

# Keyword expansion
expander = KeywordExpander(client)
related = expander.get_related(["director", "leader"])
print(related)

# Table management
from autoclay import TableManager

tm = TableManager(client)
tables = tm.list_tables()
tm.delete_table("t_xxx")
```

## Architecture

```
autoclay/
├── __init__.py           # Public exports
├── __main__.py           # python -m autoclay entry point
├── auth.py               # Session management (login, cookie refresh, 23h auto-refresh)
├── client.py             # HTTP client (auth, retries, 401 re-login)
├── cli.py                # argparse CLI dispatcher
├── config.py             # Constants (API base, action IDs, timeouts)
├── enums.py              # Validated enum values (seniority, functions, sizes)
├── exceptions.py         # Error hierarchy
├── models.py             # Dataclasses (Person, SearchFilters, SearchResult, etc.)
├── output/               # Output writers (CSV, SQLite, JSON)
├── search/
│   ├── _base.py          # Abstract 6-step Sculptor flow
│   ├── keywords.py       # Related keywords expansion API
│   └── people.py         # People search (build_inputs, parse records)
└── tables/
    ├── manager.py         # Table CRUD + field mapping
    └── records.py         # Record fetching + parsing
```

### Search Flow

The SDK implements Clay's 6-step "Sculptor" flow:

1. **Create conversation** — `POST /v3/{wsId}/ai-generation/chat-conversation`
2. **Preview search** — `POST /v3/actions/run-enrichment` (max 50 results, returns taskId)
3. **Create table** — `POST /v3/sources/create-cpj-table` (uses conversationId + taskId)
4. **Poll completion** — `GET /v3/sources/{sourceId}/runs?limit=1`
5. **Fetch record IDs** — `GET /v3/tables/{tableId}/views/{viewId}/records/ids`
6. **Bulk fetch records** — `POST /v3/tables/{tableId}/bulk-fetch-records`

Preview mode runs only step 2. Full mode runs all 6 steps.

### Retry Logic

- 5xx errors: exponential backoff (1s/2s/4s), 3 attempts
- 401 errors: automatic session refresh + single retry
- Source polling: configurable timeout (default 120s)

## Filter Fields Reference

| SearchFilters field | API parameter | Type | CLI flag |
|---|---|---|---|
| seniority_levels | job_title_seniority_levels | string[] | --seniority |
| job_functions | job_functions | string[] | --functions |
| job_title_keywords | job_title_keywords | string[] | --title-keywords |
| job_title_exclude_keywords | job_title_exclude_keywords | string[] | --exclude-titles |
| job_title_mode | job_title_mode | string | --title-mode |
| countries_include | location_countries_include | string[] | --countries |
| countries_exclude | location_countries_exclude | string[] | --countries-exclude |
| states_include | location_states_include | string[] | --states |
| states_exclude | location_states_exclude | string[] | --states-exclude |
| cities_include | location_cities_include | string[] | --cities |
| cities_exclude | location_cities_exclude | string[] | --cities-exclude |
| regions_include | location_regions_include | string[] | --regions |
| regions_exclude | location_regions_exclude | string[] | --regions-exclude |
| company_sizes | company_sizes | string[] | --company-sizes |
| company_industries_include | company_industries_include | string[] | --industries |
| company_industries_exclude | company_industries_exclude | string[] | --industries-exclude |
| company_description_keywords | company_description_keywords | string[] | --company-keywords |
| company_description_keywords_exclude | company_description_keywords_exclude | string[] | --company-keywords-exclude |
| headline_keywords | headline_keywords | string[] | --headline-keywords |
| about_keywords | about_keywords | string[] | --about-keywords |
| profile_keywords | profile_keywords | string[] | --profile-keywords |
| job_description_keywords | job_description_keywords | string[] | --job-description-keywords |
| certification_keywords | certification_keywords | string[] | --certification-keywords |
| school_names | school_names | string[] | --school-names |
| connection_count | connection_count | int | --min-connections |
| max_connection_count | max_connection_count | int | --max-connections |
| follower_count | follower_count | int | --min-followers |
| max_follower_count | max_follower_count | int | --max-followers |
| experience_count | experience_count | int | --min-experience |
| max_experience_count | max_experience_count | int | --max-experience |
| current_role_min_months | current_role_min_months_since_start_date | int | --min-role-months |
| current_role_max_months | current_role_max_months_since_start_date | int | --max-role-months |
| languages | languages | string[] | --languages |
| names | names | string[] | --names |
| include_past_experiences | include_past_experiences | bool | --include-past |
| role_range_start_month | role_range_start_month | int | SDK only |
| role_range_end_month | role_range_end_month | int | SDK only |
| job_title_exact_match | job_title_exact_match | bool | SDK only |
| job_title_exact_keyword_match | job_title_exact_keyword_match | bool | SDK only |
| search_raw_location | search_raw_location | bool | SDK only |

## Enum Values

### Seniority Levels

`owner`, `partner`, `c-suite`, `vp`, `director`, `head`, `manager`, `senior`, `entry`, `assistant`, `intern`, `freelance`, `certified`

### Job Functions

`Administrative`, `Agriculture, Horticulture, and the Outdoors`, `Arts and Design`, `Business Development`, `Community and Social Services`, `Construction, Extraction, and Architecture`, `Customer Success and Support`, `Education`, `Engineering`, `Finance`, `Healthcare`, `Hospitality, Food, and Tourism`, `Human Resources and Recruiting`, `Information Technology (IT) and Computer Science`, `Legal, Compliance, and Public Safety`, `Maintenance, Repair, and Installation`, `Manufacturing and Production`, `Marketing and Public Relations`, `Military`, `Performing Arts`, `Personal Services`, `Sales`, `Science and Research`, `Social Analysis and Planning`, `Student`

### Company Sizes

`1`, `2-10`, `11-50`, `51-200`, `201-500`, `501-1000`, `1001-5000`, `5001-10000`, `10001+`

### Title Modes

`smart` (default — fuzzy match), `contain` (substring match), `exact` (exact string match)

## Limitations

- **Authentication:** Uses session cookies, not API keys. Sessions expire and require re-login.
- **Rate limits:** 25,000 people search lookups per account. Preview limited to 50 results.
- **No server-side exclusion:** De-duplication against previously fetched records must be handled locally (e.g., via SQLite output with dedup on LinkedIn URL).
- **Industries list:** Uses LinkedIn's industry taxonomy (~200+ values). Not enumerated in the SDK — pass exact LinkedIn industry name strings.
- **Countries list:** Standard world country names (~240). Not enumerated — pass full English country names.

## License

MIT
