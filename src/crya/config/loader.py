import importlib
from pathlib import Path


def load_config_dict(root: Path, config_directory: str, name: str) -> dict | None:
    config_file = root / config_directory / f"{name}.py"
    if not config_file.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"_crya_{config_directory}_{name}", config_file)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "config") or not isinstance(module.config, dict):
        raise ValueError(
            f"'{config_directory}/{name}.py' must define a top-level 'config' dict"
        )
    return module.config
