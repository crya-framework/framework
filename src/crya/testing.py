from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from httpx import ASGITransport, AsyncClient

if TYPE_CHECKING:
    from crya.app import App


def _is_subset(subset: Any, full: Any) -> bool:
    if isinstance(subset, dict) and isinstance(full, dict):
        return all(
            key in full and _is_subset(val, full[key]) for key, val in subset.items()
        )
    if isinstance(subset, list) and isinstance(full, list):
        return len(subset) == len(full) and all(
            _is_subset(s, f) for s, f in zip(subset, full)
        )
    return subset == full


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


class TestResponse:
    def __init__(self, response: Any) -> None:
        self._response = response

    # --- Proxy the most common httpx.Response attributes ---

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def text(self) -> str:
        return self._response.text

    @property
    def headers(self) -> Any:
        return self._response.headers

    def json(self) -> Any:
        return self._response.json()

    # --- Assertion methods (all return self for chaining) ---

    def assert_status(self, code: int) -> "TestResponse":
        actual = self._response.status_code
        assert actual == code, f"Expected status {code}, got {actual}"
        return self

    def assert_ok(self) -> "TestResponse":
        return self.assert_status(200)

    def assert_created(self) -> "TestResponse":
        return self.assert_status(201)

    def assert_no_content(self) -> "TestResponse":
        return self.assert_status(204)

    def assert_not_found(self) -> "TestResponse":
        return self.assert_status(404)

    def assert_unauthorized(self) -> "TestResponse":
        return self.assert_status(401)

    def assert_forbidden(self) -> "TestResponse":
        return self.assert_status(403)

    def assert_unprocessable(self) -> "TestResponse":
        return self.assert_status(422)

    def assert_server_error(self) -> "TestResponse":
        actual = self._response.status_code
        assert 500 <= actual < 600, f"Expected 5xx status, got {actual}"
        return self

    def assert_redirect(self, url: str | None = None) -> "TestResponse":
        actual = self._response.status_code
        assert 300 <= actual < 400, f"Expected redirect status, got {actual}"
        if url is not None:
            location = self._response.headers.get("location", "")
            assert location == url, f"Expected redirect to {url!r}, got {location!r}"
        return self

    def assert_see(self, text: str) -> "TestResponse":
        body = self._response.text
        assert text in body, f"Expected to see {text!r} in response body"
        return self

    def assert_dont_see(self, text: str) -> "TestResponse":
        body = self._response.text
        assert text not in body, f"Expected not to see {text!r} in response body"
        return self

    def assert_see_text(self, text: str) -> "TestResponse":
        plain = _strip_html(self._response.text)
        assert text in plain, f"Expected to see text {text!r} in response (HTML stripped)"
        return self

    def assert_dont_see_text(self, text: str) -> "TestResponse":
        plain = _strip_html(self._response.text)
        assert text not in plain, (
            f"Expected not to see text {text!r} in response (HTML stripped)"
        )
        return self

    def assert_json(self, data: dict | list) -> "TestResponse":
        """Assert that the response JSON contains the given data (subset match)."""
        actual = self._response.json()
        assert _is_subset(data, actual), (
            f"Response JSON does not contain expected data.\n"
            f"Expected subset: {data!r}\n"
            f"Actual: {actual!r}"
        )
        return self

    def assert_json_exact(self, data: dict | list) -> "TestResponse":
        """Assert that the response JSON equals the given data exactly."""
        actual = self._response.json()
        assert actual == data, (
            f"Response JSON does not match.\nExpected: {data!r}\nActual: {actual!r}"
        )
        return self

    def assert_header(self, name: str, value: str | None = None) -> "TestResponse":
        assert name in self._response.headers, (
            f"Expected header {name!r} to be present"
        )
        if value is not None:
            actual = self._response.headers[name]
            assert actual == value, (
                f"Expected header {name!r} to be {value!r}, got {actual!r}"
            )
        return self

    def assert_header_missing(self, name: str) -> "TestResponse":
        assert name not in self._response.headers, (
            f"Expected header {name!r} to be absent"
        )
        return self


class TestClient:
    def __init__(self, app: "App", base_url: str = "http://test") -> None:
        self._app = app
        self._base_url = base_url
        self._client: AsyncClient | None = None

    async def __aenter__(self) -> "TestClient":
        self._client = AsyncClient(
            transport=ASGITransport(app=self._app),
            base_url=self._base_url,
        )
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client is not None:
            await self._client.__aexit__(*args)
            self._client = None

    def _require_client(self) -> AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "TestClient must be used as an async context manager: "
                "`async with TestClient(app) as client: ...`"
            )
        return self._client

    async def get(self, url: str, **kwargs: Any) -> TestResponse:
        return TestResponse(await self._require_client().get(url, **kwargs))

    async def post(self, url: str, **kwargs: Any) -> TestResponse:
        return TestResponse(await self._require_client().post(url, **kwargs))

    async def put(self, url: str, **kwargs: Any) -> TestResponse:
        return TestResponse(await self._require_client().put(url, **kwargs))

    async def patch(self, url: str, **kwargs: Any) -> TestResponse:
        return TestResponse(await self._require_client().patch(url, **kwargs))

    async def delete(self, url: str, **kwargs: Any) -> TestResponse:
        return TestResponse(await self._require_client().delete(url, **kwargs))
