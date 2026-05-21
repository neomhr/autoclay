"""Generic Clay Companies/People/Jobs source search flow."""

import sys
import time

from ..client import ClayClient
from ..config import ACTION_PACKAGE_ID, DEFAULT_POLL_INTERVAL, DEFAULT_POLL_TIMEOUT
from ..exceptions import ClayAPIError
from ..models import SearchFilters, SearchResult
from ..runs import persist_run_manifest, update_run_manifest
from ..tables.manager import TableManager
from ..tables.records import RecordFetcher


class BaseSearch:
    """Generic CPJ source runner.

    Subclasses provide entity-specific action keys, field metadata, input
    construction, and raw record parsing.
    """

    ENTITY: str = ""
    SOURCE_TYPE: str = ""
    ACTION_KEY: str = ""
    PREVIEW_ACTION_KEY: str = ""
    TABLE_TYPE: str = ""
    FIELD_ID: str = ""
    FIELD_NAME: str = ""
    ICON_TYPE: str = ""
    PREVIEW_TEXT_PATH: str = ""
    DEFAULT_PREVIEW_TEXT: str = ""
    RECORDS_PATH: str = ""
    COUNT_PATH: str = ""
    ID_PATH: str = ""
    BASIC_FIELDS: list = []
    RECORD_CLASS = None

    def __init__(self, client: ClayClient):
        self.client = client

    def search(
        self,
        identifiers=None,
        filters=None,
        limit=None,
        mode="auto",
        cleanup=False,
        wait_timeout=DEFAULT_POLL_TIMEOUT,
        detach=False,
        on_progress=None,
    ):
        """Run a CPJ search and return a SearchResult."""
        identifiers = identifiers or []
        filters = filters or SearchFilters()
        on_progress = on_progress or (lambda msg: print(msg, file=sys.stderr))

        use_preview = self._resolve_mode(mode, limit)
        if use_preview:
            return self._run_preview(identifiers, filters, limit, on_progress)
        return self._full_search(
            identifiers,
            filters,
            limit,
            cleanup,
            wait_timeout,
            detach,
            on_progress,
        )

    @staticmethod
    def _resolve_mode(mode, limit):
        if mode == "preview":
            return True
        if mode == "full":
            return False
        return limit is not None and limit <= 50

    def _preview_search(self, identifiers, filters, limit):
        if limit is not None and limit > 50:
            limit = 50

        body = {
            "workspaceId": self.client.workspace_id,
            "enrichmentType": self.PREVIEW_ACTION_KEY,
            "options": {
                "returnTaskId": True,
                "returnActionMetadata": True,
            },
            "inputs": self.build_inputs(identifiers, filters, limit),
        }

        data = self.client.post("actions/run-cpj-preview-enrichment", body)
        task_id = data.get("taskId")
        result = data.get("result") or {}
        raw_records = result.get(self.RECORDS_PATH, [])
        records = [self.parse_preview_record(record) for record in raw_records]
        count = result.get(self.COUNT_PATH)
        return task_id, records, count

    def _run_preview(self, identifiers, filters, limit, on_progress):
        on_progress(f"Running {self.ENTITY} preview search...")
        _, records, count = self._preview_search(identifiers, filters, limit)
        on_progress(f"Preview complete - {len(records)} results.")
        return SearchResult(
            records=self._apply_client_limit(records, limit),
            total_count=count if isinstance(count, int) else len(records),
            mode="preview",
            entity=self.ENTITY,
        )

    def _full_search(self, identifiers, filters, limit, cleanup, wait_timeout, detach, on_progress):
        on_progress("Step 1/6: Creating conversation...")
        conversation_id = self._create_conversation(filters)

        on_progress("Step 2/6: Running preview for task ID...")
        preview_limit = min(limit, 50) if limit is not None else 50
        task_id, _, _ = self._preview_search(identifiers, filters, preview_limit)

        on_progress("Step 3/6: Creating table...")
        table_meta = self._create_table(identifiers, filters, limit, conversation_id, task_id)
        table_id = table_meta["tableId"]
        view_id = table_meta["viewId"]
        source_id = table_meta["sourceId"]
        workbook_id = table_meta.get("workbookId")
        manifest_path = persist_run_manifest(
            entity=self.ENTITY,
            workspace_id=self.client.workspace_id,
            table_id=table_id,
            view_id=view_id,
            source_id=source_id,
            workbook_id=workbook_id,
            status="pending",
            wait_timeout=wait_timeout,
            detach=detach,
        )
        on_progress("Remote run created:")
        on_progress(f"  Workbook ID: {workbook_id or ''}")
        on_progress(f"  Table ID: {table_id}")
        on_progress(f"  View ID: {view_id}")
        on_progress(f"  Source ID: {source_id}")
        on_progress(f"  Run manifest: {manifest_path}")

        if detach:
            on_progress("Detached. Remote run is still pending in Clay.")
            on_progress("Export when Clay finishes:")
            on_progress(f"  clay-cpj table export {table_id} --entity {self.ENTITY} --output csv")
            return SearchResult(
                records=[],
                total_count=0,
                mode="full",
                entity=self.ENTITY,
                table_id=table_id,
                view_id=view_id,
                source_id=source_id,
                workbook_id=workbook_id,
                run_status="pending",
                manifest_path=str(manifest_path),
            )

        on_progress("Step 4/6: Polling for source run completion...")
        status = self._poll_source(source_id, wait_timeout, on_progress)
        if status != "SUCCESS":
            update_run_manifest(manifest_path, status=status.lower())
            on_progress(f"Remote run still pending after {wait_timeout}s.")
            on_progress("No local output was written yet. Export when Clay finishes:")
            on_progress(f"  clay-cpj table export {table_id} --entity {self.ENTITY} --output csv")
            return SearchResult(
                records=[],
                total_count=0,
                mode="full",
                entity=self.ENTITY,
                table_id=table_id,
                view_id=view_id,
                source_id=source_id,
                workbook_id=workbook_id,
                run_status=status.lower(),
                manifest_path=str(manifest_path),
            )

        on_progress("Step 5/6: Fetching records...")
        fetcher = RecordFetcher(self.client)
        manager = TableManager(self.client)
        raw_records = fetcher.fetch_all(table_id, view_id)
        field_mapping = manager.get_field_mapping(table_id, self.field_name_map())
        records = RecordFetcher.parse_records(raw_records, field_mapping, self.RECORD_CLASS)
        records = self._apply_client_limit(records, limit)
        on_progress(f"Step 6/6: Fetched {len(records)} records.")

        if cleanup:
            on_progress("Cleaning up - deleting table...")
            manager.delete_table(table_id)
            if workbook_id:
                on_progress("Cleaning up - deleting workbook...")
                manager.delete_workbook(workbook_id)

        update_run_manifest(manifest_path, status="success")
        return SearchResult(
            records=records,
            total_count=len(records),
            mode="full",
            entity=self.ENTITY,
            table_id=table_id,
            view_id=view_id,
            source_id=source_id,
            workbook_id=workbook_id,
            run_status="success",
            manifest_path=str(manifest_path),
        )

    @staticmethod
    def _apply_client_limit(records, limit):
        if limit is None:
            return records
        return records[:limit]

    def _create_conversation(self, filters):
        inputs = self.build_inputs([], filters, None)
        now = time.time()
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
                    "createdAt": now,
                    "lastModifiedAt": now,
                },
            },
        }
        resp = self.client.post(
            f"{self.client.workspace_id}/ai-generation/chat-conversation",
            body,
        )
        return resp["conversationId"]

    def _create_table(self, identifiers, filters, limit, conversation_id, task_id):
        body = {
            "workspaceId": self.client.workspace_id,
            "workbookName": self._workbook_name(identifiers),
            "workbookId": None,
            "conversationId": conversation_id,
            "assignedFieldId": self.FIELD_ID,
            "cpjConfig": {
                "type": self.SOURCE_TYPE,
                "typeSettings": {
                    "name": self.FIELD_NAME,
                    "iconType": self.ICON_TYPE,
                    "actionKey": self.ACTION_KEY,
                    "actionPackageId": ACTION_PACKAGE_ID,
                    "previewTextPath": self.PREVIEW_TEXT_PATH,
                    "defaultPreviewText": self.DEFAULT_PREVIEW_TEXT,
                    "recordsPath": self.RECORDS_PATH,
                    "idPath": self.ID_PATH,
                    "scheduleConfig": {"runSettings": "once"},
                    "dedupeOnUniqueIds": True,
                    "hasEvaluatedInputs": True,
                    "inputs": self.build_inputs(identifiers, filters, limit),
                    "previewActionKey": self.PREVIEW_ACTION_KEY,
                },
                "clientSettings": {"tableType": self.TABLE_TYPE},
                "basicFields": self.BASIC_FIELDS,
                "previewActionTaskId": task_id,
            },
        }
        return self.client.post("sources/create-cpj-table", body)

    def _poll_source(self, source_id, wait_timeout, on_progress):
        deadline = time.time() + wait_timeout
        last_status = "PENDING"
        while time.time() < deadline:
            resp = self.client.get(f"sources/{source_id}/runs?limit=1")
            runs = resp.get("runs", [])
            if runs:
                status = runs[0].get("status", "")
                last_status = status or last_status
                if status == "SUCCESS":
                    on_progress("Source run completed successfully.")
                    return status
                if status in ("ERROR", "FAILED"):
                    msg = runs[0].get("message", "Unknown error")
                    raise ClayAPIError(
                        f"Source run failed with status {status}: {msg}",
                        status_code=None,
                        response_body=msg,
                    )
                on_progress(f"  Status: {status} - waiting...")
            time.sleep(DEFAULT_POLL_INTERVAL)

        return last_status

    def field_name_map(self):
        return {field["name"]: field["attr"] for field in self.OUTPUT_FIELDS}

    def build_inputs(self, identifiers, filters, limit):
        raise NotImplementedError

    def parse_preview_record(self, raw):
        raise NotImplementedError

    def _workbook_name(self, identifiers):
        raise NotImplementedError
