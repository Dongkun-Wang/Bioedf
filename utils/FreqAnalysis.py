"""Sliding-window frequency summary metrics."""

import matplotlib.pyplot as plt
import numpy as np
from scipy.fft import fft
from scipy.signal.windows import hann

from utils.ui import as_bool, finish_figure, print_status, print_subsection, print_success, style_axes


def run_freq_analysis(dataset, data_title, config):
    """Compute sliding-window RMS, MPF, and MDF for every segment."""
    fs = float(config["datainfo"]["Fs"])
    seq_len = max(1, int(fs * float(config["analysis"].get("rms_time", 1.0))))
    seq_gap = max(1, int(fs * float(config["analysis"].get("rms_gap", 0.5))))
    show = as_bool(config["display"].get("freq_analysis_show", False))
    segment_labels = config["datainfo"].get("segment_labels", [])

    print_subsection("Frequency Summary")
    print_status("Computing sliding-window RMS, MPF, and MDF.")

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

        if show:
            # TODO: Visualization styling lives here so it can be tuned globally later.
            fig_rms, ax_rms = plt.subplots(figsize=(10.5, 4.5))
            ax_rms.plot(time_s, rms, color="#6b4c9a", linewidth=1.7)
            style_axes(ax_rms, f"{label} {data_title} RMS", "Time (s)", "RMS")
            finish_figure(fig_rms, show=True)

            # TODO: Visualization styling lives here so it can be tuned globally later.
            fig_mpf, ax_mpf = plt.subplots(figsize=(10.5, 4.5))
            ax_mpf.plot(time_s, mpf, color="#0b6e4f", linewidth=1.7)
            style_axes(ax_mpf, f"{label} {data_title} MPF", "Time (s)", "Frequency (Hz)")
            finish_figure(fig_mpf, show=True)

            # TODO: Visualization styling lives here so it can be tuned globally later.
            fig_mdf, ax_mdf = plt.subplots(figsize=(10.5, 4.5))
            ax_mdf.plot(time_s, mdf, color="#c84c09", linewidth=1.7)
            style_axes(ax_mdf, f"{label} {data_title} MDF", "Time (s)", "Frequency (Hz)")
            finish_figure(fig_mdf, show=True)

        results.append(
            {
                "label": label,
                "rms": rms,
                "mpf_hz": mpf,
                "mdf_hz": mdf,
                "time_s": time_s,
            }
        )

    print_success("Frequency summary finished.")
    return {"segments": results}
