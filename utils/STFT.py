"""Short-time Fourier transform analysis."""

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import spectrogram

from utils.ui import as_bool, finish_figure, make_plot_title, print_status, print_subsection, print_success, style_colorbar, style_heatmap


def run_stft(dataset, data_title, config):
    """Perform STFT spectrogram analysis and mandatory energy estimation."""
    fs = float(config["datainfo"]["Fs"])
    segment_labels = config["datainfo"].get("segment_labels", [])
    display_config = config.get("display", {})
    output_config = config.get("output", {})
    stft_show = as_bool(display_config.get("stft_show", False))
    save_figures = as_bool(output_config.get("save_figures", False))
    stft_overlap = float(config["analysis"].get("stft_overlap", 0.5))
    calorie_show = as_bool(display_config.get("calorie_show", False))
    calorie_power_ratio = float(config["analysis"].get("calorie_power_ratio", 25))

    print_subsection("STFT")
    print_status("Computing spectrograms and energy estimates.")

    win_len = max(8, 2 ** int(np.floor(np.log2(fs))))
    noverlap = min(int(win_len * stft_overlap), win_len - 1)

    results = []
    for idx, signal in enumerate(dataset):
        label = segment_labels[idx] if idx < len(segment_labels) else f"segment_{idx + 1}"
        signal = np.asarray(signal, dtype=float)
        freqs, times, spectrum = spectrogram(
            signal,
            fs=fs,
            window="hann",
            nperseg=win_len,
            noverlap=noverlap,
            nfft=win_len,
        )

        valid_idx = freqs <= 250
        freqs = freqs[valid_idx]
        spectrum = spectrum[valid_idx, :]

        rms = float(np.sqrt(np.mean(signal**2)))
        duration = len(signal) / fs
        power_est = rms * calorie_power_ratio
        kcal_est = (power_est * duration) / 4184
        if calorie_show:
            print_status(f"{label}: RMS={rms:.4f}, estimated power={power_est:.2f} W, calories~{kcal_est:.4f} kcal")

        if stft_show or save_figures:
            # TODO: Visualization styling lives here so it can be tuned globally later.
            fig_spec, ax_spec = plt.subplots(figsize=(10.8, 4.8), constrained_layout=True)
            log_spectrum = 10 * np.log10(spectrum + 1e-12)
            vmin, vmax = np.percentile(log_spectrum, [5, 99.5])
            image = ax_spec.pcolormesh(
                times,
                freqs,
                log_spectrum,
                shading="auto",
                cmap="magma",
                vmin=vmin,
                vmax=vmax,
            )
            colorbar = fig_spec.colorbar(image, ax=ax_spec, pad=0.02, aspect=28)
            style_colorbar(colorbar, "Power/Frequency (dB/Hz)")
            style_heatmap(ax_spec, make_plot_title(config, label, "Spectrogram"), "Time (s)", "Frequency (Hz)")
            finish_figure(
                fig_spec,
                config=config,
                module_name="stft",
                label=label,
                data_title=data_title,
                figure_name="spectrogram",
                show=stft_show,
                layout="none",
            )

        results.append(
            {
                "label": label,
                "frequency_hz": freqs,
                "time_s": times,
                "spectrum": spectrum,
                "power_estimate_w": power_est,
                "calorie_estimate_kcal": kcal_est,
            }
        )

    print_success("STFT finished.")
    return {"segments": results}
