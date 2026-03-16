from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable, Literal, Self

from crya.orm import db, disconnect_all
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Mount, Route as StarletteRoute
from starlette.staticfiles import StaticFiles

from crya.routing import wrap_handler
from crya.templating import render, set_cache_dir
from crya.vite import ViteConfig, _configure as _configure_vite

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
    def _make(
        cls, path: str, methods: list[Method], callable: Callable
    ) -> InternalRoute:
        route = InternalRoute(StarletteRoute(path, wrap_handler(callable), methods=methods))
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
    def __init__(
        self,
        *,
        root_path: Path | str,
        templates_path: Path | str,
        templates_cache_path: Path | str,
        vite: ViteConfig | None = None,
        db_url: str | None = None,
    ):
        root = Path(root_path)
        self.templates_path = root / templates_path
        self._routes: list[InternalRoute] = []
        self.starlette_app: Starlette | None = None
        self._vite_build_dir: Path | None = None
        self._vite_build_url: str = "/build"
        self._db_url = db_url
        set_cache_dir(root / templates_cache_path)

        if vite is not None:
            _configure_vite(root, vite)
            self._vite_build_dir = root / vite.build_dir
            self._vite_build_url = vite.build_url

    def _add_route(self, route: InternalRoute) -> None:
        self._routes.append(route)
        self.starlette_app = None

    def _build_starlette_app(self) -> Starlette:
        db_url = self._db_url

        @asynccontextmanager
        async def lifespan(app: Starlette):
            if db_url is not None:
                await db.init(default=db_url)
            yield
            if db_url is not None:
                await disconnect_all()

        routes = [r.route for r in self._routes]
        if self._vite_build_dir is not None and self._vite_build_dir.exists():
            routes.append(
                Mount(
                    self._vite_build_url,
                    StaticFiles(directory=self._vite_build_dir),
                )
            )
        return Starlette(debug=True, routes=routes, lifespan=lifespan)

    async def __call__(self, scope, receive, send, *args, **kwargs):
        if self.starlette_app is None:
            self.starlette_app = self._build_starlette_app()

        return await self.starlette_app(scope, receive, send, *args, **kwargs)
