from starlette.requests import Request
from starlette.responses import JSONResponse, Response


async def plain() -> Response:
    return Response("plain")


async def order_handler(request: Request) -> Response:
    order = getattr(request.state, "order", [])
    return JSONResponse(order)
