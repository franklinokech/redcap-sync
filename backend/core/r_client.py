# core/r_client.py
# HTTP client that calls the R plumber sync service
import httpx
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class RServiceClient:
    """
    Thin client wrapping the R plumber REST API.
    Base URL and timeout come from Django settings.
    """

    def __init__(self):
        self.base_url = getattr(settings, "R_SYNC_SERVICE_URL", "http://localhost:8000").rstrip("/")
        self.timeout  = getattr(settings, "R_SYNC_SERVICE_TIMEOUT", 300)

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        logger.info("R service POST %s", url)
        try:
            response = httpx.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to R sync service at {self.base_url}. "
                "Is the plumber service running?"
            )
        except httpx.TimeoutException:
            raise TimeoutError(
                f"R sync service timed out after {self.timeout}s."
            )
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"R service returned {e.response.status_code}: {e.response.text}"
            )

    def health(self) -> dict:
        """GET /health"""
        url = f"{self.base_url}/health"
        response = httpx.get(url, timeout=10)
        return response.json()

    def project_info(self, token: str, redcap_url: str) -> dict:
        """POST /project-info — validate token and fetch project metadata."""
        return self._post("/project-info", {
            "token":      token,
            "redcap_url": redcap_url,
        })

    def preview(self, token: str, redcap_url: str,
                sync_type: str = "full",
                date_from: str = None,
                date_to: str   = None) -> dict:
        """POST /preview — pull records without writing to registry."""
        payload = {
            "token":      token,
            "redcap_url": redcap_url,
            "full_sync":  sync_type == "full",
        }
        if date_from: payload["date_from"] = date_from
        if date_to:   payload["date_to"]   = date_to
        return self._post("/preview", payload)

    def sync(self, source_token: str, source_url: str,
             registry_token: str, registry_url: str,
             sync_type: str = "full",
             date_from: str = None,
             date_to: str   = None,
             forms: list    = None,
             fields: list   = None,
             overwrite_with_blanks: bool = False,
             record_id_prefix: str = None) -> dict:
        """POST /sync — pull from source and push to registry."""
        payload = {
            "source_token":          source_token,
            "source_url":            source_url,
            "registry_token":        registry_token,
            "registry_url":          registry_url,
            "full_sync":             sync_type == "full",
            "overwrite_with_blanks": overwrite_with_blanks,
        }
        if date_from: payload["date_from"] = date_from
        if date_to:   payload["date_to"]   = date_to
        if forms:     payload["forms"]     = ",".join(forms)
        if fields:    payload["fields"]    = ",".join(fields)
        if record_id_prefix:  payload["record_id_prefix"]  = record_id_prefix
        return self._post("/sync", payload)