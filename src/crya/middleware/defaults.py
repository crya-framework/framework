from typing import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import Response

type MiddlewareCallable = Callable[[Request, Callable], Awaitable[Response]]

DEFAULT_WEB_MIDDLEWARE: list[MiddlewareCallable] = []
DEFAULT_API_MIDDLEWARE: list[MiddlewareCallable] = []
