from pathlib import Path

from crya import App, set_app

app = App(
    root_path=Path(__file__).parent,
    templates_path="templates",
    templates_cache_path="cache/compiled/templates",
)
set_app(app)

from .routes import web  # noqa: E402, F401 — must import after set_app
