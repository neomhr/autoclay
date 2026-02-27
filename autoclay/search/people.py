"""People search — find people by company domain with filters."""

from ..models import Person
from ._base import BaseSearch


class PeopleSearch(BaseSearch):
    """Search for people across companies using Clay's Mixrank source."""

    SOURCE_TYPE = "people"
    ACTION_KEY = "find-lists-of-people-with-mixrank-source"
    PREVIEW_ACTION_KEY = "find-lists-of-people-with-mixrank-source-preview"
    TABLE_TYPE = "people"
    BASIC_FIELDS = [
        {"name": "First Name", "dataType": "text", "formulaText": "{{source}}.first_name"},
        {"name": "Last Name", "dataType": "text", "formulaText": "{{source}}.last_name"},
        {"name": "Full Name", "dataType": "text", "formulaText": "{{source}}.name"},
        {"name": "Job Title", "dataType": "text", "formulaText": "{{source}}.latest_experience_title"},
        {"name": "Location", "dataType": "text", "formulaText": "{{source}}.location_name"},
        {"name": "Company Domain", "dataType": "url", "formulaText": "{{source}}.domain"},
        {"name": "LinkedIn Profile", "dataType": "url", "formulaText": "{{source}}.url", "isDedupeField": True},
    ]

    def build_inputs(self, identifiers, filters, limit):
        """Build the full inputs dict for people search.

        Args:
            identifiers: List of company domains.
            filters: SearchFilters dataclass.
            limit: Max results, or None.

        Returns:
            dict matching the Clay people-search API schema.
        """
        return {
            "start_from_method": "CsvOfCompanies",
            "company_identifier": identifiers,
            "company_record_id": [],
            "company_table_id": "",
            "company_audience_segment_id": None,
            "include_company_filter_bitmap": None,
            "limit": limit,
            "job_functions": filters.job_functions,
            "job_title_keywords": filters.job_title_keywords,
            "job_title_exclude_keywords": filters.job_title_exclude_keywords,
            "job_title_seniority_levels": filters.seniority_levels,
            "job_title_mode": filters.job_title_mode,
            "job_title_exact_keyword_match": filters.job_title_exact_keyword_match,
            "job_title_exact_match": filters.job_title_exact_match,
            "locations": [],
            "locations_exclude": [],
            "location_countries_include": filters.countries_include,
            "location_countries_exclude": filters.countries_exclude,
            "location_states_include": filters.states_include,
            "location_states_exclude": filters.states_exclude,
            "location_cities_include": filters.cities_include,
            "location_cities_exclude": filters.cities_exclude,
            "location_regions_include": filters.regions_include,
            "location_regions_exclude": filters.regions_exclude,
            "search_raw_location": filters.search_raw_location,
            "company_sizes": filters.company_sizes,
            "company_industries_include": filters.company_industries_include,
            "company_industries_exclude": filters.company_industries_exclude,
            "company_description_keywords": filters.company_description_keywords,
            "company_description_keywords_exclude": filters.company_description_keywords_exclude,
            "include_past_experiences": filters.include_past_experiences,
            "headline_keywords": filters.headline_keywords,
            "about_keywords": filters.about_keywords,
            "profile_keywords": filters.profile_keywords,
            "job_description_keywords": filters.job_description_keywords,
            "certification_keywords": filters.certification_keywords,
            "school_names": filters.school_names,
            "languages": filters.languages,
            "names": filters.names,
            "connection_count": filters.connection_count,
            "max_connection_count": filters.max_connection_count,
            "follower_count": filters.follower_count,
            "max_follower_count": filters.max_follower_count,
            "experience_count": filters.experience_count,
            "max_experience_count": filters.max_experience_count,
            "current_role_min_months_since_start_date": filters.current_role_min_months,
            "current_role_max_months_since_start_date": filters.current_role_max_months,
            "exclude_entities_configuration": [],
            "exclude_entities_bitmap": None,
            "previous_entities_bitmap": None,
            "exclude_entity_bitmap": None,
            "exclude_people_identifiers_mixed": [],
            "role_range_start_month": filters.role_range_start_month,
            "role_range_end_month": filters.role_range_end_month,
            "result_count": True,
            "name": "",
        }

    def parse_preview_record(self, raw):
        """Parse a single raw preview record into a Person."""
        return Person(
            first_name=raw.get("first_name", ""),
            last_name=raw.get("last_name", ""),
            full_name=raw.get("name", ""),
            job_title=raw.get("latest_experience_title", ""),
            location=raw.get("location_name", ""),
            company_domain=raw.get("domain", ""),
            linkedin_url=raw.get("url", ""),
        )

    def _workbook_name(self, identifiers):
        """Generate a workbook name from the search identifiers."""
        if len(identifiers) == 1:
            return f"People Search - {identifiers[0]}"
        return f"People Search - {len(identifiers)} companies"
