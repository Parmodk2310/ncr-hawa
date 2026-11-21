"""Tests for ingest/fetch_observations.py with mocked network responses."""

from __future__ import annotations

import hashlib
import io
import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

import pytest

from ingest.fetch_observations import (
    DEFAULT_PILOT_STATIONS,
    RequestTracker,
    build_hours_url,
    fetch_sensor_hours,
    main,
    normalize_iso_utc,
    run_observation_pilot,
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


def sample_hours_payload(
    param_name: str = "pm25",
    value: float = 42.5,
    records_count: int = 1,
) -> dict[str, Any]:
    """Generate valid sample /v3/sensors/{id}/hours payload."""
    results = [
        {
            "value": value,
            "flagInfo": {"hasFlags": False},
            "parameter": {
                "id": 2 if param_name == "pm25" else 1,
                "name": param_name,
                "units": "µg/m³",
                "displayName": param_name.upper(),
            },
            "period": {
                "label": "1hour",
                "interval": "01:00:00",
                "datetimeFrom": {
                    "utc": "2026-11-01T00:00:00Z",
                    "local": "2026-11-01T05:30:00+05:30",
                },
                "datetimeTo": {
                    "utc": "2026-11-01T01:00:00Z",
                    "local": "2026-11-01T06:30:00+05:30",
                },
            },
            "coordinates": None,
            "summary": {"min": 40.0, "max": 45.0, "avg": value},
            "coverage": {
                "expectedCount": 1,
                "observedCount": 1,
                "percentComplete": 100.0,
                "percentCoverage": 100.0,
            },
        }
        for _ in range(records_count)
    ]
    return {
        "meta": {
            "name": "openaq-api",
            "website": "/",
            "page": 1,
            "limit": 1000,
            "found": records_count,
        },
        "results": results,
    }


def test_normalize_iso_utc() -> None:
    """Test date parsing and UTC standardization."""
    assert (
        normalize_iso_utc("2026-11-01", is_end_of_day=False) == "2026-11-01T00:00:00Z"
    )
    assert normalize_iso_utc("2026-11-07", is_end_of_day=True) == "2026-11-07T23:59:59Z"
    assert normalize_iso_utc("2026-11-01T06:00:00Z") == "2026-11-01T06:00:00Z"


def test_build_hours_url() -> None:
    """Test URL composition for hourly sensor measurements."""
    url = build_hours_url(
        sensor_id=23534,
        datetime_from="2026-11-01T00:00:00Z",
        datetime_to="2026-11-07T23:59:59Z",
        limit=1000,
        page=1,
    )
    assert url.startswith("https://api.openaq.org/v3/sensors/23534/hours?")
    assert "datetime_from=2026-11-01T00%3A00%3A00Z" in url
    assert "datetime_to=2026-11-07T23%3A59%3A59Z" in url
    assert "limit=1000" in url
    assert "page=1" in url


def test_manifest_content_and_atomic_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    """Manifest records all 8 fields, valid hash, and no request headers."""
    raw_dir = tmp_path / "openaq"
    fixed_now = datetime(2026, 11, 21, 8, 0, 0, tzinfo=UTC)

    payload = sample_hours_payload("pm25", value=55.0)
    raw_payload_bytes = json.dumps(payload).encode("utf-8")
    expected_hash = hashlib.sha256(raw_payload_bytes).hexdigest()

    def mock_urlopen(
        req: urllib.request.Request, timeout: float = 15.0
    ) -> MockHTTPResponse:
        return MockHTTPResponse(
            data=raw_payload_bytes,
            status=200,
            headers={"content-type": "application/json", "x-ratelimit-remaining": "59"},
        )

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    monkeypatch.setattr("time.sleep", lambda _: None)

    tracker = RequestTracker(max_requests=10)
    saved, failures = fetch_sensor_hours(
        station_id=8118,
        sensor_id=23534,
        parameter="pm25",
        datetime_from="2026-11-01T00:00:00Z",
        datetime_to="2026-11-07T23:59:59Z",
        api_key="test-api-key",
        raw_dir=str(raw_dir),
        tracker=tracker,
        fetch_dt=fixed_now,
    )

    assert saved == 1
    assert failures == 0

    # Verify target file exists
    target_file = raw_dir / "8118" / "23534" / "20261121T080000Z_p1.json"
    assert target_file.exists()
    assert json.loads(target_file.read_text(encoding="utf-8")) == payload

    # Verify manifest.jsonl
    manifest_file = raw_dir / "manifest.jsonl"
    assert manifest_file.exists()
    lines = manifest_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["fetch_time_utc"] == "2026-11-21T08:00:00Z"
    assert entry["station_id"] == 8118
    assert entry["sensor_id"] == 23534
    assert entry["parameter"] == "pm25"
    assert "https://api.openaq.org/v3/sensors/23534/hours" in entry["url"]
    assert entry["http_status"] == 200
    assert entry["sha256"] == expected_hash
    assert entry["file_path"].endswith(
        "data/raw/openaq/8118/23534/20261121T080000Z_p1.json".replace(
            "data/raw/openaq", str(raw_dir).replace("\\", "/")
        )
    )

    # Crucial: verify headers are NEVER in manifest
    assert "headers" not in entry
    assert "X-API-Key" not in entry
    assert "x-ratelimit-remaining" not in entry


def test_no_overwrite_and_check_existence_before_request(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    """Pre-existing file is never overwritten and no HTTP call is made."""
    raw_dir = tmp_path / "openaq"
    fixed_now = datetime(2026, 11, 21, 8, 0, 0, tzinfo=UTC)

    target_file = raw_dir / "8118" / "23534" / "20261121T080000Z_p1.json"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(json.dumps({"initial": "unmodified"}), encoding="utf-8")

    called = False

    def mock_urlopen(
        req: urllib.request.Request, timeout: float = 15.0
    ) -> MockHTTPResponse:
        nonlocal called
        called = True
        return MockHTTPResponse(data=b"{}", status=200)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    tracker = RequestTracker(max_requests=10)
    saved, failures = fetch_sensor_hours(
        station_id=8118,
        sensor_id=23534,
        parameter="pm25",
        datetime_from="2026-11-01T00:00:00Z",
        datetime_to="2026-11-07T23:59:59Z",
        api_key="test-api-key",
        raw_dir=str(raw_dir),
        tracker=tracker,
        fetch_dt=fixed_now,
    )

    assert called is False
    assert saved == 0
    assert failures == 0
    assert json.loads(target_file.read_text(encoding="utf-8")) == {
        "initial": "unmodified"
    }


def test_validation_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    """Invalid payload is not saved to archive and logs failure."""
    raw_dir = tmp_path / "openaq"
    fixed_now = datetime(2026, 11, 21, 8, 0, 0, tzinfo=UTC)

    # Invalid JSON missing 'results'
    bad_payload = {"meta": {"name": "openaq-api", "page": 1}}

    def mock_urlopen(
        req: urllib.request.Request, timeout: float = 15.0
    ) -> MockHTTPResponse:
        return MockHTTPResponse(
            data=json.dumps(bad_payload).encode("utf-8"), status=200
        )

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    monkeypatch.setattr("time.sleep", lambda _: None)

    tracker = RequestTracker(max_requests=10)
    saved, failures = fetch_sensor_hours(
        station_id=8118,
        sensor_id=23534,
        parameter="pm25",
        datetime_from="2026-11-01T00:00:00Z",
        datetime_to="2026-11-07T23:59:59Z",
        api_key="test-api-key",
        raw_dir=str(raw_dir),
        tracker=tracker,
        fetch_dt=fixed_now,
    )

    assert saved == 0
    assert failures == 1

    # Verify target file does NOT exist
    target_file = raw_dir / "8118" / "23534" / "20261121T080000Z_p1.json"
    assert not target_file.exists()

    # Verify failures.jsonl
    failures_file = raw_dir / "failures.jsonl"
    assert failures_file.exists()
    lines = failures_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    f_entry = json.loads(lines[0])
    assert f_entry["station_id"] == 8118
    assert f_entry["sensor_id"] == 23534
    assert f_entry["error"] == "validation_failed"
    assert "missing_or_invalid_results" in f_entry["error_detail"]


def test_401_with_no_key_leak(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Any,
) -> None:
    """HTTP 401 prints 'API key rejected' with no key text and logs failure."""
    raw_dir = tmp_path / "openaq"
    fixed_now = datetime(2026, 11, 21, 8, 0, 0, tzinfo=UTC)
    secret_key = "super-secret-production-token-42"

    def mock_urlopen(
        req: urllib.request.Request, timeout: float = 15.0
    ) -> MockHTTPResponse:
        raise urllib.error.HTTPError(
            url=req.full_url,
            code=401,
            msg="Unauthorized",
            hdrs=None,  # type: ignore[arg-type]
            fp=io.BytesIO(b'{"detail":"Invalid API Key"}'),
        )

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    monkeypatch.setattr("time.sleep", lambda _: None)

    tracker = RequestTracker(max_requests=10)
    saved, failures = fetch_sensor_hours(
        station_id=8118,
        sensor_id=23534,
        parameter="pm25",
        datetime_from="2026-11-01T00:00:00Z",
        datetime_to="2026-11-07T23:59:59Z",
        api_key=secret_key,
        raw_dir=str(raw_dir),
        tracker=tracker,
        fetch_dt=fixed_now,
    )

    captured = capsys.readouterr()
    assert "API key rejected" in captured.err
    assert secret_key not in captured.err
    assert secret_key not in captured.out

    assert saved == 0
    assert failures == 1

    # Verify failure recorded with 401
    failures_file = raw_dir / "failures.jsonl"
    assert failures_file.exists()
    content = failures_file.read_text(encoding="utf-8")
    assert secret_key not in content
    assert '"http_status": 401' in content


def test_cap_warning(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Any,
) -> None:
    """Warning is displayed when request cap is reached and run stops."""
    raw_dir = tmp_path / "openaq"
    monkeypatch.setenv("OPENAQ_API_KEY", "dummy-key")
    monkeypatch.setattr("time.sleep", lambda _: None)

    payload = sample_hours_payload("pm25", value=30.0)

    def mock_urlopen(
        req: urllib.request.Request, timeout: float = 15.0
    ) -> MockHTTPResponse:
        return MockHTTPResponse(data=payload, status=200)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    # Set max_requests to 2; with 5 stations x 2 sensors, cap will halt run early
    exit_code = run_observation_pilot(
        datetime_from="2026-11-01",
        datetime_to="2026-11-07",
        raw_dir=str(raw_dir),
        max_requests=2,
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert (
        "Warning: Request cap (--max-requests) was reached during the run."
        in captured.err
    )
    assert "HTTP requests made: 2/2" in captured.out


def test_dry_run_makes_no_request(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Any,
) -> None:
    """--dry-run prints planned paths and URLs without network requests or API key."""
    raw_dir = tmp_path / "openaq"

    # Network block is active; if urlopen is called, test will fail
    exit_code = run_observation_pilot(
        datetime_from="2026-11-01",
        datetime_to="2026-11-07",
        raw_dir=str(raw_dir),
        dry_run=True,
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "[DRY-RUN]" in captured.out
    assert "station=8118 sensor=23534 param=pm25" in captured.out
    assert "Station 8118: no PM10 sensor (skipped)" in captured.out
    assert "station=6934 sensor=12235011 param=pm25" in captured.out
    assert "station=6934 sensor=12235010 param=pm10" in captured.out
    assert "Stations with no PM10 sensor (skipped): [8118]" in captured.out


def test_atomic_write_leaves_no_partial_file(
    tmp_path: Any,
) -> None:
    """Atomic write failure cleans up temporary file and leaves no partial output."""
    target = tmp_path / "test_file.json"

    with pytest.raises(TypeError):
        # Passing non-bytes to trigger failure during write
        write_raw_file_atomically(str(target), 12345)  # type: ignore[arg-type]

    assert not target.exists()
    assert not (tmp_path / "test_file.json.tmp").exists()


def test_skip_missing_pm10_sensor_reported_in_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Any,
) -> None:
    """Station lacking PM10 sensor skips PM10 and reports in summary without error."""
    raw_dir = tmp_path / "openaq"
    monkeypatch.setenv("OPENAQ_API_KEY", "dummy-key")
    monkeypatch.setattr("time.sleep", lambda _: None)

    # Use only station 8118 (Central Delhi AirNow), which lacks PM10
    station_8118 = [s for s in DEFAULT_PILOT_STATIONS if s["station_id"] == 8118]

    payload = sample_hours_payload("pm25", value=45.0)

    def mock_urlopen(
        req: urllib.request.Request, timeout: float = 15.0
    ) -> MockHTTPResponse:
        return MockHTTPResponse(data=payload, status=200)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    exit_code = run_observation_pilot(
        datetime_from="2026-11-01",
        datetime_to="2026-11-07",
        raw_dir=str(raw_dir),
        stations=station_8118,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Station 8118: no PM10 sensor (skipped)" in captured.out
    assert "Stations with no PM10 sensor (skipped): [8118]" in captured.out
    assert "Failures recorded: 0" in captured.out
    assert "Files saved: 1" in captured.out


def test_retry_backoff_on_429_and_5xx(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    """HTTP 429 and 500 retry with backoff and succeed on subsequent attempt."""
    raw_dir = tmp_path / "openaq"
    monkeypatch.setattr("time.sleep", lambda _: None)

    calls = 0

    def mock_urlopen(
        req: urllib.request.Request, timeout: float = 15.0
    ) -> MockHTTPResponse:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise urllib.error.HTTPError(
                url=req.full_url,
                code=429,
                msg="Too Many Requests",
                hdrs=None,  # type: ignore[arg-type]
                fp=io.BytesIO(b"Rate limit exceeded"),
            )
        if calls == 2:
            raise urllib.error.HTTPError(
                url=req.full_url,
                code=502,
                msg="Bad Gateway",
                hdrs=None,  # type: ignore[arg-type]
                fp=io.BytesIO(b"Bad Gateway"),
            )
        return MockHTTPResponse(data=sample_hours_payload(), status=200)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    tracker = RequestTracker(max_requests=10)
    saved, failures = fetch_sensor_hours(
        station_id=8118,
        sensor_id=23534,
        parameter="pm25",
        datetime_from="2026-11-01T00:00:00Z",
        datetime_to="2026-11-07T23:59:59Z",
        api_key="test-api-key",
        raw_dir=str(raw_dir),
        tracker=tracker,
        fetch_dt=datetime(2026, 11, 21, 8, 0, 0, tzinfo=UTC),
    )

    assert calls == 3
    assert saved == 1
    assert failures == 0


def test_cli_execution_dry_run(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Any,
) -> None:
    """CLI execution with --dry-run prints plan and exits 0."""
    raw_dir = tmp_path / "openaq"
    argv = [
        "--from",
        "2026-11-01",
        "--to",
        "2026-11-07",
        "--raw-dir",
        str(raw_dir),
        "--dry-run",
    ]
    exit_code = main(argv)
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "[DRY-RUN]" in captured.out
