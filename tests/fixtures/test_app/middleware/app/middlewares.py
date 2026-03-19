from starlette.requests import Request
from starlette.responses import Response


async def add_header_middleware(request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers["X-Test-Header"] = "present"
    return response


async def forbidden_middleware(request: Request, call_next) -> Response:
    return Response("Forbidden", status_code=403)


async def order_a_middleware(request: Request, call_next) -> Response:
    if not hasattr(request.state, "order"):
        request.state.order = []
    request.state.order.append("A")
    return await call_next(request)


async def order_b_middleware(request: Request, call_next) -> Response:
    if not hasattr(request.state, "order"):
        request.state.order = []
    request.state.order.append("B")
    return await call_next(request)


async def order_c_middleware(request: Request, call_next) -> Response:
    if not hasattr(request.state, "order"):
        request.state.order = []
    request.state.order.append("C")
    return await call_next(request)
