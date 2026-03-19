from tests.fixtures.test_app.middleware.app.middlewares import order_a_middleware

config = {
    "web": {
        "append": [order_a_middleware],
    }
}
