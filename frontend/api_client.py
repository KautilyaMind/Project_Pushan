"""Small, testable HTTP client used by the Pushan Streamlit dashboard."""

import os
from typing import Any

import httpx


DEFAULT_API_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 5.0


class PushanAPIError(Exception):
    """A safe API error suitable for display in the dashboard."""


class BackendUnavailableError(PushanAPIError):
    """Raised when the FastAPI backend cannot be reached."""


class MalformedResponseError(PushanAPIError):
    """Raised when the backend response does not match the expected shape."""


def get_api_base_url() -> str:
    """Return the configured backend URL without a trailing slash."""
    return os.getenv("PUSHAN_API_URL", DEFAULT_API_URL).rstrip("/")


def check_health() -> dict[str, Any]:
    """Return service health information."""
    return _expect_dictionary(_request("GET", "/health"))


def get_fields() -> list[dict[str, Any]]:
    """Return configured field metadata."""
    return _expect_list(_request("GET", "/fields"))


def get_sensor_reading(field_id: str) -> dict[str, Any]:
    """Return the selected field's current simulated sensor state."""
    return _expect_dictionary(_request("GET", f"/fields/{field_id}/sensor"))


def get_irrigation_recommendation(
    field_id: str,
    crop: str,
    crop_stage: str,
    field_area_m2: float,
) -> dict[str, Any]:
    """Request a full rule, ML, operational, and persistence assessment."""
    payload = {
        "field_id": field_id,
        "crop": crop,
        "crop_stage": crop_stage,
        "field_area_m2": field_area_m2,
    }
    return _expect_dictionary(
        _request("POST", "/irrigation/recommend", json_body=payload)
    )


def get_sensor_history(field_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Return recent sensor records through the API."""
    return _history_request(field_id, "sensors", limit)


def get_decision_history(field_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Return recent rule-decision records through the API."""
    return _history_request(field_id, "decisions", limit)


def get_action_history(field_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Return recent operational-action records through the API."""
    return _history_request(field_id, "actions", limit)


def _history_request(
    field_id: str,
    history_type: str,
    limit: int,
) -> list[dict[str, Any]]:
    response = _request(
        "GET",
        f"/fields/{field_id}/history/{history_type}",
        query_parameters={"limit": limit},
    )
    return _expect_list(response)


def _request(
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
    query_parameters: dict[str, Any] | None = None,
) -> Any:
    """Perform one bounded request and convert failures to display-safe errors."""
    try:
        response = httpx.request(
            method,
            f"{get_api_base_url()}{path}",
            json=json_body,
            params=query_parameters,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.TimeoutException as error:
        raise PushanAPIError(
            "The Pushan backend request timed out. Please try again."
        ) from error
    except httpx.RequestError as error:
        raise BackendUnavailableError(
            "Pushan backend is unavailable. Start the FastAPI service and refresh."
        ) from error
    except httpx.HTTPStatusError as error:
        detail = _safe_error_detail(error.response)
        raise PushanAPIError(
            f"Pushan API returned {error.response.status_code}: {detail}"
        ) from error

    try:
        return response.json()
    except ValueError as error:
        raise MalformedResponseError(
            "Pushan API returned an unreadable response."
        ) from error


def _safe_error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return "The request could not be completed."
    if isinstance(body, dict) and isinstance(body.get("detail"), str):
        return body["detail"]
    return "The request could not be completed."


def _expect_dictionary(response: Any) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise MalformedResponseError(
            "Pushan API response did not contain the expected object."
        )
    return response


def _expect_list(response: Any) -> list[dict[str, Any]]:
    if not isinstance(response, list) or not all(
        isinstance(record, dict) for record in response
    ):
        raise MalformedResponseError(
            "Pushan API response did not contain the expected record list."
        )
    return response
