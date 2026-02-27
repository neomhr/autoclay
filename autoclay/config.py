"""Clay SDK configuration — constants, env var loading, defaults."""

import os

# API
CLAY_API_BASE = "https://api.clay.com/v3"
CLAY_APP_ORIGIN = "https://app.clay.com"
CLAY_APP_REFERER = "https://app.clay.com/"
CLAY_FRONTEND_VERSION = "v20260226_193559Z_fc7e8d7d1f"

# Workspace
DEFAULT_WORKSPACE_ID = None

# People search
ACTION_PACKAGE_ID = "e251a70e-46d7-4f3a-b3ef-a211ad3d8bd2"
ACTION_KEY = "find-lists-of-people-with-mixrank-source"
PREVIEW_ACTION_KEY = "find-lists-of-people-with-mixrank-source-preview"

# Limits
PREVIEW_MAX_RESULTS = 50
DEFAULT_POLL_TIMEOUT = 120
DEFAULT_POLL_INTERVAL = 2
BULK_FETCH_BATCH_SIZE = 200

# Retry
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]  # seconds

# Auth
SESSION_COOKIE_MAX_AGE_HOURS = 23


def get_workspace_id():
    ws_id = os.environ.get("CLAY_WORKSPACE_ID") or DEFAULT_WORKSPACE_ID
    if not ws_id:
        raise RuntimeError(
            "CLAY_WORKSPACE_ID is not set. "
            "Set it via environment variable or .env file."
        )
    return ws_id


def get_session_cookie():
    """Get raw session cookie from env, or None."""
    return os.environ.get("CLAY_SESSION_COOKIE")


def get_credentials():
    """Get email/password credentials from env, or (None, None)."""
    return (
        os.environ.get("CLAY_EMAIL"),
        os.environ.get("CLAY_PASSWORD"),
    )
