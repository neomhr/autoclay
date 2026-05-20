"""Clay CPL CLI configuration."""

import json
import os
from pathlib import Path


CLAY_API_BASE = "https://api.clay.com/v3"
CLAY_APP_ORIGIN = "https://app.clay.com"
CLAY_APP_REFERER = "https://app.clay.com/"
CLAY_FRONTEND_VERSION = "v20260518_222738Z_bc4ef1d5e6"

ACTION_PACKAGE_ID = "e251a70e-46d7-4f3a-b3ef-a211ad3d8bd2"

PREVIEW_MAX_RESULTS = 50
DEFAULT_POLL_TIMEOUT = 120
DEFAULT_POLL_INTERVAL = 2
BULK_FETCH_BATCH_SIZE = 200

MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]
SESSION_COOKIE_MAX_AGE_HOURS = 23

CLAY_CPL_DIR = Path.home() / ".clay-cpl"
CREDENTIALS_FILE = CLAY_CPL_DIR / "credentials.json"
SESSION_FILE = CLAY_CPL_DIR / "session.json"


def ensure_clay_cpl_dir():
    CLAY_CPL_DIR.mkdir(mode=0o700, exist_ok=True)


def _load_credentials_file():
    if not CREDENTIALS_FILE.exists():
        return {}
    try:
        return json.loads(CREDENTIALS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_credentials(email, password, workspace_id):
    ensure_clay_cpl_dir()
    CREDENTIALS_FILE.write_text(
        json.dumps({"email": email, "password": password, "workspace_id": workspace_id}, indent=2) + "\n"
    )
    CREDENTIALS_FILE.chmod(0o600)


def get_workspace_id():
    workspace_id = os.environ.get("CLAY_WORKSPACE_ID") or _load_credentials_file().get("workspace_id")
    if not workspace_id:
        raise RuntimeError(
            "CLAY_WORKSPACE_ID is not set. Run 'clay-cpl setup' or set the environment variable."
        )
    return str(workspace_id)


def get_session_cookie():
    return os.environ.get("CLAY_SESSION_COOKIE")


def get_credentials():
    email = os.environ.get("CLAY_EMAIL")
    password = os.environ.get("CLAY_PASSWORD")
    if email and password:
        return email, password
    creds = _load_credentials_file()
    return creds.get("email"), creds.get("password")
