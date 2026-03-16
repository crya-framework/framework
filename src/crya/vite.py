import json
from dataclasses import dataclass
from pathlib import Path

_hot_file: Path | None = None
_manifest_path: Path | None = None
_build_url: str = "/build"


@dataclass
class ViteConfig:
    hot_file: str = "public/hot"
    manifest: str = "public/build/.vite/manifest.json"
    build_url: str = "/build"
    build_dir: str = "public/build"


def _configure(root: Path, config: ViteConfig) -> None:
    global _hot_file, _manifest_path, _build_url
    _hot_file = root / config.hot_file
    _manifest_path = root / config.manifest
    _build_url = config.build_url


def _is_dev() -> bool:
    return _hot_file is not None and _hot_file.exists()


def _dev_server_url() -> str:
    if _hot_file and _hot_file.exists():
        url = _hot_file.read_text().strip()
        return url if url else "http://localhost:5173"
    return "http://localhost:5173"


def vite(entries: str | list[str]) -> str:
    """Generate Vite asset tags. Used via @vite() directive in templates."""
    if isinstance(entries, str):
        entries = [entries]

    if _is_dev():
        url = _dev_server_url()
        tags = [f'<script type="module" src="{url}/@vite/client"></script>']
        for entry in entries:
            tags.append(f'<script type="module" src="{url}/{entry}"></script>')
        return "\n".join(tags)

    if _manifest_path is None:
        raise RuntimeError(
            "Vite is not configured. Pass vite=ViteConfig(...) to App()."
        )

    manifest = json.loads(_manifest_path.read_text())
    tags = []
    for entry in entries:
        chunk = manifest[entry]
        for css in chunk.get("css", []):
            tags.append(f'<link rel="stylesheet" href="{_build_url}/{css}">')
        tags.append(
            f'<script type="module" src="{_build_url}/{chunk["file"]}"></script>'
        )
    return "\n".join(tags)
