"""Clay HTTP client — wraps urllib with auth, headers, and retries."""

import json
import time
import urllib.request
import urllib.error

from .auth import SessionManager
from .config import (
    CLAY_API_BASE,
    CLAY_APP_ORIGIN,
    CLAY_APP_REFERER,
    CLAY_FRONTEND_VERSION,
    MAX_RETRIES,
    RETRY_BACKOFF,
    get_workspace_id,
)
from .exceptions import ClayAPIError, ClayAuthError


class ClayClient:
    """HTTP client for Clay API.

    Handles authentication, headers, retries, and JSON serialization.
    All search/table operations use this as the transport layer.
    """

    def __init__(self, session=None, workspace_id=None):
        self.session = session or SessionManager()
        self.workspace_id = workspace_id or get_workspace_id()

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "Cookie": self.session.cookie,
            "Origin": CLAY_APP_ORIGIN,
            "Referer": CLAY_APP_REFERER,
            "x-clay-frontend-version": CLAY_FRONTEND_VERSION,
        }

    def _request(self, method, path, body=None):
        """Make a single HTTP request. Returns parsed JSON."""
        if path.startswith("http"):
            url = path
        else:
            url = f"{CLAY_API_BASE}/{path}"

        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)

        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise ClayAPIError(
                f"HTTP {e.code}: {error_body}",
                status_code=e.code,
                response_body=error_body,
            )

    def request(self, method, path, body=None):
        """Make an HTTP request with auth, retries, and 401 re-login.

        - Ensures session is valid before request
        - Retries on 5xx with exponential backoff
        - On 401, invalidates session, re-auths, retries once
        """
        self.session.ensure_session()

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return self._request(method, path, body)
            except ClayAPIError as e:
                last_error = e

                # 401: try re-auth once
                if e.status_code == 401 and attempt == 0:
                    self.session.invalidate()
                    try:
                        self.session.ensure_session()
                    except ClayAuthError:
                        raise e
                    continue

                # 5xx: retry with backoff
                if e.should_retry and attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)])
                    continue

                raise

        raise last_error

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, body=None):
        return self.request("POST", path, body)

    def delete(self, path):
        return self.request("DELETE", path)
