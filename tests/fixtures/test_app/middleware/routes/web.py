from crya import Router

from ..app.handlers import order_handler, plain
from ..app.middlewares import (
    add_header_middleware,
    forbidden_middleware,
    order_b_middleware,
    order_c_middleware,
)

router = Router()

router.get("/plain", plain)
router.get("/with-header", plain).middleware(add_header_middleware)
router.get("/forbidden", plain).middleware(forbidden_middleware)

with router.group(prefix="/group", middlewares=[add_header_middleware]):
    router.get("/route", plain)

with router.group(
    prefix="/named",
    middlewares=[order_b_middleware],
    middleware_group="web",
):
    router.get("/route", order_handler).middleware(order_c_middleware)
