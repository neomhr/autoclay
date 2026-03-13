# autoclay

CLI for Clay's People Search API. Zero external dependencies.

## Quick Install

```bash
curl -sSf https://raw.githubusercontent.com/neomhr/autoclay/main/install.sh | bash
clay setup
```

This clones the repo to `~/.autoclay/src/`, installs the `clay` command, and links a Claude Code skill so Claude can use the CLI from any directory.

### Manual Install

```bash
git clone https://github.com/neomhr/autoclay.git
cd autoclay
pip install -e .
clay setup
```

### Update

```bash
clay update
```

## Setup

```bash
clay setup
```

This prompts for your Clay email/password, verifies authentication, and stores credentials in `~/.autoclay/credentials.json` (permissions `0600`). The session cookie is cached in `~/.autoclay/session.json` and shared across parallel processes (23h TTL, auto-refreshes).

Alternatively, set environment variables (these override the credentials file):

```bash
export CLAY_EMAIL=you@example.com
export CLAY_PASSWORD=yourpassword
export CLAY_WORKSPACE_ID=123456
```

Verify auth:

```bash
clay auth login
```

## CLI Reference

### People Search

```bash
# Basic search (auto mode: preview if limit <= 50, else full)
clay people search --domains acme.com

# No domains — search across all companies matching filters
clay people search --title-keywords "CEO" --countries "United States"

# Multi-domain
clay people search --domains "acme.com,example.com,startup.io"

# From CSV file (first column = domains)
clay people search --domains-file companies.csv

# Full mode (creates Clay table, polls, extracts all records)
clay people search --domains acme.com --mode full

# Preview mode (max 50 results, no table creation)
clay people search --domains acme.com --mode preview

# Limit total results and per-company results
clay people search --domains "acme.com,example.com" --limit 500 --limit-per-company 100

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

#### Role Date Range

```bash
--role-range-start-month 3    # role start date filter (months ago)
--role-range-end-month 12     # role end date filter (months ago)
```

#### Limits

```bash
--limit 500              # total max results across all companies (default: plan cap ~25k)
--limit-per-company 50   # max results per company (default: no cap)
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
  --limit-per-company 200 \
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

## How it works

- **Preview mode** — fast, no credits, max 50 results. Good for testing filters.
- **Full mode** — creates a Clay table, polls for completion, extracts all records. Use for production searches.
- **Auto mode** (default) — preview if limit <= 50, full otherwise.

Credentials are stored in `~/.autoclay/credentials.json`. The session cookie is cached in `~/.autoclay/session.json` and auto-refreshes every 23 hours. Parallel processes share the cached session.

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
- **Industries list:** Uses LinkedIn's industry taxonomy (~200+ values). Pass exact LinkedIn industry name strings.
- **Countries list:** Standard world country names (~240). Pass full English country names.

## License

MIT
