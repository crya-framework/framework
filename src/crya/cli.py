import importlib
import os
import sys
from pathlib import Path

import asyncclick as click
import uvicorn

from crya.console import blank, error, info, success, warning


def _get_db_config():
    """Get database configuration from environment."""
    try:
        importlib.import_module("config.env")
    except ImportError as e:
        error("Could not import config/env.py", emoji=True)
        info(f"   Error: {e}")
        info("   Create config/env.py with a BaseEnv subclass defining DATABASE_URL")
        raise click.Abort()

    from crya.config import env

    try:
        db_url = env("DATABASE_URL")
    except Exception as e:
        error("DATABASE_URL not found in environment", emoji=True)
        info(f"   Error: {e}")
        info("   Set DATABASE_URL in your .env file or config/env.py")
        raise click.Abort()

    from crya.orm.migrations import detect_dialect

    db_url, dialect = detect_dialect(db_url)

    if dialect == "postgres" and "postgresql://" not in db_url and "postgres://" not in db_url:
        warning("Unknown database URL scheme, defaulting to postgres", emoji=True)

    return db_url, dialect


@click.group()
async def cli():
    pass


@cli.command()
@click.argument("app", default="bootstrap:app")
async def serve(app: str):
    sys.path.insert(0, os.getcwd())
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, reload=True)
    server = uvicorn.Server(config)

    await server.serve()


@cli.command()
@click.option("--name", default=None, help="Migration name")
@click.option("--dry-run", is_flag=True, help="Show what would be created without creating")
@click.option("--models", default=None, help="Comma-separated list of model modules (e.g., 'models,app.models')")
@click.option("--migrations-dir", default="database/migrations", help="Migrations directory")
async def makemigrations(name: str | None, dry_run: bool, models: str | None, migrations_dir: str):
    """Create migration files from model changes."""
    from crya.orm.migrations import (
        DEFAULT_MODELS,
        compute_diff,
        create_migration_file,
        extract_schema,
        generate_type_stubs,
        import_models,
        replay_schema,
    )

    sys.path.insert(0, os.getcwd())

    db_url, dialect = _get_db_config()

    info("📝 Creating migrations...")
    blank()

    # Import models
    info("0️⃣  Loading models...")
    modules = [m.strip() for m in models.split(",")] if models else DEFAULT_MODELS
    result = import_models(modules)

    for module_name, err in result.failed:
        warning(f"   Failed to import '{module_name}': {err}", emoji=True)

    if not result.imported:
        error("   No modules imported", emoji=True)
        raise click.Abort()

    success(f"   Imported {len(result.imported)} module(s)", emoji=True)

    # Extract current schema
    blank()
    info("1️⃣  Extracting schema from models...")
    try:
        schema_result = extract_schema(dialect=dialect)
        if schema_result.table_names:
            tables = ", ".join(schema_result.table_names)
            success(f"   Found {len(schema_result.table_names)} table(s): {tables}", emoji=True)
        else:
            warning("   No tables found", emoji=True)
            info("   Make sure your models have 'class Meta: is_table = True'")
    except Exception as e:
        error(f"   Error extracting schema: {e}", emoji=True)
        raise click.Abort()

    # Replay existing migrations
    blank()
    info("2️⃣  Replaying existing migrations...")
    migrations_path = Path(migrations_dir)

    if not migrations_path.exists():
        if not dry_run:
            migrations_path.mkdir(parents=True, exist_ok=True)
        old_schema = {"version": 1, "tables": {}}
    else:
        try:
            old_schema = replay_schema(migrations_dir)
            migration_count = len(list(migrations_path.glob("[0-9]*.py")))
            success(f"   Replayed {migration_count} migration(s)", emoji=True)
        except Exception as e:
            error(f"   Error replaying migrations: {e}", emoji=True)
            info("   Fix the broken migration(s) before running makemigrations.")
            raise click.Abort()

    # Compute diff
    blank()
    info("3️⃣  Computing diff...")
    try:
        diff = compute_diff(old_schema, schema_result.schema)

        if not diff.operations:
            blank()
            success("   ✨ No changes detected")
            return

        success(f"   Found {len(diff.operations)} operation(s):", emoji=True)
        for op in diff.operations:
            op_type = op.get("type", "unknown")
            if op_type == "create_table":
                info(f"      - Create table: {op['table']['name']}")
            elif op_type == "drop_table":
                info(f"      - Drop table: {op['name']}")
            elif op_type == "add_column":
                info(f"      - Add column: {op['table']}.{op['field']['name']}")
            elif op_type == "drop_column":
                info(f"      - Drop column: {op['table']}.{op['field']}")
            else:
                info(f"      - {op_type}")

    except Exception as e:
        error(f"   Error computing diff: {e}", emoji=True)
        raise click.Abort()

    # Generate migration file
    blank()
    if dry_run:
        warning("   [DRY RUN] Would create migration file")
        info(f"   Migration name: {name or 'auto'}")
        info(f"   Operations: {len(diff.operations)}")
    else:
        info("4️⃣  Generating migration file...")
        try:
            filepath = create_migration_file(diff.operations, migrations_dir=migrations_dir, name=name)
            blank()
            success(f"   Created: {filepath}", emoji=True, bold=True)
        except Exception as e:
            error(f"   Error generating migration: {e}", emoji=True)
            raise click.Abort()

        # Generate type stubs
        blank()
        info("5️⃣  Generating type stubs...")
        try:
            stubs = generate_type_stubs()
            if stubs.count:
                success(f"   Generated {stubs.count} stub file(s)", emoji=True)
            else:
                warning("   No models to generate stubs for", emoji=True)
        except Exception as e:
            warning(f"   Warning: Could not generate stubs: {e}", emoji=True)


