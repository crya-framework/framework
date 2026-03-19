import fnmatch
import re

from starlette.types import ASGIApp, Receive, Scope, Send

from crya.config.schemas import CorsConfig

type RequestHeaders = dict[bytes, bytes]
type ResponseHeaders = list[tuple[bytes, bytes]]


class CorsMiddleware:
    def __init__(self, app: ASGIApp, config: CorsConfig) -> None:
        if config.supports_credentials and "*" in config.allowed_origins:
            raise ValueError(
                "CORS: supports_credentials=True cannot be combined with "
                "allowed_origins=['*']. Specify explicit origins instead."
            )
        self.app = app
        self.config = config
        self._origin_patterns = [
            re.compile(p) for p in config.allowed_origins_patterns
        ]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        if not self._path_matches(path):
            await self.app(scope, receive, send)
            return

        req_headers: RequestHeaders = dict(scope["headers"])
        origin = req_headers.get(b"origin", b"").decode()

        if not origin:
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        if method == "OPTIONS" and b"access-control-request-method" in req_headers:
            await self._handle_preflight(req_headers, send, origin)
            return

        await self._handle_actual(scope, receive, send, origin)

    def _path_matches(self, path: str) -> bool:
        return any(fnmatch.fnmatch(path, pattern) for pattern in self.config.paths)

    def _origin_allowed(self, origin: str) -> bool:
        if "*" in self.config.allowed_origins:
            return True
        if origin in self.config.allowed_origins:
            return True
        return any(p.fullmatch(origin) for p in self._origin_patterns)

    def _allow_origin_header(self, origin: str) -> bytes:
        # supports_credentials + wildcard is rejected at init, so wildcard is safe here
        if "*" in self.config.allowed_origins:
            return b"*"
        return origin.encode()

    async def _handle_preflight(
        self,
        req_headers: RequestHeaders,
        send: Send,
        origin: str,
    ) -> None:
        response_headers: ResponseHeaders = []

        if self._origin_allowed(origin):
            response_headers.append(
                (b"access-control-allow-origin", self._allow_origin_header(origin))
            )

            if self.config.supports_credentials:
                response_headers.append(
                    (b"access-control-allow-credentials", b"true")
                )

            if "*" in self.config.allowed_methods:
                response_headers.append((b"access-control-allow-methods", b"*"))
            else:
                response_headers.append(
                    (
                        b"access-control-allow-methods",
                        ", ".join(self.config.allowed_methods).encode(),
                    )
                )

            if "*" in self.config.allowed_headers:
                response_headers.append((b"access-control-allow-headers", b"*"))
            else:
                response_headers.append(
                    (
                        b"access-control-allow-headers",
                        ", ".join(self.config.allowed_headers).encode(),
                    )
                )

            if self.config.max_age > 0:
                response_headers.append(
                    (b"access-control-max-age", str(self.config.max_age).encode())
                )

            response_headers.append((b"vary", b"Origin"))

        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": response_headers,
            }
        )
        await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def _handle_actual(
        self, scope: Scope, receive: Receive, send: Send, origin: str
    ) -> None:
        cors_headers: ResponseHeaders = []

        if self._origin_allowed(origin):
            cors_headers.append(
                (b"access-control-allow-origin", self._allow_origin_header(origin))
            )

            if self.config.supports_credentials:
                cors_headers.append((b"access-control-allow-credentials", b"true"))

            if self.config.exposed_headers:
                cors_headers.append(
                    (
                        b"access-control-expose-headers",
                        ", ".join(self.config.exposed_headers).encode(),
                    )
                )

            cors_headers.append((b"vary", b"Origin"))

        async def send_with_cors(message: dict) -> None:
            if message["type"] == "http.response.start" and cors_headers:
                message = {
                    **message,
                    "headers": list(message.get("headers", [])) + cors_headers,
                }
            await send(message)

        await self.app(scope, receive, send_with_cors)
