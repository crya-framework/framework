from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from crya import App
from crya.config.schemas import CorsConfig
from crya.middleware.cors import CorsMiddleware


def make_starlette_app() -> Starlette:
    async def handler(request: Request):
        return JSONResponse({"ok": True})

    return Starlette(routes=[
        Route("/api/posts", handler, methods=["GET"]),
        Route("/web/page", handler, methods=["GET"]),
    ])


def make_cors_app(config: CorsConfig) -> CorsMiddleware:
    return CorsMiddleware(make_starlette_app(), config)


# --- Path filtering ---


async def test_matched_path_gets_cors_headers():
    app = make_cors_app(CorsConfig(paths=["/api/*"]))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/posts", headers={"Origin": "https://example.com"})

    assert "access-control-allow-origin" in response.headers


async def test_unmatched_path_has_no_cors_headers():
    app = make_cors_app(CorsConfig(paths=["/api/*"]))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/web/page", headers={"Origin": "https://example.com"})

    assert "access-control-allow-origin" not in response.headers


# --- Preflight ---


async def test_preflight_returns_200_with_cors_headers():
    app = make_cors_app(CorsConfig(paths=["/api/*"]))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/api/posts",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-methods" in response.headers


async def test_preflight_on_unmatched_path_passes_through():
    app = make_cors_app(CorsConfig(paths=["/api/*"]))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/web/page",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert "access-control-allow-origin" not in response.headers


# --- Origin validation ---


async def test_wildcard_allows_any_origin():
    app = make_cors_app(CorsConfig(paths=["/api/*"], allowed_origins=["*"]))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/posts", headers={"Origin": "https://anything.com"})

    assert response.headers.get("access-control-allow-origin") == "*"


async def test_exact_origin_allowed():
    app = make_cors_app(CorsConfig(paths=["/api/*"], allowed_origins=["https://example.com"]))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/posts", headers={"Origin": "https://example.com"})

    assert response.headers.get("access-control-allow-origin") == "https://example.com"


async def test_disallowed_origin_gets_no_cors_headers():
    app = make_cors_app(CorsConfig(paths=["/api/*"], allowed_origins=["https://example.com"]))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/posts", headers={"Origin": "https://evil.com"})

    assert "access-control-allow-origin" not in response.headers


async def test_origin_pattern_allows_subdomain():
    app = make_cors_app(CorsConfig(
        paths=["/api/*"],
        allowed_origins=[],
        allowed_origins_patterns=[r"https://.*\.example\.com"],
    ))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/posts", headers={"Origin": "https://sub.example.com"})

    assert response.headers.get("access-control-allow-origin") == "https://sub.example.com"


# --- Credentials ---


async def test_supports_credentials_adds_header():
    app = make_cors_app(CorsConfig(
        paths=["/api/*"],
        allowed_origins=["https://example.com"],
        supports_credentials=True,
    ))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/posts", headers={"Origin": "https://example.com"})

    assert response.headers.get("access-control-allow-credentials") == "true"


async def test_credentials_with_wildcard_origin_raises():
    config = CorsConfig(paths=["/api/*"], allowed_origins=["*"], supports_credentials=True)

    with pytest.raises(ValueError, match="supports_credentials"):
        CorsMiddleware(make_starlette_app(), config)


# --- Disabled ---


async def test_no_cors_middleware_means_no_cors_headers():
    # App without config/cors.py should not add CORS headers
    simple_root = Path(__file__).parent / "fixtures" / "test_app" / "simple"
    app = App(
        root_directory=simple_root,
        routes=["tests.fixtures.test_app.simple.routes.web"],
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/", headers={"Origin": "https://example.com"})

    assert "access-control-allow-origin" not in response.headers
