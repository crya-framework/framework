import os
import sys

import asyncclick as click
import uvicorn


@click.group()
async def cli():
    pass


@cli.command()
async def serve():
    sys.path.insert(0, os.getcwd())
    config = uvicorn.Config("crya.entrypoint:app", host="127.0.0.1", port=8000)
    server = uvicorn.Server(config)

    await server.serve()


def main():
    cli()


if __name__ == "__main__":
    main()
