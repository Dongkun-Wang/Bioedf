"""Sliding-window frequency summary metrics."""

import matplotlib.pyplot as plt
import numpy as np
from scipy.fft import fft
from scipy.signal.windows import hann

from utils.ui import add_series, as_bool, finish_figure, make_plot_title, print_status, print_subsection, print_success, style_axes


def _moving_average(values, window_size):
    """Return a centered moving average for visualization-only trend overlays."""
    if window_size <= 1 or len(values) < window_size:
        return np.asarray(values, dtype=float)

    padded = np.pad(values, (window_size // 2, window_size - 1 - window_size // 2), mode="edge")
    kernel = np.ones(window_size, dtype=float) / window_size
    return np.convolve(padded, kernel, mode="valid")


def run_freq_analysis(dataset, data_title, config):
    """Compute sliding-window RMS, MPF, and MDF while plotting only RMS and MDF."""
    fs = float(config["datainfo"]["Fs"])
    seq_len = max(1, int(fs * float(config["analysis"].get("rms_time", 1.0))))
    seq_gap = max(1, int(fs * float(config["analysis"].get("rms_gap", 0.5))))
    display_config = config.get("display", {})
    output_config = config.get("output", {})
    show = as_bool(display_config.get("freq_analysis_show", False))
    save_figures = as_bool(output_config.get("save_figures", False))
    segment_labels = config["datainfo"].get("segment_labels", [])
    trend_seconds = max(0.0, float(config["analysis"].get("mdf_trend_seconds", 5.0)))

    print_subsection("Frequency Summary")
    print_status("Computing sliding-window EMG summary metrics (RMS, MPF, MDF).")

    results = []
    for idx, signal in enumerate(dataset):
        label = segment_labels[idx] if idx < len(segment_labels) else f"segment_{idx + 1}"
        signal = np.asarray(signal, dtype=float)
        if len(signal) < seq_len:
            results.append({"label": label, "rms": [], "mpf_hz": [], "mdf_hz": [], "time_s": []})
            continue

        window = hann(seq_len)
        freqs = np.arange(0, seq_len // 2) * fs / seq_len
        mpf = []
        mdf = []
        rms = []
        time_s = []

        for start in range(0, len(signal) - seq_len + 1, seq_gap):
            segment = signal[start : start + seq_len]
            power = np.abs(fft(segment * window) / seq_len)[: len(freqs)] ** 2
            power_sum = np.sum(power)
            if power_sum == 0:
                power_sum = 1e-12

            mpf.append(float(np.sum(freqs * power) / power_sum))
            cumulative_power = np.cumsum(power)
            mdf.append(float(freqs[np.argmin(np.abs(cumulative_power - 0.5 * cumulative_power[-1]))]))
            rms.append(float(np.sqrt(np.mean(np.abs(segment) ** 2))))
            time_s.append(start / fs)

        step_seconds = seq_gap / fs if fs else 0.0
        trend_window = max(1, int(round(trend_seconds / step_seconds))) if step_seconds > 0 else 1
        mdf_trend = _moving_average(np.asarray(mdf, dtype=float), trend_window)

        if show or save_figures:
            # TODO: Visualization styling lives here so it can be tuned globally later.
            fig, (ax_rms, ax_mdf) = plt.subplots(
                2,
                1,
                figsize=(10.5, 7.2),
                sharex=True,
                constrained_layout=True,
                gridspec_kw={"hspace": 0.18},
            )
            fig.suptitle(make_plot_title(config, label, "RMS and MDF"), fontsize=13.0, fontweight="semibold")
            add_series(ax_rms, time_s, rms, color="#6c5b7b", linewidth=1.9, fill=True)
            style_axes(ax_rms, "RMS", "", "RMS")

            add_series(
                ax_mdf,
                time_s,
                mdf,
                color="#a8a4b8",
                linewidth=1.1,
                alpha=0.85,
                label="Raw MDF",
            )
            add_series(
                ax_mdf,
                time_s,
                mdf_trend,
                color="#c8553d",
                linewidth=2.2,
                label="Trend MDF",
            )
            style_axes(ax_mdf, "MDF", "Time (s)", "Frequency (Hz)")
            ax_mdf.legend(loc="upper right", frameon=False)
            finish_figure(
                fig,
                config=config,
                module_name="freq_analysis",
                label=label,
                data_title=data_title,
                figure_name="rms_mdf",
                show=show,
                layout="none",
            )

        results.append(
            {
                "label": label,
                "rms": rms,
                "mpf_hz": mpf,
                "mdf_hz": mdf,
                "mdf_trend_hz": mdf_trend.tolist(),
                "time_s": time_s,
            }
        )

    print_success("Frequency summary finished.")
    return {"segments": results}
