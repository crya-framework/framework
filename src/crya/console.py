import click


def error(msg: str, emoji: bool = False) -> None:
    prefix = "❌ " if emoji else ""
    click.secho(f"{prefix}{msg}", fg="red")


def warning(msg: str, emoji: bool = False) -> None:
    prefix = "⚠️  " if emoji else ""
    click.secho(f"{prefix}{msg}", fg="yellow")


def success(msg: str, emoji: bool = False, bold: bool = False) -> None:
    prefix = "✅ " if emoji else ""
    click.secho(f"{prefix}{msg}", fg="green", bold=bold)


def info(msg: str, emoji: bool = False) -> None:
    prefix = "ℹ️  " if emoji else ""
    click.echo(f"{prefix}{msg}")


def blank() -> None:
    click.echo()
