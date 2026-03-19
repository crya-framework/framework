# crya.logging

Logging for Crya apps, backed by [Loguru](https://github.com/Delgan/loguru).

## Usage

```python
from crya import log

log.debug("Cache miss", key="user:42")
log.info("Request complete", method="GET", path="/users")
log.warning("Slow query", duration_ms=320)
log.error("Payment failed", order_id=99)
log.critical("Database unreachable")
```

`log` is Loguru's `logger` — any Loguru feature works directly.

## Setup

`log` is available as soon as `crya` is imported. No configuration is required.

`App.__init__` calls `setup_logging()` automatically, which routes all stdlib `logging` output (Uvicorn, Starlette, third-party libraries) through Loguru so all log lines share a single format.

## Default output

Loguru writes to `stderr` by default with coloured, structured output. No file sink is configured by the framework.

## Adding sinks

Use Loguru's `logger.add()` directly:

```python
from crya import log

# Rotate at 10 MB, keep 14 days
# enqueue=True is required when running multiple uvicorn workers — without it,
# concurrent processes writing to the same file can produce corrupted log lines.
log.add("storage/logs/app.log", rotation="10 MB", retention="14 days", enqueue=True)
```

A good place for this is your `bootstrap.py`, before the `App` is created.

## Log levels

Standard levels in ascending severity: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

Filter by minimum level:

```python
log.add("storage/logs/errors.log", level="ERROR", enqueue=True)
```
