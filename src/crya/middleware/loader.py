from pathlib import Path

from crya.config.loader import load_config_dict
from crya.config.schemas import MiddlewareConfig
from crya.middleware.defaults import MiddlewareCallable


def load_middleware_stack(
    root: Path,
    config_directory: str,
    group: str,
    defaults: list[MiddlewareCallable],
) -> list[MiddlewareCallable]:
    config_dict = load_config_dict(root, config_directory, "middleware")
    if config_dict is None:
        return list(defaults)

    config = MiddlewareConfig.model_validate(config_dict)
    mutation = getattr(config, group)
    stack = list(defaults)

    for mw in mutation.remove:
        stack = [m for m in stack if m is not mw]
    stack = mutation.prepend + stack
    stack = stack + mutation.append

    return stack
