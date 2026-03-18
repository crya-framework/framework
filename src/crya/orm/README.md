# crya.orm

`crya.orm` is a thin re-export layer over [Oxyde](https://github.com/mr-fatalyst/oxyde), an async ORM with a Rust core and Pydantic v2 models. It is the built-in ORM of the Crya framework.

## Setup

Set your database URL as an env var and expose it via `config/env.py`:

```python
# config/env.py
from crya import BaseEnv

class Env(BaseEnv):
    DATABASE_URL: str

Env()
```

Then reference it in `config/database.py`:

```python
# config/database.py
from crya import env

config = {
    "url": env("DATABASE_URL"),
}
```

Crya reads `config/database.py` automatically on startup, opens the connection during lifespan, and closes it on shutdown.

Supported URL schemes: `sqlite:///`, `postgresql://`, `mysql://`.

## Defining models

```python
from crya.orm import Model, Field

class Post(Model):
    id: int | None = Field(default=None, db_pk=True)
    title: str
    body: str
    published: bool = Field(default=False)

    class Meta:
        is_table = True
```

Common `Field` parameters:

| Parameter | Description |
|-----------|-------------|
| `db_pk=True` | Primary key |
| `db_unique=True` | Unique constraint |
| `db_default` | Database-level default (e.g. `"CURRENT_TIMESTAMP"`) |
| `db_on_delete` | Cascade rule for FK relations (e.g. `"CASCADE"`) |

## CRUD

```python
# Create
post = await Post.objects.create(title="Hello", body="World")

# Read
all_posts = await Post.objects.all()
post = await Post.objects.get(id=1)
published = await Post.objects.filter(published=True)

# Update
await Post.objects.filter(id=1).update(title="Updated")

# Delete
await Post.objects.filter(id=1).delete()
```

## Querying

### Q objects (complex filters)

```python
from crya.orm import Q

results = await Post.objects.filter(Q(published=True) & Q(title__contains="crya"))
```

### F expressions (column references)

```python
from crya.orm import F

await Post.objects.filter(id=1).update(views=F("views") + 1)
```

### Aggregations

```python
from crya.orm import Count, Sum, Avg, Max, Min

count = await Post.objects.count()
total = await Post.objects.aggregate(Sum("views"))
```

### Joins

```python
posts = await Post.objects.join("author")
```

## Transactions

```python
from crya.orm import atomic

async with atomic():
    author = await Author.objects.create(name="Alice")
    await Post.objects.create(title="First", author=author)
```

Nested `atomic()` blocks use savepoints automatically.

## Migrations

Migrations are managed through the Crya CLI, which integrates with Oxyde's migration system:

### Commands

```bash
# Generate a migration from model changes
crya makemigrations

# Generate with a custom name
crya makemigrations --name add_user_email

# Apply pending migrations
crya migrate

# Show migration status
crya showmigrations
```

### Options

**makemigrations**:
- `--name`: Custom migration name
- `--models`: Comma-separated list of model modules (auto-discovers `models` by default)
- `--migrations-dir`: Custom migrations directory (defaults to `database/migrations`)
- `--dry-run`: Preview changes without creating files

**migrate**:
- `[target]`: Migrate to a specific migration (e.g., `0001`)
- `--fake`: Mark migrations as applied without executing SQL
- `--migrations-dir`: Custom migrations directory (defaults to `database/migrations`)

**showmigrations**:
- `--migrations-dir`: Custom migrations directory (defaults to `database/migrations`)

### Model Location

By default, Crya looks for models in `app/models.py`. To use a different location, specify it with `--models`:

```bash
crya makemigrations --models myapp.db.models,shared.models
```

## Full API reference

All public symbols from Oxyde are re-exported from `crya.orm`:

| Symbol | Description |
|--------|-------------|
| `Model` | Base class for all models |
| `Field` | Field definition with DB constraints |
| `Index`, `Check` | Additional schema constraints |
| `Q` | Composable filter expressions |
| `F` | Column reference for expressions |
| `atomic` | Async transaction context manager |
| `Count`, `Sum`, `Avg`, `Max`, `Min` | Aggregation functions |
| `Concat`, `Coalesce`, `RawSQL` | SQL expressions |
| `db` | Low-level database handle (`db.init(...)`) |
| `disconnect_all` | Close all connections |
| `get_connection`, `register_connection` | Manual connection management |
| `execute_raw` | Run raw SQL |
| `AsyncDatabase`, `PoolSettings` | Connection configuration |
| `OxydeError`, `NotFoundError`, `IntegrityError`, `ManagerError`, `MultipleObjectsReturned`, `FieldError`, `FieldLookupError`, `FieldLookupValueError`, `TransactionTimeoutError` | Exceptions |
| `Query`, `QueryManager` | Low-level query building |
