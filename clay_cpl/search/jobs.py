"""Job search via Clay's Companies, People, Jobs source."""

from ..models import JobRecord, _stringify
from ._base import BaseSearch


class JobSearch(BaseSearch):
    """Search for active jobs using Clay's Mixrank CPJ source."""

    ENTITY = "jobs"
    SOURCE_TYPE = "jobs"
    ACTION_KEY = "find-lists-of-jobs-with-mixrank-source"
    PREVIEW_ACTION_KEY = "find-lists-of-jobs-with-mixrank-source-preview"
    TABLE_TYPE = "jobs"
    FIELD_ID = "f_jobs_search"
    FIELD_NAME = "Find jobs"
    ICON_TYPE = "BriefcaseBusiness"
    PREVIEW_TEXT_PATH = "title"
    DEFAULT_PREVIEW_TEXT = "Job"
    RECORDS_PATH = "jobs"
    COUNT_PATH = "jobCount"
    ID_PATH = "job_id"
    RECORD_CLASS = JobRecord
    OUTPUT_FIELDS = [
        {"name": "Company Name", "attr": "company_name", "path": "company_name", "type": "text"},
        {"name": "Title", "attr": "title", "path": "title", "type": "text"},
        {"name": "Normalized Title", "attr": "normalized_title", "path": "normalized_title", "type": "text"},
        {"name": "Location", "attr": "location", "path": "location", "type": "text"},
        {"name": "URL", "attr": "url", "path": "url", "type": "url", "dedupe": True},
        {"name": "Posted At", "attr": "posted_at", "path": "posted_at", "type": "date"},
        {"name": "Company Domain", "attr": "company_domain", "path": "domain", "type": "url"},
        {"name": "Job ID", "attr": "job_id", "path": "job_id", "type": "text"},
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
            "startFrom": "CsvOfCompanies",
            "company_identifier": company_identifier,
            "job_title_keywords": filters.job_title_keywords,
            "job_title_exclude_keywords": filters.job_title_exclude_keywords,
            "locations": filters.locations,
            "locations_exclude": filters.locations_exclude,
            "job_description_keywords": filters.job_description_keywords,
            "has_recruiter": filters.has_recruiter if filters.has_recruiter is not None else False,
            "employment_type": filters.employment_type,
            "seniority": filters.seniority,
            "max_num_days_since_posted": filters.max_num_days_since_posted,
            "min_num_days_since_posted": filters.min_num_days_since_posted,
            "limit": limit,
        }

    def parse_preview_record(self, raw):
        domain = _stringify(raw.get("domain"))
        return JobRecord(
            company_name=_stringify(raw.get("company_name")),
            title=_stringify(raw.get("title")),
            normalized_title=_stringify(raw.get("normalized_title")),
            location=_stringify(raw.get("location")),
            url=_stringify(raw.get("url")),
            posted_at=_stringify(raw.get("posted_at")),
            company_domain=domain,
            job_id=_stringify(raw.get("job_id")),
            source_company_domain=domain,
        )

    def _workbook_name(self, identifiers):
        if not identifiers:
            return "Jobs Search - All"
        if len(identifiers) == 1:
            return f"Jobs Search - {identifiers[0]}"
        return f"Jobs Search - {len(identifiers)} companies"
