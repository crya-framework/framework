from pathlib import Path

from starlette.responses import HTMLResponse, Response

from crya._registry import get_current_app
from crya.templating import render

_BUILTIN_ERRORS_DIR = Path(__file__).parent / "templates" / "errors"


def _error_response(status_code: int, message: str) -> Response:
    template_name = f"{status_code}.loom"
    context = {"message": message}

    try:
        app = get_current_app()
        user_template = app.templates_path / "errors" / template_name
        if user_template.exists():
            return HTMLResponse(render(user_template, context), status_code=status_code)
    except RuntimeError:
        pass

    builtin_template = _BUILTIN_ERRORS_DIR / template_name
    return HTMLResponse(render(builtin_template, context), status_code=status_code)


def bad_request(message: str = "Bad Request") -> Response:
    return _error_response(400, message)


def unauthorized(message: str = "Unauthorized") -> Response:
    return _error_response(401, message)


def forbidden(message: str = "Forbidden") -> Response:
    return _error_response(403, message)


def not_found(message: str = "Not Found") -> Response:
    return _error_response(404, message)


def unprocessable(message: str = "Unprocessable Entity") -> Response:
    return _error_response(422, message)
