"""Signal preprocessing helpers."""

import os

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import butter, sosfilt

from utils.console import print_kv, print_section, print_subsection, print_success


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


def util_preprocess(config, dataset, show=None, saveon=None):
    """Filter each 1D segment according to the resolved preprocessing config."""
    show = config["display"].get("preprocess_show", "off") if show is None else show
    saveon = config["display"].get("preprocess_save", "off") if saveon is None else saveon
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
        if config["preprocess"].get(filter_field, "off") == "on":
            filter_freq = config["preprocess"].get(f"{filter_prefix}freq")
            filter_order = config["preprocess"].get(f"{filter_prefix}filtord", 4)
            print_kv(f"{filter_name} range", filter_freq)
            print_kv(f"{filter_name} order", filter_order)

    dataset_filtered = []
    for idx, signal in enumerate(dataset):
        filtered_signal = np.asarray(signal, dtype=float)
        if config["preprocess"].get("bpfilter", "off") == "on":
            filtered_signal = _apply_filter(
                filtered_signal,
                "bandpass",
                config["preprocess"]["bpfreq"],
                fs,
                config["preprocess"].get("bpfiltord", 4),
            )
        if config["preprocess"].get("bsfilter", "off") == "on":
            filtered_signal = _apply_filter(
                filtered_signal,
                "bandstop",
                config["preprocess"]["bsfreq"],
                fs,
                config["preprocess"].get("bsfiltord", 4),
            )
        dataset_filtered.append(filtered_signal)

        if show == "on" or saveon == "on":
            label = segment_labels[idx] if idx < len(segment_labels) else f"segment_{idx + 1}"
            timeline = np.arange(len(filtered_signal)) / fs
            plt.figure(figsize=(12, 4))
            plt.plot(timeline, filtered_signal)
            plt.title(f"{label} filtered signal")
            plt.xlabel("Time (s)")
            plt.ylabel("Amplitude")
            plt.tight_layout()
            if saveon == "on":
                os.makedirs(result_dir, exist_ok=True)
                plt.savefig(os.path.join(result_dir, f"{label}_filtered.pdf"))
            if show == "on":
                plt.show()
            plt.close()

    print_success("Preprocessing finished.")
    return dataset_filtered
