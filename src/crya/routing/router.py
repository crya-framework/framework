import inspect
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Awaitable, Callable, Literal, Self, TypeAlias

from starlette.datastructures import QueryParams
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route as StarletteRoute

type Method = Literal["GET", "POST", "PATCH", "HEAD", "OPTIONS", "PUT", "DELETE"]
type MiddlewareCallable = Callable[[Request, Callable], Awaitable[Response]]
type GroupStackEntry = tuple[str, list[MiddlewareCallable], str | None]

InspectedParameters: TypeAlias = MappingProxyType[str, inspect.Parameter]


@dataclass
class RequestParam:
    param_name: str
    value: Any = None
    target_type: type | None = None
    source: Source | None = None


type Source = Literal["PATH", "QUERY"]


def _extract_request_name(params: InspectedParameters) -> str | None:
    for key, param in params.items():
        if param.annotation == Request:
            return key

    return None


def _extract_path_params(
    params_in_path: dict[str, Any],
    source: Source,
    params: InspectedParameters,
) -> dict[str, RequestParam]:
    params_in_callable = {
        name: p for name, p in params.items() if name in params_in_path
    }

    request_params = {}
    for name, param in params_in_callable.items():
        target_type = (
            param.annotation if param.annotation != inspect.Parameter.empty else None
        )
        request_params[name] = RequestParam(
            param_name=name,
            value=params_in_path[name],
            target_type=target_type,
            source=source,
        )

    return request_params


def _extract_query_params(
    params_in_query: QueryParams,
    source: Source,
    params: InspectedParameters,
) -> dict[str, RequestParam]:
    params_in_callable = {
        name: p for name, p in params.items() if name in params_in_query.keys()
    }

    request_params = {}
    for name, param in params_in_callable.items():
        target_type = (
            param.annotation if param.annotation != inspect.Parameter.empty else None
        )
        request_params[name] = RequestParam(
            param_name=name,
            value=params_in_query[name],
            target_type=target_type,
            source=source,
        )

    return request_params


def wrap_handler(callable: Callable) -> Callable:
    async def wrapped(request: Request):
        params = extract_request_params(request, callable)
        kwargs: dict[str, Any] = {}
        for name, param in params.items():
            value = param.value
            if param.target_type is not None and param.source is not None:
                value = param.target_type(value)
            kwargs[name] = value
        return await callable(**kwargs)

    return wrapped


def extract_request_params(
    request: Request, callable: Callable
) -> dict[str, RequestParam]:
    signature = inspect.signature(callable)

    parameters = signature.parameters

    request_params = {}

    request_kwarg = _extract_request_name(parameters)

    if request_kwarg:
        request_params[request_kwarg] = RequestParam(
            param_name=request_kwarg, value=request, source=None
        )

    for name, parameter in _extract_path_params(
        request.path_params, "PATH", parameters
    ).items():
        request_params[name] = parameter

    for name, parameter in _extract_query_params(
        request.query_params, "QUERY", parameters
    ).items():
        request_params[name] = parameter

    return request_params


def _apply_middleware(
    handler: Callable, middlewares: list[MiddlewareCallable]
) -> Callable:
    for mw in reversed(middlewares):
        next_handler = handler

        async def wrapped(request: Request, _next=next_handler, _mw=mw) -> Response:
            return await _mw(request, _next)

        handler = wrapped
    return handler


class InternalRoute:
    def __init__(
        self,
        path: str,
        methods: list[Method],
        callable: Callable,
        group_middlewares: list[MiddlewareCallable],
        middleware_group: str | None,
    ):
        self._path = path
        self._methods = methods
        self._callable = callable
        self._group_middlewares = group_middlewares
        self._middleware_group = middleware_group
        self._middlewares: list[MiddlewareCallable] = []
        self._name: str | None = None

    def name(self, name: str) -> Self:
        self._name = name
        return self

    def middleware(self, *mw: MiddlewareCallable) -> Self:
        self._middlewares.extend(mw)
        return self

    def build(self, named_stacks: dict[str, list[MiddlewareCallable]] | None = None) -> StarletteRoute:
        handler = wrap_handler(self._callable)
        handler = _apply_middleware(handler, self._middlewares)         # route-level (innermost)
        handler = _apply_middleware(handler, self._group_middlewares)   # inline group middleware
        named_group = (named_stacks or {}).get(self._middleware_group or "", [])
        handler = _apply_middleware(handler, named_group)               # named stack (outermost)
        route = StarletteRoute(self._path, handler, methods=self._methods)
        if self._name is not None:
            route.name = self._name
        return route


class _GroupContext:
    def __init__(
        self,
        router: "Router",
        prefix: str,
        middlewares: list[MiddlewareCallable],
        middleware_group: str | None,
    ):
        self._router = router
        self._prefix = prefix
        self._middlewares = middlewares
        self._middleware_group = middleware_group

    def __enter__(self) -> "Router":
        self._router._push_group(self._prefix, self._middlewares, self._middleware_group)
        return self._router

    def __exit__(self, *args) -> None:
        self._router._pop_group()


class Router:
    def __init__(self):
        self._routes: list[InternalRoute] = []
        self._group_stack: list[GroupStackEntry] = []

    def _push_group(self, prefix: str, middlewares: list[MiddlewareCallable], middleware_group: str | None) -> None:
        self._group_stack.append((prefix, middlewares, middleware_group))

    def _pop_group(self) -> None:
        self._group_stack.pop()

    def _current_prefix(self) -> str:
        return "".join(prefix for prefix, _, __ in self._group_stack)

    def _current_middlewares(self) -> list[MiddlewareCallable]:
        result: list[MiddlewareCallable] = []
        for _, middlewares, __ in self._group_stack:
            result.extend(middlewares)
        return result

    def _current_middleware_group(self) -> str | None:
        for _, __, middleware_group in reversed(self._group_stack):
            if middleware_group is not None:
                return middleware_group
        return None

    def group(
        self,
        prefix: str = "",
        middlewares: list[MiddlewareCallable] | None = None,
        middleware_group: str | None = None,
    ) -> _GroupContext:
        return _GroupContext(self, prefix, middlewares or [], middleware_group)

    def _add(self, path: str, methods: list[Method], callable: Callable) -> InternalRoute:
        full_path = self._current_prefix() + path
        route = InternalRoute(
            full_path,
            methods,
            callable,
            group_middlewares=self._current_middlewares(),
            middleware_group=self._current_middleware_group(),
        )
        self._routes.append(route)
        return route

    def get(self, path: str, callable: Callable) -> InternalRoute:
        return self._add(path, ["GET"], callable)

    def post(self, path: str, callable: Callable) -> InternalRoute:
        return self._add(path, ["POST"], callable)

    def patch(self, path: str, callable: Callable) -> InternalRoute:
        return self._add(path, ["PATCH"], callable)

    def put(self, path: str, callable: Callable) -> InternalRoute:
        return self._add(path, ["PUT"], callable)

    def delete(self, path: str, callable: Callable) -> InternalRoute:
        return self._add(path, ["DELETE"], callable)

    def head(self, path: str, callable: Callable) -> InternalRoute:
        return self._add(path, ["HEAD"], callable)

    def options(self, path: str, callable: Callable) -> InternalRoute:
        return self._add(path, ["OPTIONS"], callable)
