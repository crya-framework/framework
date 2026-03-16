import importlib
from pathlib import Path

import pytest

_config_base = importlib.import_module("crya.config.base")
from pydantic import ValidationError

from crya import BaseEnv, env

_ENV_DIR = Path(__file__).parent / "fixtures" / "config"


class AppEnv(BaseEnv):
    APP_NAME: str
    DEBUG: bool = False
    PORT: int = 8000


class StrictEnv(BaseEnv):
    REQUIRED_KEY: str


@pytest.fixture(autouse=True)
def reset_env(monkeypatch):
    monkeypatch.chdir(_ENV_DIR)
    monkeypatch.setattr(_config_base, "_env_instance", None)


def test_reads_values_from_env_file():
    cfg = AppEnv()

    assert cfg.APP_NAME == "CryaTest"
    assert cfg.PORT == 8080


def test_casts_types_from_env_file():
    cfg = AppEnv()

    assert cfg.DEBUG is True
    assert cfg.PORT == 8080
    assert isinstance(cfg.PORT, int)


def test_default_used_when_key_absent_from_env_file():
    class EnvAbsent(BaseEnv):
        MISSING: str = "fallback"

    cfg = EnvAbsent()

    assert cfg.MISSING == "fallback"


def test_real_env_var_overrides_env_file(monkeypatch):
    monkeypatch.setenv("PORT", "1234")

    cfg = AppEnv()

    assert cfg.PORT == 1234


def test_raises_on_missing_required_key(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("REQUIRED_KEY", raising=False)

    with pytest.raises(ValidationError):
        StrictEnv()


def test_env_callable_returns_value():
    AppEnv()

    assert env("APP_NAME") == "CryaTest"
    assert env("PORT") == 8080


def test_env_attribute_returns_value():
    AppEnv()

    assert env.APP_NAME == "CryaTest"
    assert env.DEBUG is True


def test_env_callable_raises_on_undeclared_key():
    AppEnv()

    with pytest.raises(KeyError):
        env("UNDECLARED")


def test_env_attribute_raises_on_undeclared_key():
    AppEnv()

    with pytest.raises(AttributeError):
        _ = env.UNDECLARED


def test_env_raises_when_no_base_env_registered():
    with pytest.raises(RuntimeError, match="No env configured"):
        env("APP_NAME")
