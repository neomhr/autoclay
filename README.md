# Clay CPL CLI

Terminal CLI for Clay's Companies, People, and Jobs source workflows. It is built for agent-friendly list creation, table inspection, and exports from Clay's internal CPL source APIs.

This is a CLI-first project. The Python package exists as the implementation layer behind the `clay-cpl` command.

## Quick Install

```bash
curl -sSf https://raw.githubusercontent.com/neomhr/autoclay/main/install.sh | bash
clay-cpl setup
```

Manual install:

```bash
git clone https://github.com/neomhr/autoclay.git clay-cpl
cd clay-cpl
pip install -e .
clay-cpl setup
```

Update:

```bash
clay-cpl update
```

## Setup

```bash
clay-cpl setup
clay-cpl auth status
```

You can also set credentials directly:

```bash
export CLAY_EMAIL=you@example.com
export CLAY_PASSWORD=yourpassword
export CLAY_WORKSPACE_ID=your_workspace_id
```

`CLAY_WORKSPACE_ID` can also come from `~/.clay-cpl/credentials.json`. Session cookies are cached in `~/.clay-cpl/session.json`.

## Commands

```bash
clay-cpl companies search --countries "United States" --industries "Software Development" --limit 25 --output json
clay-cpl people search --domains openai.com --title-keywords "Engineer" --limit 25 --output csv -f people.csv
clay-cpl jobs search --domains openai.com --title-keywords "Engineer" --limit 25 --output sqlite -f jobs.db
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

## People Search

```bash
clay-cpl people search \
  --domains "openai.com,anthropic.com" \
  --title-keywords "Engineer,Developer Advocate" \
  --exclude-titles "Intern" \
  --countries "United States" \
  --company-sizes "51-200,201-500,501-1000" \
  --mode full \
  --limit 100 \
  --cleanup
```

Current Clay schema flags are exposed by exact input name, converted to kebab case, for example:

```bash
--company-identifier openai.com
--job-title-seniority-levels-v2 executive,manager
--job-title-include-past-experiences true
--job-description-include-past-experiences true
--limit-per-company 3
```

## Company Search

Companies expose the current Clay source inputs as typed flags, including country, type, size, funding, revenue, headcount, industry, description, location, AI-derived industry and business filters, technographics, domain flags, and limit.

Examples:

```bash
clay-cpl companies search --countries Germany --company-sizes "51-200,201-500" --industries "Software Development"
clay-cpl companies search --semantic-description "B2B SaaS companies selling to HR teams" --limit 50 --output json
```

## Job Search

Jobs expose the current Clay source inputs:

```bash
clay-cpl jobs search \
  --domains openai.com \
  --title-keywords Engineer \
  --locations "San Francisco" \
  --employment-type "Full-time" \
  --max-num-days-since-posted 30
```

## Company Table Joins

People and jobs can start from an existing company table by extracting domains:

```bash
clay-cpl jobs search --from-company-table t_xxx --company-domain-field Domain --title-keywords Engineer
clay-cpl people search --from-company-table t_xxx --company-domain-field Domain --title-keywords CEO
```

Outputs include `source_company_table_id` and `source_company_domain` when this join path is used.

## Table Management

```bash
clay-cpl table list
clay-cpl table info <table_id>
clay-cpl table count <table_id>
clay-cpl table delete <table_id>
```
