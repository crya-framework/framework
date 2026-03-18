import os
from hashlib import md5
from pathlib import Path

from .compiler import compile_template
from .components import _render_component, _render_slot
from crya.vite import vite as _vite

COMPILED_PREFIX = "template_"
PROJECT_ROOT = Path(os.getcwd())

# Cache configuration
_CACHE_DIR: Path | None = None


def set_cache_dir(path: Path | str) -> None:
    """Set the cache directory for compiled templates."""
    global _CACHE_DIR
    _CACHE_DIR = Path(path)


def get_cache_dir() -> Path:
    if _CACHE_DIR is None:
        raise RuntimeError("Template cache directory has not been configured.")
    return _CACHE_DIR


def _get_hash(template: str) -> str:
    return md5(template.encode()).hexdigest()


def _get_compiled_path(template: str) -> Path:
    hash = _get_hash(template)
    filename = f"{COMPILED_PREFIX}{hash}.py"
    return get_cache_dir() / filename


def render_from_string(template: str, context: dict | None = None) -> str:
    if context is None:
        context = {}

    template_py = compile_template(template)
    compiled_path = _get_compiled_path(template)

    if not compiled_path.exists():
        compiled_path.parent.mkdir(parents=True, exist_ok=True)

        with open(compiled_path, "w") as f:
            f.write(template_py)

    # Create a namespace with context and component helpers
    namespace = {
        **context,
        "_render_component": _render_component,
        "_render_slot": _render_slot,
        "_vite": _vite,
    }

    # Execute the compiled template in the namespace
    with open(compiled_path, "r") as f:
        exec(f.read(), namespace)

    return namespace["render"]()


def render(template_path: Path, context: dict | None = None) -> str:
    if context is None:
        context = {}

    with open(template_path, "r") as f:
        template = f.read()

    return render_from_string(template, context)
