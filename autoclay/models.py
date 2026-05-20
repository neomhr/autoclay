"""Data models for Clay SDK."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Person:
    """A person record from Clay."""

    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    job_title: str = ""
    location: str = ""
    company_domain: str = ""
    linkedin_url: str = ""

    def to_dict(self):
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "job_title": self.job_title,
            "location": self.location,
            "company_domain": self.company_domain,
            "linkedin_url": self.linkedin_url,
        }

    @classmethod
    def field_names(cls):
        return ["first_name", "last_name", "full_name", "job_title", "location", "company_domain", "linkedin_url"]


@dataclass
class SearchFilters:
    """Filters for people search."""

    seniority_levels: List[str] = field(default_factory=list)
    job_functions: List[str] = field(default_factory=list)
    job_title_keywords: List[str] = field(default_factory=list)
    job_title_exclude_keywords: List[str] = field(default_factory=list)
    job_title_mode: str = "smart"
    countries_include: List[str] = field(default_factory=list)
    countries_exclude: List[str] = field(default_factory=list)
    states_include: List[str] = field(default_factory=list)
    states_exclude: List[str] = field(default_factory=list)
    cities_include: List[str] = field(default_factory=list)
    cities_exclude: List[str] = field(default_factory=list)
    regions_include: List[str] = field(default_factory=list)
    regions_exclude: List[str] = field(default_factory=list)
    company_sizes: List[str] = field(default_factory=list)
    company_industries_include: List[str] = field(default_factory=list)
    company_industries_exclude: List[str] = field(default_factory=list)
    company_description_keywords: List[str] = field(default_factory=list)
    company_description_keywords_exclude: List[str] = field(default_factory=list)
    include_past_experiences: bool = False
    headline_keywords: List[str] = field(default_factory=list)
    about_keywords: List[str] = field(default_factory=list)
    profile_keywords: List[str] = field(default_factory=list)
    job_description_keywords: List[str] = field(default_factory=list)
    certification_keywords: List[str] = field(default_factory=list)
    school_names: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    names: List[str] = field(default_factory=list)
    connection_count: Optional[int] = None
    max_connection_count: Optional[int] = None
    follower_count: Optional[int] = None
    max_follower_count: Optional[int] = None
    experience_count: Optional[int] = None
    max_experience_count: Optional[int] = None
    current_role_min_months: Optional[int] = None
    current_role_max_months: Optional[int] = None
    role_range_start_month: Optional[int] = None
    role_range_end_month: Optional[int] = None
    job_title_exact_match: Optional[bool] = None
    job_title_exact_keyword_match: Optional[bool] = None
    search_raw_location: bool = False


@dataclass
class SearchResult:
    """Result of a people search."""

    people: List[Person]
    total_count: int
    mode: str  # "preview" or "full"
    table_id: Optional[str] = None
    source_id: Optional[str] = None
    workbook_id: Optional[str] = None


@dataclass
class TableInfo:
    """Metadata about a Clay table."""

    table_id: str
    name: str = ""
    record_count: int = 0
    view_id: str = ""
    workbook_id: str = ""


@dataclass
class SourceRun:
    """Status of a source enrichment run."""

    run_id: str
    status: str  # QUEUED, RUNNING, SUCCESS, FAILED
    rows_added: int = 0
    message: str = ""
