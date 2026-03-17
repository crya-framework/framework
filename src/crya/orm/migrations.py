"""Migration utilities for Crya ORM.

Business logic for schema diffing, model importing, and migration management.
The CLI layer calls these functions and handles all output/formatting.
"""

import importlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path


def resolve_sqlite_url(db_url: str) -> str:
    """Resolve relative SQLite paths to absolute.

    Oxyde's Rust layer interprets sqlite:///relative/path as absolute /relative/path,
    ignoring the working directory. We resolve relative paths to absolute here.
    """
    prefix = "sqlite:///"
    path_part = db_url[len(prefix):]

    if path_part == ":memory:" or path_part.startswith("/"):
        return db_url

    return f"{prefix}{Path.cwd() / path_part}"


def detect_dialect(db_url: str) -> tuple[str, str]:
    """Detect SQL dialect from a database URL.

    Returns:
        (resolved_url, dialect) where dialect is 'postgres', 'sqlite', or 'mysql'.
        For unknown schemes, dialect defaults to 'postgres'.
    """
    if "postgresql://" in db_url or "postgres://" in db_url:
        return db_url, "postgres"
    elif "sqlite://" in db_url:
        return resolve_sqlite_url(db_url), "sqlite"
    elif "mysql://" in db_url:
        return db_url, "mysql"
    else:
        return db_url, "postgres"


@dataclass
class ImportModelsResult:
    imported: list[str] = field(default_factory=list)
    failed: list[tuple[str, Exception]] = field(default_factory=list)


def import_models(modules: list[str]) -> ImportModelsResult:
    """Import model modules to register them with oxyde.

    Mutates sys.path to include CWD if not already present.
    """
    if "." not in sys.path:
        sys.path.insert(0, ".")

    result = ImportModelsResult()
    for module_name in modules:
        try:
            importlib.import_module(module_name)
            result.imported.append(module_name)
        except ImportError as e:
            result.failed.append((module_name, e))

    return result


DEFAULT_MODELS = ["app.models"]


@dataclass
class SchemaResult:
    schema: dict
    table_names: list[str]


def extract_schema(dialect: str) -> SchemaResult:
    from oxyde.migrations import extract_current_schema

    schema = extract_current_schema(dialect=dialect)
    return SchemaResult(
        schema=schema,
        table_names=list(schema["tables"].keys()),
    )


@dataclass
class DiffResult:
    operations: list[dict]


def compute_diff(old_schema: dict, current_schema: dict) -> DiffResult:
    from oxyde.core import migration_compute_diff

    operations_json = migration_compute_diff(
        json.dumps(old_schema), json.dumps(current_schema)
    )
    return DiffResult(operations=json.loads(operations_json))


def replay_schema(migrations_dir: str) -> dict:
    from oxyde.migrations import replay_migrations

    return replay_migrations(migrations_dir)


def create_migration_file(
    operations: list[dict],
    migrations_dir: str,
    name: str | None,
) -> Path:
    from oxyde.migrations import generate_migration_file

    return generate_migration_file(
        operations,
        migrations_dir=migrations_dir,
        name=name,
    )


@dataclass
class GenerateStubsResult:
    count: int


def generate_type_stubs() -> GenerateStubsResult:
    from oxyde.codegen import generate_stubs_for_models, write_stubs
    from oxyde.models.registry import registered_tables

    models_dict = registered_tables()
    if not models_dict:
        return GenerateStubsResult(count=0)

    stub_mapping = generate_stubs_for_models(list(models_dict.values()))
    write_stubs(stub_mapping)
    return GenerateStubsResult(count=len(stub_mapping))
