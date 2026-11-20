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
    main,
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

    # 1 area * 2 sources = 2 calls (no retries on 400)
    assert call_count == 2
    assert stats["failed"] == 2
    assert stats["success"] == 0

    # Failures log should exist and contain both failures
    fail_file = raw_dir / "failures.jsonl"
    assert fail_file.exists()
    fail_lines = fail_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(fail_lines) == 2

    # Manifest should not be created
    assert not (raw_dir / "manifest.jsonl").exists()
    # No raw json file created
    assert len(list(raw_dir.glob("**/*.json"))) == 0


def test_pre_existing_target_file_skips_fetch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Pre-existing target file must skip request and not duplicate manifest."""
    raw_dir = tmp_path / "raw"
    fixed_time = datetime(2026, 11, 19, 12, 0, 0, tzinfo=UTC)
    fetch_time_file = fixed_time.strftime("%Y%m%d%H%M00Z")

    pre_existing = raw_dir / "cams" / "test_area" / f"{fetch_time_file}.json"
    pre_existing.parent.mkdir(parents=True, exist_ok=True)
    pre_existing.write_text('{"cached": true}', encoding="utf-8")

    calls = 0

    def mock_urlopen(req: urllib.request.Request, *args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        return MockHTTPResponse({"hourly": {"time": ["t"], "temperature_2m": [1.0]}})

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

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
        now_utc=fixed_time,
    )

    assert stats["skipped"] == 1
    assert stats["success"] == 1
    # Only 1 network call made (for weather, cams was skipped)
    assert calls == 1

    captured = capsys.readouterr()
    assert "already exists for this minute" in captured.out


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

    # Check first manifest line (cams)
    m1 = json.loads(lines[0])
    assert m1["source"] == "cams"
    assert m1["area_id"] == "central_delhi"
    assert m1["model"] == "default"
    assert m1["request_url_has_models"] is False
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
            "temperature_2m": [20.0],
        }
    }

    def mock_urlopen(req: urllib.request.Request, *args: Any, **kwargs: Any) -> Any:
        url = req.full_url
        if "latitude=28.0" in url:
            raise urllib.error.HTTPError(
                url=url,
                code=500,
                msg="Internal Error",
                hdrs={},  # type: ignore[arg-type]
                fp=io.BytesIO(b"server error"),
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
                        "area_id": "fail_area",
                        "name": "Fail",
                        "latitude": 28.0,
                        "longitude": 77.0,
                    },
                    {
                        "area_id": "good_area",
                        "name": "Good",
                        "latitude": 28.5,
                        "longitude": 77.5,
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
                    "hourly": ["pm2_5"],
                }
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


def test_pinned_weather_models_archive_layout_and_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    """Verify WP1 model pinning: ecmwf and gfs requests and layout."""
    mock_payload = {
        "hourly": {
            "time": ["2026-11-20T00:00"],
            "temperature_2m": [15.2],
            "pm2_5": [60.1],
        }
    }
    requested_urls: list[str] = []

    def mock_urlopen(req: urllib.request.Request, *args: Any, **kwargs: Any) -> Any:
        requested_urls.append(req.full_url)
        return MockHTTPResponse(mock_payload)

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
                        "name": "Central Delhi",
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
                    "models": [
                        {
                            "model": "ecmwf_ifs025",
                            "folder": "weather_ecmwf",
                        },
                        {
                            "model": "ncep_gfs_seamless",
                            "folder": "weather_gfs",
                        },
                    ],
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

    # 1 area * (1 cams + 2 weather models) = 3 calls
    assert stats["success"] == 3
    assert stats["failed"] == 0
    assert len(requested_urls) == 3

    # Check request URLs
    cams_url = [u for u in requested_urls if "air-quality" in u][0]
    ecmwf_url = [u for u in requested_urls if "models=ecmwf_ifs025" in u][0]
    gfs_url = [u for u in requested_urls if "models=ncep_gfs_seamless" in u][0]

    assert "domains=cams_global" in cams_url
    assert "models=" not in cams_url
    assert "models=ecmwf_ifs025" in ecmwf_url
    assert "models=ncep_gfs_seamless" in gfs_url

    # Check files exist in data/raw/open_meteo/weather_ecmwf/ and weather_gfs/
    ecmwf_files = list((raw_dir / "weather_ecmwf" / "central_delhi").glob("*.json"))
    gfs_files = list((raw_dir / "weather_gfs" / "central_delhi").glob("*.json"))
    cams_files = list((raw_dir / "cams" / "central_delhi").glob("*.json"))

    assert len(ecmwf_files) == 1
    assert len(gfs_files) == 1
    assert len(cams_files) == 1

    # Check manifest entries
    manifest_lines = (
        (raw_dir / "manifest.jsonl").read_text(encoding="utf-8").strip().splitlines()
    )
    assert len(manifest_lines) == 3
    parsed = [json.loads(line) for line in manifest_lines]

    cams_entry = [p for p in parsed if p["source"] == "cams"][0]
    assert cams_entry["model"] == "default"
    assert cams_entry["request_url_has_models"] is False
    assert "/cams/central_delhi/" in cams_entry["file_path"]

    ecmwf_entry = [p for p in parsed if p["model"] == "ecmwf_ifs025"][0]
    assert ecmwf_entry["source"] == "weather"
    assert ecmwf_entry["request_url_has_models"] is True
    assert "weather_ecmwf/central_delhi" in ecmwf_entry["file_path"]

    gfs_entry = [p for p in parsed if p["model"] == "ncep_gfs_seamless"][0]
    assert gfs_entry["source"] == "weather"
    assert gfs_entry["request_url_has_models"] is True
    assert "weather_gfs/central_delhi" in gfs_entry["file_path"]


def test_main_exits_nonzero_on_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    """main() must exit with non-zero exit code if any request fails."""

    def mock_urlopen(req: urllib.request.Request, *args: Any, **kwargs: Any) -> Any:
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
                    "hourly": ["pm2_5"],
                }
            }
        ),
        encoding="utf-8",
    )

    argv = [
        "--areas",
        str(areas_cfg),
        "--vars",
        str(vars_cfg),
        "--raw-dir",
        str(raw_dir),
        "--delay",
        "0.0",
    ]

    with pytest.raises(SystemExit) as exc_info:
        main(argv)

    assert exc_info.value.code != 0


def test_main_exits_zero_on_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    """main() must exit cleanly with code 0 on full success."""
    mock_payload = {
        "hourly": {
            "time": ["2026-11-20T00:00"],
            "pm2_5": [40.0],
        }
    }

    def mock_urlopen(req: urllib.request.Request, *args: Any, **kwargs: Any) -> Any:
        return MockHTTPResponse(mock_payload)

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
                    "hourly": ["pm2_5"],
                }
            }
        ),
        encoding="utf-8",
    )

    argv = [
        "--areas",
        str(areas_cfg),
        "--vars",
        str(vars_cfg),
        "--raw-dir",
        str(raw_dir),
        "--delay",
        "0.0",
    ]

    # Does not raise SystemExit
    main(argv)
