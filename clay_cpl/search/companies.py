"""Company search via Clay's Companies, People, Jobs source."""

import difflib
import json
import os
import time

from ..enums import SIZE_LABEL_TO_CODE, SIZE_CODE_TO_LABEL
from ..exceptions import ClayAPIError
from ..models import CompanyRecord, _stringify
from ._base import BaseSearch

_SCHEMA_CACHE = os.path.expanduser("~/.clay-cpl/cache/companies-action-schema.json")
_SCHEMA_TTL = 7 * 24 * 3600


class CompanySearch(BaseSearch):
    """Search for companies using Clay's Mixrank CPJ source."""

    ENTITY = "companies"
    SOURCE_TYPE = "companies"
    ACTION_KEY = "find-lists-of-companies-with-mixrank-source"
    PREVIEW_ACTION_KEY = "find-lists-of-companies-with-mixrank-source-preview"
    TABLE_TYPE = "company"
    FIELD_ID = "f_companies_search"
    FIELD_NAME = "Find companies"
    ICON_TYPE = "Building2"
    PREVIEW_TEXT_PATH = "name"
    DEFAULT_PREVIEW_TEXT = "Company"
    RECORDS_PATH = "companies"
    COUNT_PATH = "companyCount"
    ID_PATH = "clay_company_id"
    RECORD_CLASS = CompanyRecord
    OUTPUT_FIELDS = [
        {"name": "Name", "attr": "name", "path": "name", "type": "text"},
        {"name": "Description", "attr": "description", "path": "description", "type": "text"},
        {"name": "Type", "attr": "company_type", "path": "type", "type": "text"},
        {"name": "Size", "attr": "size", "path": "size", "type": "text"},
        {"name": "Country", "attr": "country", "path": "country", "type": "text"},
        {"name": "Location", "attr": "location", "path": "location", "type": "text"},
        {"name": "Founded", "attr": "founded", "path": "founded", "type": "number"},
        {"name": "Domain", "attr": "domain", "path": "domain", "type": "url", "dedupe": True},
        {"name": "Website", "attr": "website", "path": "website", "type": "url"},
        {"name": "Employee Count", "attr": "employee_count", "path": "employee_count", "type": "number"},
        {"name": "Follower Count", "attr": "follower_count", "path": "follower_count", "type": "number"},
        {"name": "Primary Industry", "attr": "primary_industry", "path": "primary_industry", "type": "text"},
        {"name": "Industries", "attr": "industries", "path": "industries", "type": "text"},
        {"name": "Specialties", "attr": "specialties", "path": "specialties", "type": "text"},
        {"name": "LinkedIn URL", "attr": "linkedin_url", "path": "linkedin_url", "type": "url"},
        {"name": "Clay Company ID", "attr": "clay_company_id", "path": "clay_company_id", "type": "text"},
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

    def _action_schema(self):
        """Gueltige Filterwerte der Company-Action, 7 Tage gecacht. Die
        Taxonomie hat sich schon einmal still geaendert (alte
        LinkedIn-Industrienamen matchen auf 0) - deshalb live von der API
        statt hartkodiert."""
        try:
            if os.path.exists(_SCHEMA_CACHE) and \
                    time.time() - os.path.getmtime(_SCHEMA_CACHE) < _SCHEMA_TTL:
                return json.load(open(_SCHEMA_CACHE))
        except Exception:
            pass
        r = self.client.get(f"actions?workspaceId={self.client.workspace_id}")
        items = r if isinstance(r, list) else r.get("actions") or []
        a = next((x for x in items if x.get("key") == self.ACTION_KEY), None)
        schema = {}
        for par in (a or {}).get("inputParameterSchema") or []:
            opts = [o.get("value") for o in par.get("options") or []]
            if opts:
                schema[par["name"]] = opts
        try:
            os.makedirs(os.path.dirname(_SCHEMA_CACHE), exist_ok=True)
            json.dump(schema, open(_SCHEMA_CACHE, "w"))
        except Exception:
            pass
        return schema

    def _validate_inputs(self, inputs):
        schema = self._action_schema()
        for feld in ("industries", "industries_exclude", "sizes",
                     "country_names", "derived_industries"):
            werte = inputs.get(feld)
            gueltig = schema.get(feld)
            if not werte or not gueltig:
                continue
            falsch = [w for w in werte if w not in gueltig]
            if falsch:
                tipps = []
                for w in falsch[:3]:
                    n = difflib.get_close_matches(w, gueltig, n=2, cutoff=0.4)
                    if n:
                        tipps.append(f"{w!r} -> vielleicht {n}")
                raise ClayAPIError(
                    f"Ungueltige Werte in '{feld}': {falsch[:5]}. Die Server-"
                    f"Suche matcht unbekannte Werte STUMM auf 0 Zeilen. "
                    + ("Aehnlich: " + "; ".join(tipps) if tipps else
                       f"Gueltige Beispiele: {gueltig[:5]}"),
                    status_code=None, response_body=str(falsch))

    def build_inputs(self, identifiers, filters, limit):
        if filters.raw_inputs is not None:
            inputs = dict(filters.raw_inputs)
            # Groessen-Label stillschweigend in die Codes uebersetzen, die
            # die Company-Source verlangt - sonst 0 Treffer ohne Fehler.
            if inputs.get("sizes"):
                inputs["sizes"] = [
                    SIZE_LABEL_TO_CODE.get(x, x) for x in inputs["sizes"]]
            self._validate_inputs(inputs)
            return inputs
        inputs = {
            "startFromCompanyType": "semantic_description",
            "country_names": filters.country_names,
            "country_names_exclude": filters.country_names_exclude,
            "types": filters.types,
            "sizes": filters.sizes,
            "funding_amounts": filters.funding_amounts,
            "annual_revenues": filters.annual_revenues,
            "minimum_member_count": filters.minimum_member_count,
            "maximum_member_count": filters.maximum_member_count,
            "industries": filters.industries,
            "industries_exclude": filters.industries_exclude,
            "description_keywords": filters.description_keywords,
            "description_keywords_exclude": filters.description_keywords_exclude,
            "locations": filters.locations,
            "locations_exclude": filters.locations_exclude,
            "location_cities_include": filters.location_cities_include,
            "location_cities_exclude": filters.location_cities_exclude,
            "location_regions_include": filters.location_regions_include,
            "location_regions_exclude": filters.location_regions_exclude,
            "location_postal_codes_include": filters.location_postal_codes_include,
            "location_postal_codes_exclude": filters.location_postal_codes_exclude,
            "location_states_include": filters.location_states_include,
            "location_states_exclude": filters.location_states_exclude,
            "location_headquarters_only": filters.location_headquarters_only,
            "semantic_description": filters.semantic_description,
            "derived_industries": filters.derived_industries,
            "derived_subindustries": filters.derived_subindustries,
            "derived_subindustries_exclude": filters.derived_subindustries_exclude,
            "derived_revenue_streams": filters.derived_revenue_streams,
            "derived_business_types": filters.derived_business_types,
            "technographics_vendors": filters.technographics_vendors,
            "technographics_products": filters.technographics_products,
            "technographics_main_categories": filters.technographics_main_categories,
            "technographics_parent_categories": filters.technographics_parent_categories,
            "has_resolved_domain": filters.has_resolved_domain[0] if filters.has_resolved_domain else None,
            "resolved_domain_is_live": filters.resolved_domain_is_live[0] if filters.resolved_domain_is_live else None,
            "resolved_domain_redirects": filters.resolved_domain_redirects[0] if filters.resolved_domain_redirects else None,
            "limit": limit,
        }
        self._validate_inputs(inputs)
        return inputs

    def parse_preview_record(self, raw):
        return CompanyRecord(
            name=_stringify(raw.get("name")),
            description=_stringify(raw.get("description")),
            company_type=_stringify(raw.get("type")),
            size=_stringify(raw.get("size")),
            country=_stringify(raw.get("country")),
            location=_stringify(raw.get("location")),
            founded=_stringify(raw.get("founded")),
            domain=_stringify(raw.get("domain")),
            website=_stringify(raw.get("website")),
            employee_count=_stringify(raw.get("employee_count")),
            follower_count=_stringify(raw.get("follower_count")),
            primary_industry=_stringify(raw.get("primary_industry") or raw.get("industry")),
            industries=_stringify(raw.get("industries")),
            specialties=_stringify(raw.get("specialties")),
            linkedin_url=_stringify(raw.get("linkedin_url")),
            clay_company_id=_stringify(raw.get("clay_company_id")),
        )

    def _workbook_name(self, identifiers):
        return "Company Search"
