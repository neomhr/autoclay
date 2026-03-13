"""Clay SDK CLI — argparse dispatcher.

Usage:
    clay people search --domains acme.com [options]
    clay table list
    clay auth login
"""

import argparse
import csv
import getpass
import json
import sys
from datetime import datetime

import subprocess

from .auth import SessionManager
from .client import ClayClient
from .config import AUTOCLAY_DIR, CREDENTIALS_FILE, save_credentials
from .exceptions import ClayAuthError
from .models import SearchFilters
from .search import PeopleSearch, KeywordExpander
from .tables import TableManager
from .output import write_csv, write_sqlite, write_json


BANNER = r"""
       █████  ██    ██ ████████  ██████   ██████ ██       █████  ██    ██
      ██   ██ ██    ██    ██    ██    ██ ██      ██      ██   ██  ██  ██
      ███████ ██    ██    ██    ██    ██ ██      ██      ███████   ████
      ██   ██ ██    ██    ██    ██    ██ ██      ██      ██   ██    ██
      ██   ██  ██████     ██     ██████   ██████ ███████ ██   ██    ██
"""

TAGLINE = "      Built by Neo Mohr"


def _progress(msg):
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# People commands
# ---------------------------------------------------------------------------

def cmd_people_search(args):
    """Run people search."""
    domains = _load_domains(args)
    filters = _build_filters(args)
    client = ClayClient()
    ps = PeopleSearch(client)

    quiet = getattr(args, "quiet", False)
    on_progress = (lambda m: None) if quiet else _progress

    if not quiet:
        _progress("Clay People Search")
        _progress(f"  Mode: {args.mode}")
        if domains:
            _progress(f"  Domains: {len(domains)} ({', '.join(domains[:3])}{'...' if len(domains) > 3 else ''})")
        else:
            _progress("  Domains: all (no filter)")
        _progress(f"  Limit: {args.limit or 'plan cap'}")
        if args.limit_per_company:
            _progress(f"  Limit per company: {args.limit_per_company}")

    if args.mode == "full" and len(domains) > 1:
        # Full mode: one search per domain for best coverage
        all_people = []
        for i, domain in enumerate(domains):
            if not quiet:
                _progress(f"[{i+1}/{len(domains)}] {domain}")
            result = ps.search(
                [domain],
                filters=filters,
                limit=args.limit,
                limit_per_company=args.limit_per_company,
                mode="full",
                cleanup=args.cleanup,
                on_progress=on_progress,
            )
            all_people.extend(result.people)
            if not quiet:
                _progress(f"  Total so far: {len(all_people)}")
    else:
        result = ps.search(
            domains,
            filters=filters,
            limit=args.limit,
            limit_per_company=args.limit_per_company,
            mode=args.mode,
            cleanup=args.cleanup,
            on_progress=on_progress,
        )
        all_people = result.people

    _write_output(all_people, args)

    if not quiet:
        _progress(f"\nDone. {len(all_people)} total records.")


# ---------------------------------------------------------------------------
# Table commands
# ---------------------------------------------------------------------------

def cmd_table_list(args):
    client = ClayClient()
    tm = TableManager(client)
    tables = tm.list_tables()
    if not tables:
        print("No tables found.")
        return
    for t in tables:
        print(f"{t.table_id}  {t.name}  ({t.record_count} records)")


def cmd_table_info(args):
    client = ClayClient()
    tm = TableManager(client)
    t = tm.get_table(args.table_id)
    print(f"Table: {t.name}")
    print(f"  ID: {t.table_id}")
    print(f"  View: {t.view_id}")
    print(f"  Workbook: {t.workbook_id}")
    print(f"  Records: {t.record_count}")


def cmd_table_count(args):
    client = ClayClient()
    tm = TableManager(client)
    count = tm.get_record_count(args.table_id)
    print(count)


def cmd_table_delete(args):
    client = ClayClient()
    tm = TableManager(client)
    tm.delete_table(args.table_id)
    print(f"Deleted {args.table_id}")


# ---------------------------------------------------------------------------
# Auth commands
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Keywords commands
# ---------------------------------------------------------------------------