@cli.command()
@click.argument("target", required=False)
@click.option("--fake", is_flag=True, help="Mark migrations as applied without running SQL")
@click.option("--migrations-dir", default="database/migrations", help="Migrations directory")
async def migrate(target: str | None, fake: bool, migrations_dir: str):
    """Apply pending migrations."""
    from oxyde.cli.app import init_databases
    from oxyde.migrations import (
        apply_migrations,
        get_applied_migrations,
        get_migration_files,
        get_pending_migrations,
        rollback_migrations,
    )

    sys.path.insert(0, os.getcwd())

    db_url, dialect = _get_db_config()
    db_alias = "default"

    info("⏳ Applying migrations...")
    blank()

    if fake:
        warning("[FAKE MODE] Marking migrations as applied without executing SQL", emoji=True)
        blank()

    await init_databases({db_alias: db_url})

    try:
        applied = await get_applied_migrations(db_alias)
        all_migrations = get_migration_files(migrations_dir)

        if target and target.lower() == "zero":
            if not applied:
                success("✨ No migrations to roll back")
                return

            info(f"Rolling back all {len(applied)} migration(s)...")
            blank()

            rolled_back = await rollback_migrations(
                steps=len(applied),
                migrations_dir=migrations_dir,
                db_alias=db_alias,
                fake=fake,
            )

            if rolled_back:
                blank()
                success(f"Rolled back {len(rolled_back)} migration(s)", emoji=True, bold=True)
                for migration_name in rolled_back:
                    info(f"   - {migration_name}")
            return

        if target:
            target_idx = -1
            for i, m in enumerate(all_migrations):
                if m.stem == target or m.stem.startswith(target):
                    target_idx = i
                    break

            if target_idx == -1:
                error(f"Migration '{target}' not found", emoji=True)
                raise click.Abort()

            current_idx = -1
            for i, m in enumerate(all_migrations):
                if m.stem in applied:
                    current_idx = i

            if target_idx < current_idx:
                steps = current_idx - target_idx
                info(f"Rolling back {steps} migration(s) to reach {target}...")
                blank()

                rolled_back = await rollback_migrations(
                    steps=steps,
                    migrations_dir=migrations_dir,
                    db_alias=db_alias,
                    fake=fake,
                )

                if rolled_back:
                    blank()
                    success(f"Rolled back {len(rolled_back)} migration(s)", emoji=True, bold=True)
                    for migration_name in rolled_back:
                        info(f"   - {migration_name}")
                return

        pending = get_pending_migrations(migrations_dir, applied)

        if not pending:
            success("✨ No pending migrations")
            return

        if target:
            filtered = []
            for m in pending:
                filtered.append(m)
                if m.stem == target or m.stem.startswith(target):
                    break
            pending = filtered

        info(f"Found {len(pending)} pending migration(s):")
        for migration_path in pending:
            info(f"  - {migration_path.stem}")
        blank()

        if target:
            info(f"Migrating to: {target}")
        else:
            info("Migrating to latest...")

        applied_migrations = await apply_migrations(
            migrations_dir=migrations_dir,
            db_alias=db_alias,
            target=target,
            fake=fake,
        )

        if applied_migrations:
            blank()
            success(f"Applied {len(applied_migrations)} migration(s)", emoji=True, bold=True)
            for migration_name in applied_migrations:
                info(f"   - {migration_name}")

    except Exception as e:
        error(f"Error applying migrations: {e}", emoji=True)
        import traceback
        traceback.print_exc()
        raise click.Abort()


@cli.command()
@click.option("--migrations-dir", default="database/migrations", help="Migrations directory")
async def showmigrations(migrations_dir: str):
    """Show migration status."""
    from oxyde.cli.app import init_databases
    from oxyde.migrations import get_applied_migrations, get_migration_files

    sys.path.insert(0, os.getcwd())

    db_url, dialect = _get_db_config()
    db_alias = "default"

    info("📋 Migrations status:")
    blank()

    try:
        await init_databases({db_alias: db_url})

        applied = await get_applied_migrations(db_alias)
        applied_set = set(applied)

        all_migrations = get_migration_files(migrations_dir)

        if not all_migrations:
            warning("No migrations found")
            return

        for migration_path in all_migrations:
            name = migration_path.stem
            if name in applied_set:
                success(f"  [✓] {name}")
            else:
                info(f"  [ ] {name}")

        blank()
        info(f"Total: {len(all_migrations)} migration(s)")
        info(f"Applied: {len(applied_set)}")
        info(f"Pending: {len(all_migrations) - len(applied_set)}")

    except Exception as e:
        error(f"Error reading migrations: {e}", emoji=True)
        raise click.Abort()


def main():
    cli()


if __name__ == "__main__":
    main()
