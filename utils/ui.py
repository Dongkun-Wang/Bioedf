"""Shared helpers for terminal output and Matplotlib styling."""

import os
import re
from pathlib import Path

import matplotlib.pyplot as plt
from cycler import cycler


LINE_WIDTH = 80
PAPER_COLORS = {
    "blue": "#1f3c88",
    "teal": "#0f766e",
    "green": "#4c956c",
    "gold": "#c98c1d",
    "orange": "#c8553d",
    "red": "#a63446",
    "purple": "#6c5b7b",
    "charcoal": "#243447",
}
LINE_COLORS = [
    PAPER_COLORS["blue"],
    PAPER_COLORS["teal"],
    PAPER_COLORS["green"],
    PAPER_COLORS["gold"],
    PAPER_COLORS["orange"],
    PAPER_COLORS["purple"],
]

plt.rcParams.update(
    {
        "figure.dpi": 140,
        "savefig.dpi": 300,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#30343f",
        "axes.labelcolor": "#20242c",
        "axes.titlecolor": "#16191f",
        "axes.linewidth": 0.9,
        "axes.prop_cycle": cycler(color=LINE_COLORS),
        "font.family": "DejaVu Serif",
        "font.size": 10.5,
        "xtick.color": "#30343f",
        "ytick.color": "#30343f",
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 4,
        "ytick.major.size": 4,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "legend.frameon": False,
        "grid.color": "#cfd6df",
        "grid.alpha": 0.28,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.08,
    }
)


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
    ax.set_title(title, fontsize=12.4, fontweight="semibold", pad=8)
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_facecolor("white")
    if grid:
        ax.grid(True, linestyle="--", linewidth=0.8, alpha=0.28)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_alpha(0.45)
    ax.spines["bottom"].set_alpha(0.45)
    ax.tick_params(axis="both", which="major", labelsize=10)


def style_heatmap(ax, title, xlabel, ylabel):
    """Apply a publication-style layout to heatmap-like axes."""
    style_axes(ax, title, xlabel, ylabel, grid=False)


def style_colorbar(colorbar, label):
    """Apply a polished style to a figure colorbar."""
    colorbar.set_label(label, fontsize=10.5)
    colorbar.ax.tick_params(labelsize=9.5, width=0.7, length=3)
    colorbar.outline.set_alpha(0.25)


def add_series(ax, x, y, *, color, label=None, linewidth=1.8, alpha=0.95, fill=False):
    """Draw a polished line series with an optional translucent fill."""
    ax.plot(x, y, color=color, linewidth=linewidth, alpha=alpha, label=label)
    if fill:
        ax.fill_between(x, y, color=color, alpha=0.06)


def humanize_text(value):
    """Convert identifiers to reader-friendly labels."""
    text = str(value).replace("_", " ").strip()
    return re.sub(r"\s+", " ", text)


def make_plot_title(config, label, title):
    """Build compact, publication-style figure titles."""
    modality = config.get("datainfo", {}).get("signal_display_name", "Signal")
    match = re.search(r"segment_(\d+)", str(label))
    if match:
        base = f"{modality} Segment {int(match.group(1))}"
    else:
        base = humanize_text(label)
    return f"{base} {title}".strip()


def _slugify_filename_part(value):
    """Convert arbitrary labels to filesystem-safe filename parts."""
    text = re.sub(r"\s+", "_", str(value).strip())
    text = re.sub(r"[^\w.\-]+", "_", text, flags=re.UNICODE)
    return text.strip("._") or "figure"


def build_figure_path(config, module_name, label, *, data_title=None, figure_name=None):
    """Build a consistent figure output path from runtime config."""
    root = Path(config["fileinfo"].get("result_dir", "./result"))
    if as_bool(config.get("output", {}).get("organize_by_modality", True)):
        modality = config.get("datainfo", {}).get("signal_display_name") or config.get("datainfo", {}).get("signal_type", "misc")
        root = root / _slugify_filename_part(str(modality).upper())
    root = root / _slugify_filename_part(module_name)

    parts = [_slugify_filename_part(label)]
    if data_title:
        parts.append(_slugify_filename_part(data_title))
    if figure_name:
        parts.append(_slugify_filename_part(figure_name))

    figure_format = config.get("output", {}).get("figure_format", "png")
    return root / f"{'_'.join(parts)}.{figure_format}"


def finish_figure(
    fig,
    *,
    config=None,
    module_name=None,
    label=None,
    data_title=None,
    figure_name=None,
    show=False,
    layout="tight",
):
    """Finalize, optionally save, show, and close a figure."""
    if layout == "tight":
        fig.tight_layout()
    elif layout == "constrained":
        fig.set_constrained_layout(True)

    save_path = None
    if config is not None and as_bool(config.get("output", {}).get("save_figures", False)):
        if not module_name or not label:
            raise ValueError("module_name and label are required when save_figures is enabled.")
        save_path = build_figure_path(
            config,
            module_name,
            label,
            data_title=data_title,
            figure_name=figure_name,
        )
        os.makedirs(save_path.parent, exist_ok=True)
        fig.savefig(
            save_path,
            dpi=int(config.get("output", {}).get("figure_dpi", 300)),
            facecolor=fig.get_facecolor(),
        )
    if show:
        plt.show()
    plt.close(fig)
    return str(save_path) if save_path else None
