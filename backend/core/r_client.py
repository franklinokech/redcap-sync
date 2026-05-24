# core/r_client.py
from __future__ import annotations

import logging
import time
from typing import Any, Optional

import httpx
from decouple import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public exceptions  (imported by views + tasks)
# ---------------------------------------------------------------------------

class RServiceError(Exception):
    """Raised when the R sync service returns an error response."""

    def __init__(self, message: str, status_code: int = 500, payload: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload     = payload or {}


class RServiceValidationError(RServiceError):
    """Raised when the R service returns a 400-level validation error."""

    def __init__(self, message: str, payload: Optional[dict] = None):
        super().__init__(message, status_code=400, payload=payload)


class RServiceUnavailableError(RServiceError):
    """Raised when the R service cannot be reached at all."""

    def __init__(self, message: str):
        super().__init__(message, status_code=503)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class RServiceClient:
    """
    Thin HTTP client for the R plumber sync service.

    All public methods raise:
      · RServiceValidationError  — 4xx from the R service
      · RServiceUnavailableError — connection / timeout failure
      · RServiceError            — any other 5xx

    Argument order convention (URL before token, mirroring REDCapR):
      redcap_url  — the target REDCap instance base URL
      token       — the decrypted 32-char hex API token
    """

    # Maximum number of attempts (1 original + N-1 retries)
    _MAX_ATTEMPTS = 3
    # Back-off between retries in seconds (linear: attempt * _BACKOFF_BASE)
    _BACKOFF_BASE = 1.5

    def __init__(
        self,
        base_url: str | None = None,
        api_key:  str   = "",
        timeout:  float = 300.0,
    ) -> None:
        self._base_url = (
                base_url
                or config("R_SYNC_SERVICE_URL", default="http://localhost:8000")
        ).rstrip("/")
        self._timeout  = timeout
        self._headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            self._headers["X-Api-Key"] = api_key

        # Connection pool — reused across calls within the same task
        self._client = httpx.Client(
            headers=self._headers,
            timeout=httpx.Timeout(timeout),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _post(self, endpoint: str, payload: dict) -> dict:
        """POST *payload* to *endpoint* with linear back-off retry on 5xx."""
        url = f"{self._base_url}/{endpoint.lstrip('/')}"

        last_exc: Exception | None = None

        for attempt in range(1, self._MAX_ATTEMPTS + 1):
            try:
                logger.debug("R client POST %s  attempt=%s", url, attempt)
                response = self._client.post(url, json=payload)
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_exc = exc
                logger.warning(
                    "R service unreachable (attempt %s/%s): %s",
                    attempt, self._MAX_ATTEMPTS, exc,
                )
                if attempt < self._MAX_ATTEMPTS:
                    time.sleep(attempt * self._BACKOFF_BASE)
                continue

            # ---- Parse response body ---------------------------------
            try:
                data: dict = response.json()
            except Exception:
                data = {}

            if response.is_success:
                return data

            # ---- Error path -----------------------------------------
            msg = data.get("message") or response.text or "unknown error"

            if response.status_code == 401:
                raise RServiceError(
                    f"R service auth error: {msg}",
                    status_code=401,
                    payload=data,
                )

            if 400 <= response.status_code < 500:
                raise RServiceValidationError(msg, payload=data)

            # 5xx — retry
            last_exc = RServiceError(
                f"R service returned {response.status_code}: {msg}",
                status_code=response.status_code,
                payload=data,
            )
            logger.warning(
                "R service 5xx (attempt %s/%s): %s",
                attempt, self._MAX_ATTEMPTS, last_exc,
            )
            if attempt < self._MAX_ATTEMPTS:
                time.sleep(attempt * self._BACKOFF_BASE)

        # All attempts exhausted
        if isinstance(last_exc, RServiceError):
            raise last_exc
        raise RServiceUnavailableError(
            f"R service unreachable after {self._MAX_ATTEMPTS} attempts: {last_exc}"
        )

    @staticmethod
    def _require_keys(data: dict, *keys: str) -> None:
        """Raise RServiceError if any expected key is absent from *data*."""
        missing = [k for k in keys if k not in data]
        if missing:
            raise RServiceError(
                f"R service response missing keys: {missing}",
                payload=data,
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def health(self) -> dict:
        """GET /health — liveness probe."""
        url = f"{self._base_url}/health"
        try:
            r = self._client.get(url, timeout=10)
            return r.json()
        except Exception as exc:
            raise RServiceUnavailableError(f"Health check failed: {exc}") from exc

    def validate_token(
        self,
        redcap_url: str,
        token:      str,
    ) -> dict:
        """
        POST /validate-token
        Returns project metadata dict on success.

        Args:
            redcap_url: Base URL of the target REDCap instance.
            token:      Decrypted 32-char hex API token.
        """
        data = self._post(
            "/validate-token",
            {"redcap_url": redcap_url, "token": token},
        )
        self._require_keys(data, "success")
        return data

    def project_info(
        self,
        redcap_url: str,
        token:      str,
    ) -> dict:
        """
        POST /project-info
        Returns extended project metadata.

        Args:
            redcap_url: Base URL of the target REDCap instance.
            token:      Decrypted 32-char hex API token.
        """
        data = self._post(
            "/project-info",
            {"redcap_url": redcap_url, "token": token},
        )
        self._require_keys(data, "success")
        return data

    def preview(
        self,
        redcap_url: str,
        token:      str,
        date_from:  Optional[str]       = None,
        date_to:    Optional[str]       = None,
        forms:      Optional[list[str]] = None,
        fields:     Optional[list[str]] = None,
    ) -> dict:
        """
        POST /preview
        Returns record_count and available_fields.

        Args:
            redcap_url: Base URL of the target REDCap instance.
            token:      Decrypted 32-char hex API token.
            date_from:  Optional ISO-8601 date filter start.
            date_to:    Optional ISO-8601 date filter end.
            forms:      Optional list of form names to include.
            fields:     Optional list of field names to include.
        """
        payload: dict[str, Any] = {
            "redcap_url": redcap_url,
            "token":      token,
        }
        if date_from:
            payload["date_from"] = date_from
        if date_to:
            payload["date_to"] = date_to
        if forms:
            payload["forms"] = forms
        if fields:
            payload["fields"] = fields

        data = self._post("/preview", payload)
        self._require_keys(data, "success")
        return data

    def sync(
        self,
        redcap_url:        str,
        token:             str,
        target_redcap_url: str,
        target_token:      str,
        record_id_prefix:  str                  = "",
        forms:             Optional[list[str]]  = None,
        fields:            Optional[list[str]]  = None,
        date_from:         Optional[str]        = None,
        date_to:           Optional[str]        = None,
    ) -> dict:
        """
        POST /sync
        Returns records_pulled, records_pushed, records_skipped.

        Args:
            redcap_url:        Source REDCap instance URL.
            token:             Source project API token (decrypted).
            target_redcap_url: Destination REDCap instance URL.
            target_token:      Destination project API token (decrypted).
            record_id_prefix:  Optional prefix applied to record IDs on push.
            forms:             Optional list of form names to sync.
            fields:            Optional list of field names to sync.
            date_from:         Optional ISO-8601 filter start date.
            date_to:           Optional ISO-8601 filter end date.
        """
        payload: dict[str, Any] = {
            "redcap_url":        redcap_url,
            "token":             token,
            "target_redcap_url": target_redcap_url,
            "target_token":      target_token,
            "record_id_prefix":  record_id_prefix,
        }
        if forms:
            payload["forms"] = forms
        if fields:
            payload["fields"] = fields
        if date_from:
            payload["date_from"] = date_from
        if date_to:
            payload["date_to"] = date_to

        data = self._post("/sync", payload)
        self._require_keys(data, "records_pulled", "records_pushed", "records_skipped")
        return data

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "RServiceClient":
        return self

    def __exit__(self, *_) -> None:
        self._client.close()
