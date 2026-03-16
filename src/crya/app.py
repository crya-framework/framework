import importlib
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable, Literal, Self

from crya.orm import db, disconnect_all
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Mount, Route as StarletteRoute
from starlette.staticfiles import StaticFiles

from crya.config.schemas import DatabaseConfig, TemplatingConfig
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


def _load_config_dict(root: Path, config_directory: str, name: str) -> dict | None:
    config_file = root / config_directory / f"{name}.py"
    if not config_file.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"_crya_{config_directory}_{name}", config_file)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "config") or not isinstance(module.config, dict):
        raise ValueError(
            f"'{config_directory}/{name}.py' must define a top-level 'config' dict"
        )
    return module.config


class App:
    def __init__(
        self,
        *,
        root_directory: Path | str | None = None,
        config_directory: str = "config",
        vite: ViteConfig | None = None,
    ):
        root = Path(root_directory) if root_directory is not None else Path.cwd()

        # Load env config first so env() is available in subsequent config files
        env_file = root / config_directory / "env.py"
        if env_file.exists():
            spec = importlib.util.spec_from_file_location(
                f"_crya_{config_directory}_env", env_file
            )
            if spec is not None and spec.loader is not None:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

        templating_dict = _load_config_dict(root, config_directory, "templating")
        templating = (
            TemplatingConfig.model_validate(templating_dict)
            if templating_dict is not None
            else TemplatingConfig()
        )

        db_dict = _load_config_dict(root, config_directory, "database")
        self._db_url: str | None = (
            DatabaseConfig.model_validate(db_dict).url if db_dict is not None else None
        )

        self.templates_path = root / templating.templates_path
        self._routes: list[InternalRoute] = []
        self.starlette_app: Starlette | None = None
        self._vite_build_dir: Path | None = None
        self._vite_build_url: str = "/build"
        set_cache_dir(root / templating.cache_path)

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
