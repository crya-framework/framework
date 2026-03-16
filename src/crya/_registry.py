from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from crya.app import App

_current_app: "App | None" = None


def set_app(app: "App") -> None:
    global _current_app
    _current_app = app


def get_current_app() -> "App":
    if _current_app is None:
        raise RuntimeError("No app set. Call crya.set_app(app) first.")

    return _current_app
