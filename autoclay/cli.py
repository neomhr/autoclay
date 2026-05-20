"""Clay SDK CLI - argparse dispatcher."""

import argparse
import csv
import getpass
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from .auth import SessionManager
from .client import ClayClient
from .config import AUTOCLAY_DIR, CREDENTIALS_FILE, save_credentials
from .exceptions import ClayAuthError
from .models import SearchFilters
from .output import write_csv, write_json, write_sqlite
from .search import CompanySearch, JobSearch, KeywordExpander, PeopleSearch
from .tables import RecordFetcher, TableManager


SEARCH_CLASSES = {
    "companies": CompanySearch,
    "people": PeopleSearch,
    "jobs": JobSearch,
}

FIELD_TYPES = {
    "companies": {
        "country_names": "list",
        "country_names_exclude": "list",
        "types": "list",
        "sizes": "list",
        "funding_amounts": "list",
        "annual_revenues": "list",
        "minimum_member_count": "int",
        "maximum_member_count": "int",
        "industries": "list",
        "industries_exclude": "list",
        "description_keywords": "list",
        "description_keywords_exclude": "list",
        "locations": "list",
        "locations_exclude": "list",
        "location_cities_include": "list",
        "location_cities_exclude": "list",
        "location_regions_include": "list",
        "location_regions_exclude": "list",
        "location_postal_codes_include": "list",
        "location_postal_codes_exclude": "list",
        "location_states_include": "list",
        "location_states_exclude": "list",
        "location_headquarters_only": "bool",
        "semantic_description": "str",
        "derived_industries": "list",
        "derived_subindustries": "list",
        "derived_subindustries_exclude": "list",
        "derived_revenue_streams": "list",
        "derived_business_types": "list",
        "technographics_vendors": "list",
        "technographics_products": "list",
        "technographics_main_categories": "list",
        "technographics_parent_categories": "list",
        "has_resolved_domain": "list",
        "resolved_domain_is_live": "list",
        "resolved_domain_redirects": "list",
    },
    "people": {
        "company_identifier": "list",
        "include_past_experiences": "bool",
        "job_title_seniority_levels": "list",
        "job_title_seniority_levels_v2": "list",
        "job_title_seniority_match_mode": "str",
        "job_title_seniority_floor_level": "str",
        "job_title_keywords": "list",
        "job_title_exclude_keywords": "list",
        "job_title_include_past_experiences": "bool",
        "job_title_mode": "str",
        "job_functions": "list",
        "current_role_min_months_since_start_date": "int",
        "current_role_max_months_since_start_date": "int",
        "role_range_start_month": "int",
        "role_range_end_month": "int",
        "locations": "list",
        "company_description_keywords": "list",
        "company_description_keywords_exclude": "list",
        "company_sizes": "list",
        "company_annual_revenues": "list",
        "company_industries_include": "list",
        "company_industries_exclude": "list",
        "locations_exclude": "list",
        "location_cities_include": "list",
        "location_cities_exclude": "list",
        "location_states_include": "list",
        "location_states_exclude": "list",
        "location_countries_include": "list",
        "location_countries_exclude": "list",
        "location_regions_include": "list",
        "location_regions_exclude": "list",
        "headline_keywords": "list",
        "about_keywords": "list",
        "profile_keywords": "list",
        "job_description_keywords": "list",
        "job_description_include_past_experiences": "bool",
        "languages": "list",
        "school_names": "list",
        "certification_keywords": "list",
        "names": "list",
        "experience_count": "int",
        "max_experience_count": "int",
        "follower_count": "int",
        "max_follower_count": "int",
        "connection_count": "int",
        "max_connection_count": "int",
        "limit_per_company": "int",
    },
    "jobs": {
        "company_identifier": "list",
        "job_title_keywords": "list",
        "job_title_exclude_keywords": "list",
        "locations": "list",
        "locations_exclude": "list",
        "job_description_keywords": "list",
        "has_recruiter": "bool",
        "employment_type": "list",
        "seniority": "list",
        "max_num_days_since_posted": "int",
        "min_num_days_since_posted": "int",
    },
}

