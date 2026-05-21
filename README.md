# Clay CPJ CLI

Terminal CLI for Clay's Companies, People, and Jobs source workflows. It is built for agent-friendly list creation, table inspection, and exports from Clay's internal CPJ source APIs.

This is a CLI-first project. The Python package exists as the implementation layer behind the `clay-cpj` command.

## Quick Install

```bash
curl -sSf https://raw.githubusercontent.com/neomhr/clay-cpj-cli/main/install.sh | bash
clay-cpj setup
```

Manual install:

```bash
git clone https://github.com/neomhr/clay-cpj-cli.git clay-cpj
cd clay-cpj
pip install -e .
clay-cpj setup
```

Update:

```bash
clay-cpj update
```

## Setup

```bash
clay-cpj setup
clay-cpj auth status
```

You can also set credentials directly:

```bash
export CLAY_EMAIL=you@example.com
export CLAY_PASSWORD=yourpassword
export CLAY_WORKSPACE_ID=your_workspace_id
```

`CLAY_WORKSPACE_ID` can also come from `~/.clay-cpj/credentials.json`. Session cookies are cached in `~/.clay-cpj/session.json`.

## Commands

```bash
clay-cpj companies search --countries "United States" --industries "Software Development" --limit 25 --output json
clay-cpj people search --domains openai.com --title-keywords "Engineer" --limit 25 --output csv -f people.csv
clay-cpj jobs search --domains openai.com --title-keywords "Engineer" --limit 25 --output sqlite -f jobs.db
```

All three search commands support:

```bash
--mode preview|full|auto
--limit N
--output csv|json|sqlite
--output-file PATH
--cleanup
--wait-timeout SECONDS
--detach
--quiet
--inputs-json '{"exact":"Clay inputs"}'
--inputs-file inputs.json
```

`--inputs-json` and `--inputs-file` pass exact raw Clay source inputs. When used, typed filters are ignored and only mode, output, cleanup, and client-side limiting remain CLI-controlled.

Full-mode searches create durable Clay workbooks and tables before local polling starts. If `--wait-timeout` is reached, the CLI exits successfully with the remote run marked pending and writes a non-secret run manifest to `~/.clay-cpj/runs/`. Use `--detach` to create the Clay table and exit immediately without waiting.

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
clay-cpj people search \
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
clay-cpj companies search --countries Germany --company-sizes "51-200,201-500" --industries "Software Development"
clay-cpj companies search --semantic-description "B2B SaaS companies selling to HR teams" --limit 50 --output json
```

## Job Search

Jobs expose the current Clay source inputs:

```bash
clay-cpj jobs search \
  --domains openai.com \
  --title-keywords Engineer \
  --locations "San Francisco" \
  --employment-type "Full-time" \
  --max-num-days-since-posted 30
```

## Company Table Joins

People and jobs can start from an existing company table by extracting domains:

```bash
clay-cpj jobs search --from-company-table t_xxx --company-domain-field Domain --title-keywords Engineer
clay-cpj people search --from-company-table t_xxx --company-domain-field Domain --title-keywords CEO
```

Outputs include `source_company_table_id` and `source_company_domain` when this join path is used.

## Table Management

```bash
clay-cpj table list
clay-cpj table info <table_id>
clay-cpj table count <table_id>
clay-cpj table export <table_id> --entity companies --output csv -f companies.csv
clay-cpj table delete <table_id>
```

Use `table export` after a detached or timed-out full-mode run completes in Clay:

```bash
clay-cpj table export <table_id> --entity jobs --output sqlite -f jobs.db
clay-cpj table export <table_id> --entity people --output json -f people.json
```
