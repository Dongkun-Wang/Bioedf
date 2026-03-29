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
        "font.family": ["PingFang HK", "Hiragino Sans GB", "Songti SC", "Heiti TC", "Arial Unicode MS", "DejaVu Sans"],
        "font.size": 10.5,
        "axes.unicode_minus": False,
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


TRANSLATION_PATTERNS = [
    (r"\bfrontend run\b", ""),
    (r"\bR_BB\b|\bR BB\b", "右臂肱二头肌"),
    (r"\bL_BB\b|\bL BB\b", "左臂肱二头肌"),
    (r"\beeg_mean\b|\beeg mean\b", "脑电平均通道"),
    (r"\bRA\b", "右上肢导联"),
    (r"\bLA\b", "左上肢导联"),
    (r"\bFpz\b", "额极中线"),
    (r"\bFp1\b", "左额极"),
    (r"\bFp2\b", "右额极"),
    (r"\bF7\b", "左额颞区"),
    (r"\bF8\b", "右额颞区"),
    (r"\bV3\b", "V3导联"),
    (r"\bV5\b", "V5导联"),
    (r"\bF\b", "F导联"),
    (r"\bfiltered dataset\b", "分析结果"),
    (r"\bfiltered signal\b", "滤波后信号"),
    (r"\bband power\b", "频带功率图"),
    (r"\bderived indices\b", "专注/放松指标图"),
    (r"\bfft spectrum\b", "FFT频谱图"),
    (r"\bspectrogram\b", "时频谱图"),
    (r"\brms and mdf\b", "RMS与MDF分析图"),
    (r"\brms mdf\b", "RMS与MDF分析图"),
    (r"\btrend\b", "趋势图"),
    (r"\bspectrum\b", "频谱图"),
    (r"\bindices\b", "指标图"),
    (r"\bsegment[_ ](\d+)\b", r"第\1段"),
]

MODALITY_NAME_MAP = {
    "EEG": "脑电",
    "ECG": "心电",
    "EMG": "肌电",
}


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
    text = re.sub(r"\s+", " ", text)
    for pattern, replacement in TRANSLATION_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def make_plot_title(config, label, title):
    """Build compact, publication-style figure titles."""
    modality = config.get("datainfo", {}).get("signal_display_name", "Signal")
    modality = MODALITY_NAME_MAP.get(str(modality).upper(), humanize_text(modality))
    localized_title = humanize_text(title)
    match = re.search(r"segment_(\d+)", str(label))
    if match:
        base = f"{modality}第{int(match.group(1))}段"
    else:
        base = humanize_text(label)
    return f"{base} {localized_title}".strip()


def make_result_caption(file_stem):
    """Build a localized frontend caption from an exported figure stem."""
    return humanize_text(file_stem)


def normalize_data_title(value):
    """Hide internal pipeline markers from saved figure names and captions."""
    text = str(value or "").strip()
    if text.lower() in {"frontend_run", "filtered_dataset"}:
        return None
    return text or None


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
    normalized_title = normalize_data_title(data_title)
    if normalized_title:
        parts.append(_slugify_filename_part(normalized_title))
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
