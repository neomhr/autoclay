"""Data models for Clay CPL CLI."""

from dataclasses import dataclass, field
from typing import Any, Generic, List, Optional, TypeVar


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    if isinstance(value, dict):
        return "; ".join(f"{k}: {v}" for k, v in value.items())
    return str(value)


@dataclass
class ClayRecord:
    """Base class for output records."""

    source_company_table_id: str = ""
    source_company_domain: str = ""

    @classmethod
    def field_names(cls) -> List[str]:
        return list(cls.__dataclass_fields__.keys())

    def to_dict(self):
        return {name: getattr(self, name) for name in self.field_names()}


@dataclass
class CompanyRecord(ClayRecord):
    """A company record from Clay."""

    name: str = ""
    description: str = ""
    company_type: str = ""
    size: str = ""
    country: str = ""
    location: str = ""
    founded: str = ""
    domain: str = ""
    website: str = ""
    employee_count: str = ""
    follower_count: str = ""
    primary_industry: str = ""
    industries: str = ""
    specialties: str = ""
    linkedin_url: str = ""
    clay_company_id: str = ""

    @classmethod
    def field_names(cls) -> List[str]:
        return [
            "name",
            "description",
            "company_type",
            "size",
            "country",
            "location",
            "founded",
            "domain",
            "website",
            "employee_count",
            "follower_count",
            "primary_industry",
            "industries",
            "specialties",
            "linkedin_url",
            "clay_company_id",
            "source_company_table_id",
            "source_company_domain",
        ]


@dataclass
class PersonRecord(ClayRecord):
    """A person record from Clay."""

    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    job_title: str = ""
    location: str = ""
    company_name: str = ""
    company_domain: str = ""
    linkedin_url: str = ""
    profile_id: str = ""
    latest_experience_start_date: str = ""
    company_record_id: str = ""
    company_table_id: str = ""

    @classmethod
    def field_names(cls) -> List[str]:
        return [
            "first_name",
            "last_name",
            "full_name",
            "job_title",
            "location",
            "company_name",
            "company_domain",
            "linkedin_url",
            "profile_id",
            "latest_experience_start_date",
            "company_record_id",
            "company_table_id",
            "source_company_table_id",
            "source_company_domain",
        ]


@dataclass
class JobRecord(ClayRecord):
    """A job record from Clay."""

    company_name: str = ""
    title: str = ""
    normalized_title: str = ""
    location: str = ""
    url: str = ""
    posted_at: str = ""
    company_domain: str = ""
    job_id: str = ""

    @classmethod
    def field_names(cls) -> List[str]:
        return [
            "company_name",
            "title",
            "normalized_title",
            "location",
            "url",
            "posted_at",
            "company_domain",
            "job_id",
            "source_company_table_id",
            "source_company_domain",
        ]


# Backward-compatible public name.
Person = PersonRecord


@dataclass
class SearchFilters:
    """Filters for CPJ source searches."""

    raw_inputs: Optional[dict] = None

    # Company identifiers / join fields.
    company_identifier: List[str] = field(default_factory=list)
    company_record_id: List[str] = field(default_factory=list)
    company_table_id: str = ""
    company_table_view_id: str = ""
    company_table_field_id: str = ""
    start_from_method: str = "CsvOfCompanies"

    # Shared company filters.
    country_names: List[str] = field(default_factory=list)
    country_names_exclude: List[str] = field(default_factory=list)
    types: List[str] = field(default_factory=list)
    sizes: List[str] = field(default_factory=list)
    funding_amounts: List[str] = field(default_factory=list)
    annual_revenues: List[str] = field(default_factory=list)
    minimum_member_count: Optional[int] = None
    maximum_member_count: Optional[int] = None
    industries: List[str] = field(default_factory=list)
    industries_exclude: List[str] = field(default_factory=list)
    description_keywords: List[str] = field(default_factory=list)
    description_keywords_exclude: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    locations_exclude: List[str] = field(default_factory=list)
    location_cities_include: List[str] = field(default_factory=list)
    location_cities_exclude: List[str] = field(default_factory=list)
    location_regions_include: List[str] = field(default_factory=list)
    location_regions_exclude: List[str] = field(default_factory=list)
    location_postal_codes_include: List[str] = field(default_factory=list)
    location_postal_codes_exclude: List[str] = field(default_factory=list)
    location_states_include: List[str] = field(default_factory=list)
    location_states_exclude: List[str] = field(default_factory=list)
    location_headquarters_only: Optional[bool] = None
    semantic_description: str = ""
    derived_industries: List[str] = field(default_factory=list)
    derived_subindustries: List[str] = field(default_factory=list)
    derived_subindustries_exclude: List[str] = field(default_factory=list)
    derived_revenue_streams: List[str] = field(default_factory=list)
    derived_business_types: List[str] = field(default_factory=list)
    technographics_vendors: List[str] = field(default_factory=list)
    technographics_products: List[str] = field(default_factory=list)
    technographics_main_categories: List[str] = field(default_factory=list)
    technographics_parent_categories: List[str] = field(default_factory=list)
    has_resolved_domain: List[str] = field(default_factory=list)
    resolved_domain_is_live: List[str] = field(default_factory=list)
    resolved_domain_redirects: List[str] = field(default_factory=list)

    # People filters.
    seniority_levels: List[str] = field(default_factory=list)
    seniority_levels_v2: List[str] = field(default_factory=list)
    seniority_match_mode: str = "exact"
    seniority_floor_level: Optional[str] = None
    job_functions: List[str] = field(default_factory=list)
    job_title_keywords: List[str] = field(default_factory=list)
    job_title_exclude_keywords: List[str] = field(default_factory=list)
    job_title_include_past_experiences: Optional[bool] = None
    job_title_mode: str = "smart"
    company_sizes: List[str] = field(default_factory=list)
    company_annual_revenues: List[str] = field(default_factory=list)
    company_industries_include: List[str] = field(default_factory=list)
    company_industries_exclude: List[str] = field(default_factory=list)
    company_description_keywords: List[str] = field(default_factory=list)
    company_description_keywords_exclude: List[str] = field(default_factory=list)
    include_past_experiences: bool = False
    headline_keywords: List[str] = field(default_factory=list)
    about_keywords: List[str] = field(default_factory=list)
    profile_keywords: List[str] = field(default_factory=list)
    job_description_keywords: List[str] = field(default_factory=list)
    job_description_include_past_experiences: Optional[bool] = None
    certification_keywords: List[str] = field(default_factory=list)
    school_names: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    names: List[str] = field(default_factory=list)
    connection_count: Optional[int] = None
    max_connection_count: Optional[int] = None
    limit_per_company: Optional[int] = None
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

    # Jobs filters.
    has_recruiter: Optional[bool] = None
    employment_type: List[str] = field(default_factory=list)
    seniority: List[str] = field(default_factory=list)
    max_num_days_since_posted: Optional[int] = None
    min_num_days_since_posted: Optional[int] = None


T = TypeVar("T", bound=ClayRecord)


@dataclass
class SearchResult(Generic[T]):
    """Result of a CPJ source search."""

    records: List[T]
    total_count: int
    mode: str
    entity: str
    table_id: Optional[str] = None
    view_id: Optional[str] = None
    source_id: Optional[str] = None
    workbook_id: Optional[str] = None
    run_status: str = ""
    manifest_path: Optional[str] = None

    @property
    def companies(self):
        return self.records if self.entity == "companies" else []

    @property
    def people(self):
        return self.records if self.entity == "people" else []

    @property
    def jobs(self):
        return self.records if self.entity == "jobs" else []


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
    status: str
    rows_added: int = 0
    message: str = ""
