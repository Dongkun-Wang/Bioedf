"""Shared helpers for consistent terminal output."""

LINE_WIDTH = 80


def print_section(title):
    """Print a top-level section banner."""
    line = "=" * LINE_WIDTH
    print(f"\n{line}\n{title}\n{line}")


def print_subsection(title):
    """Print a compact subsection label."""
    print(f"\n[{title}]")


def print_kv(label, value):
    """Print a simple key-value line."""
    print(f"{label:<24} {value}")


def print_status(message):
    """Print a single status line."""
    print(f"-> {message}")


def print_success(message="Completed."):
    """Print a success line."""
    print(f"[ok] {message}")
