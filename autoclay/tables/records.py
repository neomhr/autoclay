"""Record fetching — bulk retrieval and parsing of Clay table rows."""

import time

from ..client import ClayClient
from ..config import BULK_FETCH_BATCH_SIZE
from ..models import Person


class RecordFetcher:
    """Fetch, batch-load, and parse records from a Clay table."""

    def __init__(self, client: ClayClient):
        self.client = client

    def get_record_ids(self, table_id: str, view_id: str) -> list:
        """Return all record IDs for a table view."""
        resp = self.client.get(
            f"tables/{table_id}/views/{view_id}/records/ids"
        )
        return resp["results"]

    def bulk_fetch(self, table_id: str, record_ids: list) -> list:
        """Fetch raw records in batches of BULK_FETCH_BATCH_SIZE.

        Sleeps 0.1s between batches to stay under rate limits.
        Returns a flat list of raw record dicts.
        """
        all_records = []
        for i in range(0, len(record_ids), BULK_FETCH_BATCH_SIZE):
            batch = record_ids[i : i + BULK_FETCH_BATCH_SIZE]
            resp = self.client.post(
                f"tables/{table_id}/bulk-fetch-records",
                {
                    "recordIds": batch,
                    "includeExternalContentFieldIds": [],
                },
            )
            all_records.extend(resp.get("results", []))
            # Rate-limit courtesy pause between batches.
            if i + BULK_FETCH_BATCH_SIZE < len(record_ids):
                time.sleep(0.1)
        return all_records

    def fetch_all(self, table_id: str, view_id: str) -> list:
        """Convenience: get all record IDs then bulk-fetch them."""
        ids = self.get_record_ids(table_id, view_id)
        return self.bulk_fetch(table_id, ids)

    @staticmethod
    def parse_records(raw_records: list, field_mapping: dict) -> list:
        """Convert raw API records into Person dataclass instances.

        Args:
            raw_records: List of record dicts from bulk_fetch.
            field_mapping: Dict of field_id -> Person attribute name
                           (produced by TableManager.get_field_mapping).

        Returns:
            List of Person objects with mapped fields populated.
        """
        people = []
        for record in raw_records:
            cells = record.get("cells", {})
            kwargs = {}
            for field_id, col_name in field_mapping.items():
                cell = cells.get(field_id)
                if cell is not None:
                    kwargs[col_name] = cell.get("value", "")
            people.append(Person(**kwargs))
        return people
