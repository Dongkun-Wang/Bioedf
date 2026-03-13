"""Configuration defaults and signal-modality inference helpers."""

import os
from pathlib import Path


DATASET_DIRECTORY_ALIASES = {
    # Keep English aliases and legacy Chinese directory names for compatibility.
    "eeg": ("eeg", "\u8111\u7535"),
    "ecg": ("ecg", "ekg", "\u5fc3\u7535"),
    "emg": ("emg", "leg", "arm", "\u53f3\u817f", "\u5de6\u817f", "\u808c\u7535", "\u5de6\u81c2"),
}


SIGNAL_PROFILES = {
    "eeg": {
        "display_name": "EEG",
        "keywords": DATASET_DIRECTORY_ALIASES["eeg"],
        "bandpass": [1, 60],
        "bandstop": [48, 52],
        "channel_strategy": "average_to_single",
        "analysis_modules": ["band"],
    },
    "ecg": {
        "display_name": "ECG",
        "keywords": DATASET_DIRECTORY_ALIASES["ecg"],
        "bandpass": [1, 10],
        "bandstop": [48, 52],
        "channel_strategy": "single",
        "analysis_modules": ["heart_rate"],
    },
    "emg": {
        "display_name": "EMG",
        "keywords": DATASET_DIRECTORY_ALIASES["emg"] + ("bicep", "tricep"),
        "bandpass": [1, 250],
        "bandstop": [48, 52],
        "channel_strategy": "single",
        "analysis_modules": ["fft", "stft", "freq_alg"],
    },
}


def infer_signal_modality(file_dir, file_names):
    """Infer EEG, ECG, or EMG from directory and file naming patterns."""
    text_parts = [file_dir, os.path.basename(file_dir)] + list(file_names)
    searchable = " ".join(part.lower() for part in text_parts if part)

    for modality, profile in SIGNAL_PROFILES.items():
        if any(keyword.lower() in searchable for keyword in profile["keywords"]):
            return modality, profile

    if len(file_names) >= 4:
        return "eeg", SIGNAL_PROFILES["eeg"]
    raise ValueError(f"Unable to infer signal modality from directory name: {file_dir}")


def nm_config():
    """Build the default runtime configuration."""
    result_dir = Path("./result")
    result_dir.mkdir(exist_ok=True)

    return {
        "fileinfo": {
            "fullpath": "",
            "filetype": ".csv",
            "result_dir": str(result_dir),
        },
        "dataset": {
            "source_sampling_rate": 1000,
            "timestamp_column": 0,
            "signal_column": 2,
            "sort_files": True,
            "slice_enabled": False,
            "slice_start": None,  # Example: "17:17:10" or "2024-06-26 17:17:10"
            "slice_end": None,  # Example: "17:19:30" or "2024-06-26 17:19:30"
            "segment_duration_seconds": 60,
            # Preserve the original device-specific scaling formula.
            "sampling_rate_scale": 8e6 / 42 / 6 / 32 / 1000,
        },
        "preprocess": {
            "bpfilter": "on",
            "bsfilter": "on",
            # Filled automatically after modality inference:
            # EEG 1-60 Hz, ECG 1-10 Hz, EMG 1-250 Hz.
            "bpfreq": None,
            "bsfreq": None,
            "bpfiltord": 4,
            "bsfiltord": 4,
        },
        "analysis": {
            "enabled_modules": [],
            "fft_type": "log",
            "stft_overlap": 0.5,
            "avg_segment_len": 20,
            "band_freq_limit": 60,
            "rms_time": 1.0,
            "rms_gap": 0.5,
            "calorie_tool": "off",
            "calorie_power_ratio": 25,
        },
        "display": {
            "preprocess_show": "on",
            "preprocess_save": "off",
            "heart_rate_show": "on",
            "fft_show": "on",
            "fft_save": "off",
            "stft_show": "on",
            "median_freq_plot": True,
            "band_show": "on",
            "band_save_csv": "off",
            "freqalg_show": "on",
            "calorie_show": "off",
        },
    }
