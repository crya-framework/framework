# Testing

`crya.testing` provides `TestClient` and `TestResponse` for writing HTTP tests against your Crya application without starting a real server.

## Setup

Install the required dev dependencies:

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["."]          # makes bootstrap.py importable from the project root

[dependency-groups]
dev = [
    "pytest>=9.0.2",
    "pytest-asyncio>=1.3.0",
]
```

## conftest.py

Create a shared `client` fixture at the root of your `tests/` directory:

```python
import pytest
from crya.testing import TestClient
from bootstrap import app

@pytest.fixture
async def client():
    async with TestClient(app) as client:
        yield client
```

## Writing tests

Inject the `client` fixture into any async test function:

```python
async def test_home(client):
    response = await client.get("/")
    response.assert_ok().assert_see("Welcome")
```

## TestClient

`TestClient` is an async context manager that wraps `httpx` and sends requests directly to your ASGI app. It accepts an optional `base_url` (defaults to `"http://test"`).

All methods accept the same keyword arguments as `httpx` (e.g. `json=`, `data=`, `headers=`, `params=`):

```python
await client.get("/users")
await client.post("/users", json={"name": "Alice"})
await client.put("/users/1", json={"name": "Bob"})
await client.patch("/users/1", json={"name": "Charlie"})
await client.delete("/users/1")
```

Every method returns a `TestResponse`.

## TestResponse

`TestResponse` wraps `httpx.Response` and exposes assertion methods that all return `self` for chaining.

### Raw attributes

```python
response.status_code   # int
response.text          # str
response.headers       # httpx.Headers
response.json()        # parsed JSON (dict or list)
```

### Status assertions

```python
response.assert_status(201)        # exact status code
response.assert_ok()               # 200
response.assert_created()          # 201
response.assert_no_content()       # 204
response.assert_not_found()        # 404
response.assert_unauthorized()     # 401
response.assert_forbidden()        # 403
response.assert_unprocessable()    # 422
response.assert_server_error()     # any 5xx
response.assert_redirect()                        # any 3xx
response.assert_redirect("/login")                # 3xx with exact Location header
```

### Body assertions

```python
response.assert_see("Welcome")          # text present in raw body
response.assert_dont_see("Error")       # text absent from raw body
response.assert_see_text("Welcome")     # text present after stripping HTML tags
response.assert_dont_see_text("Error")  # text absent after stripping HTML tags
```

### JSON assertions

`assert_json` uses **subset matching** — the response may contain extra keys:

```python
# passes even if actual JSON is {"id": 1, "name": "Alice", "role": "admin"}
response.assert_json({"name": "Alice"})
```

`assert_json_exact` requires an exact match:

```python
response.assert_json_exact({"id": 1, "name": "Alice", "role": "admin"})
```

### Header assertions

```python
response.assert_header("x-request-id")               # header is present
response.assert_header("content-type", "application/json")  # header has exact value
response.assert_header_missing("x-internal-token")   # header is absent
```

## Chaining

All assertion methods return `self`, so they can be chained:

```python
async def test_create_user(client):
    response = await client.post("/users", json={"name": "Alice"})
    (
        response
        .assert_created()
        .assert_json({"name": "Alice"})
        .assert_header("content-type", "application/json")
    )
```
