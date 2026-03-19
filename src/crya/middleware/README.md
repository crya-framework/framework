# Middleware

Crya has two middleware layers:

- **Route middleware** — applied per route or per route group, defined in your route files.
- **Named stacks** (`web` / `api`) — applied globally to all routes in a named group, configured via `config/middleware.py`.

## Middleware callable signature

Every middleware is an async callable with this signature:

```python
from starlette.requests import Request
from starlette.responses import Response

async def my_middleware(request: Request, call_next) -> Response:
    # before handler
    response = await call_next(request)
    # after handler
    return response
```

To short-circuit (e.g. authentication failure), return a response without calling `call_next`:

```python
async def auth_middleware(request: Request, call_next) -> Response:
    if not is_authenticated(request):
        return Response("Unauthorized", status_code=401)
    return await call_next(request)
```

## Route-level middleware

Attach middleware to a single route with `.middleware()`:

```python
router.get("/dashboard", dashboard_handler).middleware(auth_middleware)
```

Multiple middleware are applied left to right (first in list = outermost):

```python
router.get("/admin", admin_handler).middleware(auth_middleware, log_middleware)
```

## Group middleware

Pass `middlewares` to `router.group()` to apply middleware to every route in that group:

```python
with router.group(prefix="/admin", middlewares=[auth_middleware]):
    router.get("/users", list_users)
    router.get("/settings", settings)
```

Groups can be nested; middleware accumulates from outer to inner groups.

## Named stacks: `web` and `api`

Named stacks are a global set of middleware associated with the `"web"` or `"api"` string key. Assign a route group to a named stack with `middleware_group`:

```python
with router.group(prefix="/api", middleware_group="api"):
    router.get("/posts", list_posts)
```

Define the stack contents in `config/middleware.py`:

```python
# config/middleware.py
from app.middleware import throttle_middleware, log_middleware

config = {
    "web": {
        "append": [log_middleware],     # added after defaults
        "prepend": [],                  # added before defaults
        "remove": [],                   # removed from defaults
    },
    "api": {
        "append": [throttle_middleware],
    },
}
```

Each key (`append`, `prepend`, `remove`) is optional. The built-in defaults for both stacks are empty, so any middleware you add goes in directly.

If `config/middleware.py` does not exist, the default (empty) stacks are used.

## Execution order

For a given request the middleware runs outermost-first:

```
named stack → inline group middleware → route-level middleware → handler
```

Example with all three layers:

```python
# config/middleware.py
config = {"web": {"append": [stack_mw]}}

# routes/web.py
with router.group(prefix="/foo", middlewares=[group_mw], middleware_group="web"):
    router.get("/bar", handler).middleware(route_mw)
```

Execution: `stack_mw → group_mw → route_mw → handler`

---

# CORS

CORS is an ASGI-level middleware applied globally before routing. It is activated by creating `config/cors.py`.

## Enabling CORS

```python
# config/cors.py
config = {
    "paths": ["/api/*"],
    "allowed_origins": ["https://app.example.com"],
}
```

Crya reads this file at startup and wraps the application in `CorsMiddleware` automatically. If `config/cors.py` does not exist, no CORS headers are added.

## Configuration reference

All fields are optional and have defaults:

| Field | Type | Default | Description |
|---|---|---|---|
| `paths` | `list[str]` | `["/api/*"]` | Path patterns (fnmatch) that CORS applies to |
| `allowed_origins` | `list[str]` | `["*"]` | Exact origin strings, or `["*"]` for wildcard |
| `allowed_origins_patterns` | `list[str]` | `[]` | Full-match regex patterns for allowed origins |
| `allowed_methods` | `list[str]` | `["*"]` | Allowed HTTP methods |
| `allowed_headers` | `list[str]` | `["*"]` | Allowed request headers |
| `exposed_headers` | `list[str]` | `[]` | Headers exposed to the browser |
| `supports_credentials` | `bool` | `False` | Add `Access-Control-Allow-Credentials: true` |
| `max_age` | `int` | `0` | Preflight cache duration in seconds (0 = omitted) |

## Path filtering

`paths` uses `fnmatch` patterns. Requests whose path does not match any pattern are passed through without CORS headers.

```python
config = {
    "paths": ["/api/*", "/graphql"],
}
```

## Origin matching

Origins are matched in this order:

1. `"*"` in `allowed_origins` — any origin is allowed (responds with `Access-Control-Allow-Origin: *`).
2. Exact match in `allowed_origins`.
3. Full regex match against any entry in `allowed_origins_patterns`.

```python
# Exact origins
config = {"allowed_origins": ["https://app.example.com", "https://admin.example.com"]}

# Regex — allows any subdomain of example.com
config = {
    "allowed_origins": [],
    "allowed_origins_patterns": [r"https://.*\.example\.com"],
}
```

If the origin is not matched, CORS headers are simply omitted from the response (the request is not rejected).

## Credentials

```python
config = {
    "allowed_origins": ["https://app.example.com"],  # must be explicit, not ["*"]
    "supports_credentials": True,
}
```

`supports_credentials=True` combined with `allowed_origins=["*"]` raises `ValueError` at startup — browsers prohibit this combination.

## Preflight requests

Preflight (`OPTIONS` + `Access-Control-Request-Method`) is handled automatically. A 200 response with the appropriate headers is returned immediately without reaching the route handler.
