"""Related keywords expansion via Clay's search/related-keywords API."""

from ..client import ClayClient


class KeywordExpander:
    """Expand search terms using Clay's related-keywords endpoint."""

    def __init__(self, client: ClayClient):
        self.client = client

    def get_related(self, keywords: list) -> list:
        """Call search/related-keywords API and return expanded terms.

        Args:
            keywords: List of seed keywords to expand.

        Returns:
            List of related keyword strings from Clay.
        """
        body = {
            "keywords": keywords,
        }
        data = self.client.post("search/related-keywords", body)
        return data.get("keywords", [])
