# Routing

Routes are defined per file using a `Router` instance. Each route file exposes a `router` variable that `App` collects on startup.

## Basic usage

```python
# routes/web.py
from crya import Router
from app.handlers import home, about

router = Router()
router.get("/", home)
router.post("/contact", about)
```

Register the module with `App`:

```python
# app.py
from crya import App

app = App(
    root_directory=...,
    routes=["routes.web"],
)
```

## Route methods

```python
router.get(path, handler)
router.post(path, handler)
router.put(path, handler)
router.patch(path, handler)
router.delete(path, handler)
router.head(path, handler)
router.options(path, handler)
```

## Named routes

```python
router.get("/", home).name("home")
```

## Grouping

`router.group()` is a context manager that applies a prefix and/or middleware to all routes defined inside it. Groups can be nested.

```python
router = Router()

with router.group(prefix="/api", middlewares=[AuthMiddleware]):
    router.get("/users", list_users)      # → GET /api/users
    router.post("/users", create_user)    # → POST /api/users

    with router.group(prefix="/v1"):
        router.get("/posts", list_posts)  # → GET /api/v1/posts
```

## Handler injection

Handlers do not need to accept a `Request` object explicitly. Parameters are injected by name and type annotation:

- A parameter annotated as `Request` receives the raw Starlette request.
- Parameters matching path segments (`/posts/{id}`) are injected as path params and cast to their annotated type.
- Any remaining parameters are looked up in the query string.

```python
from crya import Request

async def get_post(request: Request, id: int):
    # id injected from /posts/{id}, cast to int
    # request injected as the full Request object
    ...

async def search(q: str, page: int = 1):
    # q and page injected from query string
    ...
```
