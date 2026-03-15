from crya import App, set_app

app = App()
set_app(app)

from .routes import web  # noqa: E402, F401 — must import after set_app
