"""FFT-based spectrum analysis."""

import matplotlib.pyplot as plt
import numpy as np

from utils.ui import as_bool, finish_figure, print_status, print_subsection, print_success, style_axes


def run_fft(dataset, data_title, config):
    """Run FFT for every segment and optionally plot or save the spectrum."""
    fs = float(config["datainfo"]["Fs"])
    fftshow = as_bool(config["display"].get("fft_show", False))
    ffttype = config["analysis"].get("fft_type", "log")
    fftsave = as_bool(config["display"].get("fft_save", False))
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

        if fftshow or fftsave:
            # TODO: Visualization styling lives here so it can be tuned globally later.
            fig, ax = plt.subplots(figsize=(10.5, 4.5))
            if ffttype == "log":
                plot_y = 10 * np.log10(power + 1e-12)
                ylabel = "Power (dB)"
                ax.set_xlim(0, fs / 2)
            else:
                plot_y = power
                ylabel = "Power"
                ax.set_xlim(0, min(30, fs / 2))

            ax.plot(frequency, plot_y, color="#0b6e4f", linewidth=1.6)
            style_axes(ax, f"{label} {data_title} FFT", "Frequency (Hz)", ylabel)
            save_path = os.path.join(result_dir, f"{label}_{data_title}_fft.pdf") if fftsave else None
            finish_figure(fig, save_path=save_path, show=fftshow)

    print_success("FFT finished.")
    return {"segments": fft_results}
