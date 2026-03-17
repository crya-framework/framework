import importlib
import os
import sys
from pathlib import Path

import asyncclick as click
import uvicorn


def _get_db_config():
    """Get database configuration from environment."""
    try:
        importlib.import_module("config.env")
    except ImportError as e:
        click.secho("❌ Could not import config/env.py", fg="red")
        click.echo(f"   Error: {e}")
        click.echo("   Create config/env.py with a BaseEnv subclass defining DATABASE_URL")
        raise click.Abort()

    from crya.config import env

    try:
        db_url = env("DATABASE_URL")
    except Exception as e:
        click.secho("❌ DATABASE_URL not found in environment", fg="red")
        click.echo(f"   Error: {e}")
        click.echo("   Set DATABASE_URL in your .env file or config/env.py")
        raise click.Abort()

    from crya.orm.migrations import detect_dialect

    db_url, dialect = detect_dialect(db_url)

    if dialect == "postgres" and "postgresql://" not in db_url and "postgres://" not in db_url:
        click.secho("⚠️  Unknown database URL scheme, defaulting to postgres", fg="yellow")

    return db_url, dialect


@click.group()
async def cli():
    pass


@cli.command()
@click.argument("app")
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

    click.echo("📝 Creating migrations...")
    click.echo()

    # Import models
    click.echo("0️⃣  Loading models...")
    modules = [m.strip() for m in models.split(",")] if models else DEFAULT_MODELS
    result = import_models(modules)

    for module_name, error in result.failed:
        click.secho(f"   ⚠️  Failed to import '{module_name}': {error}", fg="yellow")

    if not result.imported:
        click.secho("   ❌ No modules imported", fg="red")
        raise click.Abort()

    click.echo(f"   ✅ Imported {len(result.imported)} module(s)")

    # Extract current schema
    click.echo()
    click.echo("1️⃣  Extracting schema from models...")
    try:
        schema_result = extract_schema(dialect=dialect)
        if schema_result.table_names:
            tables = ", ".join(schema_result.table_names)
            click.echo(f"   ✅ Found {len(schema_result.table_names)} table(s): {tables}")
        else:
            click.secho("   ⚠️  No tables found", fg="yellow")
            click.echo("   Make sure your models have 'class Meta: is_table = True'")
    except Exception as e:
        click.secho(f"   ❌ Error extracting schema: {e}", fg="red")
        raise click.Abort()

    # Replay existing migrations
    click.echo()
    click.echo("2️⃣  Replaying existing migrations...")
    migrations_path = Path(migrations_dir)

    if not migrations_path.exists():
        if not dry_run:
            migrations_path.mkdir(parents=True, exist_ok=True)
        old_schema = {"version": 1, "tables": {}}
    else:
        try:
            old_schema = replay_schema(migrations_dir)
            migration_count = len(list(migrations_path.glob("[0-9]*.py")))
            click.echo(f"   ✅ Replayed {migration_count} migration(s)")
        except Exception as e:
            click.secho(f"   ❌ Error replaying migrations: {e}", fg="red")
            click.echo("   Fix the broken migration(s) before running makemigrations.")
            raise click.Abort()

    # Compute diff
    click.echo()
    click.echo("3️⃣  Computing diff...")
    try:
        diff = compute_diff(old_schema, schema_result.schema)

        if not diff.operations:
            click.echo()
            click.secho("   ✨ No changes detected", fg="green")
            return

        click.echo(f"   ✅ Found {len(diff.operations)} operation(s):")
        for op in diff.operations:
            op_type = op.get("type", "unknown")
            if op_type == "create_table":
                click.echo(f"      - Create table: {op['table']['name']}")
            elif op_type == "drop_table":
                click.echo(f"      - Drop table: {op['name']}")
            elif op_type == "add_column":
                click.echo(f"      - Add column: {op['table']}.{op['field']['name']}")
            elif op_type == "drop_column":
                click.echo(f"      - Drop column: {op['table']}.{op['field']}")
            else:
                click.echo(f"      - {op_type}")

    except Exception as e:
        click.secho(f"   ❌ Error computing diff: {e}", fg="red")
        raise click.Abort()

    # Generate migration file
    click.echo()
    if dry_run:
        click.secho("   [DRY RUN] Would create migration file", fg="yellow")
        click.echo(f"   Migration name: {name or 'auto'}")
        click.echo(f"   Operations: {len(diff.operations)}")
    else:
        click.echo("4️⃣  Generating migration file...")
        try:
            filepath = create_migration_file(diff.operations, migrations_dir=migrations_dir, name=name)
            click.echo()
            click.secho(f"   ✅ Created: {filepath}", fg="green", bold=True)
        except Exception as e:
            click.secho(f"   ❌ Error generating migration: {e}", fg="red")
            raise click.Abort()

        # Generate type stubs
        click.echo()
        click.echo("5️⃣  Generating type stubs...")
        try:
            stubs = generate_type_stubs()
            if stubs.count:
                click.secho(f"   ✅ Generated {stubs.count} stub file(s)", fg="green")
            else:
                click.echo("   ⚠️  No models to generate stubs for")
        except Exception as e:
            click.secho(f"   ⚠️  Warning: Could not generate stubs: {e}", fg="yellow")


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

    click.echo("⏳ Applying migrations...")
    click.echo()

    if fake:
        click.secho(
            "⚠️  [FAKE MODE] Marking migrations as applied without executing SQL",
            fg="yellow",
        )
        click.echo()

    await init_databases({db_alias: db_url})

    try:
        applied = await get_applied_migrations(db_alias)
        all_migrations = get_migration_files(migrations_dir)

        if target and target.lower() == "zero":
            if not applied:
                click.secho("✨ No migrations to roll back", fg="green")
                return

            click.echo(f"Rolling back all {len(applied)} migration(s)...")
            click.echo()

            rolled_back = await rollback_migrations(
                steps=len(applied),
                migrations_dir=migrations_dir,
                db_alias=db_alias,
                fake=fake,
            )

            if rolled_back:
                click.echo()
                click.secho(f"✅ Rolled back {len(rolled_back)} migration(s)", fg="green", bold=True)
                for migration_name in rolled_back:
                    click.echo(f"   - {migration_name}")
            return

        if target:
            target_idx = -1
            for i, m in enumerate(all_migrations):
                if m.stem == target or m.stem.startswith(target):
                    target_idx = i
                    break

            if target_idx == -1:
                click.secho(f"❌ Migration '{target}' not found", fg="red")
                raise click.Abort()

            current_idx = -1
            for i, m in enumerate(all_migrations):
                if m.stem in applied:
                    current_idx = i

            if target_idx < current_idx:
                steps = current_idx - target_idx
                click.echo(f"Rolling back {steps} migration(s) to reach {target}...")
                click.echo()

                rolled_back = await rollback_migrations(
                    steps=steps,
                    migrations_dir=migrations_dir,
                    db_alias=db_alias,
                    fake=fake,
                )

                if rolled_back:
                    click.echo()
                    click.secho(f"✅ Rolled back {len(rolled_back)} migration(s)", fg="green", bold=True)
                    for migration_name in rolled_back:
                        click.echo(f"   - {migration_name}")
                return

        pending = get_pending_migrations(migrations_dir, applied)

        if not pending:
            click.secho("✨ No pending migrations", fg="green")
            return

        if target:
            filtered = []
            for m in pending:
                filtered.append(m)
                if m.stem == target or m.stem.startswith(target):
                    break
            pending = filtered

        click.echo(f"Found {len(pending)} pending migration(s):")
        for migration_path in pending:
            click.echo(f"  - {migration_path.stem}")
        click.echo()

        if target:
            click.echo(f"Migrating to: {target}")
        else:
            click.echo("Migrating to latest...")

        applied_migrations = await apply_migrations(
            migrations_dir=migrations_dir,
            db_alias=db_alias,
            target=target,
            fake=fake,
        )

        if applied_migrations:
            click.echo()
            click.secho(f"✅ Applied {len(applied_migrations)} migration(s)", fg="green", bold=True)
            for migration_name in applied_migrations:
                click.echo(f"   - {migration_name}")

    except Exception as e:
        click.secho(f"❌ Error applying migrations: {e}", fg="red")
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

    click.echo("📋 Migrations status:")
    click.echo()

    try:
        await init_databases({db_alias: db_url})

        applied = await get_applied_migrations(db_alias)
        applied_set = set(applied)

        all_migrations = get_migration_files(migrations_dir)

        if not all_migrations:
            click.secho("No migrations found", fg="yellow")
            return

        for migration_path in all_migrations:
            name = migration_path.stem
            if name in applied_set:
                click.secho(f"  [✓] {name}", fg="green")
            else:
                click.echo(f"  [ ] {name}")

        click.echo()
        click.echo(f"Total: {len(all_migrations)} migration(s)")
        click.echo(f"Applied: {len(applied_set)}")
        click.echo(f"Pending: {len(all_migrations) - len(applied_set)}")

    except Exception as e:
        click.secho(f"❌ Error reading migrations: {e}", fg="red")
        raise click.Abort()


def main():
    cli()


if __name__ == "__main__":
    main()
