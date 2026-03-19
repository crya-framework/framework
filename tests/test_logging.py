import logging

import pytest
from loguru import logger

from crya.logging import _InterceptHandler, log, setup_logging


def test_log_is_loguru_logger():
    assert log is logger


def test_setup_logging_installs_intercept_handler():
    setup_logging()

    root = logging.getLogger()
    assert any(isinstance(h, _InterceptHandler) for h in root.handlers)


def test_setup_logging_is_idempotent():
    setup_logging()
    setup_logging()

    root = logging.getLogger()
    intercept_handlers = [h for h in root.handlers if isinstance(h, _InterceptHandler)]
    assert len(intercept_handlers) == 1


def test_intercept_handler_routes_stdlib_log_through_loguru():
    setup_logging()

    received = []
    handler_id = logger.add(lambda msg: received.append(msg), format="{message}")

    try:
        logging.getLogger("test").info("hello from stdlib")
    finally:
        logger.remove(handler_id)

    assert len(received) == 1
    assert "hello from stdlib" in received[0]


@pytest.mark.parametrize("level_name,level_method", [
    ("INFO", "info"),
    ("WARNING", "warning"),
    ("ERROR", "error"),
    ("DEBUG", "debug"),
])
def test_intercept_handler_maps_stdlib_level_to_loguru(level_name, level_method):
    setup_logging()

    received = []
    handler_id = logger.add(
        lambda msg: received.append(msg),
        format="{level} {message}",
    )

    try:
        getattr(logging.getLogger("test"), level_method)("test message")
    finally:
        logger.remove(handler_id)

    assert len(received) == 1
    assert level_name in received[0]
    assert "test message" in received[0]


def test_intercept_handler_falls_back_to_levelno_for_unknown_level():
    handler = _InterceptHandler()
    record = logging.LogRecord(
        name="test",
        level=42,
        pathname="",
        lineno=0,
        msg="custom level message",
        args=(),
        exc_info=None,
    )
    record.levelname = "CUSTOM_UNKNOWN_LEVEL"

    received = []
    handler_id = logger.add(lambda msg: received.append(msg), format="{message}")

    try:
        handler.emit(record)
    finally:
        logger.remove(handler_id)

    assert len(received) == 1
    assert "custom level message" in received[0]
