"""Short-time Fourier transform analysis."""

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import spectrogram

from utils.console import print_status, print_success, print_subsection


def util_stft(dataset, data_title, config):
    """Perform STFT, median-frequency tracking, and optional energy estimation."""
    fs = float(config["datainfo"]["Fs"])
    segment_labels = config["datainfo"].get("segment_labels", [])
    stft_show = config["display"].get("stft_show", "off")
    stft_overlap = float(config["analysis"].get("stft_overlap", 0.5))
    plot_median_freq = bool(config["display"].get("median_freq_plot", False))
    avg_segment_len = float(config["analysis"].get("avg_segment_len", 20))
    calorie_tool = config["analysis"].get("calorie_tool", "off")
    calorie_show = config["display"].get("calorie_show", "off")
    calorie_power_ratio = float(config["analysis"].get("calorie_power_ratio", 25))

    print_subsection("STFT")
    print_status("Computing spectrograms and median-frequency trends.")

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

        cumulative_power = np.cumsum(spectrum, axis=0)
        total_power = cumulative_power[-1, :]
        thresholds = 0.5 * total_power
        median_idx = np.argmax(cumulative_power >= thresholds, axis=0)
        median_freq = freqs[median_idx]

        if len(times) >= 2:
            time_resolution = times[1] - times[0]
            windows_per_segment = max(1, int(round(avg_segment_len / time_resolution)))
            median_segments = np.array_split(median_freq, max(1, int(np.ceil(len(times) / windows_per_segment))))
            time_segments = np.array_split(times, len(median_segments))
            segment_time = np.array([np.mean(seg) for seg in time_segments])
            median_freq_avg = np.array([np.mean(seg) for seg in median_segments])
        else:
            segment_time = np.asarray(times)
            median_freq_avg = np.asarray(median_freq)

        power_est = None
        kcal_est = None
        if calorie_tool == "on":
            rms = float(np.sqrt(np.mean(signal**2)))
            duration = len(signal) / fs
            power_est = rms * calorie_power_ratio
            kcal_est = (power_est * duration) / 4184
            if calorie_show == "on":
                print_status(
                    f"{label}: RMS={rms:.4f}, estimated power={power_est:.2f} W, calories~{kcal_est:.4f} kcal"
                )

        if plot_median_freq:
            plt.figure(figsize=(12, 4))
            plt.plot(times, median_freq, label="Median Frequency", alpha=0.5)
            plt.plot(segment_time, median_freq_avg, "o-", label=f"Avg ({avg_segment_len}s)")
            plt.title(f"{label} {data_title} Median Frequency")
            plt.xlabel("Time (s)")
            plt.ylabel("Median Frequency (Hz)")
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            plt.show()
            plt.close()

        if stft_show == "on":
            plt.figure(figsize=(10, 4))
            plt.imshow(
                10 * np.log10(spectrum + 1e-12),
                aspect="auto",
                extent=[times[0], times[-1], freqs[0], freqs[-1]],
                origin="lower",
            )
            plt.colorbar(label="Power/Frequency (dB/Hz)")
            plt.title(f"{label} {data_title} Spectrogram")
            plt.xlabel("Time (s)")
            plt.ylabel("Frequency (Hz)")
            plt.tight_layout()
            plt.show()
            plt.close()

        results.append(
            {
                "label": label,
                "frequency_hz": freqs,
                "time_s": times,
                "spectrum": spectrum,
                "median_frequency_hz": median_freq,
                "median_frequency_avg_hz": median_freq_avg,
                "median_frequency_avg_time_s": segment_time,
                "power_estimate_w": power_est,
                "calorie_estimate_kcal": kcal_est,
            }
        )

    print_success("STFT finished.")
    return {"segments": results}