FILTER_ATTRS = {
    "company_identifier": "company_identifier",
    "include_past_experiences": "include_past_experiences",
    "job_title_seniority_levels": "seniority_levels",
    "job_title_seniority_levels_v2": "seniority_levels_v2",
    "job_title_seniority_match_mode": "seniority_match_mode",
    "job_title_seniority_floor_level": "seniority_floor_level",
    "job_title_keywords": "job_title_keywords",
    "job_title_exclude_keywords": "job_title_exclude_keywords",
    "job_title_include_past_experiences": "job_title_include_past_experiences",
    "job_title_mode": "job_title_mode",
    "job_functions": "job_functions",
    "current_role_min_months_since_start_date": "current_role_min_months",
    "current_role_max_months_since_start_date": "current_role_max_months",
    "role_range_start_month": "role_range_start_month",
    "role_range_end_month": "role_range_end_month",
    "locations": "locations",
    "locations_exclude": "locations_exclude",
    "location_cities_include": "location_cities_include",
    "location_cities_exclude": "location_cities_exclude",
    "location_states_include": "location_states_include",
    "location_states_exclude": "location_states_exclude",
    "location_countries_include": "country_names",
    "location_countries_exclude": "country_names_exclude",
    "location_regions_include": "location_regions_include",
    "location_regions_exclude": "location_regions_exclude",
    "company_description_keywords": "company_description_keywords",
    "company_description_keywords_exclude": "company_description_keywords_exclude",
    "company_sizes": "company_sizes",
    "company_annual_revenues": "company_annual_revenues",
    "company_industries_include": "company_industries_include",
    "company_industries_exclude": "company_industries_exclude",
    "headline_keywords": "headline_keywords",
    "about_keywords": "about_keywords",
    "profile_keywords": "profile_keywords",
    "job_description_keywords": "job_description_keywords",
    "job_description_include_past_experiences": "job_description_include_past_experiences",
    "languages": "languages",
    "school_names": "school_names",
    "certification_keywords": "certification_keywords",
    "names": "names",
    "experience_count": "experience_count",
    "max_experience_count": "max_experience_count",
    "follower_count": "follower_count",
    "max_follower_count": "max_follower_count",
    "connection_count": "connection_count",
    "max_connection_count": "max_connection_count",
    "limit_per_company": "limit_per_company",
}

ALIASES = {
    "people": {
        "domains": ("company_identifier", "list"),
        "seniority": ("job_title_seniority_levels", "list"),
        "functions": ("job_functions", "list"),
        "title_keywords": ("job_title_keywords", "list"),
        "exclude_titles": ("job_title_exclude_keywords", "list"),
        "title_mode": ("job_title_mode", "str"),
        "countries": ("location_countries_include", "list"),
        "countries_exclude": ("location_countries_exclude", "list"),
        "states": ("location_states_include", "list"),
        "states_exclude": ("location_states_exclude", "list"),
        "cities": ("location_cities_include", "list"),
        "cities_exclude": ("location_cities_exclude", "list"),
        "regions": ("location_regions_include", "list"),
        "regions_exclude": ("location_regions_exclude", "list"),
        "industries": ("company_industries_include", "list"),
        "industries_exclude": ("company_industries_exclude", "list"),
        "company_keywords": ("company_description_keywords", "list"),
        "company_keywords_exclude": ("company_description_keywords_exclude", "list"),
        "include_past": ("include_past_experiences", "bool"),
        "min_connections": ("connection_count", "int"),
        "max_connections": ("max_connection_count", "int"),
        "min_followers": ("follower_count", "int"),
        "max_followers": ("max_follower_count", "int"),
        "min_experience": ("experience_count", "int"),
        "max_experience": ("max_experience_count", "int"),
        "min_role_months": ("current_role_min_months_since_start_date", "int"),
        "max_role_months": ("current_role_max_months_since_start_date", "int"),
    },
    "companies": {
        "countries": ("country_names", "list"),
        "countries_exclude": ("country_names_exclude", "list"),
        "company_types": ("types", "list"),
        "company_sizes": ("sizes", "list"),
        "industries_include": ("industries", "list"),
        "industries_exclude_alias": ("industries_exclude", "list"),
    },
    "jobs": {
        "domains": ("company_identifier", "list"),
        "title_keywords": ("job_title_keywords", "list"),
        "exclude_titles": ("job_title_exclude_keywords", "list"),
    },
}


def _progress(msg):
    print(msg, file=sys.stderr)


