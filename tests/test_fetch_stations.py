"""Tests for ingest/fetch_stations.py with mocked network responses."""

from __future__ import annotations

import csv
import io
import json
import os
import socket
import urllib.error
import urllib.request
from typing import Any

import pytest

from ingest.fetch_stations import (
    CSV_COLUMNS,
    build_csv_rows,
    fetch_locations,
    format_flag,
    get_api_key,
    make_request,
    parse_found,
    run_audit,
)


class MockHTTPResponse:
    """Mock urllib response object."""

    def __init__(
        self,
        data: dict[str, Any],
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.data = data
        self.status = status
        self.headers = headers or {}
        self._raw = json.dumps(data).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> MockHTTPResponse:
        return self

    def __exit__(self, *args: object) -> None:
        pass


def test_network_block_fixture_works() -> None:
    """Verify that unmocked socket calls are blocked by test fixture."""
    with pytest.raises(RuntimeError, match="Real network access is blocked in tests!"):
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)


@pytest.mark.parametrize(
    ("found_input", "expected_count", "expected_str"),
    [
        (100, 100, "100"),
        (">100", None, ">100"),
        ("abc", None, "unknown"),
        (None, None, "unknown"),
        (" 250 ", 250, "250"),
    ],
)
def test_parse_found_defensive(
    found_input: Any, expected_count: int | None, expected_str: str
) -> None:
    """Ensure meta.found parsing handles int, >100, text, and None safely."""
    count, display = parse_found(found_input)
    assert count == expected_count
    assert display == expected_str


def test_parse_found_missing_key() -> None:
    """Missing found key in meta dict must default to unknown safely."""
    meta: dict[str, Any] = {}
    count, display = parse_found(meta.get("found"))
    assert count is None
    assert display == "unknown"


def test_format_flag_never_defaults_to_false() -> None:
    """Absent or None flags must return empty string, never False."""
    assert format_flag(None) == ""
    assert format_flag("") == ""
    assert format_flag(True) == "True"
    assert format_flag(False) == "False"


