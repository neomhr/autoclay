"""Abstract base for Clay search modules — encodes the 6-step Sculptor flow."""

import sys
import time

from ..client import ClayClient
from ..config import ACTION_PACKAGE_ID, DEFAULT_POLL_INTERVAL, DEFAULT_POLL_TIMEOUT
from ..exceptions import ClayAPIError, ClayTimeoutError
from ..models import Person, SearchFilters, SearchResult
from ..tables.manager import TableManager
from ..tables.records import RecordFetcher


class BaseSearch:
    """Abstract base encoding the Sculptor search flow.

    Subclasses override class attributes and implement the three abstract
    methods: build_inputs, parse_preview_record, and _workbook_name.
    """

    # -- Subclass overrides ---------------------------------------------------

    SOURCE_TYPE: str = ""
    ACTION_KEY: str = ""
    PREVIEW_ACTION_KEY: str = ""
    TABLE_TYPE: str = ""
    BASIC_FIELDS: list = []

    # -- Construction ---------------------------------------------------------

    def __init__(self, client: ClayClient):
        self.client = client

    # -- Public API -----------------------------------------------------------

    def search(
        self,
        identifiers,
        filters=None,
        limit=None,
        limit_per_company=None,
        mode="auto",
        cleanup=False,
        on_progress=None,
    ):
        """Run a search and return a SearchResult.

        Args:
            identifiers: List of search identifiers (e.g. company domains).
            filters: Optional SearchFilters dataclass.
            limit: Total max results across all companies (None = API default).
            limit_per_company: Max results per company (None = no per-company cap).
            mode: "auto" (preview if limit <= 50, else full), "preview", or "full".
            cleanup: If True, delete the table after fetching records (full mode only).
            on_progress: Optional callable(str) for progress messages.
                         Defaults to printing to stderr.

        Returns:
            SearchResult with people, total_count, mode, and optional table metadata.
        """
        if filters is None:
            filters = SearchFilters()
        if on_progress is None:
            on_progress = lambda msg: print(msg, file=sys.stderr)

        use_preview = self._resolve_mode(mode, limit)

        if use_preview:
            return self._run_preview(identifiers, filters, limit, limit_per_company, on_progress)
        return self._full_search(identifiers, filters, limit, limit_per_company, cleanup, on_progress)

    # -- Mode resolution ------------------------------------------------------

    @staticmethod
    def _resolve_mode(mode, limit):
        """Return True if preview mode should be used."""
        if mode == "preview":
            return True
        if mode == "full":
            return False
        # auto: preview when limit fits
        return limit is not None and limit <= 50

    # -- Preview flow ---------------------------------------------------------

    def _preview_search(self, identifiers, filters, limit, limit_per_company=None):
        """Execute a synchronous preview search.

        Returns:
            (task_id, list_of_Person)
        """
        if limit is not None and limit > 50:
            limit = 50

        body = {
            "workspaceId": self.client.workspace_id,
            "enrichmentType": self.PREVIEW_ACTION_KEY,
            "options": {
                "returnTaskId": True,
                "returnActionMetadata": True,
            },
            "inputs": self.build_inputs(identifiers, filters, limit, limit_per_company),
        }

        data = self.client.post("actions/run-cpj-preview-enrichment", body)
        task_id = data.get("taskId")
        result = data.get("result") or {}
        raw_people = result.get("people", [])
        people = [self.parse_preview_record(p) for p in raw_people]
        return task_id, people

    def _run_preview(self, identifiers, filters, limit, limit_per_company, on_progress):
        """Run preview and wrap into SearchResult."""
        on_progress("Running preview search...")
        _, people = self._preview_search(identifiers, filters, limit, limit_per_company)
        on_progress(f"Preview complete — {len(people)} results.")
        return SearchResult(
            people=people,
            total_count=len(people),
            mode="preview",
        )

    # -- Full table flow ------------------------------------------------------

    def _full_search(self, identifiers, filters, limit, limit_per_company, cleanup, on_progress):
        """Execute the full 6-step Sculptor flow.

        1. Create conversation
        2. Run preview (for taskId)
        3. Create table
        4. Poll until source run completes
        5-6. Fetch records, parse, return
        """
        # Step 1: Create conversation
        on_progress("Step 1/6: Creating conversation...")
        conversation_id = self._create_conversation()

        # Step 2: Run preview for taskId
        on_progress("Step 2/6: Running preview for task ID...")
        preview_limit = min(limit, 50) if limit is not None else 50
        task_id, _ = self._preview_search(identifiers, filters, preview_limit, limit_per_company)

        # Step 3: Create table
        on_progress("Step 3/6: Creating table...")
        table_meta = self._create_table(
            identifiers, filters, limit, limit_per_company, conversation_id, task_id
        )
        table_id = table_meta["tableId"]
        view_id = table_meta["viewId"]
        source_id = table_meta["sourceId"]
        workbook_id = table_meta.get("workbookId")

        # Step 4: Poll for completion
        on_progress("Step 4/6: Polling for source run completion...")
        self._poll_source(source_id, on_progress)

        # Step 5-6: Fetch and parse records
        on_progress("Step 5/6: Fetching records...")
        fetcher = RecordFetcher(self.client)
        manager = TableManager(self.client)

        raw_records = fetcher.fetch_all(table_id, view_id)
        field_mapping = manager.get_field_mapping(table_id)
        people = RecordFetcher.parse_records(raw_records, field_mapping)
        people = self._apply_client_limits(people, limit, limit_per_company)
        total_count = len(people)

        on_progress(f"Step 6/6: Fetched {total_count} records.")

        # Cleanup if requested
        if cleanup:
            on_progress("Cleaning up — deleting table...")
            manager.delete_table(table_id)
            if workbook_id:
                on_progress("Cleaning up — deleting workbook...")
                manager.delete_workbook(workbook_id)

        return SearchResult(
            people=people,
            total_count=total_count,
            mode="full",
            table_id=table_id,
            source_id=source_id,
            workbook_id=workbook_id,
        )

    @staticmethod
    def _apply_client_limits(people, limit, limit_per_company):
        """Apply CLI limits after fetch as a guard against API limit drift."""
        if limit_per_company is not None:
            per_company_counts = {}
            limited = []
            for person in people:
                key = (person.company_domain or "").lower()
                current = per_company_counts.get(key, 0)
                if current >= limit_per_company:
                    continue
                per_company_counts[key] = current + 1
                limited.append(person)
            people = limited

        if limit is not None:
            people = people[:limit]

        return people

    def _create_conversation(self):
        """Step 1: Create an AI onboarding conversation."""
        inputs = self.build_inputs([], SearchFilters(), None)
        body = {
            "conversationType": "ai_onboarding",
            "initialSourceState": {
                "sourceType": self.SOURCE_TYPE,
                "sourceConfig": {
                    "type": "search",
                    "entityType": self.SOURCE_TYPE,
                    "mode": "filters",
                    "filters": inputs,
                    "additionalRequirements": [],
                    "originalQuery": "",
                    "createdAt": time.time(),
                    "lastModifiedAt": time.time(),
                },
            },
        }
        resp = self.client.post(
            f"{self.client.workspace_id}/ai-generation/chat-conversation",
            body,
        )
        return resp["conversationId"]

    def _create_table(self, identifiers, filters, limit, limit_per_company, conversation_id, task_id):
        """Step 3: Create a CPJ table from the search spec."""
        body = {
            "workspaceId": self.client.workspace_id,
            "workbookName": self._workbook_name(identifiers),
            "workbookId": None,
            "conversationId": conversation_id,
            "assignedFieldId": "f_people_search",
            "cpjConfig": {
                "type": self.SOURCE_TYPE,
                "typeSettings": {
                    "name": "Find people",
                    "iconType": "User",
                    "actionKey": self.ACTION_KEY,
                    "actionPackageId": ACTION_PACKAGE_ID,
                    "previewTextPath": "name",
                    "defaultPreviewText": "Clay Profile",
                    "recordsPath": "people",
                    "idPath": "profile_id",
                    "scheduleConfig": {"runSettings": "once"},
                    "dedupeOnUniqueIds": True,
                    "hasEvaluatedInputs": True,
                    "inputs": self.build_inputs(identifiers, filters, limit, limit_per_company),
                    "previewActionKey": self.PREVIEW_ACTION_KEY,
                },
                "clientSettings": {"tableType": self.TABLE_TYPE},
                "basicFields": self.BASIC_FIELDS,
                "previewActionTaskId": task_id,
            },
        }
        return self.client.post("sources/create-cpj-table", body)

    def _poll_source(self, source_id, on_progress):
        """Step 4: Poll source runs until SUCCESS, ERROR, or timeout."""
        deadline = time.time() + DEFAULT_POLL_TIMEOUT
        while time.time() < deadline:
            resp = self.client.get(f"sources/{source_id}/runs?limit=1")
            runs = resp.get("runs", [])
            if runs:
                status = runs[0].get("status", "")
                if status == "SUCCESS":
                    on_progress("Source run completed successfully.")
                    return
                if status in ("ERROR", "FAILED"):
                    msg = runs[0].get("message", "Unknown error")
                    raise ClayAPIError(
                        f"Source run failed with status {status}: {msg}",
                        status_code=None,
                        response_body=msg,
                    )
                on_progress(f"  Status: {status} — waiting...")
            time.sleep(DEFAULT_POLL_INTERVAL)

        raise ClayTimeoutError(
            f"Source run did not complete within {DEFAULT_POLL_TIMEOUT}s"
        )

    # -- Abstract methods (subclass must implement) ---------------------------

    def build_inputs(self, identifiers, filters, limit, limit_per_company=None):
        """Build the API inputs dict for this search type.

        Args:
            identifiers: List of search identifiers.
            filters: SearchFilters dataclass.
            limit: Total max results, or None.
            limit_per_company: Max results per company, or None.

        Returns:
            dict suitable for the Clay API inputs field.
        """
        raise NotImplementedError

    def parse_preview_record(self, raw):
        """Parse a single raw preview result dict into a Person.

        Args:
            raw: Dict from the preview API response.

        Returns:
            Person instance.
        """
        raise NotImplementedError

    def _workbook_name(self, identifiers):
        """Generate a human-readable workbook name.

        Args:
            identifiers: List of search identifiers.

        Returns:
            str workbook name.
        """
        raise NotImplementedError
