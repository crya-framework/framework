from dataclasses import dataclass
from typing import Callable, Literal

from starlette.applications import Starlette
from starlette.routing import Route

type Method = Literal["GET", "POST", "PATCH", "HEAD", "OPTIONS", "PUT", "DELETE"]


@dataclass
class App:
    def __init__(self):
        self._routes: list[Route] = []
        self.starlette_app: Starlette | None = None

    def _add_route(self, method: Method, path: str):
        def wrapper(callable: Callable):
            route = Route(path, callable, methods=[method])
            self._routes.append(route)

            return callable

        return wrapper

    def get(self, path: str) -> Callable:
        return self._add_route("GET", path)

    def post(self, path: str) -> Callable:
        return self._add_route("POST", path)

    def patch(self, path: str) -> Callable:
        return self._add_route("PATCH", path)

    def put(self, path: str) -> Callable:
        return self._add_route("PUT", path)

    def delete(self, path: str) -> Callable:
        return self._add_route("DELETE", path)

    def head(self, path: str) -> Callable:
        return self._add_route("HEAD", path)

    def options(self, path: str) -> Callable:
        return self._add_route("OPTIONS", path)

    async def __call__(self, scope, receive, send, *args, **kwargs):
        if self.starlette_app is None:
            self.starlette_app = Starlette(debug=True, routes=self._routes)

        return await self.starlette_app(scope, receive, send, *args, **kwargs)


app = App()
