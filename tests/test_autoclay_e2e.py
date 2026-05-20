"""Extensive AutoClay regression suite.

Run from the repository root with:

    CLAY_WORKSPACE_ID=your_workspace_id python3 -m unittest discover -s tests -v

The suite intentionally mixes unit-level contract tests with live Clay API
checks. Live checks are skipped unless CLAY_WORKSPACE_ID is set. They use tiny
limits and test tables are deleted.
"""

from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
import subprocess
import sys
import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autoclay import cli
from autoclay.cli import _build_filters, _parse_company_sizes, build_parser
from autoclay.client import ClayClient
from autoclay.exceptions import ClayAPIError
from autoclay.models import Person, SearchFilters
from autoclay.output import write_csv, write_json, write_sqlite
from autoclay.search import PeopleSearch
from autoclay.search._base import BaseSearch
from autoclay.tables.manager import TableManager


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = Path(
    os.environ.get(
        "AUTOCLAY_E2E_DIR",
        str(Path(tempfile.gettempdir()) / "autoclay-e2e" / "suite"),
    )
)
LIVE_WORKSPACE_ID = os.environ.get("CLAY_WORKSPACE_ID")
WORKSPACE_ID = LIVE_WORKSPACE_ID or "test-workspace"


def run_cli(
    *args: str,
    timeout: int = 180,
    input_text: str | None = None,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["CLAY_WORKSPACE_ID"] = WORKSPACE_ID
    if env_overrides:
        env.update(env_overrides)
    cmd = [sys.executable, "-m", "autoclay", *args]
    return subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def assert_success(testcase: unittest.TestCase, proc: subprocess.CompletedProcess[str]) -> None:
    testcase.assertEqual(
        proc.returncode,
        0,
        msg=f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}",
    )


