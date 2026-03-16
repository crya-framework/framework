from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from crya import App


@pytest.fixture
def simple_app():
    return App(
        root_directory=Path(__file__).parent / "fixtures" / "test_app" / "simple",
        routes=["tests.fixtures.test_app.simple.routes.web"],
    )


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
    assert "This is a crya app" in response.text
