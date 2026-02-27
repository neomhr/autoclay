"""autoclay — Python SDK and CLI for Clay's People Search API.

Usage (programmatic):
    from autoclay import ClayClient, PeopleSearch, SearchFilters

    client = ClayClient()
    ps = PeopleSearch(client)
    result = ps.search(["acme.com"], filters=SearchFilters(seniority_levels=["vp"]))

Usage (CLI):
    clay people search --domains acme.com
    clay table list
    clay auth login
"""

from .client import ClayClient
from .models import Person, SearchFilters, SearchResult, TableInfo, SourceRun
from .search import PeopleSearch, KeywordExpander
from .tables import TableManager, RecordFetcher
from .auth import SessionManager
from .exceptions import ClayError, ClayAPIError, ClayAuthError, ClayTimeoutError

__all__ = [
    "ClayClient",
    "Person",
    "SearchFilters",
    "SearchResult",
    "TableInfo",
    "SourceRun",
    "PeopleSearch",
    "KeywordExpander",
    "TableManager",
    "RecordFetcher",
    "SessionManager",
    "ClayError",
    "ClayAPIError",
    "ClayAuthError",
    "ClayTimeoutError",
]
