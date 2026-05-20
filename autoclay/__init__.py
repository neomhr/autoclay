"""Clay Python SDK — composable API wrapper for Clay's internal API.

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
from .models import CompanyRecord, Person, PersonRecord, JobRecord, SearchFilters, SearchResult, TableInfo, SourceRun
from .search import CompanySearch, PeopleSearch, JobSearch, KeywordExpander
from .tables import TableManager, RecordFetcher
from .auth import SessionManager
from .exceptions import ClayError, ClayAPIError, ClayAuthError, ClayTimeoutError

__all__ = [
    "ClayClient",
    "CompanyRecord",
    "Person",
    "PersonRecord",
    "JobRecord",
    "SearchFilters",
    "SearchResult",
    "TableInfo",
    "SourceRun",
    "CompanySearch",
    "PeopleSearch",
    "JobSearch",
    "KeywordExpander",
    "TableManager",
    "RecordFetcher",
    "SessionManager",
    "ClayError",
    "ClayAPIError",
    "ClayAuthError",
    "ClayTimeoutError",
]
