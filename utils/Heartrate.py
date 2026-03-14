"""Heart-rate and HRV analysis helpers."""

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from scipy.signal import find_peaks

from utils.ui import as_bool, finish_figure, print_kv, print_status, print_subsection, print_success, style_axes


def _robust_scale(values):
    """Scale a signal using MAD first and standard deviation as fallback."""
    centered = values - np.median(values)
    mad = np.median(np.abs(centered))
    if mad > 1e-9:
        return centered / (1.4826 * mad)

    std = np.std(centered)
    if std > 1e-9:
        return centered / std
    return centered


def _smooth_signal(values, fs):
    """Apply a short moving average to reduce isolated spikes before peak picking."""
    window = max(1, int(round(fs * 0.08)))
    if window <= 1:
        return values

    kernel = np.ones(window, dtype=float) / window
    return np.convolve(values, kernel, mode="same")


def _detect_r_peaks(signal, fs):
    """Detect ECG R-peaks using adaptive polarity and two-stage thresholds."""
    normalized = _robust_scale(np.asarray(signal, dtype=float))

    positive_tail = np.percentile(normalized, 95)
    negative_tail = abs(np.percentile(normalized, 5))
    if negative_tail > positive_tail:
        normalized = -normalized

    enhanced = _smooth_signal(normalized, fs)
    min_distance = max(1, int(round(fs * 0.35)))
    spread = max(np.std(enhanced), 1e-6)

    peaks, _ = find_peaks(
        enhanced,
        distance=min_distance,
        height=max(0.6, float(np.percentile(enhanced, 75))),
        prominence=max(0.5, 0.3 * spread),
    )
    if len(peaks) > 1:
        return peaks

    peaks, _ = find_peaks(
        enhanced,
        distance=min_distance,
        height=max(0.3, float(np.percentile(enhanced, 65))),
        prominence=max(0.3, 0.2 * spread),
    )
    return peaks


def heartrate_analysis(dataset, config):
    """Compute RR intervals, heart rate, and HRV metrics for each ECG segment."""
    fs = float(config["datainfo"]["Fs"])
    show = as_bool(config["display"].get("heart_rate_show", False))
    segment_labels = config["datainfo"].get("segment_labels", [])

    print_subsection("Heart Rate")
    print_status("Detecting R-peaks and computing HRV metrics.")

    results = []
    for idx, arr in enumerate(dataset):
        label = segment_labels[idx] if idx < len(segment_labels) else f"segment_{idx + 1}"
        peaks = _detect_r_peaks(arr, fs)
        if len(peaks) <= 1:
            print_status(f"{label}: not enough R-peaks detected.")
            results.append({"label": label, "detected": False})
            continue

        rr_intervals = np.diff(peaks) / fs
        rr_ms = rr_intervals * 1000
        heart_rate = 60 / rr_intervals
        time_hr = peaks[1:] / fs
        sdnn = float(np.std(rr_ms))
        rmssd = float(np.sqrt(np.mean(np.diff(rr_ms) ** 2))) if len(rr_ms) > 1 else 0.0

        print_kv(f"{label} SDNN", f"{sdnn:.2f} ms")
        print_kv(f"{label} RMSSD", f"{rmssd:.2f} ms")

        if show:
            # TODO: Visualization styling lives here so it can be tuned globally later.
            fig, ax = plt.subplots(figsize=(10.5, 4.5))
            ax.plot(time_hr, heart_rate, color="#c84c09", linewidth=2.0, label=label)
            style_axes(ax, f"Heart Rate - {label}", "Time (s)", "Heart Rate (bpm)")
            ax.legend(loc="upper right", frameon=False)
            ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
            finish_figure(fig, show=True)

        results.append(
            {
                "label": label,
                "detected": True,
                "rr_intervals_ms": rr_ms,
                "sdnn_ms": sdnn,
                "rmssd_ms": rmssd,
                "heart_rate_bpm": heart_rate,
                "time_s": time_hr,
            }
        )

    print_success("Heart-rate analysis finished.")
    return {"segments": results}
