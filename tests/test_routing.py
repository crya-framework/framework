from unittest.mock import MagicMock

from starlette.datastructures import QueryParams

from crya import Request
from crya.routing import RequestParam, extract_request_params


async def test_it_extracts_request():
    async def my_endpoint(request: Request):
        pass

    request = MagicMock(Request)

    params = extract_request_params(request, my_endpoint)

    assert params == {
        "request": RequestParam(param_name="request", value=request, source=None)
    }


async def test_it_extracts_query():
    async def my_endpoint(q: str):
        pass

    request = MagicMock(Request)
    query_params = QueryParams({"q": "hello"})

    request.query_params = query_params

    params = extract_request_params(request, my_endpoint)

    assert params == {
        "q": RequestParam(
            param_name="q", value="hello", source="QUERY", target_type=str
        )
    }


async def test_it_extracts_path():
    async def my_endpoint(id: int):
        pass

    request = MagicMock(Request)
    path_params = {"id": None}

    request.path_params = path_params

    params = extract_request_params(request, my_endpoint)

    assert params == {
        "id": RequestParam(param_name="id", value=None, source="PATH", target_type=int)
    }