def cmd_keywords_expand(args):
    """Expand keywords using Clay's related-keywords API."""
    terms = [t.strip() for t in args.terms.split(",") if t.strip()]
    if not terms:
        print("ERROR: Provide at least one term via --terms", file=sys.stderr)
        sys.exit(1)
    client = ClayClient()
    expander = KeywordExpander(client)
    related = expander.get_related(terms)
    if args.output == "json":
        print(json.dumps(related, indent=2))
    else:
        for kw in related:
            print(kw)


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def cmd_setup(args):
    """Interactive setup wizard."""
    print(BANNER)
    print(TAGLINE)
    print()
    print("  ─── Setup ───")
    print()

    # Step 1: Python version check
    v = sys.version_info
    if v >= (3, 8):
        print(f"  Checking Python version... ok  Python {v.major}.{v.minor}.{v.micro}")
    else:
        print(f"  Checking Python version... FAIL  Python {v.major}.{v.minor}.{v.micro} (need 3.8+)")
        sys.exit(1)

    # Step 2: Check existing credentials
    existing_email = None
    if CREDENTIALS_FILE.exists():
        try:
            creds = json.loads(CREDENTIALS_FILE.read_text())
            existing_email = creds.get("email")
        except (json.JSONDecodeError, OSError):
            pass

    if existing_email:
        print(f"  Found existing credentials ({existing_email})")
        print()
        overwrite = input("  Overwrite existing credentials? [y/N] ").strip().lower()
        if overwrite not in ("y", "yes"):
            print()
            print("  Keeping existing credentials. Run 'clay auth status' to check session.")
            print()
            return
    else:
        print("  No existing credentials found")

    # Step 3: Prompt for credentials
    print()
    print("  Enter your Clay credentials:")
    try:
        email = input("    Email: ").strip()
        password = getpass.getpass("    Password: ")
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Setup cancelled.")
        sys.exit(1)

    if not email or not password:
        print("\n  Error: Email and password are required.")
        sys.exit(1)

    # Step 4: Test authentication
    print()
    print("  Authenticating...", end=" ", flush=True)
    session = SessionManager()
    try:
        detected_workspace_id = session.login(email, password)
    except ClayAuthError as e:
        print("FAIL")
        print(f"\n  Error: {e}")
        print("  Credentials NOT saved.")
        sys.exit(1)

    status = session.status()
    print(f"ok  Logged in (session expires in {status['expires_in']})")

    # Step 5: Prompt for workspace ID
    print()
    print("  Workspace ID")
    print("    Find it in your Clay URL: app.clay.com/workspaces/<WORKSPACE_ID>")
    if detected_workspace_id:
        print(f"    Detected from login: {detected_workspace_id}")
    print()
    try:
        default_label = f" [{detected_workspace_id}]" if detected_workspace_id else ""
        workspace_id = input(f"    Workspace ID{default_label}: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Setup cancelled.")
        sys.exit(1)

    if not workspace_id:
        if detected_workspace_id:
            workspace_id = detected_workspace_id
        else:
            print("\n  Error: Workspace ID is required.")
            sys.exit(1)

    # Step 6: Save to ~/.autoclay/credentials.json
    print()
    print(f"  Saving credentials to {CREDENTIALS_FILE}...", end=" ", flush=True)
    save_credentials(email, password, workspace_id)
    print("ok")

    # Step 7: Success banner
    print()
    print("  ─── Setup complete! ───")
    print()
    print("  Credentials stored in ~/.autoclay/credentials.json")
    print("  Session cached in ~/.autoclay/session.json")
    print()
    print("  Try it out:")
    print("    clay people search --domains github.com")
    print()


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

def _find_source_dir():
    """Find the autoclay source directory.

    Checks, in order:
    1. ~/.autoclay/src/ (standard install location)
    2. The directory containing this package (editable/dev install)
    """
    from pathlib import Path

    standard = AUTOCLAY_DIR / "src"
    if (standard / ".git").is_dir():
        return standard

    # Fallback: this file's parent's parent (repo root)
    pkg_root = Path(__file__).resolve().parent.parent
    if (pkg_root / ".git").is_dir():
        return pkg_root

    return None


