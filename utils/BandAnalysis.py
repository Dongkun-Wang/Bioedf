"""EEG band-power analysis."""

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import spectrogram
from scipy.stats import entropy

from utils.ui import (
    add_series,
    as_bool,
    finish_figure,
    humanize_text,
    make_plot_title,
    print_status,
    print_subsection,
    print_success,
    style_axes,
)


BAND_LABELS = {
    "theta": "Theta θ波",
    "alpha": "Alpha α波",
    "beta_low": "低频Beta β波",
    "beta_high": "高频Beta β波",
    "gamma": "Gamma γ波",
}


def run_band_analysis(dataset, data_title, config):
    """Compute EEG band-power metrics and derived concentration/relaxation indices."""
    fs = float(config["datainfo"]["Fs"])
    segment_labels = config["datainfo"].get("segment_labels", [])
    display_config = config.get("display", {})
    output_config = config.get("output", {})
    show = as_bool(display_config.get("band_show", True))
    save_figures = as_bool(output_config.get("save_figures", False))
    save_csv = as_bool(output_config.get("save_band_metrics_csv", False))
    result_dir = config["fileinfo"].get("result_dir", "./result")
    freq_limit = float(config["analysis"].get("band_freq_limit", 60))

    print_subsection("Band Analysis")
    print_status("Computing EEG band metrics.")

    win_len = max(8, int(round(fs)))
    noverlap = min(int(win_len * 0.5), win_len - 1)
    freq_bands = {
        "theta": (4, 7),
        "alpha": (8, 13),
        "beta_low": (14, 25),
        "beta_high": (25, 35),
        "gamma": (35, 60),
    }
    band_colors = {
        "theta": "#1f3c88",
        "alpha": "#0f766e",
        "beta_low": "#4c956c",
        "beta_high": "#c98c1d",
        "gamma": "#a63446",
    }

    segment_results = []
    for idx, signal in enumerate(dataset):
        label = segment_labels[idx] if idx < len(segment_labels) else f"segment_{idx + 1}"
        signal = np.asarray(signal, dtype=float)
        nfft = 2 ** int(np.ceil(np.log2(win_len)))
        freqs, times, spectrum = spectrogram(
            signal,
            fs=fs,
            window="hann",
            nperseg=win_len,
            noverlap=noverlap,
            nfft=nfft,
        )

        keep = freqs <= freq_limit
        freqs = freqs[keep]
        spectrum = spectrum[keep, :]
        total_power = np.sum(spectrum, axis=0)
        total_power = np.where(total_power == 0, 1e-12, total_power)

        metrics = pd.DataFrame(index=times)
        render_power = show or save_figures
        render_indices = show or save_figures
        if render_power:
            # TODO: Visualization styling lives here so it can be tuned globally later.
            fig_power, ax_power = plt.subplots(figsize=(12, 4.5))

        for band_name, band_range in freq_bands.items():
            band_idx = np.where((freqs >= band_range[0]) & (freqs < band_range[1]))[0]
            if len(band_idx) == 0:
                band_power = np.zeros_like(times)
            else:
                band_power = np.mean(spectrum[band_idx, :], axis=0)

            metrics[band_name] = band_power
            metrics[f"{band_name}_rel"] = band_power / total_power

            if render_power:
                add_series(
                    ax_power,
                    times,
                    band_power,
                    color=band_colors[band_name],
                    label=f"{BAND_LABELS.get(band_name, humanize_text(band_name))} {band_range[0]}-{band_range[1]} Hz",
                    linewidth=1.6,
                )

        # Derived metrics summarize where the spectrum is centered and how spread it is.
        spectrum_sum = np.sum(spectrum, axis=0) + 1e-12
        spectral_centroid = np.sum(freqs[:, None] * spectrum, axis=0) / spectrum_sum
        psd_norm = spectrum / spectrum_sum
        spectral_entropy = entropy(psd_norm, axis=0)

        metrics["spectral_centroid"] = spectral_centroid
        metrics["spectral_entropy"] = spectral_entropy
        metrics["concentration"] = (metrics["beta_low"] + metrics["beta_high"]) / (
            metrics["alpha"] + metrics["theta"] + 1e-12
        )
        metrics["relaxation"] = metrics["alpha"] / (
            metrics["alpha"] + metrics["beta_low"] + metrics["beta_high"] + metrics["theta"] + 1e-12
        )

        if save_csv:
            os.makedirs(result_dir, exist_ok=True)
            metrics.to_csv(os.path.join(result_dir, f"{label}_{data_title}_band_metrics.csv"))

        if render_power:
            style_axes(ax_power, make_plot_title(config, label, "Band Power"), "时间（秒）", "功率")
            ax_power.set_ylim(bottom=0)
            ax_power.legend(frameon=False, ncol=2)
            finish_figure(
                fig_power,
                config=config,
                module_name="band",
                label=label,
                data_title=data_title,
                figure_name="band_power",
                show=show,
            )

        if render_indices:
            # TODO: Visualization styling lives here so it can be tuned globally later.
            fig_index, ax_index = plt.subplots(figsize=(12, 4.5))
            add_series(
                ax_index,
                metrics.index,
                metrics["concentration"],
                label="专注度",
                color="#1f3c88",
                linewidth=1.9,
            )
            add_series(
                ax_index,
                metrics.index,
                metrics["relaxation"],
                label="放松度",
                color="#4c956c",
                linewidth=1.9,
            )
            style_axes(ax_index, make_plot_title(config, label, "Derived Indices"), "时间（秒）", "指数")
            ax_index.set_ylim(bottom=0)
            ax_index.legend(frameon=False)
            finish_figure(
                fig_index,
                config=config,
                module_name="band",
                label=label,
                data_title=data_title,
                figure_name="indices",
                show=show,
            )

        segment_results.append(
            {
                "label": label,
                "frequency_hz": freqs,
                "time_s": times,
                "spectrum": spectrum,
                "metrics": metrics,
            }
        )

    print_success("Band analysis finished.")
    return {"segments": segment_results}
