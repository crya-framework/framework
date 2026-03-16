from pathlib import Path

from crya import App

app = App(
    root_directory=Path(__file__).parent,
    routes=["tests.fixtures.test_app.simple.routes.web"],
)
