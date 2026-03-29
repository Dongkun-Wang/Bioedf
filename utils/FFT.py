"""FFT-based spectrum analysis."""

import matplotlib.pyplot as plt
import numpy as np

from utils.ui import add_series, as_bool, finish_figure, make_plot_title, print_status, print_subsection, print_success, style_axes


def run_fft(dataset, data_title, config):
    """Run FFT for every segment and optionally plot or save the spectrum."""
    fs = float(config["datainfo"]["Fs"])
    display_config = config.get("display", {})
    output_config = config.get("output", {})
    fftshow = as_bool(display_config.get("fft_show", False))
    ffttype = config["analysis"].get("fft_type", "log")
    fftsave = as_bool(output_config.get("save_figures", False))
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
                ylabel = "功率（dB）"
            else:
                plot_y = power
                ylabel = "功率"
            high_cut = float(config["preprocess"].get("bpfreq", [0, fs / 2])[1])
            ax.set_xlim(0, min(fs / 2, max(30.0, high_cut * 1.15)))

            add_series(ax, frequency, plot_y, color="#0f766e", linewidth=1.7)
            style_axes(ax, make_plot_title(config, label, "FFT Spectrum"), "频率（Hz）", ylabel)
            finish_figure(
                fig,
                config=config,
                module_name="fft",
                label=label,
                data_title=data_title,
                figure_name="spectrum",
                show=fftshow,
            )

    print_success("FFT finished.")
    return {"segments": fft_results}
