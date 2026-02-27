"""Clay session management — email/password login with cookie caching.

Auth flow ported from clay-mcp: POST /v3/auth/login with email/password,
parse Set-Cookie for claysession, cache with 23-hour expiry.

Fallback: CLAY_SESSION_COOKIE env var for manual override.
"""

import json
import sys
import time
import urllib.request
import urllib.error

from .config import (
    CLAY_API_BASE,
    SESSION_COOKIE_MAX_AGE_HOURS,
    get_credentials,
    get_session_cookie,
)
from .exceptions import ClayAuthError


class SessionManager:
    """Manages Clay session authentication."""

    def __init__(self):
        self._cookie = None
        self._expiry = 0  # unix timestamp

    @property
    def cookie(self):
        """Get current cookie string (e.g. 'claysession=...')."""
        return self._cookie

    @property
    def is_expired(self):
        return time.time() >= self._expiry

    @property
    def is_authenticated(self):
        return self._cookie is not None and not self.is_expired

    def ensure_session(self):
        """Ensure we have a valid session. Re-auth if expired.

        Priority:
        1. Cached cookie that hasn't expired
        2. Login with CLAY_EMAIL + CLAY_PASSWORD
        3. CLAY_SESSION_COOKIE env var (manual override)
        """
        if self.is_authenticated:
            return

        # Try email/password login
        email, password = get_credentials()
        if email and password:
            self.login(email, password)
            return

        # Fallback to env cookie
        raw = get_session_cookie()
        if raw:
            if not raw.startswith("claysession="):
                raw = f"claysession={raw}"
            self._cookie = raw
            # Manual cookies get 23-hour expiry from now
            self._expiry = time.time() + SESSION_COOKIE_MAX_AGE_HOURS * 3600
            return

        raise ClayAuthError(
            "No auth configured. Set CLAY_EMAIL + CLAY_PASSWORD, "
            "or CLAY_SESSION_COOKIE as fallback."
        )

    def login(self, email, password):
        """Login via POST /v3/auth/login and extract claysession cookie."""
        url = f"{CLAY_API_BASE}/auth/login"
        payload = json.dumps({
            "email": email,
            "password": password,
            "source": None,
        }).encode()

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req) as resp:
                # Extract claysession from Set-Cookie headers
                cookie_value = None
                for header_name, header_value in resp.headers.items():
                    if header_name.lower() == "set-cookie":
                        if "claysession=" in header_value:
                            # Parse "claysession=VALUE; Path=/; ..."
                            parts = header_value.split(";")
                            for part in parts:
                                part = part.strip()
                                if part.startswith("claysession="):
                                    cookie_value = part
                                    break

                if not cookie_value:
                    raise ClayAuthError(
                        "Login succeeded but no claysession cookie in response."
                    )

                self._cookie = cookie_value
                self._expiry = time.time() + SESSION_COOKIE_MAX_AGE_HOURS * 3600
                return True

        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if e.code == 401:
                raise ClayAuthError(f"Invalid credentials: {body}")
            raise ClayAuthError(f"Login failed ({e.code}): {body}")

    def invalidate(self):
        """Force re-auth on next ensure_session() call."""
        self._expiry = 0

    def status(self):
        """Return human-readable status dict."""
        if not self._cookie:
            return {"authenticated": False, "method": None}

        remaining = max(0, self._expiry - time.time())
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)

        email, _ = get_credentials()
        method = "email/password" if email else "env cookie"

        return {
            "authenticated": not self.is_expired,
            "method": method,
            "expires_in": f"{hours}h {minutes}m",
        }

    def print_status(self, file=sys.stderr):
        """Print auth status to stderr."""
        s = self.status()
        if s["authenticated"]:
            print(f"Authenticated via {s['method']} (expires in {s['expires_in']})", file=file)
        else:
            print("Not authenticated", file=file)
