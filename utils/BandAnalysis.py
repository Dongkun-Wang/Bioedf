"""EEG band-power analysis."""

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import spectrogram
from scipy.stats import entropy

from utils.ui import as_bool, finish_figure, print_status, print_subsection, print_success, style_axes


def run_band_analysis(dataset, data_title, config):
    """Compute EEG band-power metrics and derived concentration/relaxation indices."""
    fs = float(config["datainfo"]["Fs"])
    segment_labels = config["datainfo"].get("segment_labels", [])
    show = as_bool(config["display"].get("band_show", True))
    save_csv = as_bool(config["display"].get("band_save_csv", False))
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
        if show:
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

            if show:
                ax_power.plot(times, band_power, linewidth=1.5, label=f"{band_name} {band_range[0]}-{band_range[1]} Hz")

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

        if show:
            style_axes(ax_power, f"{label} {data_title} Frequency Band Comparison", "Time (s)", "Power")
            ax_power.legend(frameon=False, ncol=2)
            finish_figure(fig_power, show=True)

            # TODO: Visualization styling lives here so it can be tuned globally later.
            fig_index, ax_index = plt.subplots(figsize=(12, 4.5))
            ax_index.plot(metrics.index, metrics["concentration"], label="Concentration", color="#245caa", linewidth=1.8)
            ax_index.plot(metrics.index, metrics["relaxation"], label="Relaxation", color="#3b8f57", linewidth=1.8)
            style_axes(ax_index, f"{label} {data_title} Derived Band Indices", "Time (s)", "Index")
            ax_index.legend(frameon=False)
            finish_figure(fig_index, show=True)

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
