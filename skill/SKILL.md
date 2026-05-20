---
name: clay-cpl
description: Use this skill when the user wants to search Clay companies, people, or jobs via Clay CPL CLI, build lead/account/job lists, run Clay source searches, export results, or inspect Clay tables.
user-invocable: true
---

# Clay CPL CLI Skill

Clay CPL CLI is a local CLI wrapper around Clay's Companies, People, Jobs source APIs.

It supports:

```bash
clay-cpl companies search ...
clay-cpl people search ...
clay-cpl jobs search ...
```

Credentials and sessions are stored locally in `~/.clay-cpl/credentials.json` and `~/.clay-cpl/session.json`. Set `CLAY_WORKSPACE_ID` explicitly for workspace-specific work.

## Search Commands

### Companies

```bash
clay-cpl companies search \
  --countries "United States" \
  --industries "Software Development" \
  --limit 25 \
  --output json
```

### People

```bash
clay-cpl people search \
  --domains "openai.com,anthropic.com" \
  --title-keywords "Engineer,Developer Advocate" \
  --mode full \
  --cleanup \
  --output csv \
  -f /tmp/people.csv
```

### Jobs

```bash
clay-cpl jobs search \
  --domains openai.com \
  --title-keywords Engineer \
  --max-num-days-since-posted 30 \
  --output json
```

## Shared Flags

All entity searches support:

| Flag | Notes |
|------|-------|
| `--mode preview/full/auto` | Preview is fast and capped; full creates a Clay table |
| `--limit N` | Client/source result limit |
| `--output csv/json/sqlite` | Entity-shaped outputs |
| `--output-file`, `-f` | Output path |
| `--cleanup` | Delete generated Clay table/workbook after extraction |
| `--quiet`, `-q` | Suppress progress |
| `--inputs-json` | Exact raw Clay source inputs |
| `--inputs-file` | JSON file with exact raw Clay source inputs |

Raw inputs replace typed filter construction. Only mode, output, cleanup, and client-side limit remain CLI-controlled.

## Company Table Joins

People and jobs can start from an existing Clay company table by extracting domains:

```bash
clay-cpl people search --from-company-table t_xxx --company-domain-field Domain --title-keywords CEO
clay-cpl jobs search --from-company-table t_xxx --company-domain-field Domain --title-keywords Engineer
```

Outputs include `source_company_table_id` and `source_company_domain` when this join path is used.

## Table Commands

```bash
clay-cpl table list
clay-cpl table info <table_id>
clay-cpl table count <table_id>
clay-cpl table delete <table_id>
```

## Rules

- Use `--mode full --cleanup` for production searches that must be complete.
- Use preview for filter validation and small smoke tests.
- Use `--inputs-json` or `--inputs-file` when exact Clay UI payload parity matters.
- Do not commit credentials, cookies, session files, workspace-specific artifacts, or exported Clay data.