def cmd_entity_search(args):
    entity = args.entity
    filters = _build_filters(args, entity)
    identifiers = _load_identifiers(args, entity)

    if getattr(args, "from_company_table", None):
        domains = _domains_from_company_table(
            args.from_company_table,
            args.company_domain_field,
        )
        identifiers.extend(domains)
        filters.company_identifier = identifiers

    client = ClayClient()
    searcher = SEARCH_CLASSES[entity](client)
    quiet = getattr(args, "quiet", False)
    on_progress = (lambda m: None) if quiet else _progress

    if not quiet:
        _progress(f"Clay {entity.title()} Search")
        _progress(f"  Mode: {args.mode}")
        _progress(f"  Limit: {args.limit if args.limit is not None else 'source default'}")
        if identifiers:
            _progress(f"  Company identifiers: {len(identifiers)}")
        if filters.raw_inputs is not None:
            _progress("  Inputs: raw Clay payload")

    result = searcher.search(
        identifiers,
        filters=filters,
        limit=args.limit,
        mode=args.mode,
        cleanup=args.cleanup,
        on_progress=on_progress,
    )
    records = result.records
    if filters.raw_inputs is not None and args.limit is not None:
        records = records[: args.limit]
    if getattr(args, "from_company_table", None):
        for record in records:
            record.source_company_table_id = args.from_company_table
            if not record.source_company_domain:
                record.source_company_domain = getattr(record, "company_domain", "")

    _write_output(records, args, entity)
    if not quiet:
        _progress(f"\nDone. {len(records)} total records.")


def cmd_people_search(args):
    args.entity = "people"
    return cmd_entity_search(args)


def cmd_company_search(args):
    args.entity = "companies"
    return cmd_entity_search(args)


def cmd_job_search(args):
    args.entity = "jobs"
    return cmd_entity_search(args)


def cmd_table_list(args):
    tables = TableManager(ClayClient()).list_tables()
    if not tables:
        print("No tables found.")
        return
    for t in tables:
        print(f"{t.table_id}  {t.name}  ({t.record_count} records)")


def cmd_table_info(args):
    t = TableManager(ClayClient()).get_table(args.table_id)
    print(f"Table: {t.name}")
    print(f"  ID: {t.table_id}")
    print(f"  View: {t.view_id}")
    print(f"  Workbook: {t.workbook_id}")
    print(f"  Records: {t.record_count}")


def cmd_table_count(args):
    print(TableManager(ClayClient()).get_record_count(args.table_id))


def cmd_table_delete(args):
    TableManager(ClayClient()).delete_table(args.table_id)
    print(f"Deleted {args.table_id}")


def cmd_auth_login(args):
    client = ClayClient()
    client.session.ensure_session()
    client.session.print_status(file=sys.stdout)


def cmd_auth_status(args):
    client = ClayClient()
    try:
        client.session.ensure_session()
    except Exception:
        pass
    client.session.print_status(file=sys.stdout)


def cmd_keywords_expand(args):
    terms = [t.strip() for t in args.terms.split(",") if t.strip()]
    if not terms:
        print("ERROR: Provide at least one term via --terms", file=sys.stderr)
        sys.exit(1)
    related = KeywordExpander(ClayClient()).get_related(terms)
    if args.output == "json":
        print(json.dumps(related, indent=2))
    else:
        for kw in related:
            print(kw)


def cmd_setup(args):
    print()
    print("Clay SDK Setup")
    print()

    existing_email = None
    if CREDENTIALS_FILE.exists():
        try:
            existing_email = json.loads(CREDENTIALS_FILE.read_text()).get("email")
        except (json.JSONDecodeError, OSError):
            pass

    if existing_email:
        overwrite = input(f"Overwrite existing credentials ({existing_email})? [y/N] ").strip().lower()
        if overwrite not in ("y", "yes"):
            print("Keeping existing credentials. Run 'clay auth status' to check session.")
            return
    try:
        email = input("Email: ").strip()
        password = getpass.getpass("Password: ")
    except (KeyboardInterrupt, EOFError):
        print("\nSetup cancelled.")
        sys.exit(1)
    if not email or not password:
        print("Error: Email and password are required.", file=sys.stderr)
        sys.exit(1)
    session = SessionManager()
    try:
        detected_workspace_id = session.login(email, password)
    except ClayAuthError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print()
    if detected_workspace_id:
        workspace_id = input(f"Workspace ID [{detected_workspace_id}]: ").strip() or detected_workspace_id
    else:
        workspace_id = input("Workspace ID: ").strip()
    if not workspace_id:
        print("Error: Workspace ID is required.", file=sys.stderr)
        sys.exit(1)

    save_credentials(email, password, workspace_id)
    print(f"Setup complete. Credentials stored in {CREDENTIALS_FILE}.")


