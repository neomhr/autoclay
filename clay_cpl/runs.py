"""Local CPJ run manifests for resumable full-mode exports."""

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import RUNS_DIR


def _now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def persist_run_manifest(
    *,
    entity,
    workspace_id,
    table_id,
    view_id,
    source_id,
    workbook_id=None,
    status="pending",
    wait_timeout=None,
    detach=False,
    path=None,
):
    """Write a local non-secret manifest for a remote Clay CPJ run."""
    RUNS_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    created_at = _now_iso()
    manifest = {
        "version": 1,
        "entity": entity,
        "workspace_id": str(workspace_id),
        "workbook_id": workbook_id or "",
        "table_id": table_id,
        "view_id": view_id,
        "source_id": source_id,
        "status": status,
        "detach": bool(detach),
        "wait_timeout": wait_timeout,
        "created_at": created_at,
        "updated_at": created_at,
    }
    if path is None:
        safe_entity = entity.replace("/", "-")
        path = RUNS_DIR / f"{created_at.replace(':', '').replace('.', '')}-{safe_entity}-{table_id}.json"
    else:
        path = Path(path)
        if path.exists():
            try:
                existing = json.loads(path.read_text())
                manifest["created_at"] = existing.get("created_at", manifest["created_at"])
            except (OSError, json.JSONDecodeError):
                pass
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    path.chmod(0o600)
    return path


def update_run_manifest(path, **updates):
    """Update a local run manifest in place."""
    if not path:
        return None
    path = Path(path)
    try:
        manifest = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    manifest.update(updates)
    manifest["updated_at"] = _now_iso()
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    path.chmod(0o600)
    return path


def find_run_manifest_by_table_id(table_id):
    """Return the newest manifest path for a Clay table id, if present."""
    if not RUNS_DIR.exists():
        return None
    matches = sorted(RUNS_DIR.glob(f"*-{table_id}.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None
