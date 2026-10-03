"""API smoke tests."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    # Lifespan runs init_db + seed
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_zones_and_concept(client):
    assert client.get("/api/grid/zones").status_code == 200
    concept = client.get("/api/concept/flexibility-accounting").json()
    assert "Flexibility Accounting Layer" in concept["title"]
    reg = client.get("/api/concept/regulatory").json()
    assert "NEPRA" in reg["institutions"]


def test_login_and_wallet(client):
    r = client.post(
        "/api/auth/token",
        json={"email": "consumer@gridflex.pk", "password": "demo1234"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    wallet = client.get("/api/wallet/me", headers={"Authorization": f"Bearer {token}"})
    assert wallet.status_code == 200


def test_simulation_endpoint(client):
    r = client.post(
        "/api/simulation/run",
        json={
            "households": 500,
            "commercial": 50,
            "industrial": 5,
            "solar_systems": 100,
            "batteries": 25,
            "seed": 3,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["peak_with_mw"] <= body["peak_without_mw"]


def test_zone_constrained_clearing(client):
    from datetime import datetime, timedelta

    login = client.post(
        "/api/auth/token",
        json={"email": "utility@gridflex.pk", "password": "demo1234"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    zones = client.get("/api/grid/zones").json()
    khi = next(z for z in zones if z["code"] == "KHI")
    participants = client.get("/api/participants").json()
    seller_login = client.post(
        "/api/auth/token",
        json={"email": "aggregator@gridflex.pk", "password": "demo1234"},
    )
    seller_headers = {"Authorization": f"Bearer {seller_login.json()['access_token']}"}
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    client.post(
        "/api/market/offers",
        headers=seller_headers,
        json={
            "participant_id": participants[0]["id"],
            "flexibility_type": "aggregated",
            "power_kw": 100,
            "duration_hours": 2,
            "available_from": (now + timedelta(hours=1)).isoformat(),
            "available_to": (now + timedelta(hours=3)).isoformat(),
            "min_price_pkr_per_kwh": 8,
        },
    )
    client.post(
        "/api/market/bids",
        headers=headers,
        json={
            "zone_id": khi["id"],
            "power_kw": 80,
            "duration_hours": 2,
            "needed_from": (now + timedelta(hours=1)).isoformat(),
            "needed_to": (now + timedelta(hours=3)).isoformat(),
            "max_price_pkr_per_kwh": 12,
        },
    )

    result = client.post("/api/market/clear", json={"zone_id": khi["id"]}, headers=headers)
    assert result.status_code == 200
    data = result.json()
    assert data["transaction_count"] >= 1
    assert data["cleared_volume_kw"] > 0