def _find_source_dir():
    standard = AUTOCLAY_DIR / "src"
    if (standard / ".git").is_dir():
        return standard
    pkg_root = Path(__file__).resolve().parent.parent
    if (pkg_root / ".git").is_dir():
        return pkg_root
    return None


def cmd_update(args):
    src_dir = _find_source_dir()
    if not src_dir:
        print("Error: Cannot find autoclay source directory.", file=sys.stderr)
        print("If you installed manually, cd into the repo and run: git pull", file=sys.stderr)
        sys.exit(1)

    print(f"Updating from {src_dir}...")
    result = subprocess.run(
        ["git", "-C", str(src_dir), "pull"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"git pull failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    output = result.stdout.strip()
    if output == "Already up to date.":
        print("Already up to date.")
    else:
        print(output)
        print("\nUpdated successfully. Changes are live.")


def _split(val):
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [v.strip() for v in str(val).split(",") if v.strip()]


_COMPANY_SIZE_TOKENS = [
    "10,001+", "5,001-10,000", "1,001-5,000", "501-1,000",
    "10001+", "5001-10000", "1001-5000", "501-1000",
    "201-500", "51-200", "11-50", "2-10", "1",
]
_COMPANY_SIZE_FREE_TO_CANONICAL = {
    "10001+": "10,001+",
    "5001-10000": "5,001-10,000",
    "1001-5000": "1,001-5,000",
    "501-1000": "501-1,000",
}


def _parse_company_sizes(val):
    """Parse Clay company size labels, accepting comma-free thousands."""
    s = str(val).strip()
    out = []
    while s:
        for token in _COMPANY_SIZE_TOKENS:
            if s.startswith(token):
                out.append(_COMPANY_SIZE_FREE_TO_CANONICAL.get(token, token))
                s = s[len(token):].lstrip(", \t")
                break
        else:
            raise SystemExit(f"error: unrecognized company size near {s!r}")
    return out


def _parse_bool(val):
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("1", "true", "yes", "y", "on")


def _coerce(raw, kind):
    if raw is None:
        return None
    if kind == "list":
        return _split(raw)
    if kind == "int":
        return int(raw)
    if kind == "bool":
        return _parse_bool(raw)
    return raw


def _load_raw_inputs(args):
    if args.inputs_json and args.inputs_file:
        raise SystemExit("error: use only one of --inputs-json or --inputs-file")
    if args.inputs_json:
        return json.loads(args.inputs_json)
    if args.inputs_file:
        with open(args.inputs_file) as f:
            return json.load(f)
    return None


def _build_filters(args, entity="people"):
    raw_inputs = _load_raw_inputs(args)
    if raw_inputs is not None:
        return SearchFilters(raw_inputs=raw_inputs)

    kw = {}
    for field, kind in FIELD_TYPES[entity].items():
        if field == "limit":
            continue
        attr = FILTER_ATTRS.get(field, field)
        raw = getattr(args, field, None)
        if raw is not None:
            kw[attr] = _parse_company_sizes(raw) if field in ("company_sizes", "sizes") else _coerce(raw, kind)

    for alias, (field, kind) in ALIASES.get(entity, {}).items():
        raw = getattr(args, alias, None)
        if raw is not None and raw is not False:
            attr = FILTER_ATTRS.get(field, field)
            kw[attr] = _parse_company_sizes(raw) if field in ("company_sizes", "sizes") else _coerce(raw, kind)

    if entity == "people" and getattr(args, "title_mode", None):
        kw["job_title_mode"] = args.title_mode

    return SearchFilters(**kw)


def _load_identifiers(args, entity):
    identifiers = []
    for attr in ("company_identifier", "domains"):
        raw = getattr(args, attr, None)
        if raw:
            identifiers.extend(_split(raw))
    if getattr(args, "domains_file", None):
        with open(args.domains_file) as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip() and not row[0].lower().startswith("domain"):
                    identifiers.append(row[0].strip())
    return list(dict.fromkeys(identifiers))


def _domains_from_company_table(table_id, field_name):
    client = ClayClient()
    manager = TableManager(client)
    info = manager.get_table(table_id)
    fetcher = RecordFetcher(client)
    raw_records = fetcher.fetch_all(table_id, info.view_id)
    table = client.get(f"tables/{table_id}")["table"]
    fields = table.get("fields", [])
    field_ids = [f["id"] for f in fields if f.get("name") == field_name]
    if not field_ids:
        raise SystemExit(f"error: field {field_name!r} not found in table {table_id}")
    field_id = field_ids[0]
    domains = []
    for record in raw_records:
        cell = record.get("cells", {}).get(field_id) or {}
        value = cell.get("value")
        if isinstance(value, dict):
            value = value.get("Domain") or value.get("domain")
        if value:
            domains.append(str(value).strip())
    return list(dict.fromkeys(d for d in domains if d))


def _write_output(records, args, entity):
    quiet = getattr(args, "quiet", False)
    if args.output == "json":
        json_str = write_json(records, args.output_file, entity=entity)
        if not args.output_file:
            print(json_str)
        elif not quiet:
            _progress(f"Wrote {len(records)} records to {args.output_file}")
    elif args.output == "sqlite":
        output_file = args.output_file or f"clay_{entity}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        inserted, skipped = write_sqlite(records, output_file, entity=entity)
        if not quiet:
            _progress(f"Wrote {inserted} records to {output_file} ({skipped} duplicates skipped)")
    else:
        output_file = args.output_file or f"clay_{entity}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        count = write_csv(records, output_file, entity=entity)
        if not quiet:
            _progress(f"Wrote {count} records to {output_file}")


def _add_shared_search_args(parser):
    parser.add_argument("--mode", choices=["preview", "full", "auto"], default="auto")
    parser.add_argument("--output", choices=["csv", "sqlite", "json"], default="csv")
    parser.add_argument("--output-file", "-f", help="Output file path")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--cleanup", action="store_true", help="Delete Clay table/workbook after extraction")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress output")
    parser.add_argument("--inputs-json", help="Exact raw Clay source inputs JSON object")
    parser.add_argument("--inputs-file", help="File containing exact raw Clay source inputs JSON object")


def _add_typed_args(parser, entity):
    for field, kind in FIELD_TYPES[entity].items():
        option = "--" + field.replace("_", "-")
        if field == "limit":
            continue
        if kind == "bool":
            parser.add_argument(option, nargs="?", const="true", help=f"{field} (true/false)")
        elif kind == "int":
            parser.add_argument(option, type=int)
        else:
            parser.add_argument(option)


def _add_people_alias_args(parser):
    parser.add_argument("--domains", help="Backward-compatible alias for --company-identifier")
    parser.add_argument("--domains-file", help="CSV file with domains in the first column")
    parser.add_argument("--seniority", help="Alias for --job-title-seniority-levels")
    parser.add_argument("--functions", help="Alias for --job-functions")
    parser.add_argument("--title-keywords", help="Alias for --job-title-keywords")
    parser.add_argument("--exclude-titles", help="Alias for --job-title-exclude-keywords")
    parser.add_argument("--title-mode", choices=["smart", "contain", "exact"], default=None)
    parser.add_argument("--countries", help="Alias for --location-countries-include")
    parser.add_argument("--countries-exclude", help="Alias for --location-countries-exclude")
    parser.add_argument("--states", help="Alias for --location-states-include")
    parser.add_argument("--states-exclude", help="Alias for --location-states-exclude")
    parser.add_argument("--cities", help="Alias for --location-cities-include")
    parser.add_argument("--cities-exclude", help="Alias for --location-cities-exclude")
    parser.add_argument("--regions", help="Alias for --location-regions-include")
    parser.add_argument("--regions-exclude", help="Alias for --location-regions-exclude")
    parser.add_argument("--industries", help="Alias for --company-industries-include")
    parser.add_argument("--industries-exclude", help="Alias for --company-industries-exclude")
    parser.add_argument("--company-keywords", help="Alias for --company-description-keywords")
    parser.add_argument("--company-keywords-exclude", help="Alias for --company-description-keywords-exclude")
    parser.add_argument("--include-past", action="store_true", help="Alias for --include-past-experiences")
    parser.add_argument("--min-connections", type=int, help="Alias for --connection-count")
    parser.add_argument("--max-connections", type=int, help="Alias for --max-connection-count")
    parser.add_argument("--min-followers", type=int, help="Alias for --follower-count")
    parser.add_argument("--max-followers", type=int, help="Alias for --max-follower-count")
    parser.add_argument("--min-experience", type=int, help="Alias for --experience-count")
    parser.add_argument("--max-experience", type=int, help="Alias for --max-experience-count")
    parser.add_argument("--min-role-months", type=int, help="Alias for current role minimum months")
    parser.add_argument("--max-role-months", type=int, help="Alias for current role maximum months")
    parser.add_argument("--from-company-table", help="Extract company domains from an existing company table")
    parser.add_argument("--company-domain-field", default="Domain", help="Company table field containing domains")


def _add_company_alias_args(parser):
    parser.add_argument("--countries", help="Alias for --country-names")
    parser.add_argument("--countries-exclude", help="Alias for --country-names-exclude")
    parser.add_argument("--company-types", help="Alias for --types")
    parser.add_argument("--company-sizes", help="Alias for --sizes")
    parser.add_argument("--industries-include", help="Alias for --industries")
    parser.add_argument("--industries-exclude-alias", help="Alias for --industries-exclude")


def _add_job_alias_args(parser):
    parser.add_argument("--domains", help="Alias for --company-identifier")
    parser.add_argument("--domains-file", help="CSV file with domains in the first column")
    parser.add_argument("--title-keywords", help="Alias for --job-title-keywords")
    parser.add_argument("--exclude-titles", help="Alias for --job-title-exclude-keywords")
    parser.add_argument("--from-company-table", help="Extract company domains from an existing company table")
    parser.add_argument("--company-domain-field", default="Domain", help="Company table field containing domains")


def build_parser():
    parser = argparse.ArgumentParser(prog="clay", description="Clay SDK CLI")
    sub = parser.add_subparsers(dest="command")

    subparsers = {}
    for entity, help_text, handler in [
        ("companies", "Company operations", cmd_company_search),
        ("people", "People operations", cmd_people_search),
        ("jobs", "Job operations", cmd_job_search),
    ]:
        entity_parser = sub.add_parser(entity, help=help_text)
        subparsers[entity] = entity_parser
        entity_sub = entity_parser.add_subparsers(dest=f"{entity}_command")
        search = entity_sub.add_parser("search", help=f"Search for {entity}")
        search.set_defaults(func=handler, entity=entity)
        _add_shared_search_args(search)
        _add_typed_args(search, entity)
        if entity == "people":
            _add_people_alias_args(search)
        elif entity == "companies":
            _add_company_alias_args(search)
        else:
            _add_job_alias_args(search)

    table_parser = sub.add_parser("table", help="Table operations")
    subparsers["table"] = table_parser
    table_sub = table_parser.add_subparsers(dest="table_command")
    list_p = table_sub.add_parser("list", help="List tables in workspace")
    list_p.set_defaults(func=cmd_table_list)
    info_p = table_sub.add_parser("info", help="Get table info")
    info_p.add_argument("table_id")
    info_p.set_defaults(func=cmd_table_info)
    count_p = table_sub.add_parser("count", help="Get record count")
    count_p.add_argument("table_id")
    count_p.set_defaults(func=cmd_table_count)
    del_p = table_sub.add_parser("delete", help="Delete a table")
    del_p.add_argument("table_id")
    del_p.set_defaults(func=cmd_table_delete)

    auth_parser = sub.add_parser("auth", help="Authentication")
    subparsers["auth"] = auth_parser
    auth_sub = auth_parser.add_subparsers(dest="auth_command")
    login_p = auth_sub.add_parser("login", help="Login and verify session")
    login_p.set_defaults(func=cmd_auth_login)
    status_p = auth_sub.add_parser("status", help="Show auth status")
    status_p.set_defaults(func=cmd_auth_status)

    kw_parser = sub.add_parser("keywords", help="Keyword expansion tools")
    subparsers["keywords"] = kw_parser
    kw_sub = kw_parser.add_subparsers(dest="keywords_command")
    expand_p = kw_sub.add_parser("expand", help="Expand keywords with related terms")
    expand_p.add_argument("--terms", required=True)
    expand_p.add_argument("--output", choices=["text", "json"], default="text")
    expand_p.set_defaults(func=cmd_keywords_expand)

    setup_p = sub.add_parser("setup", help="Interactive setup wizard")
    setup_p.set_defaults(func=cmd_setup)

    update_p = sub.add_parser("update", help="Update autoclay to latest version")
    update_p.set_defaults(func=cmd_update)

    return parser, subparsers


def main():
    parser, subparsers = build_parser()
    if len(sys.argv) == 2 and sys.argv[1] in subparsers:
        subparsers[sys.argv[1]].print_help()
        sys.exit(1)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    handler = getattr(args, "func", None)
    if handler:
        handler(args)
        return

    if args.command in subparsers:
        subparsers[args.command].print_help()
        sys.exit(1)
    parser.print_help()
    sys.exit(1)
