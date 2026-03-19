import pytest
from starlette.requests import Request
from starlette.responses import Response

from crya.routing.router import InternalRoute, _apply_middleware


def make_request() -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
        "path_params": {},
    }
    return Request(scope)


# --- _apply_middleware unit tests ---


async def test_apply_middleware_empty_returns_handler_unchanged():
    async def handler(request: Request) -> Response:
        return Response("ok")

    wrapped = _apply_middleware(handler, [])
    assert wrapped is handler


async def test_apply_middleware_single_wraps_correctly():
    called = []

    async def mw(request: Request, call_next) -> Response:
        called.append("before")
        response = await call_next(request)
        called.append("after")
        return response

    async def handler(request: Request) -> Response:
        called.append("handler")
        return Response("ok")

    wrapped = _apply_middleware(handler, [mw])
    response = await wrapped(make_request())

    assert called == ["before", "handler", "after"]
    assert response.status_code == 200


async def test_apply_middleware_multiple_correct_order():
    called = []

    async def mw_a(request: Request, call_next) -> Response:
        called.append("A-before")
        response = await call_next(request)
        called.append("A-after")
        return response

    async def mw_b(request: Request, call_next) -> Response:
        called.append("B-before")
        response = await call_next(request)
        called.append("B-after")
        return response

    async def mw_c(request: Request, call_next) -> Response:
        called.append("C-before")
        response = await call_next(request)
        called.append("C-after")
        return response

    async def handler(request: Request) -> Response:
        called.append("handler")
        return Response("ok")

    wrapped = _apply_middleware(handler, [mw_a, mw_b, mw_c])
    await wrapped(make_request())

    assert called == [
        "A-before", "B-before", "C-before",
        "handler",
        "C-after", "B-after", "A-after",
    ]


async def test_apply_middleware_short_circuit():
    handler_called = []

    async def blocking_mw(request: Request, call_next) -> Response:
        return Response("blocked", status_code=403)

    async def handler(request: Request) -> Response:
        handler_called.append(True)
        return Response("ok")

    wrapped = _apply_middleware(handler, [blocking_mw])
    response = await wrapped(make_request())

    assert response.status_code == 403
    assert handler_called == []


# --- InternalRoute.build() unit tests ---


async def test_internal_route_build_applies_route_middleware():
    called = []

    async def mw(request: Request, call_next) -> Response:
        called.append("mw")
        return await call_next(request)

    async def handler() -> Response:
        called.append("handler")
        return Response("ok")

    route = InternalRoute("/", ["GET"], handler, group_middlewares=[], middleware_group=None)
    route.middleware(mw)
    starlette_route = route.build()

    await starlette_route.endpoint(make_request())

    assert called == ["mw", "handler"]


async def test_internal_route_build_group_middleware_is_outer():
    called = []

    async def group_mw(request: Request, call_next) -> Response:
        called.append("group")
        return await call_next(request)

    async def route_mw(request: Request, call_next) -> Response:
        called.append("route")
        return await call_next(request)

    async def handler() -> Response:
        called.append("handler")
        return Response("ok")

    route = InternalRoute("/", ["GET"], handler, group_middlewares=[group_mw], middleware_group=None)
    route.middleware(route_mw)
    starlette_route = route.build()

    await starlette_route.endpoint(make_request())

    assert called == ["group", "route", "handler"]


async def test_internal_route_build_named_stack_is_outermost():
    called = []

    async def named_mw(request: Request, call_next) -> Response:
        called.append("named")
        return await call_next(request)

    async def group_mw(request: Request, call_next) -> Response:
        called.append("group")
        return await call_next(request)

    async def route_mw(request: Request, call_next) -> Response:
        called.append("route")
        return await call_next(request)

    async def handler() -> Response:
        called.append("handler")
        return Response("ok")

    route = InternalRoute("/", ["GET"], handler, group_middlewares=[group_mw], middleware_group="web")
    route.middleware(route_mw)
    starlette_route = route.build(named_stacks={"web": [named_mw]})

    await starlette_route.endpoint(make_request())

    assert called == ["named", "group", "route", "handler"]
