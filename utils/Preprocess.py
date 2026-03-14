"""Signal preprocessing helpers."""

import os

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import butter, sosfilt

from utils.ui import as_bool, finish_figure, print_kv, print_section, print_subsection, print_success, style_axes


def _validate_filter_config(freq, fs, name):
    """Validate the configured cutoff range for a digital filter."""
    if freq is None:
        raise ValueError(f"{name} frequency is not set. Load data and infer the signal profile first.")
    if not isinstance(freq, (list, tuple)) or len(freq) != 2:
        raise ValueError(f"{name} frequency must be a two-element list or tuple.")

    low, high = float(freq[0]), float(freq[1])
    nyquist = 0.5 * float(fs)
    if low <= 0 or high <= 0 or low >= high:
        raise ValueError(f"Invalid {name} frequency range: {freq}")
    if high >= nyquist:
        raise ValueError(f"{name} high cutoff must be lower than the Nyquist frequency {nyquist:.4f} Hz.")


def _apply_filter(data, btype, freq, fs, order):
    """Apply a Butterworth filter in second-order sections form."""
    _validate_filter_config(freq, fs, btype)
    normal_freq = np.asarray(freq, dtype=float) / (0.5 * float(fs))
    sos = butter(int(order), normal_freq, btype=btype, output="sos")
    return sosfilt(sos, data)


def preprocess_dataset(config, dataset, show=None, saveon=None):
    """Filter each 1D segment according to the resolved preprocessing config."""
    show = as_bool(config["display"].get("preprocess_show", False) if show is None else show)
    saveon = as_bool(config["display"].get("preprocess_save", False) if saveon is None else saveon)
    fs = config["datainfo"]["Fs"]
    segment_labels = config["datainfo"].get("segment_labels", [])
    result_dir = config["fileinfo"].get("result_dir", "./result")

    print_section("PREPROCESS")
    print_subsection("Filter Setup")

    filters = [
        ("bpfilter", "bp", "Band-pass"),
        ("bsfilter", "bs", "Band-stop"),
    ]
    for filter_field, filter_prefix, filter_name in filters:
        if as_bool(config["preprocess"].get(filter_field, False)):
            filter_freq = config["preprocess"].get(f"{filter_prefix}freq")
            filter_order = config["preprocess"].get(f"{filter_prefix}filtord", 4)
            print_kv(f"{filter_name} range", filter_freq)
            print_kv(f"{filter_name} order", filter_order)

    dataset_filtered = []
    for idx, signal in enumerate(dataset):
        filtered_signal = np.asarray(signal, dtype=float)
        if as_bool(config["preprocess"].get("bpfilter", False)):
            filtered_signal = _apply_filter(
                filtered_signal,
                "bandpass",
                config["preprocess"]["bpfreq"],
                fs,
                config["preprocess"].get("bpfiltord", 4),
            )
        if as_bool(config["preprocess"].get("bsfilter", False)):
            filtered_signal = _apply_filter(
                filtered_signal,
                "bandstop",
                config["preprocess"]["bsfreq"],
                fs,
                config["preprocess"].get("bsfiltord", 4),
            )
        dataset_filtered.append(filtered_signal)

        if show or saveon:
            label = segment_labels[idx] if idx < len(segment_labels) else f"segment_{idx + 1}"
            timeline = np.arange(len(filtered_signal)) / fs
            # TODO: Visualization styling lives here so it can be tuned globally later.
            fig, ax = plt.subplots(figsize=(12, 4.5))
            ax.plot(timeline, filtered_signal, color="#1f4e79", linewidth=1.6)
            style_axes(ax, f"{label} Filtered Signal", "Time (s)", "Amplitude")
            save_path = os.path.join(result_dir, f"{label}_filtered.pdf") if saveon else None
            finish_figure(fig, save_path=save_path, show=show)

    print_success("Preprocessing finished.")
    return dataset_filtered
