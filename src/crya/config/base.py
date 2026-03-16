from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

_env_instance: "BaseEnv | None" = None


class BaseEnv(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **data):
        super().__init__(**data)
        global _env_instance
        _env_instance = self


class _EnvProxy:
    def __call__(self, key: str) -> Any:
        if _env_instance is None:
            raise RuntimeError("No env configured. Create config/env.py with a BaseEnv subclass.")
        try:
            return getattr(_env_instance, key)
        except AttributeError:
            raise KeyError(f"'{key}' is not declared in your BaseEnv")

    def __getattr__(self, key: str) -> Any:
        if _env_instance is None:
            raise RuntimeError("No env configured. Create config/env.py with a BaseEnv subclass.")
        try:
            return getattr(_env_instance, key)
        except AttributeError:
            raise AttributeError(f"'{key}' is not declared in your BaseEnv")


env = _EnvProxy()
