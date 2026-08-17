"""Validated enum values for Clay API filter parameters.

Source: knowledge_base/technical/clay-people-search-enums.md
Validated via XHR interception on app.clay.com (2026-02-13).
"""

SENIORITY_LEVELS = [
    "owner",
    "partner",
    "c-suite",
    "vp",
    "director",
    "head",
    "manager",
    "senior",
    "entry",
    "assistant",
    "intern",
    "freelance",
    "certified",
]

JOB_FUNCTIONS = [
    "Administrative",
    "Agriculture, Horticulture, and the Outdoors",
    "Arts and Design",
    "Business Development",
    "Community and Social Services",
    "Construction, Extraction, and Architecture",
    "Customer Success and Support",
    "Education",
    "Engineering",
    "Finance",
    "Healthcare",
    "Hospitality, Food, and Tourism",
    "Human Resources and Recruiting",
    "Information Technology (IT) and Computer Science",
    "Legal, Compliance, and Public Safety",
    "Maintenance, Repair, and Installation",
    "Manufacturing and Production",
    "Marketing and Public Relations",
    "Military",
    "Performing Arts",
    "Personal Services",
    "Sales",
    "Science and Research",
    "Social Analysis and Planning",
    "Student",
]

JOB_TITLE_MODES = ["smart", "contain", "exact"]

# Company-Source: Bucket-CODES; People-Source: LABELS.
# 2026-08-17 gegen die inputParameterSchema beider Actions verifiziert.
SIZE_CODE_TO_LABEL = {
    "1": "1", "2": "2-10", "10": "11-50", "50": "51-200", "200": "201-500",
    "500": "501-1,000", "1000": "1,001-5,000", "5000": "5,001-10,000",
    "10000": "10,001+",
}
SIZE_LABEL_TO_CODE = {v: k for k, v in SIZE_CODE_TO_LABEL.items()}

COMPANY_SIZES = [
    "1",
    "2-10",
    "11-50",
    "51-200",
    "201-500",
    "501-1,000",
    "1,001-5,000",
    "5,001-10,000",
    "10,001+",
]


def validate_seniority(values):
    """Validate seniority level values. Returns list of invalid values, or empty list."""
    return [v for v in values if v not in SENIORITY_LEVELS]


def validate_job_functions(values):
    """Validate job function values. Returns list of invalid values, or empty list."""
    return [v for v in values if v not in JOB_FUNCTIONS]