def test_missing_api_key_exits_without_secrets(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Ensure missing OPENAQ_API_KEY causes clean exit with clear error."""
    monkeypatch.delenv("OPENAQ_API_KEY", raising=False)
    with pytest.raises(SystemExit) as exc_info:
        get_api_key()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error: OPENAQ_API_KEY environment variable is not set." in captured.err


def test_http_401_exits_with_api_key_rejected_no_key_leak(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Any,
) -> None:
    """HTTP 401 must print 'API key rejected' and leak no key characters."""
    secret_key = "super-secret-key-xyz-98765"
    monkeypatch.setenv("OPENAQ_API_KEY", secret_key)

    def mock_urlopen(req: urllib.request.Request, *args: Any, **kwargs: Any) -> Any:
        raise urllib.error.HTTPError(
            url=req.full_url,
            code=401,
            msg="Unauthorized",
            hdrs={},  # type: ignore[arg-type]
            fp=io.BytesIO(b'{"message":"Unauthorized"}'),
        )

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    output_csv = str(tmp_path / "test_licences.csv")
    with pytest.raises(SystemExit) as exc_info:
        run_audit(
            output_path=output_csv,
            bbox="76.5,27.8,78.2,29.2",
            max_pages=1,
            delay_sec=0.0,
        )
    assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "API key rejected" in captured.err
    # Guarantee no key leakage
    assert secret_key not in captured.err
    assert secret_key not in captured.out


def test_parse_locations_and_licenses_join(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test full audit flow with mocked location and licence responses."""
    monkeypatch.setenv("OPENAQ_API_KEY", "dummy-test-key")

    mock_locations_payload = {
        "meta": {"found": ">100", "page": 1, "limit": 100},
        "results": [
            {
                "id": 101,
                "name": "Anand Vihar, Delhi",
                "provider": {"id": 1, "name": "CPCB"},
                "coordinates": {"latitude": 28.6468, "longitude": 77.3160},
                "isMonitor": True,
                "isMobile": False,
                "datetimeFirst": {"utc": "2018-01-01T00:00:00Z"},
                "datetimeLast": {"utc": "2026-11-15T00:00:00Z"},
                "sensors": [{"id": 1, "parameter": {"id": 2, "name": "pm25"}}],
                "licenses": [{"id": 41, "name": "CC BY 4.0"}],
            },
            {
                "id": 102,
                "name": "Sector 62, Noida",
                "provider": {"id": 2, "name": "UPPCB"},
                "coordinates": {"latitude": 28.6245, "longitude": 77.3649},
                "isMonitor": True,
                "isMobile": False,
                "datetimeFirst": {"utc": "2019-01-01T00:00:00Z"},
                "datetimeLast": {"utc": "2026-11-15T00:00:00Z"},
                "sensors": [{"id": 2, "parameter": {"id": 5, "name": "no2"}}],
                "licenses": [{"id": 42, "name": "Custom License"}],
            },
            {
                "id": 103,
                "name": "Unlicensed Station",
                "provider": {"id": 3, "name": "Other Provider"},
                "coordinates": {"latitude": 28.5000, "longitude": 77.2000},
                "isMonitor": False,
                "isMobile": True,
                "datetimeFirst": None,
                "datetimeLast": None,
                "sensors": [],
                "licenses": [],
            },
        ],
    }

    mock_licenses_payload = {
        "results": [
            {
                "id": 41,
                "name": "CC BY 4.0",
                "commercialUseAllowed": True,
                "attributionRequired": True,
                "redistributionAllowed": True,
                "sourceUrl": "https://creativecommons.org/licenses/by/4.0/",
            },
            {
                "id": 42,
                "name": "Custom License",
                # Absent/unknown -> must become empty string ""
                "commercialUseAllowed": None,
                "attributionRequired": True,
                "redistributionAllowed": False,
                "sourceUrl": "https://example.com/custom-terms",
            },
        ]
    }

    def mock_urlopen(req: urllib.request.Request, *args: Any, **kwargs: Any) -> Any:
        url = req.full_url
        if "/locations" in url:
            return MockHTTPResponse(mock_locations_payload)
        if "/licenses" in url:
            return MockHTTPResponse(mock_licenses_payload)
        raise ValueError(f"Unexpected URL: {url}")

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    output_csv = str(tmp_path / "licences.csv")
    rows = run_audit(
        output_path=output_csv,
        bbox="76.5,27.8,78.2,29.2",
        max_pages=1,
        delay_sec=0.0,
    )

    assert len(rows) == 3
    assert os.path.exists(output_csv)

    # Read back CSV and verify exact columns and data
    with open(output_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == CSV_COLUMNS
        saved_rows = list(reader)

    assert len(saved_rows) == 3

    # Check station 101
    s101 = saved_rows[0]
    assert s101["station_id"] == "101"
    assert s101["name"] == "Anand Vihar, Delhi"
    assert s101["provider"] == "CPCB"
    assert s101["lat"] == "28.6468"
    assert s101["lon"] == "77.316"
    assert s101["licence_name"] == "CC BY 4.0"
    assert s101["commercialUseAllowed"] == "True"
    assert s101["attributionRequired"] == "True"
    assert s101["redistributionAllowed"] == "True"
    assert s101["source_url"] == "https://creativecommons.org/licenses/by/4.0/"
    assert s101["decision"] == ""
    assert s101["is_monitor"] == "True"
    assert s101["is_mobile"] == "False"
    assert s101["has_pm25"] == "True"
    assert s101["datetime_first"] == "2018-01-01T00:00:00Z"
    assert s101["datetime_last"] == "2026-11-15T00:00:00Z"

    # Check station 102 (absent commercialUseAllowed must be empty string, NOT False)
    s102 = saved_rows[1]
    assert s102["station_id"] == "102"
    assert s102["commercialUseAllowed"] == ""
    assert s102["attributionRequired"] == "True"
    assert s102["redistributionAllowed"] == "False"
    assert s102["has_pm25"] == "False"

    # Check station 103 (unlicensed)
    s103 = saved_rows[2]
    assert s103["station_id"] == "103"
    assert s103["licence_name"] == ""
    assert s103["commercialUseAllowed"] == ""
    assert s103["attributionRequired"] == ""
    assert s103["redistributionAllowed"] == ""
    assert s103["is_mobile"] == "True"
    assert s103["has_pm25"] == ""

    # Check summary output in stdout
    captured = capsys.readouterr()
    assert "Total stations fetched: 3" in captured.out
    assert "CC BY 4.0: 1" in captured.out
    assert "Custom License: 1" in captured.out


def test_rate_limit_429_triggers_backoff_and_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP 429 must trigger backoff retry and succeed when rate limit clears."""
    call_count = 0

    def mock_urlopen(req: urllib.request.Request, *args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Simulate 429 Too Many Requests
            hdrs = {"Retry-After": "0.01"}
            raise urllib.error.HTTPError(
                url=req.full_url,
                code=429,
                msg="Too Many Requests",
                hdrs=hdrs,  # type: ignore[arg-type]
                fp=io.BytesIO(b'{"message":"Too Many Requests"}'),
            )
        return MockHTTPResponse({"results": [{"id": 1, "name": "Test"}]})

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    res = make_request(
        "https://api.openaq.org/v3/test",
        api_key="test-key",
        timeout=5.0,
        delay_sec=0.0,
    )
    assert call_count == 2
    assert res["results"][0]["id"] == 1


def test_pagination_stops_on_partial_page_without_warning(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When a page returns fewer items than limit (100), pagination stops clean."""
    mock_response = {
        "meta": {"found": 42},
        "results": [{"id": i, "name": f"Station {i}"} for i in range(42)],
    }

    def mock_urlopen(req: urllib.request.Request, *args: Any, **kwargs: Any) -> Any:
        return MockHTTPResponse(mock_response)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    locs, found_str = fetch_locations(
        bbox="76.5,27.8,78.2,29.2",
        api_key="key",
        max_pages=5,
        delay_sec=0.0,
    )
    assert len(locs) == 42
    assert found_str == "42"
    captured = capsys.readouterr()
    assert "Warning" not in captured.err


def test_request_cap_full_page_warning(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """If max_pages is reached and full page was returned, warn user."""
    # 100 items returned on page 1, max_pages=1
    mock_response = {
        "meta": {"found": ">100"},
        "results": [{"id": i, "name": f"Station {i}"} for i in range(100)],
    }

    def mock_urlopen(req: urllib.request.Request, *args: Any, **kwargs: Any) -> Any:
        return MockHTTPResponse(mock_response)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    locs, found_str = fetch_locations(
        bbox="76.5,27.8,78.2,29.2",
        api_key="key",
        max_pages=1,
        delay_sec=0.0,
    )
    assert len(locs) == 100
    assert found_str == ">100"
    captured = capsys.readouterr()
    assert "Warning: Reached --max-pages (1) with a full page returned." in captured.err


def test_save_raw_option_writes_clean_payloads(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    """--save-raw must write raw response files without secrets or request headers."""
    secret_key = "sensitive-api-token-should-not-be-in-file"
    monkeypatch.setenv("OPENAQ_API_KEY", secret_key)

    mock_loc = {
        "meta": {"found": 1},
        "results": [{"id": 501, "name": "Raw Test Station", "licenses": []}],
    }
    mock_lic = {
        "results": [{"id": 1, "name": "Licence 1"}],
    }

    def mock_urlopen(req: urllib.request.Request, *args: Any, **kwargs: Any) -> Any:
        url = req.full_url
        if "/locations" in url:
            return MockHTTPResponse(mock_loc)
        if "/licenses" in url:
            return MockHTTPResponse(mock_lic)
        raise ValueError(url)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    raw_dir = tmp_path / "raw_storage"
    out_csv = tmp_path / "out.csv"

    run_audit(
        output_path=str(out_csv),
        bbox="76.5,27.8,78.2,29.2",
        max_pages=1,
        delay_sec=0.0,
        save_raw=True,
        raw_dir=str(raw_dir),
    )

    saved_files = os.listdir(raw_dir)
    assert len(saved_files) >= 2  # locations and licenses
    for fname in saved_files:
        fpath = raw_dir / fname
        with open(fpath, encoding="utf-8") as f:
            content = f.read()
            # Verify valid JSON
            parsed = json.loads(content)
            assert isinstance(parsed, dict)
            # Guarantee secret is not leaked in file
            assert secret_key not in content
            assert "X-API-Key" not in content


def test_handles_multiple_licences_per_location() -> None:
    """A station with multiple licences produces one row per licence."""
    location = {
        "id": 999,
        "name": "Multi-Licence Station",
        "provider": {"name": "Test Provider"},
        "licenses": [
            {"id": 10, "name": "Licence A"},
            {"id": 20, "name": "Licence B"},
        ],
    }
    licenses_map = {
        10: {"id": 10, "name": "Licence A", "commercialUseAllowed": True},
        20: {"id": 20, "name": "Licence B", "commercialUseAllowed": False},
    }
    rows = build_csv_rows(
        locations=[location],
        licenses_map=licenses_map,
        api_key="key",
        checked_on="2026-11-19",
        delay_sec=0.0,
    )
    assert len(rows) == 2
    assert rows[0]["licence_name"] == "Licence A"
    assert rows[0]["commercialUseAllowed"] == "True"
    assert rows[1]["licence_name"] == "Licence B"
    assert rows[1]["commercialUseAllowed"] == "False"
