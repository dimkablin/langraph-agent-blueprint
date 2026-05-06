"""Command-line module entry point that delegates to the Typer CLI application."""

from .cli import app


if __name__ == "__main__":
    app()

