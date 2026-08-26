"""Unit tests for the Streamlit dashboard's FastAPI client."""

import unittest
from unittest.mock import patch

import httpx

from frontend.api_client import (
    BackendUnavailableError,
    MalformedResponseError,
    PushanAPIError,
    check_health,
    get_fields,
    get_irrigation_recommendation,
    get_sensor_history,
    get_sensor_reading,
    run_agent,
)


class FrontendApiClientTests(unittest.TestCase):
    @patch("frontend.api_client.httpx.request")
    def test_agent_request_uses_endpoint_and_payload(self, mock_request: object) -> None:
        mock_request.return_value = json_response({"intent": "FIELD_ASSESSMENT"})  # type: ignore[attr-defined]
        run_agent("Assess FIELD_001")
        self.assertTrue(mock_request.call_args.args[1].endswith("/agent/run"))  # type: ignore[attr-defined]
        self.assertEqual(mock_request.call_args.kwargs["json"], {"message": "Assess FIELD_001"})  # type: ignore[attr-defined]

    @patch("frontend.api_client.httpx.request")
    def test_health_request_success(self, mock_request: object) -> None:
        mock_request.return_value = json_response(  # type: ignore[attr-defined]
            {"status": "ok", "service": "Pushan", "version": "0.5"}
        )
        self.assertEqual(check_health()["status"], "ok")

    @patch("frontend.api_client.httpx.request")
    def test_health_request_failure(self, mock_request: object) -> None:
        request = httpx.Request("GET", "http://127.0.0.1:8000/health")
        mock_request.side_effect = httpx.ConnectError(  # type: ignore[attr-defined]
            "connection failed", request=request
        )
        with self.assertRaisesRegex(BackendUnavailableError, "backend is unavailable"):
            check_health()

    @patch("frontend.api_client.httpx.request")
    def test_fields_request_returns_parsed_data(self, mock_request: object) -> None:
        mock_request.return_value = json_response(  # type: ignore[attr-defined]
            [{"field_id": "FIELD_001", "crop": "tomato"}]
        )
        self.assertEqual(get_fields()[0]["field_id"], "FIELD_001")

    @patch("frontend.api_client.httpx.request")
    def test_sensor_request_uses_correct_endpoint(self, mock_request: object) -> None:
        mock_request.return_value = json_response(  # type: ignore[attr-defined]
            {"field_id": "FIELD_002", "soil_moisture": 35}
        )
        get_sensor_reading("FIELD_002")
        called_url = mock_request.call_args.args[1]  # type: ignore[attr-defined]
        self.assertTrue(called_url.endswith("/fields/FIELD_002/sensor"))

    @patch("frontend.api_client.httpx.request")
    def test_recommendation_sends_correct_payload(self, mock_request: object) -> None:
        mock_request.return_value = json_response(  # type: ignore[attr-defined]
            {"field_id": "FIELD_001"}
        )
        get_irrigation_recommendation(
            "FIELD_001", "tomato", "flowering", 1000
        )
        payload = mock_request.call_args.kwargs["json"]  # type: ignore[attr-defined]
        self.assertEqual(
            payload,
            {
                "field_id": "FIELD_001",
                "crop": "tomato",
                "crop_stage": "flowering",
                "field_area_m2": 1000,
            },
        )

    @patch("frontend.api_client.httpx.request")
    def test_history_request_respects_limit(self, mock_request: object) -> None:
        mock_request.return_value = json_response([])  # type: ignore[attr-defined]
        get_sensor_history("FIELD_001", limit=4)
        parameters = mock_request.call_args.kwargs["params"]  # type: ignore[attr-defined]
        self.assertEqual(parameters, {"limit": 4})

    @patch("frontend.api_client.httpx.request")
    def test_api_error_becomes_clear_client_error(self, mock_request: object) -> None:
        mock_request.return_value = json_response(  # type: ignore[attr-defined]
            {"detail": "Unknown field ID: FIELD_999"}, status_code=404
        )
        with self.assertRaisesRegex(PushanAPIError, "404.*Unknown field ID"):
            get_sensor_reading("FIELD_999")

    @patch("frontend.api_client.httpx.request")
    def test_timeout_is_handled(self, mock_request: object) -> None:
        request = httpx.Request("GET", "http://127.0.0.1:8000/health")
        mock_request.side_effect = httpx.ReadTimeout(  # type: ignore[attr-defined]
            "timed out", request=request
        )
        with self.assertRaisesRegex(PushanAPIError, "timed out"):
            check_health()

    @patch("frontend.api_client.httpx.request")
    def test_malformed_json_is_handled_safely(self, mock_request: object) -> None:
        request = httpx.Request("GET", "http://127.0.0.1:8000/health")
        mock_request.return_value = httpx.Response(  # type: ignore[attr-defined]
            200, content=b"not-json", request=request
        )
        with self.assertRaisesRegex(MalformedResponseError, "unreadable response"):
            check_health()

    @patch("frontend.api_client.httpx.request")
    def test_wrong_response_shape_is_handled_safely(self, mock_request: object) -> None:
        mock_request.return_value = json_response(["not", "an", "object"])  # type: ignore[attr-defined]
        with self.assertRaisesRegex(MalformedResponseError, "expected object"):
            check_health()


def json_response(body: object, status_code: int = 200) -> httpx.Response:
    """Build a realistic HTTPX response that supports raise_for_status."""
    request = httpx.Request("GET", "http://127.0.0.1:8000/test")
    return httpx.Response(status_code, json=body, request=request)


if __name__ == "__main__":
    unittest.main()
