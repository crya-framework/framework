import sys
from pathlib import Path

import pytest

from crya import config

_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "config_proxy"


@pytest.fixture(autouse=True)
def isolated_config_env(monkeypatch):
    monkeypatch.chdir(_FIXTURE_DIR)
    monkeypatch.syspath_prepend(str(_FIXTURE_DIR))
    for key in list(sys.modules.keys()):
        if key.startswith("config"):
            monkeypatch.delitem(sys.modules, key)


def test_flat_config_returns_module():
    module = config.app

    assert module.app_config.app_name == "CryaTest"


def test_flat_config_module_attributes():
    module = config.app

    assert module.app_config.debug is True


def test_nested_config_returns_module():
    module = config.database.main

    assert module.db_config.url == "sqlite:///db.sqlite3"


def test_missing_module_raises_attribute_error():
    with pytest.raises(AttributeError, match="No config module"):
        _ = config.nonexistent


def test_missing_nested_module_raises_attribute_error():
    with pytest.raises(AttributeError, match="No config module"):
        _ = config.database.nonexistent
