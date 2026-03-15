from pathlib import Path
from typing import Callable, Literal, Self

from crya_loom import render, set_cache_dir
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Route as StarletteRoute

type Method = Literal["GET", "POST", "PATCH", "HEAD", "OPTIONS", "PUT", "DELETE"]

_current_app: "App | None" = None


def set_app(app: "App") -> None:
    global _current_app
    _current_app = app


def get_current_app() -> "App":
    if _current_app is None:
        raise RuntimeError("No app set. Call crya.set_app(app) first.")
    return _current_app


def view(template: str, context: dict | None = None) -> HTMLResponse:
    app = get_current_app()
    content = render(app.templates_path / template, context)
    return HTMLResponse(content)


class InternalRoute:
    def __init__(self, route: StarletteRoute):
        self.route = route

    def name(self, name: str) -> Self:
        self.route.name = name
        return self


class Route:
    @classmethod
    def _make(cls, path: str, methods: list[Method], callable: Callable) -> InternalRoute:
        route = InternalRoute(StarletteRoute(path, callable, methods=methods))
        get_current_app()._add_route(route)
        return route

    @classmethod
    def get(cls, path: str, callable: Callable) -> InternalRoute:
        return cls._make(path, ["GET"], callable)

    @classmethod
    def post(cls, path: str, callable: Callable) -> InternalRoute:
        return cls._make(path, ["POST"], callable)

    @classmethod
    def patch(cls, path: str, callable: Callable) -> InternalRoute:
        return cls._make(path, ["PATCH"], callable)

    @classmethod
    def put(cls, path: str, callable: Callable) -> InternalRoute:
        return cls._make(path, ["PUT"], callable)

    @classmethod
    def delete(cls, path: str, callable: Callable) -> InternalRoute:
        return cls._make(path, ["DELETE"], callable)

    @classmethod
    def head(cls, path: str, callable: Callable) -> InternalRoute:
        return cls._make(path, ["HEAD"], callable)

    @classmethod
    def options(cls, path: str, callable: Callable) -> InternalRoute:
        return cls._make(path, ["OPTIONS"], callable)


class App:
    def __init__(self, *, root_path: Path | str, templates_path: Path | str, templates_cache_path: Path | str):
        root = Path(root_path)
        self.templates_path = root / templates_path
        self._routes: list[InternalRoute] = []
        self.starlette_app: Starlette | None = None
        set_cache_dir(root / templates_cache_path)

    def _add_route(self, route: InternalRoute) -> None:
        self._routes.append(route)
        self.starlette_app = None

    async def __call__(self, scope, receive, send, *args, **kwargs):
        if self.starlette_app is None:
            self.starlette_app = Starlette(
                debug=True, routes=[r.route for r in self._routes]
            )
        return await self.starlette_app(scope, receive, send, *args, **kwargs)
