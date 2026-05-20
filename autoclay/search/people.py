"""People search via Clay's Companies, People, Jobs source."""

from ..models import PersonRecord, SearchFilters, _stringify
from ._base import BaseSearch


class PeopleSearch(BaseSearch):
    """Search for people using Clay's Mixrank CPJ source."""

    ENTITY = "people"
    SOURCE_TYPE = "people"
    ACTION_KEY = "find-lists-of-people-with-mixrank-source"
    PREVIEW_ACTION_KEY = "find-lists-of-people-with-mixrank-source-preview"
    TABLE_TYPE = "people"
    FIELD_ID = "f_people_search"
    FIELD_NAME = "Find people"
    ICON_TYPE = "User"
    PREVIEW_TEXT_PATH = "name"
    DEFAULT_PREVIEW_TEXT = "Clay Profile"
    RECORDS_PATH = "people"
    COUNT_PATH = "peopleCount"
    ID_PATH = "profile_id"
    RECORD_CLASS = PersonRecord
    OUTPUT_FIELDS = [
        {"name": "First Name", "attr": "first_name", "path": "first_name", "type": "text"},
        {"name": "Last Name", "attr": "last_name", "path": "last_name", "type": "text"},
        {"name": "Full Name", "attr": "full_name", "path": "name", "type": "text"},
        {"name": "Job Title", "attr": "job_title", "path": "latest_experience_title", "type": "text"},
        {"name": "Location", "attr": "location", "path": "location_name", "type": "text"},
        {"name": "Company Name", "attr": "company_name", "path": "latest_experience_company", "type": "text"},
        {"name": "Company Domain", "attr": "company_domain", "path": "domain", "type": "url"},
        {"name": "LinkedIn Profile", "attr": "linkedin_url", "path": "url", "type": "url", "dedupe": True},
        {"name": "Profile ID", "attr": "profile_id", "path": "profile_id", "type": "text"},
        {"name": "Latest Experience Start Date", "attr": "latest_experience_start_date", "path": "latest_experience_start_date", "type": "date"},
        {"name": "Company Record ID", "attr": "company_record_id", "path": "company_record_id", "type": "text"},
        {"name": "Company Table ID", "attr": "company_table_id", "path": "company_table_id", "type": "text"},
    ]
    BASIC_FIELDS = [
        {
            "name": field["name"],
            "dataType": field["type"],
            "formulaText": f"{{{{source}}}}.{field['path']}",
            **({"isDedupeField": True} if field.get("dedupe") else {}),
        }
        for field in OUTPUT_FIELDS
    ]

    def build_inputs(self, identifiers, filters, limit):
        if filters.raw_inputs is not None:
            return dict(filters.raw_inputs)

        company_identifier = filters.company_identifier or identifiers
        return {
            "company_identifier": company_identifier,
            "include_past_experiences": filters.include_past_experiences,
            "job_title_seniority_levels": filters.seniority_levels,
            "job_title_seniority_levels_v2": filters.seniority_levels_v2,
            "job_title_seniority_match_mode": filters.seniority_match_mode,
            "job_title_seniority_floor_level": filters.seniority_floor_level,
            "job_title_keywords": filters.job_title_keywords,
            "job_title_exclude_keywords": filters.job_title_exclude_keywords,
            "job_title_include_past_experiences": filters.job_title_include_past_experiences,
            "job_title_mode": filters.job_title_mode,
            "job_functions": filters.job_functions,
            "current_role_min_months_since_start_date": filters.current_role_min_months,
            "current_role_max_months_since_start_date": filters.current_role_max_months,
            "role_range_start_month": filters.role_range_start_month,
            "role_range_end_month": filters.role_range_end_month,
            "locations": filters.locations,
            "company_description_keywords": filters.company_description_keywords,
            "company_description_keywords_exclude": filters.company_description_keywords_exclude,
            "company_sizes": filters.company_sizes,
            "company_annual_revenues": filters.company_annual_revenues,
            "company_industries_include": filters.company_industries_include,
            "company_industries_exclude": filters.company_industries_exclude,
            "locations_exclude": filters.locations_exclude,
            "location_cities_include": filters.location_cities_include,
            "location_cities_exclude": filters.location_cities_exclude,
            "location_states_include": filters.location_states_include,
            "location_states_exclude": filters.location_states_exclude,
            "location_countries_include": filters.country_names,
            "location_countries_exclude": filters.country_names_exclude,
            "location_regions_include": filters.location_regions_include,
            "location_regions_exclude": filters.location_regions_exclude,
            "headline_keywords": filters.headline_keywords,
            "about_keywords": filters.about_keywords,
            "profile_keywords": filters.profile_keywords,
            "job_description_keywords": filters.job_description_keywords,
            "job_description_include_past_experiences": filters.job_description_include_past_experiences,
            "languages": filters.languages,
            "school_names": filters.school_names,
            "certification_keywords": filters.certification_keywords,
            "names": filters.names,
            "experience_count": filters.experience_count,
            "max_experience_count": filters.max_experience_count,
            "follower_count": filters.follower_count,
            "max_follower_count": filters.max_follower_count,
            "connection_count": filters.connection_count,
            "max_connection_count": filters.max_connection_count,
            "limit_per_company": getattr(filters, "limit_per_company", None),
            "limit": limit,
            "company_record_id": filters.company_record_id,
            "company_table_id": filters.company_table_id,
            "company_table_view_id": filters.company_table_view_id,
            "company_table_field_id": filters.company_table_field_id,
            "start_from_method": filters.start_from_method,
            "result_count": True,
        }

    def parse_preview_record(self, raw):
        return PersonRecord(
            first_name=_stringify(raw.get("first_name")),
            last_name=_stringify(raw.get("last_name")),
            full_name=_stringify(raw.get("name")),
            job_title=_stringify(raw.get("latest_experience_title")),
            location=_stringify(raw.get("location_name")),
            company_name=_stringify(raw.get("latest_experience_company")),
            company_domain=_stringify(raw.get("domain")),
            linkedin_url=_stringify(raw.get("url")),
            profile_id=_stringify(raw.get("profile_id")),
            latest_experience_start_date=_stringify(raw.get("latest_experience_start_date")),
            company_record_id=_stringify(raw.get("company_record_id")),
            company_table_id=_stringify(raw.get("company_table_id")),
            source_company_table_id=_stringify(raw.get("company_table_id")),
            source_company_domain=_stringify(raw.get("domain")),
        )

    def _workbook_name(self, identifiers):
        if not identifiers:
            return "People Search - All"
        if len(identifiers) == 1:
            return f"People Search - {identifiers[0]}"
        return f"People Search - {len(identifiers)} companies"
