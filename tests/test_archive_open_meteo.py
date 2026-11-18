"""Tests for ingest/archive_open_meteo.py with mocked network responses."""

from __future__ import annotations

import hashlib
import io
import json
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

import pytest

from ingest.archive_open_meteo import (
    archive_forecasts,
    build_request_url,
    fetch_with_retries,
    validate_response_payload,
    write_raw_file_atomically,
)


class MockHTTPResponse:
    """Mock urllib response object."""

    def __init__(
        self,
        data: dict[str, Any] | bytes,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        if isinstance(data, bytes):
            self._raw = data
        else:
            self._raw = json.dumps(data).encode("utf-8")
        self.status = status
        self.headers = headers or {}

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> MockHTTPResponse:
        return self

    def __exit__(self, *args: object) -> None:
        pass


def test_dry_run_makes_no_network_requests(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Any,
) -> None:
    """--dry-run must print planned URLs and targets without network calls."""
    areas_cfg = tmp_path / "areas.json"
    vars_cfg = tmp_path / "vars.json"

    areas_cfg.write_text(
        json.dumps(
            {
                "areas": [
                    {
                        "area_id": "test_area",
                        "name": "Test",
                        "latitude": 28.5,
                        "longitude": 77.2,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    vars_cfg.write_text(
        json.dumps(
            {
                "cams": {
                    "endpoint": "https://air-quality-api.open-meteo.com/v1/air-quality",
                    "domains": "cams_global",
                    "hourly": ["pm2_5"],
                },
                "weather": {
                    "endpoint": "https://api.open-meteo.com/v1/forecast",
                    "hourly": ["temperature_2m"],
                },
            }
        ),
        encoding="utf-8",
    )

    stats = archive_forecasts(
        areas_path=str(areas_cfg),
        vars_path=str(vars_cfg),
        raw_dir=str(tmp_path / "raw"),
        dry_run=True,
    )

    assert stats == {"success": 0, "skipped": 0, "failed": 0}
    captured = capsys.readouterr()
    assert "[DRY RUN] source=cams area=test_area" in captured.out
    assert "[DRY RUN] source=weather area=test_area" in captured.out
    assert "domains=cams_global" in captured.out


def test_cams_url_includes_domains_parameter() -> None:
    """Verify build_request_url includes domains=cams_global for CAMS requests."""
    url = build_request_url(
        endpoint="https://air-quality-api.open-meteo.com/v1/air-quality",
        lat=28.61,
        lon=77.21,
        hourly_vars=["pm2_5", "pm10"],
        domains="cams_global",
    )
    assert "domains=cams_global" in url
    assert "hourly=pm2_5%2Cpm10" in url or "hourly=pm2_5,pm10" in url
    assert "forecast_days=5" in url
    assert "timezone=UTC" in url


def test_http_400_handling_logs_to_failures_no_archive(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    """HTTP 400 must log failure, avoid retry, and not write to archive."""
    call_count = 0

    def mock_urlopen(req: urllib.request.Request, *args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        call_count += 1
        raise urllib.error.HTTPError(
            url=req.full_url,
            code=400,
            msg="Bad Request",
            hdrs={},  # type: ignore[arg-type]
            fp=io.BytesIO(b'{"error":true,"reason":"Invalid variable"}'),
        )

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    areas_cfg = tmp_path / "areas.json"
    vars_cfg = tmp_path / "vars.json"
    raw_dir = tmp_path / "raw"

    areas_cfg.write_text(
        json.dumps(
            {
                "areas": [
                    {
                        "area_id": "test_area",
                        "name": "Test",
                        "latitude": 28.5,
                        "longitude": 77.2,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    vars_cfg.write_text(
        json.dumps(
            {
                "cams": {
                    "endpoint": "https://air-quality-api.open-meteo.com/v1/air-quality",
                    "domains": "cams_global",
                    "hourly": ["invalid_var"],
                },
                "weather": {
                    "endpoint": "https://api.open-meteo.com/v1/forecast",
                    "hourly": ["temperature_2m"],
                },
            }
        ),
        encoding="utf-8",
    )

    stats = archive_forecasts(
        areas_path=str(areas_cfg),
        vars_path=str(vars_cfg),
        raw_dir=str(raw_dir),
        delay_sec=0.0,
    )

    # 1 area * 2 sources = 2 calls (no retries on 400)
    assert call_count == 2
    assert stats["failed"] == 2
    assert stats["success"] == 0

    failures_file = raw_dir / "failures.jsonl"
    assert failures_file.exists()
    lines = failures_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    record = json.loads(lines[0])
    assert record["http_status"] == 400
    assert "Invalid variable" in record["reason"]

    # Manifest should not be created
    assert not (raw_dir / "manifest.jsonl").exists()
    # No raw json file created
    assert not os.path.exists(raw_dir / "cams" / "test_area")


def test_validation_failure_missing_variable_logs_to_failures() -> None:
    """Response missing required hourly variables must fail validation."""
    mock_payload = {
        "hourly": {
            "time": ["2026-11-19T00:00", "2026-11-19T01:00"],
            "pm2_5": [50.0, 55.0],
            # pm10 is missing!
        }
    }

    data, err = validate_response_payload(
        json.dumps(mock_payload).encode("utf-8"),
        expected_vars=["pm2_5", "pm10"],
    )
    assert data is None
    assert "missing_hourly_variables: pm10" in str(err)


def test_validation_failure_missing_time() -> None:
    """Response missing hourly.time must fail validation."""
    payload = {"hourly": {"pm2_5": [10.0]}}
    data, err = validate_response_payload(
        json.dumps(payload).encode("utf-8"),
        expected_vars=["pm2_5"],
    )
    assert data is None
    assert "missing_or_empty_hourly_time" in str(err)


def test_atomic_write_no_partial_file_on_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """Verify atomic write cleans up .tmp file when write/replace fails."""
    target = str(tmp_path / "corrupt_test.json")
    tmp_target = f"{target}.tmp"

    def mock_replace(src: str, dst: str) -> None:
        raise OSError("Simulated filesystem error during atomic replace")

    monkeypatch.setattr(os, "replace", mock_replace)

    with pytest.raises(OSError, match="Simulated filesystem error"):
        write_raw_file_atomically(target, b'{"valid":"bytes"}')

    assert not os.path.exists(target)
    assert not os.path.exists(tmp_target)


def test_idempotency_skips_request_if_target_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Pre-existing target file must skip request and not duplicate manifest."""
    raw_dir = tmp_path / "raw"
    existing_file = raw_dir / "cams" / "test_area" / "20261119024000Z.json"
    existing_file.parent.mkdir(parents=True, exist_ok=True)
    existing_file.write_text('{"existing":"data"}', encoding="utf-8")

    def fail_if_called(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("urlopen should not have been called!")

    monkeypatch.setattr(urllib.request, "urlopen", fail_if_called)

    areas_cfg = tmp_path / "areas.json"
    vars_cfg = tmp_path / "vars.json"
    areas_cfg.write_text(
        json.dumps(
            {
                "areas": [
                    {
                        "area_id": "test_area",
                        "name": "Test",
                        "latitude": 28.5,
                        "longitude": 77.2,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    vars_cfg.write_text(
        json.dumps(
            {
                "cams": {
                    "endpoint": "https://air-quality-api.open-meteo.com/v1/air-quality",
                    "domains": "cams_global",
                    "hourly": ["pm2_5"],
                },
            }
        ),
        encoding="utf-8",
    )

    fixed_time = datetime(2026, 11, 19, 2, 40, 0, tzinfo=UTC)

    stats = archive_forecasts(
        areas_path=str(areas_cfg),
        vars_path=str(vars_cfg),
        raw_dir=str(raw_dir),
        delay_sec=0.0,
        now_utc=fixed_time,
    )

    assert stats["skipped"] == 1
    assert stats["success"] == 0
    captured = capsys.readouterr()
    assert "already exists for this minute" in captured.out
    assert not (raw_dir / "manifest.jsonl").exists()


def test_successful_archive_flow_and_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    """Successful archive writes exact file and generates verified manifest line."""
    mock_cams = {
        "hourly": {
            "time": ["2026-11-19T00:00"],
            "pm2_5": [45.2],
        }
    }
    mock_weather = {
        "hourly": {
            "time": ["2026-11-19T00:00"],
            "temperature_2m": [18.5],
        }
    }

    def mock_urlopen(req: urllib.request.Request, *args: Any, **kwargs: Any) -> Any:
        url = req.full_url
        if "air-quality" in url:
            return MockHTTPResponse(mock_cams)
        return MockHTTPResponse(mock_weather)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    areas_cfg = tmp_path / "areas.json"
    vars_cfg = tmp_path / "vars.json"
    raw_dir = tmp_path / "raw"

    areas_cfg.write_text(
        json.dumps(
            {
                "areas": [
                    {
                        "area_id": "central_delhi",
                        "name": "Delhi",
                        "latitude": 28.61,
                        "longitude": 77.21,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    vars_cfg.write_text(
        json.dumps(
            {
                "cams": {
                    "endpoint": "https://air-quality-api.open-meteo.com/v1/air-quality",
                    "domains": "cams_global",
                    "hourly": ["pm2_5"],
                },
                "weather": {
                    "endpoint": "https://api.open-meteo.com/v1/forecast",
                    "hourly": ["temperature_2m"],
                },
            }
        ),
        encoding="utf-8",
    )

    stats = archive_forecasts(
        areas_path=str(areas_cfg),
        vars_path=str(vars_cfg),
        raw_dir=str(raw_dir),
        delay_sec=0.0,
    )

    assert stats["success"] == 2
    assert stats["failed"] == 0

    manifest_file = raw_dir / "manifest.jsonl"
    assert manifest_file.exists()
    lines = manifest_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

    # Check first manifest line
    m1 = json.loads(lines[0])
    assert m1["source"] == "cams"
    assert m1["area_id"] == "central_delhi"
    assert m1["http_status"] == 200
    assert "file_path" in m1
    assert os.path.exists(m1["file_path"])

    with open(m1["file_path"], "rb") as f:
        data = f.read()
    assert hashlib.sha256(data).hexdigest() == m1["sha256"]


def test_failure_of_one_area_does_not_stop_others(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    """If one area fails with HTTP 500, other areas must continue and succeed."""
    mock_valid = {
        "hourly": {
            "time": ["2026-11-19T00:00"],
            "pm2_5": [50.0],
        }
    }

    def mock_urlopen(req: urllib.request.Request, *args: Any, **kwargs: Any) -> Any:
        url = req.full_url
        if "28.5" in url:
            # Area 1 fails with 500
            raise urllib.error.HTTPError(
                url=url,
                code=500,
                msg="Server Error",
                hdrs={},  # type: ignore[arg-type]
                fp=io.BytesIO(b"error"),
            )
        return MockHTTPResponse(mock_valid)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    areas_cfg = tmp_path / "areas.json"
    vars_cfg = tmp_path / "vars.json"
    raw_dir = tmp_path / "raw"

    areas_cfg.write_text(
        json.dumps(
            {
                "areas": [
                    {
                        "area_id": "area_fail",
                        "name": "Fail",
                        "latitude": 28.5,
                        "longitude": 77.1,
                    },
                    {
                        "area_id": "area_ok",
                        "name": "OK",
                        "latitude": 28.6,
                        "longitude": 77.2,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    vars_cfg.write_text(
        json.dumps(
            {
                "cams": {
                    "endpoint": "https://air-quality-api.open-meteo.com/v1/air-quality",
                    "domains": "cams_global",
                    "hourly": ["pm2_5"],
                },
            }
        ),
        encoding="utf-8",
    )

    stats = archive_forecasts(
        areas_path=str(areas_cfg),
        vars_path=str(vars_cfg),
        raw_dir=str(raw_dir),
        delay_sec=0.0,
    )

    assert stats["failed"] == 1
    assert stats["success"] == 1
    assert (raw_dir / "failures.jsonl").exists()
    assert (raw_dir / "manifest.jsonl").exists()


def test_retry_backoff_on_429_and_5xx(monkeypatch: pytest.MonkeyPatch) -> None:
    """429 and 5xx trigger exponential retries."""
    attempts = 0

    def mock_urlopen(req: urllib.request.Request, *args: Any, **kwargs: Any) -> Any:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise urllib.error.HTTPError(
                url=req.full_url,
                code=429,
                msg="Too Many Requests",
                hdrs={"Retry-After": "0.01"},  # type: ignore[arg-type]
                fp=io.BytesIO(b"rate limit"),
            )
        if attempts == 2:
            raise urllib.error.HTTPError(
                url=req.full_url,
                code=503,
                msg="Unavailable",
                hdrs={},  # type: ignore[arg-type]
                fp=io.BytesIO(b"unavailable"),
            )
        return MockHTTPResponse(b'{"status":"ok"}')

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    status, raw, err = fetch_with_retries(
        "https://test.endpoint", timeout=5.0, max_retries=3, delay_sec=0.0
    )
    assert attempts == 3
    assert status == 200
    assert raw == b'{"status":"ok"}'
    assert err is None
