import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.app.disaster_api import LiveDisaster, DisasterFeedManager
from backend.app.main import app


def test_live_disaster_model():
    """Verify LiveDisaster schema validation with and without geospatial coordinates."""
    disaster_with_geo = LiveDisaster(
        id="EMSR934",
        title="Earthquake in Los Santos, Panama",
        source="Copernicus EMS",
        status="Active Rapid Mapping",
        url="https://mapping.emergency.copernicus.eu/activations/EMSR934",
        lat=8.0067,
        lng=-80.6708
    )
    assert disaster_with_geo.id == "EMSR934"
    assert disaster_with_geo.lat == 8.0067
    assert disaster_with_geo.lng == -80.6708

    disaster_without_geo = LiveDisaster(
        id="rw-101",
        title="Flash Floods in South Asia",
        source="UN ReliefWeb",
        status="current",
        url="https://reliefweb.int/disaster/rw-101"
    )
    assert disaster_without_geo.lat is None
    assert disaster_without_geo.lng is None
    data = disaster_without_geo.model_dump()
    assert data["source"] == "UN ReliefWeb"


def test_disaster_feed_manager_unified():
    """Verify DisasterFeedManager produces a combined list of live/fallback disaster alerts."""
    manager = DisasterFeedManager()
    alerts = manager.get_unified_feed()
    assert isinstance(alerts, list)
    assert len(alerts) > 0

    sources = {a.source for a in alerts}
    assert any("ReliefWeb" in s or "GDACS" in s for s in sources)
    assert any("Copernicus" in s for s in sources)


def test_reliefweb_mocked_success():
    """Verify parsing when ReliefWeb API returns structured JSON data."""
    manager = DisasterFeedManager()
    mock_payload = {
        "data": [
            {
                "id": "mock-rw-1",
                "fields": {
                    "name": "Mock Flood Event",
                    "status": "ongoing",
                    "url": "https://reliefweb.int/disaster/mock-rw-1"
                }
            }
        ]
    }
    with patch.object(manager, "_fetch_url", return_value=(200, b"{}", mock_payload)):
        alerts = manager.get_reliefweb_alerts()
        assert len(alerts) == 1
        assert alerts[0].id == "mock-rw-1"
        assert alerts[0].title == "Mock Flood Event"
        assert alerts[0].source == "UN ReliefWeb"
        assert alerts[0].status == "ongoing"


def test_reliefweb_fallback_on_network_failure():
    """Verify field resilience: manager falls back to curated records on total network failure."""
    manager = DisasterFeedManager()
    with patch.object(manager, "_fetch_url", return_value=(500, b"", None)):
        alerts = manager.get_reliefweb_alerts()
        assert len(alerts) >= 2
        assert any("Panama" in a.title for a in alerts)


def test_cems_mocked_success():
    """Verify Copernicus EMS centroid WKT parsing into lat/lng."""
    manager = DisasterFeedManager()
    mock_cems_data = {
        "results": [
            {
                "code": "EMSR999",
                "name": "Flood in Valencia, Spain",
                "centroid": "POINT (-0.3763 39.4699)",
                "closed": False
            }
        ]
    }
    with patch.object(manager, "_fetch_url", return_value=(200, b"{}", mock_cems_data)):
        alerts = manager.get_cems_activations()
        assert len(alerts) == 1
        assert alerts[0].id == "EMSR999"
        assert alerts[0].title == "Flood in Valencia, Spain"
        assert alerts[0].source == "Copernicus EMS"
        assert alerts[0].status == "Active Rapid Mapping"
        assert alerts[0].lng == -0.3763
        assert alerts[0].lat == 39.4699


def test_cems_fallback_on_network_failure():
    """Verify CEMS fallback on network failure."""
    manager = DisasterFeedManager()
    with patch.object(manager, "_fetch_url", return_value=(500, b"", None)):
        alerts = manager.get_cems_activations()
        assert len(alerts) >= 2
        assert any(a.id == "EMSR934" for a in alerts)


def test_fastapi_live_disaster_endpoint():
    """Verify the /api/live-disasters endpoint responds with 200 OK and expected schema."""
    client = TestClient(app)
    response = client.get("/api/live-disasters")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert len(items) > 0

    for item in items:
        assert "id" in item
        assert "title" in item
        assert "source" in item
        assert "status" in item
        assert "url" in item
