"""Sliding-window frequency summary metrics."""

import matplotlib.pyplot as plt
import numpy as np
from scipy.fft import fft
from scipy.signal.windows import hann

from utils.console import print_status, print_success, print_subsection


def util_freq_analysis(dataset, data_title, config):
    """Compute sliding-window RMS, MPF, and MDF for every segment."""
    fs = float(config["datainfo"]["Fs"])
    seq_len = max(1, int(fs * float(config["analysis"].get("rms_time", 1.0))))
    seq_gap = max(1, int(fs * float(config["analysis"].get("rms_gap", 0.5))))
    show = config["display"].get("freqalg_show", "off")
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

        if show == "on":
            plt.figure(figsize=(10, 4))
            plt.plot(time_s, rms)
            plt.title(f"{label} {data_title} RMS")
            plt.xlabel("Time (s)")
            plt.ylabel("RMS")
            plt.tight_layout()
            plt.show()
            plt.close()

            plt.figure(figsize=(10, 4))
            plt.plot(time_s, mpf)
            plt.title(f"{label} {data_title} MPF")
            plt.xlabel("Time (s)")
            plt.ylabel("Frequency (Hz)")
            plt.tight_layout()
            plt.show()
            plt.close()

            plt.figure(figsize=(10, 4))
            plt.plot(time_s, mdf)
            plt.title(f"{label} {data_title} MDF")
            plt.xlabel("Time (s)")
            plt.ylabel("Frequency (Hz)")
            plt.tight_layout()
            plt.show()
            plt.close()

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
