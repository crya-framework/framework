from typing import Any, Never, Type

from pydantic import BaseModel, ValidationError


def raise_config_error(e: ValidationError, source: str) -> Never:
    lines = [f"Configuration error in {source}:"]
    for err in e.errors():
        field = ".".join(str(loc) for loc in err["loc"])
        if err["type"] == "missing":
            lines.append(f"  - {field}: missing required value")
        else:
            lines.append(f"  - {field}: {err['msg']}")
    raise RuntimeError("\n".join(lines)) from None


def model_validate_config(model_cls: Type[BaseModel], data: Any, source: str) -> Any:
    try:
        return model_cls.model_validate(data)
    except ValidationError as e:
        raise_config_error(e, source)
