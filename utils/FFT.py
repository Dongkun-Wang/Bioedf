"""FFT-based spectrum analysis."""

import os

import matplotlib.pyplot as plt
import numpy as np

from utils.console import print_status, print_success, print_subsection


def util_fft(dataset, data_title, config):
    """Run FFT for every segment and optionally plot or save the spectrum."""
    fs = float(config["datainfo"]["Fs"])
    fftshow = config["display"].get("fft_show", "off")
    ffttype = config["analysis"].get("fft_type", "log")
    fftsave = config["display"].get("fft_save", "off")
    result_dir = config["fileinfo"].get("result_dir", "./result")
    segment_labels = config["datainfo"].get("segment_labels", [])

    print_subsection("FFT")
    print_status("Computing spectra.")

    fft_results = []
    for idx, signal in enumerate(dataset):
        signal = np.asarray(signal, dtype=float)
        n_len = len(signal)
        ns = 2 ** int(np.floor(np.log2(n_len)))
        if ns == 0:
            continue

        # Use the largest power-of-two window from the tail for stable FFT sizing.
        windowed_signal = signal[-ns:] * np.hanning(ns)
        windowed_fft = np.fft.rfft(windowed_signal)
        magnitude = np.abs(windowed_fft) / ns
        power = magnitude**2
        frequency = np.fft.rfftfreq(ns, d=1.0 / fs)
        label = segment_labels[idx] if idx < len(segment_labels) else f"segment_{idx + 1}"

        fft_results.append(
            {
                "label": label,
                "frequency_hz": frequency,
                "magnitude": magnitude,
                "power": power,
            }
        )

        if fftshow == "on" or fftsave == "on":
            plt.figure(figsize=(10, 4))
            if ffttype == "log":
                plot_y = 10 * np.log10(power + 1e-12)
                plt.ylabel("Power (dB)")
                plt.xlim(0, fs / 2)
            else:
                plot_y = power
                plt.ylabel("Power")
                plt.xlim(0, min(30, fs / 2))

            plt.plot(frequency, plot_y)
            plt.title(f"{label} {data_title} FFT")
            plt.xlabel("Frequency (Hz)")
            plt.tight_layout()
            if fftsave == "on":
                os.makedirs(result_dir, exist_ok=True)
                plt.savefig(os.path.join(result_dir, f"{label}_{data_title}_fft.pdf"))
            if fftshow == "on":
                plt.show()
            plt.close()

    print_success("FFT finished.")
    return {"segments": fft_results}