def wait_for_workbook_absent(manager: TableManager, workbook_id: str, timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        active_ids = {t.workbook_id for t in manager.list_workbooks()}
        if workbook_id not in active_ids:
            return True
        time.sleep(2)
    return False


class UnitContractTests(unittest.TestCase):
    def test_cli_help_and_missing_subcommands_are_wired(self):
        top = run_cli()
        self.assertEqual(top.returncode, 1)
        self.assertIn("Clay SDK CLI", top.stdout)
        self.assertIn("people", top.stdout)

        for command, expected in [
            ("people", "Search for people"),
            ("table", "delete"),
            ("auth", "status"),
            ("keywords", "expand"),
        ]:
            proc = run_cli(command)
            self.assertEqual(proc.returncode, 1, msg=proc.stderr)
            self.assertIn(expected, proc.stdout)

    def test_setup_keeps_existing_credentials_when_user_declines_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp_home:
            home = Path(tmp_home)
            autoclay_dir = home / ".autoclay"
            autoclay_dir.mkdir()
            credentials = autoclay_dir / "credentials.json"
            original = {
                "email": "existing@example.com",
                "password": "placeholder",
                "workspace_id": "workspace-placeholder",
            }
            credentials.write_text(json.dumps(original) + "\n")

            proc = run_cli("setup", input_text="n\n", env_overrides={"HOME": tmp_home})

            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertIn("Keeping existing credentials", proc.stdout)
            self.assertEqual(json.loads(credentials.read_text()), original)

    def test_update_command_reports_already_current_without_real_git_pull(self):
        completed = subprocess.CompletedProcess(
            ["git", "-C", "/tmp/autoclay", "pull"],
            0,
            stdout="Already up to date.\n",
            stderr="",
        )
        with patch.object(cli, "_find_source_dir", return_value=Path("/tmp/autoclay")):
            with patch.object(cli.subprocess, "run", return_value=completed) as run:
                with patch("sys.stdout", new_callable=io.StringIO) as stdout:
                    cli.cmd_update(object())

        run.assert_called_once_with(
            ["git", "-C", "/tmp/autoclay", "pull"],
            capture_output=True,
            text=True,
        )
        self.assertIn("Already up to date.", stdout.getvalue())

    def test_company_size_parser_accepts_canonical_and_comma_free_forms(self):
        self.assertEqual(
            _parse_company_sizes("501-1000,1001-5000,5001-10000,10001+"),
            ["501-1,000", "1,001-5,000", "5,001-10,000", "10,001+"],
        )
        self.assertEqual(
            _parse_company_sizes("501-1,000,1,001-5,000,10,001+"),
            ["501-1,000", "1,001-5,000", "10,001+"],
        )

    def test_every_people_search_flag_maps_into_search_filters(self):
        parser, _ = build_parser()
        args = parser.parse_args(
            [
                "people",
                "search",
                "--domains",
                "openai.com",
                "--seniority",
                "c-suite,vp",
                "--functions",
                "Sales,Engineering",
                "--title-keywords",
                "CEO,Founder",
                "--exclude-titles",
                "Intern,Assistant",
                "--title-mode",
                "contain",
                "--countries",
                "United States,Germany",
                "--countries-exclude",
                "China",
                "--states",
                "California",
                "--states-exclude",
                "Texas",
                "--cities",
                "San Francisco",
                "--cities-exclude",
                "Houston",
                "--regions",
                "NAM",
                "--regions-exclude",
                "APAC",
                "--company-sizes",
                "501-1000,1001-5000",
                "--industries",
                "Software Development",
                "--industries-exclude",
                "Mining",
                "--company-keywords",
                "AI",
                "--company-keywords-exclude",
                "nonprofit",
                "--headline-keywords",
                "growth",
                "--about-keywords",
                "entrepreneur",
                "--profile-keywords",
                "machine learning",
                "--job-description-keywords",
                "team lead",
                "--certification-keywords",
                "PMP",
                "--school-names",
                "MIT",
                "--min-connections",
                "500",
                "--max-connections",
                "5000",
                "--min-followers",
                "100",
                "--max-followers",
                "10000",
                "--min-experience",
                "1",
                "--max-experience",
                "10",
                "--min-role-months",
                "6",
                "--max-role-months",
                "24",
                "--role-range-start-month",
                "3",
                "--role-range-end-month",
                "12",
                "--languages",
                "English,German",
                "--names",
                "Sam,Alex",
                "--include-past",
            ]
        )
        f = _build_filters(args)
        self.assertEqual(f.seniority_levels, ["c-suite", "vp"])
        self.assertEqual(f.job_functions, ["Sales", "Engineering"])
        self.assertEqual(f.job_title_keywords, ["CEO", "Founder"])
        self.assertEqual(f.job_title_exclude_keywords, ["Intern", "Assistant"])
        self.assertEqual(f.job_title_mode, "contain")
        self.assertEqual(f.countries_include, ["United States", "Germany"])
        self.assertEqual(f.countries_exclude, ["China"])
        self.assertEqual(f.states_include, ["California"])
        self.assertEqual(f.states_exclude, ["Texas"])
        self.assertEqual(f.cities_include, ["San Francisco"])
        self.assertEqual(f.cities_exclude, ["Houston"])
        self.assertEqual(f.regions_include, ["NAM"])
        self.assertEqual(f.regions_exclude, ["APAC"])
        self.assertEqual(f.company_sizes, ["501-1,000", "1,001-5,000"])
        self.assertEqual(f.company_industries_include, ["Software Development"])
        self.assertEqual(f.company_industries_exclude, ["Mining"])
        self.assertEqual(f.company_description_keywords, ["AI"])
        self.assertEqual(f.company_description_keywords_exclude, ["nonprofit"])
        self.assertEqual(f.headline_keywords, ["growth"])
        self.assertEqual(f.about_keywords, ["entrepreneur"])
        self.assertEqual(f.profile_keywords, ["machine learning"])
        self.assertEqual(f.job_description_keywords, ["team lead"])
        self.assertEqual(f.certification_keywords, ["PMP"])
        self.assertEqual(f.school_names, ["MIT"])
        self.assertEqual(f.connection_count, 500)
        self.assertEqual(f.max_connection_count, 5000)
        self.assertEqual(f.follower_count, 100)
        self.assertEqual(f.max_follower_count, 10000)
        self.assertEqual(f.experience_count, 1)
        self.assertEqual(f.max_experience_count, 10)
        self.assertEqual(f.current_role_min_months, 6)
        self.assertEqual(f.current_role_max_months, 24)
        self.assertEqual(f.role_range_start_month, 3)
        self.assertEqual(f.role_range_end_month, 12)
        self.assertEqual(f.languages, ["English", "German"])
        self.assertEqual(f.names, ["Sam", "Alex"])
        self.assertTrue(f.include_past_experiences)

    def test_people_inputs_match_current_clay_shape(self):
        ps = PeopleSearch(ClayClient(workspace_id=WORKSPACE_ID))
        filters = SearchFilters(
            job_title_keywords=["CEO"],
            countries_include=["United States"],
            company_sizes=["501-1,000"],
        )
        inputs = ps.build_inputs(["openai.com"], filters, limit=5, limit_per_company=2)
        self.assertEqual(inputs["start_from_method"], "CsvOfCompanies")
        self.assertEqual(inputs["company_identifier"], ["openai.com"])
        self.assertEqual(inputs["limit"], 5)
        self.assertEqual(inputs["limit_per_company"], 2)
        self.assertEqual(inputs["cluster_count"], 5)
        self.assertEqual(inputs["clustering_method"], "hdbscan")
        self.assertIn("job_title_seniority_levels_v2", inputs)
        self.assertIn("company_annual_revenues", inputs)
        self.assertTrue(inputs["result_count"])

    def test_client_side_limits_are_enforced(self):
        people = [
            Person(full_name="A", company_domain="a.com"),
            Person(full_name="B", company_domain="a.com"),
            Person(full_name="C", company_domain="b.com"),
            Person(full_name="D", company_domain="b.com"),
        ]
        limited = BaseSearch._apply_client_limits(people, limit=3, limit_per_company=1)
        self.assertEqual([p.full_name for p in limited], ["A", "C"])

    def test_output_writers_round_trip(self):
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        people = [
            Person(
                first_name="Ada",
                last_name="Lovelace",
                full_name="Ada Lovelace",
                job_title="Founder",
                location="London, United Kingdom",
                company_domain="example.com",
                linkedin_url="https://linkedin.com/in/ada",
            )
        ]
        csv_path = ARTIFACT_DIR / "unit-output.csv"
        json_path = ARTIFACT_DIR / "unit-output.json"
        db_path = ARTIFACT_DIR / "unit-output.db"
        for path in (csv_path, json_path, db_path):
            if path.exists():
                path.unlink()

        self.assertEqual(write_csv(people, csv_path), 1)
        self.assertEqual(json.loads(write_json(people, json_path))["count"], 1)
        inserted, skipped = write_sqlite(people, db_path)
        self.assertEqual((inserted, skipped), (1, 0))

        with csv_path.open() as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[0]["full_name"], "Ada Lovelace")

        with sqlite3.connect(db_path) as conn:
            count = conn.execute("select count(*) from clay_people").fetchone()[0]
        self.assertEqual(count, 1)


