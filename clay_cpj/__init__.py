"""Internal Python API for the Clay CPJ CLI.

Usage (programmatic):
    from clay_cpj import ClayClient, PeopleSearch, SearchFilters

    client = ClayClient()
    ps = PeopleSearch(client)
    result = ps.search(["acme.com"], filters=SearchFilters(seniority_levels=["vp"]))

Usage (CLI):
    clay-cpj people search --domains acme.com
    clay-cpj table list
    clay-cpj auth login
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
