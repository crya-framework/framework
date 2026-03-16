from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from crya import App
from crya.orm import disconnect_all, db, execute_raw

_CREATE_POSTS_TABLE = """
    CREATE TABLE posts (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL
    )
"""


@pytest.fixture
async def orm_app(tmp_path):
    db_file = tmp_path / "test.db"
    await db.init(default=f"sqlite:///{db_file}")
    await execute_raw(_CREATE_POSTS_TABLE)

    app = App(
        root_directory=Path(__file__).parent / "fixtures" / "test_app" / "orm",
        routes=["tests.fixtures.test_app.orm.routes.web"],
    )

    yield app

    await disconnect_all()


@pytest.fixture
async def client(orm_app):
    async with AsyncClient(
        transport=ASGITransport(app=orm_app), base_url="http://test"
    ) as client:
        yield client


async def test_list_posts_returns_empty(client):
    response = await client.get("/posts")

    assert response.status_code == 200
    assert response.json() == []


async def test_create_post(client):
    response = await client.post("/posts", json={"title": "Hello", "content": "World"})

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Hello"
    assert data["content"] == "World"
    assert data["id"] is not None


async def test_get_post(client):
    created = await client.post("/posts", json={"title": "Crya", "content": "Framework"})
    post_id = created.json()["id"]

    response = await client.get(f"/posts/{post_id}")

    assert response.status_code == 200
    assert response.json()["title"] == "Crya"


async def test_get_post_not_found(client):
    response = await client.get("/posts/9999")

    assert response.status_code == 404


async def test_delete_post(client):
    created = await client.post("/posts", json={"title": "To delete", "content": "Bye"})
    post_id = created.json()["id"]

    response = await client.delete(f"/posts/{post_id}")
    assert response.status_code == 204

    response = await client.get(f"/posts/{post_id}")
    assert response.status_code == 404


async def test_list_posts_returns_all(client):
    await client.post("/posts", json={"title": "First", "content": "One"})
    await client.post("/posts", json={"title": "Second", "content": "Two"})

    response = await client.get("/posts")

    assert response.status_code == 200
    assert len(response.json()) == 2
