import importlib
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from crya import App, set_app

_ROUTES_MODULE = "tests.fixtures.test_app.simple.routes.web"


@pytest.fixture
def simple_app():
    app = App(
        root_path=Path(__file__).parent / "fixtures" / "test_app" / "simple",
        templates_path="templates",
        templates_cache_path=Path("cache") / "framework" / "templates",
    )
    set_app(app)
    if _ROUTES_MODULE in sys.modules:
        importlib.reload(sys.modules[_ROUTES_MODULE])
    else:
        importlib.import_module(_ROUTES_MODULE)
    return app


@pytest.fixture
async def client(simple_app):
    async with AsyncClient(
        transport=ASGITransport(app=simple_app), base_url="http://test"
    ) as client:
        yield client


async def test_it_returns_404_if_not_found(client):
    response = await client.get("/foobar")

    assert response.status_code == 404


async def test_home_returns_hello(client):
    response = await client.get("/")

    assert response.status_code == 200
    assert response.text == "hello world"


async def test_welcome_returns_welcome_template(client):
    response = await client.get("/welcome")

    assert response.status_code == 200
