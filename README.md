# Clay Python SDK

Composable Python SDK and CLI for Clay's internal Companies, People, Jobs source APIs. Stdlib only.

## Quick Install

```bash
curl -sSf https://raw.githubusercontent.com/neomhr/autoclay/main/install.sh | bash
clay setup
```

Manual install:

```bash
git clone https://github.com/neomhr/autoclay.git
cd autoclay
pip install -e .
clay setup
```

Update:

```bash
clay update
```

## Setup

```bash
clay setup
clay auth status
```

You can also set credentials directly:

```bash
export CLAY_EMAIL=you@example.com
export CLAY_PASSWORD=yourpassword
export CLAY_WORKSPACE_ID=your_workspace_id
```

`CLAY_WORKSPACE_ID` can also come from `~/.autoclay/credentials.json`. Session cookies are cached in `~/.autoclay/session.json`.

## Commands

```bash
clay companies search --countries "United States" --industries "Software Development" --limit 25 --output json
clay people search --domains openai.com --title-keywords "Engineer" --limit 25 --output csv -f people.csv
clay jobs search --domains openai.com --title-keywords "Engineer" --limit 25 --output sqlite -f jobs.db
```

All three search commands support:

```bash
--mode preview|full|auto
--limit N
--output csv|json|sqlite
--output-file PATH
--cleanup
--quiet
--inputs-json '{"exact":"Clay inputs"}'
--inputs-file inputs.json
```

`--inputs-json` and `--inputs-file` pass exact raw Clay source inputs. When used, typed filters are ignored and only mode, output, cleanup, and client-side limiting remain CLI-controlled.

## Entity Outputs

JSON output is entity-shaped:

```json
{ "count": 1, "companies": [] }
{ "count": 1, "people": [] }
{ "count": 1, "jobs": [] }
```

SQLite output writes to `clay_companies`, `clay_people`, and `clay_jobs`.

## People Search Compatibility

Existing people-search flags still work:

```bash
clay people search \
  --domains "openai.com,anthropic.com" \
  --title-keywords "Engineer,Developer Advocate" \
  --exclude-titles "Intern" \
  --countries "United States" \
  --company-sizes "51-200,201-500,501-1000" \
  --mode full \
  --limit 100 \
  --cleanup
```

Current Clay schema flags are also exposed by exact input name, converted to kebab case, for example:

```bash
--company-identifier openai.com
--job-title-seniority-levels-v2 executive,manager
--job-title-include-past-experiences true
--job-description-include-past-experiences true
--limit-per-company 3
```

## Company Search

Companies expose all current Clay source inputs as typed flags, including country, type, size, funding, revenue, headcount, industry, description, location, AI-derived industry/business filters, technographics, domain flags, and limit.

Examples:

```bash
clay companies search --countries Germany --company-sizes "51-200,201-500" --industries "Software Development"
clay companies search --semantic-description "B2B SaaS companies selling to HR teams" --limit 50 --output json
```

## Job Search

Jobs expose all current Clay source inputs:

```bash
clay jobs search \
  --domains openai.com \
  --title-keywords Engineer \
  --locations "San Francisco" \
  --employment-type "Full-time" \
  --max-num-days-since-posted 30
```

## Company Table Joins

People and jobs can start from an existing company table by extracting domains:

```bash
clay jobs search --from-company-table t_xxx --company-domain-field Domain --title-keywords Engineer
clay people search --from-company-table t_xxx --company-domain-field Domain --title-keywords CEO
```

Outputs include `source_company_table_id` and `source_company_domain` when this join path is used.

## Table Management

```bash
clay table list
clay table info <table_id>
clay table count <table_id>
clay table delete <table_id>
```

## SDK Usage

```python
from autoclay import ClayClient, CompanySearch, PeopleSearch, JobSearch, SearchFilters

client = ClayClient()

companies = CompanySearch(client).search(
    filters=SearchFilters(country_names=["United States"], industries=["Software Development"]),
    limit=10,
    mode="preview",
)

people = PeopleSearch(client).search(
    ["openai.com"],
    filters=SearchFilters(job_title_keywords=["Engineer"]),
    limit=10,
    mode="preview",
)

jobs = JobSearch(client).search(
    ["openai.com"],
    filters=SearchFilters(job_title_keywords=["Engineer"]),
    limit=10,
    mode="preview",
)
```
