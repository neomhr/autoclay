"""Clay CPL CLI Companies/People/Jobs regression tests."""

import csv
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from clay_cpl.cli import _build_filters, _parse_company_sizes, build_parser
from clay_cpl.models import CompanyRecord, JobRecord, PersonRecord
from clay_cpl.output import write_csv, write_json, write_sqlite
from clay_cpl.search import CompanySearch, JobSearch, PeopleSearch


ROOT = Path(__file__).resolve().parents[1]
LIVE_WORKSPACE_ID = os.environ.get("CLAY_WORKSPACE_ID")


def run_cli(*args, timeout=180):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    cmd = [sys.executable, "-m", "clay_cpl", *args]
    return subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


class UnitTests(unittest.TestCase):
    def test_commands_are_wired(self):
        parser, _ = build_parser()
        self.assertEqual(parser.prog, "clay-cpl")
        for command in ("companies", "people", "jobs"):
            args = parser.parse_args([command, "search", "--mode", "preview", "--limit", "1"])
            self.assertEqual(args.entity, command)

    def test_company_size_parser_keeps_backward_compatibility(self):
        self.assertEqual(
            _parse_company_sizes("501-1000,1001-5000,5001-10000,10001+"),
            ["501-1,000", "1,001-5,000", "5,001-10,000", "10,001+"],
        )

    def test_people_aliases_and_current_fields_map_to_filters(self):
        parser, _ = build_parser()
        args = parser.parse_args([
            "people", "search",
            "--domains", "openai.com",
            "--title-keywords", "CEO",
            "--job-title-seniority-levels-v2", "owner,executive",
            "--job-title-include-past-experiences", "true",
            "--job-description-include-past-experiences", "true",
            "--limit-per-company", "2",
        ])
        filters = _build_filters(args, "people")
        self.assertEqual(filters.company_identifier, ["openai.com"])
        self.assertEqual(filters.job_title_keywords, ["CEO"])
        self.assertEqual(filters.seniority_levels_v2, ["owner", "executive"])
        self.assertTrue(filters.job_title_include_past_experiences)
        self.assertTrue(filters.job_description_include_past_experiences)
        self.assertEqual(filters.limit_per_company, 2)

    def test_raw_inputs_take_precedence(self):
        parser, _ = build_parser()
        raw = {"company_identifier": ["example.com"], "job_title_keywords": ["CTO"]}
        args = parser.parse_args([
            "people", "search",
            "--inputs-json", json.dumps(raw),
            "--domains", "openai.com",
            "--title-keywords", "CEO",
        ])
        filters = _build_filters(args, "people")
        self.assertEqual(filters.raw_inputs, raw)
        self.assertEqual(PeopleSearch(None).build_inputs(["openai.com"], filters, 1), raw)

    def test_entity_build_inputs_include_current_schema_fields(self):
        people_inputs = PeopleSearch(None).build_inputs(["openai.com"], _build_filters(build_parser()[0].parse_args(["people", "search"]), "people"), 5)
        self.assertIn("job_title_include_past_experiences", people_inputs)
        self.assertIn("job_title_seniority_levels_v2", people_inputs)
        self.assertIn("job_description_include_past_experiences", people_inputs)
        self.assertEqual(people_inputs["limit"], 5)

        company_inputs = CompanySearch(None).build_inputs([], _build_filters(build_parser()[0].parse_args(["companies", "search"]), "companies"), 5)
        self.assertIn("startFromCompanyType", company_inputs)
        self.assertIn("technographics_vendors", company_inputs)
        self.assertEqual(company_inputs["limit"], 5)

        job_inputs = JobSearch(None).build_inputs(["openai.com"], _build_filters(build_parser()[0].parse_args(["jobs", "search"]), "jobs"), 5)
        self.assertEqual(job_inputs["startFrom"], "CsvOfCompanies")
        self.assertFalse(job_inputs["has_recruiter"])
        self.assertEqual(job_inputs["limit"], 5)

    def test_output_writers_are_entity_shaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            records = {
                "companies": [CompanyRecord(name="OpenAI", domain="openai.com")],
                "people": [PersonRecord(full_name="Ada", linkedin_url="https://linkedin.com/in/ada")],
                "jobs": [JobRecord(title="Engineer", url="https://linkedin.com/jobs/view/1")],
            }
            for entity, rows in records.items():
                csv_path = tmp / f"{entity}.csv"
                json_path = tmp / f"{entity}.json"
                db_path = tmp / f"{entity}.db"
                self.assertEqual(write_csv(rows, csv_path, entity=entity), 1)
                self.assertEqual(json.loads(write_json(rows, json_path, entity=entity))[entity][0], rows[0].to_dict())
                inserted, skipped = write_sqlite(rows, db_path, entity=entity)
                self.assertEqual((inserted, skipped), (1, 0))
                with csv_path.open() as f:
                    self.assertEqual(len(list(csv.DictReader(f))), 1)
                conn = sqlite3.connect(db_path)
                try:
                    self.assertEqual(conn.execute(f"select count(*) from clay_{entity}").fetchone()[0], 1)
                finally:
                    conn.close()


@unittest.skipUnless(LIVE_WORKSPACE_ID, "CLAY_WORKSPACE_ID is required for live Clay tests")
class LivePreviewTests(unittest.TestCase):
    def test_people_preview_json_stdout(self):
        proc = run_cli("people", "search", "--domains", "openai.com", "--mode", "preview", "--limit", "1", "--output", "json", "--quiet")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["count"], 1)

    def test_companies_preview_json_stdout(self):
        proc = run_cli("companies", "search", "--countries", "United States", "--industries", "Software Development", "--mode", "preview", "--limit", "1", "--output", "json", "--quiet")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["count"], 1)

    def test_jobs_preview_json_stdout(self):
        proc = run_cli("jobs", "search", "--domains", "openai.com", "--title-keywords", "Engineer", "--mode", "preview", "--limit", "1", "--output", "json", "--quiet")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["count"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
