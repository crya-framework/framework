import inspect
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Literal, TypeAlias

from starlette.datastructures import QueryParams

from crya import Request

type Source = Literal["PATH", "QUERY"]

InspectedParameters: TypeAlias = MappingProxyType[str, inspect.Parameter]


@dataclass
class RequestParam:
    param_name: str
    value: Any = None
    target_type: type | None = None
    source: Source | None = None


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