def cmd_update(args):
    """Pull latest changes from git."""
    src_dir = _find_source_dir()
    if not src_dir:
        print("Error: Cannot find autoclay source directory.", file=sys.stderr)
        print("If you installed manually, cd into the repo and run: git pull", file=sys.stderr)
        sys.exit(1)

    print(f"Updating from {src_dir}...")
    result = subprocess.run(
        ["git", "-C", str(src_dir), "pull"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"git pull failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    output = result.stdout.strip()
    if output == "Already up to date.":
        print("Already up to date.")
    else:
        print(output)
        print("\nUpdated successfully. Changes are live (editable install).")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_domains(args):
    if args.domains:
        return [d.strip() for d in args.domains.split(",") if d.strip()]
    if args.domains_file:
        domains = []
        with open(args.domains_file) as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip() and not row[0].startswith("#"):
                    val = row[0].strip()
                    if "." in val and not val.lower().startswith("domain"):
                        domains.append(val)
        return domains
    # No domains specified — search across all sources
    return []


def _split(val):
    """Split a comma-separated string into a trimmed list."""
    return [v.strip() for v in val.split(",") if v.strip()]


def _build_filters(args):
    kw = {}

    # Seniority & functions
    if args.seniority:
        kw["seniority_levels"] = _split(args.seniority)
    if args.functions:
        kw["job_functions"] = _split(args.functions)

    # Title
    if args.title_keywords:
        kw["job_title_keywords"] = _split(args.title_keywords)
    if args.exclude_titles:
        kw["job_title_exclude_keywords"] = _split(args.exclude_titles)
    if args.title_mode != "smart":
        kw["job_title_mode"] = args.title_mode

    # Location
    if args.countries:
        kw["countries_include"] = _split(args.countries)
    if args.countries_exclude:
        kw["countries_exclude"] = _split(args.countries_exclude)
    if args.states:
        kw["states_include"] = _split(args.states)
    if args.states_exclude:
        kw["states_exclude"] = _split(args.states_exclude)
    if args.cities:
        kw["cities_include"] = _split(args.cities)
    if args.cities_exclude:
        kw["cities_exclude"] = _split(args.cities_exclude)
    if args.regions:
        kw["regions_include"] = _split(args.regions)
    if args.regions_exclude:
        kw["regions_exclude"] = _split(args.regions_exclude)

    # Company
    if args.company_sizes:
        kw["company_sizes"] = _split(args.company_sizes)
    if args.industries:
        kw["company_industries_include"] = _split(args.industries)
    if args.industries_exclude:
        kw["company_industries_exclude"] = _split(args.industries_exclude)
    if args.company_keywords:
        kw["company_description_keywords"] = _split(args.company_keywords)
    if args.company_keywords_exclude:
        kw["company_description_keywords_exclude"] = _split(args.company_keywords_exclude)

    # Profile/keyword
    if args.headline_keywords:
        kw["headline_keywords"] = _split(args.headline_keywords)
    if args.about_keywords:
        kw["about_keywords"] = _split(args.about_keywords)
    if args.profile_keywords:
        kw["profile_keywords"] = _split(args.profile_keywords)
    if args.job_description_keywords:
        kw["job_description_keywords"] = _split(args.job_description_keywords)
    if args.certification_keywords:
        kw["certification_keywords"] = _split(args.certification_keywords)
    if args.school_names:
        kw["school_names"] = _split(args.school_names)

    # LinkedIn activity
    if args.min_connections is not None:
        kw["connection_count"] = args.min_connections
    if args.max_connections is not None:
        kw["max_connection_count"] = args.max_connections
    if args.min_followers is not None:
        kw["follower_count"] = args.min_followers
    if args.max_followers is not None:
        kw["max_follower_count"] = args.max_followers
    if args.min_experience is not None:
        kw["experience_count"] = args.min_experience
    if args.max_experience is not None:
        kw["max_experience_count"] = args.max_experience

    # Role tenure
    if args.min_role_months is not None:
        kw["current_role_min_months"] = args.min_role_months
    if args.max_role_months is not None:
        kw["current_role_max_months"] = args.max_role_months

    # Role date range
    if args.role_range_start_month is not None:
        kw["role_range_start_month"] = args.role_range_start_month
    if args.role_range_end_month is not None:
        kw["role_range_end_month"] = args.role_range_end_month

    # Other
    if args.languages:
        kw["languages"] = _split(args.languages)
    if args.names:
        kw["names"] = _split(args.names)
    if args.include_past:
        kw["include_past_experiences"] = True

    return SearchFilters(**kw)


def _write_output(people, args):
    quiet = getattr(args, "quiet", False)
    output_format = args.output

    if output_format == "json":
        json_str = write_json(people, args.output_file)
        if not args.output_file:
            print(json_str)
        elif not quiet:
            _progress(f"Wrote {len(people)} records to {args.output_file}")
    elif output_format == "sqlite":
        output_file = args.output_file or f"clay_people_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        inserted, skipped = write_sqlite(people, output_file)
        if not quiet:
            _progress(f"Wrote {inserted} records to {output_file} ({skipped} duplicates skipped)")
    else:  # csv
        output_file = args.output_file or f"clay_people_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        count = write_csv(people, output_file)
        if not quiet:
            _progress(f"Wrote {count} records to {output_file}")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(prog="clay", description="Clay SDK CLI")
    sub = parser.add_subparsers(dest="command")

    # --- people ---
    people_parser = sub.add_parser("people", help="People operations")
    people_sub = people_parser.add_subparsers(dest="people_command")

    search_p = people_sub.add_parser("search", help="Search for people at companies")
    search_p.add_argument("--domains", help="Comma-separated domains")
    search_p.add_argument("--domains-file", help="CSV file with domains (first column)")
    search_p.add_argument("--mode", choices=["preview", "full", "auto"], default="auto")
    search_p.add_argument("--output", choices=["csv", "sqlite", "json"], default="csv")
    search_p.add_argument("--output-file", "-f", help="Output file path")
    search_p.add_argument("--limit", type=int, default=None,
                          help="Total max results across all companies (default: plan cap)")
    search_p.add_argument("--limit-per-company", type=int, default=None,
                          help="Max results per company (default: no per-company cap)")
    # Filter: seniority & functions
    search_p.add_argument("--seniority", help="Comma-separated seniority levels")
    search_p.add_argument("--functions", help="Comma-separated job functions")

    # Filter: title
    search_p.add_argument("--title-keywords", help="Comma-separated title keywords")
    search_p.add_argument("--exclude-titles", help="Comma-separated title exclusion keywords")
    search_p.add_argument("--title-mode", choices=["smart", "contain", "exact"], default="smart",
                          help="Title matching mode (default: smart)")

    # Filter: location
    search_p.add_argument("--countries", help="Comma-separated country names to include")
    search_p.add_argument("--countries-exclude", help="Comma-separated country names to exclude")
    search_p.add_argument("--states", help="Comma-separated states to include")
    search_p.add_argument("--states-exclude", help="Comma-separated states to exclude")
    search_p.add_argument("--cities", help="Comma-separated cities to include")
    search_p.add_argument("--cities-exclude", help="Comma-separated cities to exclude")
    search_p.add_argument("--regions", help="Comma-separated regions to include")
    search_p.add_argument("--regions-exclude", help="Comma-separated regions to exclude")

    # Filter: company
    search_p.add_argument("--company-sizes", help="Comma-separated company sizes (e.g. '1,2-10,51-200')")
    search_p.add_argument("--industries", help="Comma-separated industries to include")
    search_p.add_argument("--industries-exclude", help="Comma-separated industries to exclude")
    search_p.add_argument("--company-keywords", help="Comma-separated company description keywords")
    search_p.add_argument("--company-keywords-exclude", help="Comma-separated company description exclusions")

    # Filter: profile/keyword
    search_p.add_argument("--headline-keywords", help="Comma-separated LinkedIn headline keywords")
    search_p.add_argument("--about-keywords", help="Comma-separated LinkedIn about section keywords")
    search_p.add_argument("--profile-keywords", help="Comma-separated general profile keywords")
    search_p.add_argument("--job-description-keywords", help="Comma-separated job description keywords")
    search_p.add_argument("--certification-keywords", help="Comma-separated certification keywords")
    search_p.add_argument("--school-names", help="Comma-separated school/university names")

    # Filter: LinkedIn activity
    search_p.add_argument("--min-connections", type=int, help="Minimum LinkedIn connections")
    search_p.add_argument("--max-connections", type=int, help="Maximum LinkedIn connections")
    search_p.add_argument("--min-followers", type=int, help="Minimum LinkedIn followers")
    search_p.add_argument("--max-followers", type=int, help="Maximum LinkedIn followers")
    search_p.add_argument("--min-experience", type=int, help="Minimum experience entries")
    search_p.add_argument("--max-experience", type=int, help="Maximum experience entries")

    # Filter: role tenure
    search_p.add_argument("--min-role-months", type=int, help="Min months in current role")
    search_p.add_argument("--max-role-months", type=int, help="Max months in current role")

    # Filter: role date range
    search_p.add_argument("--role-range-start-month", type=int, help="Role start date filter (months ago)")
    search_p.add_argument("--role-range-end-month", type=int, help="Role end date filter (months ago)")

    # Filter: other
    search_p.add_argument("--languages", help="Comma-separated languages")
    search_p.add_argument("--names", help="Comma-separated person names to filter")
    search_p.add_argument("--include-past", action="store_true", help="Include past experiences")

    search_p.add_argument("--cleanup", action="store_true", help="Delete Clay table after extraction")
    search_p.add_argument("--quiet", "-q", action="store_true", help="Suppress progress output")

    # --- table ---
    table_parser = sub.add_parser("table", help="Table operations")
    table_sub = table_parser.add_subparsers(dest="table_command")

    table_sub.add_parser("list", help="List tables in workspace")

    info_p = table_sub.add_parser("info", help="Get table info")
    info_p.add_argument("table_id", help="Table ID")

    count_p = table_sub.add_parser("count", help="Get record count")
    count_p.add_argument("table_id", help="Table ID")

    del_p = table_sub.add_parser("delete", help="Delete a table")
    del_p.add_argument("table_id", help="Table ID")

    # --- auth ---
    auth_parser = sub.add_parser("auth", help="Authentication")
    auth_sub = auth_parser.add_subparsers(dest="auth_command")
    auth_sub.add_parser("login", help="Login and verify session")
    auth_sub.add_parser("status", help="Show auth status")

    # --- keywords ---
    kw_parser = sub.add_parser("keywords", help="Keyword expansion tools")
    kw_sub = kw_parser.add_subparsers(dest="keywords_command")

    expand_p = kw_sub.add_parser("expand", help="Expand keywords with related terms")
    expand_p.add_argument("--terms", required=True, help="Comma-separated seed keywords")
    expand_p.add_argument("--output", choices=["text", "json"], default="text",
                          help="Output format (default: text)")

    # --- setup ---
    sub.add_parser("setup", help="Interactive setup wizard")

    # --- update ---
    sub.add_parser("update", help="Update autoclay to latest version")

    return parser, {"people": people_parser, "table": table_parser, "auth": auth_parser, "keywords": kw_parser}


def main():
    parser, subparsers = build_parser()

    # Intercept missing subcommands before argparse prints its own error
    if len(sys.argv) == 2 and sys.argv[1] in subparsers:
        subparsers[sys.argv[1]].print_help()
        sys.exit(1)

    args = parser.parse_args()

    if not args.command:
        print(BANNER)
        print(TAGLINE)
        print()
        parser.print_help()
        sys.exit(1)

    # Top-level commands (no subcommand)
    if args.command == "setup":
        cmd_setup(args)
        return
    if args.command == "update":
        cmd_update(args)
        return

    dispatch = {
        ("people", "search"): cmd_people_search,
        ("table", "list"): cmd_table_list,
        ("table", "info"): cmd_table_info,
        ("table", "count"): cmd_table_count,
        ("table", "delete"): cmd_table_delete,
        ("auth", "login"): cmd_auth_login,
        ("auth", "status"): cmd_auth_status,
        ("keywords", "expand"): cmd_keywords_expand,
    }

    subcmd = None
    if args.command == "people":
        subcmd = getattr(args, "people_command", None)
    elif args.command == "table":
        subcmd = getattr(args, "table_command", None)
    elif args.command == "auth":
        subcmd = getattr(args, "auth_command", None)
    elif args.command == "keywords":
        subcmd = getattr(args, "keywords_command", None)

    key = (args.command, subcmd)
    handler = dispatch.get(key)
    if handler:
        handler(args)
    elif args.command in subparsers:
        subparsers[args.command].print_help()
        sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)