@unittest.skipUnless(LIVE_WORKSPACE_ID, "CLAY_WORKSPACE_ID is required for live Clay tests")
class LiveCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    def test_auth_status(self):
        proc = run_cli("auth", "status")
        assert_success(self, proc)
        self.assertIn("Authenticated", proc.stdout)

    def test_auth_login_alias_verifies_session(self):
        proc = run_cli("auth", "login")
        assert_success(self, proc)
        self.assertIn("Authenticated", proc.stdout)

    def test_preview_mode_json_output(self):
        out = ARTIFACT_DIR / "preview-openai.json"
        proc = run_cli(
            "people",
            "search",
            "--domains",
            "openai.com",
            "--mode",
            "preview",
            "--limit",
            "5",
            "--output",
            "json",
            "-f",
            str(out),
        )
        assert_success(self, proc)
        data = json.loads(out.read_text())
        self.assertEqual(data["count"], 5)
        self.assertTrue(all(p["company_domain"] == "openai.com" for p in data["people"]))

    def test_auto_mode_uses_preview_for_small_limit(self):
        out = ARTIFACT_DIR / "auto-openai.json"
        proc = run_cli(
            "people",
            "search",
            "--domains",
            "openai.com",
            "--mode",
            "auto",
            "--limit",
            "4",
            "--output",
            "json",
            "-f",
            str(out),
        )
        assert_success(self, proc)
        self.assertIn("Preview complete", proc.stderr)
        self.assertEqual(json.loads(out.read_text())["count"], 4)

    def test_full_mode_json_output_cleanup_and_limit(self):
        out = ARTIFACT_DIR / "full-openai.json"
        proc = run_cli(
            "people",
            "search",
            "--domains",
            "openai.com",
            "--mode",
            "full",
            "--limit",
            "3",
            "--output",
            "json",
            "-f",
            str(out),
            "--cleanup",
            timeout=240,
        )
        assert_success(self, proc)
        self.assertIn("Cleaning up", proc.stderr)
        self.assertIn("deleting workbook", proc.stderr)
        self.assertEqual(json.loads(out.read_text())["count"], 3)

    def test_csv_and_domains_file_and_batching(self):
        domains = ARTIFACT_DIR / "domains.csv"
        domains.write_text("domain\nopenai.com\nanthropic.com\n")
        out = ARTIFACT_DIR / "batch.csv"
        proc = run_cli(
            "people",
            "search",
            "--domains-file",
            str(domains),
            "--mode",
            "full",
            "--batch-size",
            "2",
            "--limit-per-company",
            "2",
            "--limit",
            "4",
            "--title-keywords",
            "Engineer",
            "--output",
            "csv",
            "-f",
            str(out),
            "--cleanup",
            timeout=240,
        )
        assert_success(self, proc)
        with out.open() as f:
            rows = list(csv.DictReader(f))
        self.assertLessEqual(len(rows), 4)
        self.assertGreater(len(rows), 0)
        per_domain = {}
        for row in rows:
            per_domain[row["company_domain"]] = per_domain.get(row["company_domain"], 0) + 1
        self.assertTrue(all(v <= 2 for v in per_domain.values()))

    def test_sqlite_output_dedupes(self):
        out = ARTIFACT_DIR / "people.db"
        if out.exists():
            out.unlink()
        proc = run_cli(
            "people",
            "search",
            "--domains",
            "openai.com",
            "--mode",
            "preview",
            "--limit",
            "5",
            "--output",
            "sqlite",
            "-f",
            str(out),
        )
        assert_success(self, proc)
        with sqlite3.connect(out) as conn:
            count = conn.execute("select count(*) from clay_people").fetchone()[0]
        self.assertEqual(count, 5)

    def test_no_domain_broad_search_with_location_and_title_filters(self):
        out = ARTIFACT_DIR / "broad-ceo-germany.json"
        proc = run_cli(
            "people",
            "search",
            "--mode",
            "preview",
            "--limit",
            "3",
            "--title-keywords",
            "CEO",
            "--countries",
            "Germany",
            "--output",
            "json",
            "-f",
            str(out),
        )
        assert_success(self, proc)
        data = json.loads(out.read_text())
        self.assertLessEqual(data["count"], 3)

    def test_filter_families_are_accepted_by_live_api(self):
        out = ARTIFACT_DIR / "filters-accepted.json"
        proc = run_cli(
            "people",
            "search",
            "--mode",
            "preview",
            "--limit",
            "2",
            "--title-keywords",
            "CEO,Founder",
            "--exclude-titles",
            "Assistant,Intern",
            "--title-mode",
            "contain",
            "--seniority",
            "c-suite,owner",
            "--countries",
            "United States",
            "--countries-exclude",
            "China",
            "--states",
            "California",
            "--cities-exclude",
            "Houston",
            "--regions-exclude",
            "APAC",
            "--company-sizes",
            "501-1000,1001-5000",
            "--industries",
            "Software Development",
            "--company-keywords",
            "AI",
            "--headline-keywords",
            "founder",
            "--profile-keywords",
            "startup",
            "--min-connections",
            "1",
            "--max-connections",
            "50000",
            "--min-experience",
            "1",
            "--max-experience",
            "20",
            "--languages",
            "English",
            "--include-past",
            "--output",
            "json",
            "-f",
            str(out),
        )
        assert_success(self, proc)
        self.assertIn("count", json.loads(out.read_text()))

    def test_keyword_expansion_command(self):
        proc = run_cli("keywords", "expand", "--terms", "CEO,Founder", "--output", "json")
        assert_success(self, proc)
        self.assertIsInstance(json.loads(proc.stdout), list)

    def test_keyword_expansion_text_output(self):
        proc = run_cli("keywords", "expand", "--terms", "CEO,Founder", "--output", "text")
        assert_success(self, proc)
        self.assertNotIn("[", proc.stdout)

    def test_quiet_preview_prints_json_to_stdout_without_progress(self):
        proc = run_cli(
            "people",
            "search",
            "--domains",
            "openai.com",
            "--mode",
            "preview",
            "--limit",
            "2",
            "--output",
            "json",
            "--quiet",
        )
        assert_success(self, proc)
        data = json.loads(proc.stdout)
        self.assertEqual(data["count"], 2)
        self.assertEqual(proc.stderr, "")

    def test_table_list_uses_current_resources_fallback(self):
        proc = run_cli("table", "list")
        assert_success(self, proc)
        self.assertIn("wb_", proc.stdout)

    def test_table_info_count_delete_on_created_table(self):
        client = ClayClient(workspace_id=WORKSPACE_ID)
        manager = TableManager(client)
        ps = PeopleSearch(client)
        result = ps.search(
            ["openai.com"],
            filters=SearchFilters(job_title_keywords=["Engineer"]),
            limit=2,
            mode="full",
            cleanup=False,
            on_progress=lambda _: None,
        )
        table_id = result.table_id
        workbook_id = result.workbook_id
        self.assertTrue(table_id)
        self.assertTrue(workbook_id)
        try:
            info = run_cli("table", "info", table_id)
            assert_success(self, info)
            self.assertIn(table_id, info.stdout)

            count = run_cli("table", "count", table_id)
            assert_success(self, count)
            self.assertGreaterEqual(int(count.stdout.strip()), 1)
        finally:
            delete = run_cli("table", "delete", table_id)
            assert_success(self, delete)
            try:
                manager.delete_workbook(workbook_id)
            except ClayAPIError as e:
                if e.status_code != 404:
                    raise

    def test_sdk_cleanup_deletes_generated_workbook(self):
        client = ClayClient(workspace_id=WORKSPACE_ID)
        manager = TableManager(client)
        ps = PeopleSearch(client)
        result = ps.search(
            ["openai.com"],
            filters=SearchFilters(job_title_keywords=["Engineer"]),
            limit=2,
            mode="full",
            cleanup=True,
            on_progress=lambda _: None,
        )
        self.assertTrue(result.workbook_id)
        self.assertTrue(wait_for_workbook_absent(manager, result.workbook_id))


if __name__ == "__main__":
    unittest.main(verbosity=2)
