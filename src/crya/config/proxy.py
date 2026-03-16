import importlib


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

        return module


config = _ConfigProxy()
