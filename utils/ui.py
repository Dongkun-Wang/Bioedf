"""Shared helpers for terminal output and Matplotlib styling."""

import os

import matplotlib.pyplot as plt


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


def as_bool(value):
    """Coerce legacy on/off values and regular truthy values to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"on", "true", "yes", "1"}:
            return True
        if normalized in {"off", "false", "no", "0"}:
            return False
    return bool(value)


def style_axes(ax, title, xlabel, ylabel, *, grid=True):
    """Apply a consistent visual style to a plot axis."""
    ax.set_title(title, fontsize=13, fontweight="semibold")
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_facecolor("#fbfbfc")
    if grid:
        ax.grid(True, linestyle="--", linewidth=0.7, alpha=0.35)
    for spine in ax.spines.values():
        spine.set_alpha(0.25)


def finish_figure(fig, *, save_path=None, show=False):
    """Finalize, optionally save, show, and close a figure."""
    fig.tight_layout()
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path)
    if show:
        plt.show()
    plt.close(fig)
