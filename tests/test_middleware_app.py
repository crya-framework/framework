from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from crya import App

MIDDLEWARE_ROOT = Path(__file__).parent / "fixtures" / "test_app" / "middleware"
ROUTES = ["tests.fixtures.test_app.middleware.routes.web"]


@pytest.fixture
def middleware_app():
    return App(root_directory=MIDDLEWARE_ROOT, routes=ROUTES)


@pytest.fixture
async def client(middleware_app):
    async with AsyncClient(
        transport=ASGITransport(app=middleware_app), base_url="http://test"
    ) as client:
        yield client


async def test_route_without_middleware_has_no_header(client):
    response = await client.get("/plain")

    assert response.status_code == 200
    assert "x-test-header" not in response.headers


async def test_route_middleware_adds_header(client):
    response = await client.get("/with-header")

    assert response.status_code == 200
    assert response.headers["x-test-header"] == "present"


async def test_middleware_short_circuit_returns_early(client):
    response = await client.get("/forbidden")

    assert response.status_code == 403


async def test_group_middleware_applies_to_routes_in_group(client):
    response = await client.get("/group/route")

    assert response.status_code == 200
    assert response.headers["x-test-header"] == "present"


async def test_named_stack_execution_order(client):
    # web stack (A, via config/middleware.py) → group (B) → route (C) → handler
    response = await client.get("/named/route")

    assert response.status_code == 200
    assert response.json() == ["A", "B", "C"]
