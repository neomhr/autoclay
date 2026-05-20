"""Table management — list, inspect, delete Clay tables."""

from ..client import ClayClient
from ..exceptions import ClayAPIError
from ..models import TableInfo


# Maps Clay UI column names to our Person dataclass field names.
FIELD_NAME_MAP = {
    "First Name": "first_name",
    "Last Name": "last_name",
    "Full Name": "full_name",
    "Job Title": "job_title",
    "Location": "location",
    "Company Domain": "company_domain",
    "LinkedIn Profile": "linkedin_url",
}


class TableManager:
    """CRUD and schema operations on Clay tables."""

    def __init__(self, client: ClayClient):
        self.client = client

    def list_tables(self) -> list:
        """Return all tables in the workspace as TableInfo objects."""
        try:
            resp = self.client.get(f"tables?workspaceId={self.client.workspace_id}")
        except ClayAPIError as e:
            if e.status_code != 403:
                raise
            return self.list_workbooks()
        tables = []
        for t in resp:
            tables.append(
                TableInfo(
                    table_id=t.get("id", ""),
                    name=t.get("name", ""),
                    record_count=t.get("totalRecordsCount", 0),
                    view_id=t.get("defaultViewId") or t.get("firstViewId", ""),
                    workbook_id=t.get("workbookId", ""),
                )
            )
        return tables

    def list_workbooks(self) -> list:
        """Return visible workbooks when the table list endpoint is forbidden."""
        resp = self.client.post(
            f"workspaces/{self.client.workspace_id}/resources_v2/",
            {
                "parentResource": None,
                "filters": {},
                "isGlobalSearch": False,
            },
        )
        tables = []
        for r in resp.get("resources", []):
            if r.get("resourceType") != "WORKBOOK":
                continue
            tables.append(
                TableInfo(
                    table_id=r.get("id", ""),
                    name=r.get("name", ""),
                    record_count=0,
                    view_id="",
                    workbook_id=r.get("id", ""),
                )
            )
        return tables

    def get_table(self, table_id: str) -> TableInfo:
        """Fetch a single table's metadata."""
        resp = self.client.get(f"tables/{table_id}")
        t = resp["table"]
        return TableInfo(
            table_id=t.get("id", table_id),
            name=t.get("name", ""),
            record_count=t.get("totalRecordsCount", 0),
            view_id=t.get("defaultViewId") or t.get("firstViewId", ""),
            workbook_id=t.get("workbookId", ""),
        )

    def get_record_count(self, table_id: str) -> int:
        """Return the total number of records in a table."""
        resp = self.client.get(f"tables/{table_id}/count")
        return resp["tableTotalRecordsCount"]

    def delete_table(self, table_id: str) -> None:
        """Delete a table by ID."""
        self.client.delete(f"tables/{table_id}")

    def delete_workbook(self, workbook_id: str) -> None:
        """Delete a workbook by ID."""
        self.client.delete(f"workbooks/{workbook_id}")

    def get_field_mapping(self, table_id: str, field_name_map=None) -> dict:
        """Build a mapping of field_id -> our column name for known fields.

        Fetches the table schema, iterates over fields, and maps any Clay
        column name we recognise to the corresponding dataclass attribute name.
        Unknown fields are skipped.
        """
        field_name_map = field_name_map or FIELD_NAME_MAP
        resp = self.client.get(f"tables/{table_id}")
        fields = resp["table"].get("fields", [])
        mapping = {}
        for f in fields:
            clay_name = f.get("name", "")
            if clay_name in field_name_map:
                mapping[f["id"]] = field_name_map[clay_name]
        return mapping
