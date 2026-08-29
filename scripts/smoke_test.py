"""Readable HTTP smoke test for a running Pushan API."""

import argparse
import sys

import httpx


def run(base_url: str) -> None:
    client = httpx.Client(base_url=base_url.rstrip("/"), timeout=60)
    checks = [
        ("health", "GET", "/health", None),
        ("readiness", "GET", "/ready", None),
        ("fields", "GET", "/fields", None),
        ("sensor", "GET", "/fields/FIELD_001/sensor", None),
        ("recommendation", "POST", "/irrigation/recommend", {
            "field_id": "FIELD_001", "crop": "tomato",
            "crop_stage": "flowering", "field_area_m2": 1000,
        }),
        ("agent", "POST", "/agent/run", {
            "message": "Assess FIELD_001"
        }),
        ("history", "GET", "/fields/FIELD_001/history/actions", None),
    ]
    for name, method, path, payload in checks:
        response = client.request(method, path, json=payload)
        response.raise_for_status()
        print(f"PASS {name}: {response.status_code}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test a running Pushan API")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    try:
        run(args.base_url)
    except (httpx.HTTPError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
