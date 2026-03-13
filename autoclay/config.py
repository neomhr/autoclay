"""Clay SDK configuration — constants, env var loading, defaults."""

import json
import os
from pathlib import Path

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

# Paths
AUTOCLAY_DIR = Path.home() / ".autoclay"
CREDENTIALS_FILE = AUTOCLAY_DIR / "credentials.json"
SESSION_FILE = AUTOCLAY_DIR / "session.json"


def ensure_autoclay_dir():
    """Create ~/.autoclay/ with restricted permissions if it doesn't exist."""
    AUTOCLAY_DIR.mkdir(mode=0o700, exist_ok=True)


def _load_credentials_file():
    """Load credentials from ~/.autoclay/credentials.json, or empty dict."""
    if CREDENTIALS_FILE.exists():
        try:
            return json.loads(CREDENTIALS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_credentials(email, password, workspace_id):
    """Write credentials to ~/.autoclay/credentials.json with 0600 permissions."""
    ensure_autoclay_dir()
    data = {"email": email, "password": password, "workspace_id": workspace_id}
    CREDENTIALS_FILE.write_text(json.dumps(data, indent=2) + "\n")
    CREDENTIALS_FILE.chmod(0o600)


def get_workspace_id():
    """Get workspace ID. Env var overrides file."""
    ws_id = os.environ.get("CLAY_WORKSPACE_ID")
    if not ws_id:
        ws_id = _load_credentials_file().get("workspace_id")
    if not ws_id:
        raise RuntimeError(
            "CLAY_WORKSPACE_ID is not set. "
            "Run 'clay setup' or set the CLAY_WORKSPACE_ID environment variable."
        )
    return ws_id


def get_session_cookie():
    """Get raw session cookie from env, or None."""
    return os.environ.get("CLAY_SESSION_COOKIE")


def get_credentials():
    """Get email/password. Env vars override file."""
    email = os.environ.get("CLAY_EMAIL")
    password = os.environ.get("CLAY_PASSWORD")
    if email and password:
        return email, password
    creds = _load_credentials_file()
    return creds.get("email"), creds.get("password")
