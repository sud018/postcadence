"""Shared console, so every command prints the same way."""
from rich.console import Console
from rich.table import Table

console = Console()

__all__ = ["console", "Table"]
