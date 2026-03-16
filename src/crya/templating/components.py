import os
from pathlib import Path

# Component configuration
_COMPONENT_BASE_DIR: Path | None = None

PROJECT_ROOT = Path(os.getcwd())


def set_component_base_dir(path: Path | str) -> None:
    """Set the base directory for component templates."""
    global _COMPONENT_BASE_DIR
    _COMPONENT_BASE_DIR = Path(path)


def get_component_base_dir() -> Path:
    """Get component base directory with fallback."""
    if _COMPONENT_BASE_DIR is not None:
        return _COMPONENT_BASE_DIR
    return PROJECT_ROOT / "components"


def _resolve_component_path(component_name: str) -> Path:
    """
    Convert component name to file path.
    Examples: 'alert' -> components/alert.loom
              'card.header' -> components/card/header.loom
    """
    path_parts = component_name.replace(".", "/")
    component_path = get_component_base_dir() / path_parts
    return component_path.with_suffix(".loom")


def _render_slot(slot_template: str, parent_context: dict) -> str:
    """Render slot content as a template with parent context."""
    if not slot_template:
        return ""
    # Lazy import to avoid circular dependency
    from .renderer import render_from_string

    return render_from_string(slot_template, parent_context)


def _render_component(
    component_name: str, attributes: dict, slot_content: str, parent_context: dict
) -> str:
    """Render a component with given attributes and slot content."""
    # Lazy import to avoid circular dependency
    from .renderer import render_from_string

    component_path = _resolve_component_path(component_name)

    if not component_path.exists():
        raise FileNotFoundError(
            f"Component '{component_name}' not found at {component_path}"
        )

    with open(component_path, "r") as f:
        component_template = f.read()

    # Build component context: parent + attributes + special vars
    component_context = {
        **parent_context,
        **attributes,
        "slot": slot_content,
        "attributes": attributes,
    }

    return render_from_string(component_template, component_context)
