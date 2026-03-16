import importlib


class _DotDict:
    def __init__(self, data: dict):
        object.__setattr__(self, "_data", data)

    def __getattr__(self, name: str):
        data = object.__getattribute__(self, "_data")
        try:
            value = data[name]
        except KeyError:
            raise AttributeError(f"No config key '{name}'")
        if isinstance(value, dict):
            return _DotDict(value)
        return value

    def _as_dict(self) -> dict:
        return object.__getattribute__(self, "_data")

    def __repr__(self):
        return f"_DotDict({object.__getattribute__(self, '_data')!r})"


class _ConfigProxy:
    def __init__(self, prefix: str = "config"):
        object.__setattr__(self, "_prefix", prefix)

    def __getattr__(self, name: str):
        path = f"{object.__getattribute__(self, '_prefix')}.{name}"

        try:
            module = importlib.import_module(path)
        except ModuleNotFoundError:
            raise AttributeError(f"No config module '{path.replace('.', '/')}' found")

        if hasattr(module, "__path__"):
            return _ConfigProxy(path)

        if not hasattr(module, "config"):
            raise AttributeError(
                f"Config module '{path.replace('.', '/') + '.py'}' must define a 'config' dict"
            )

        data = getattr(module, "config")
        if not isinstance(data, dict):
            raise AttributeError(
                f"'config' in '{path.replace('.', '/') + '.py'}' must be a dict, got {type(data).__name__}"
            )

        return _DotDict(data)


config = _ConfigProxy()
