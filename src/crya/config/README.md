# crya.config

Two-layer configuration system for Crya apps.

- **Layer 1** — env var validation via `BaseEnv` (pydantic-settings). Single source of truth for what the app requires from the environment.
- **Layer 2** — plain config files (dataclasses or any Python) that call `env()` to pull validated values in. No validation overhead; structure is up to the user.

## Layer 1 — env vars

Create `config/env.py` in your skeleton app with a single `BaseEnv` subclass:

```python
# config/env.py
from crya import BaseEnv

class Env(BaseEnv):
    APP_NAME: str
    DEBUG: bool = False
    DATABASE_URL: str

Env()
```

`App.__init__` imports `config/env.py` eagerly. The `BaseEnv` subclass registers itself globally on instantiation, making its values available via the `env` proxy. Missing required fields raise a `ValidationError` before the first request is served.

Values are resolved in this order (highest priority first):

1. Real environment variables
2. Variables from `.env` in the working directory
3. Field defaults declared on the class

Your `.env` file:

```dotenv
APP_NAME=MyApp
DEBUG=true
DATABASE_URL=sqlite:///db.sqlite3
```

### Accessing env vars

```python
from crya import env

# Callable — returns Any
db_url = env("DATABASE_URL")

# Attribute — preserves type information for the type-checker
db_url = env.DATABASE_URL
```

Both raise clearly if the key was not declared in `BaseEnv`, or if no `BaseEnv` has been registered yet.

## Layer 2 — config files

Config files are plain Python. Each file must expose a top-level `config` dict. Use `env()` to pull validated values in.

```python
# config/database.py
from crya import env

config = {
    "url": env("DATABASE_URL"),
    "pool_size": 5,
}
```

```python
# config/app.py
from crya import env

config = {
    "name": env("APP_NAME"),
    "debug": env("DEBUG"),
}
```

### Accessing config via the proxy

`config.foo` imports `config/foo.py`, reads its `config` dict, and returns a dot-access wrapper. Nesting is supported: `config.foo.bar` imports `config/foo/bar.py` (intermediate directories must be Python packages with `__init__.py`). Nested dicts are also accessible via dot notation.

```python
from crya import config

config.database.url              # config/database.py → config["url"]
config.app.name                  # config/app.py → config["name"]
config.payments.stripe.secret_key  # config/payments/stripe.py → config["secret_key"]
```

Accessing a path with no matching file, a missing `config` dict, or an unknown key raises `AttributeError`.

### Accessing config directly

```python
from config.database import config as database_config

database_config["url"]
```

## Module layout

| File | Purpose |
|------|---------|
| `base.py` | `BaseEnv` — `BaseSettings` subclass that registers itself globally on instantiation; `_EnvProxy` class; `env` instance |
| `proxy.py` | `_ConfigProxy` — recursive `__getattr__` that maps attribute paths to config modules |
