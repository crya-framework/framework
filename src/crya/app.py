import importlib
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from crya._registry import get_current_app, set_app as set_app
from crya.config.loader import load_config_dict
from crya.config.schemas import DatabaseConfig, TemplatingConfig
from crya.middleware.defaults import DEFAULT_API_MIDDLEWARE, DEFAULT_WEB_MIDDLEWARE
from crya.middleware.loader import load_middleware_stack
from crya.orm import db, disconnect_all
from crya.routing import InternalRoute, Router
from crya.templating import render, set_cache_dir
from crya.vite import ViteConfig, _configure as _configure_vite
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles


def view(template: str, context: dict | None = None) -> HTMLResponse:
    app = get_current_app()
    content = render(app.templates_path / template, context)

    return HTMLResponse(content)


class App:
    def __init__(
        self,
        *,
        root_directory: Path | str | None = None,
        config_directory: str = "config",
        vite: ViteConfig | None = None,
        routes: list[str] | None = None,
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

        templating_dict = load_config_dict(root, config_directory, "templating")
        templating = (
            TemplatingConfig.model_validate(templating_dict)
            if templating_dict is not None
            else TemplatingConfig()
        )

        db_dict = load_config_dict(root, config_directory, "database")
        self._db_url: str | None = (
            DatabaseConfig.model_validate(db_dict).url if db_dict is not None else None
        )

        self.templates_path = root / templating.templates_path
        self._root = root
        self._config_directory = config_directory
        self._routes: list[InternalRoute] = []
        self.starlette_app: Starlette | None = None
        self._vite_build_dir: Path | None = None
        self._vite_build_url: str = "/build"
        set_cache_dir(root / templating.cache_path)

        if vite is not None:
            _configure_vite(root, vite)
            self._vite_build_dir = root / vite.build_dir
            self._vite_build_url = vite.build_url

        set_app(self)

        for module_path in routes or []:
            if module_path in sys.modules:
                module = importlib.reload(sys.modules[module_path])
            else:
                module = importlib.import_module(module_path)
            router: Router = getattr(module, "router")
            for route in router._routes:
                self._routes.append(route)

    def _build_starlette_app(self) -> Starlette:
        db_url = self._db_url

        @asynccontextmanager
        async def lifespan(app: Starlette):
            if db_url is not None:
                await db.init(default=db_url)
            yield
            if db_url is not None:
                await disconnect_all()

        web_stack = load_middleware_stack(
            self._root, self._config_directory, "web", DEFAULT_WEB_MIDDLEWARE
        )
        api_stack = load_middleware_stack(
            self._root, self._config_directory, "api", DEFAULT_API_MIDDLEWARE
        )
        named_stacks = {"web": web_stack, "api": api_stack}

        routes = [r.build(named_stacks=named_stacks) for r in self._routes]
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
