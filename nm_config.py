"""Configuration defaults and signal-modality inference helpers."""

import os
from pathlib import Path


DATASET_DIRECTORY_ALIASES = {
    "eeg": ("eeg", "脑电"),
    "ecg": ("ecg", "ekg", "心电"),
    "emg": ("emg", "leg", "arm", "右腿", "左腿", "肌电", "左臂"),
}


SIGNAL_PROFILES = {
    "eeg": {
        "display_name": "EEG",
        "keywords": DATASET_DIRECTORY_ALIASES["eeg"] + ("f7", "fp1", "fpz", "fp2", "f8"),
        "bandpass": [0.4, 60],
        "bandstop": [48, 52],
        "channel_strategy": "average_to_single",
        "analysis_modules": ["band"],
    },
    "ecg": {
        "display_name": "ECG",
        "keywords": DATASET_DIRECTORY_ALIASES["ecg"] + ("ra", "la", "v3", "v5"),
        "bandpass": [5, 25],
        "bandstop": [48, 52],
        "channel_strategy": "ecg_third_or_single",
        "analysis_modules": ["heart_rate"],
    },
    "emg": {
        "display_name": "EMG",
        "keywords": DATASET_DIRECTORY_ALIASES["emg"] + ("bicep", "tricep", "r_bb", "l_bb"),
        "bandpass": [20, 250],
        "bandstop": [48, 52],
        "channel_strategy": "single",
        "analysis_modules": ["fft", "stft", "freq_analysis"],
    },
}


def infer_signal_modality(file_dir, file_names):
    """Infer EEG, ECG, or EMG from directory and signal naming patterns."""
    text_parts = [file_dir, os.path.basename(file_dir)] + list(file_names)
    searchable = " ".join(part.lower() for part in text_parts if part)

    for modality, profile in SIGNAL_PROFILES.items():
        if any(keyword.lower() in searchable for keyword in profile["keywords"]):
            return modality, profile

    if len(file_names) >= 4:
        return "eeg", SIGNAL_PROFILES["eeg"]
    raise ValueError(f"Unable to infer signal modality from directory name: {file_dir}")


def _build_fileinfo(result_dir):
    """Return file and export location defaults."""
    return {
        "fullpath": "",
        "filetype": ".edf",
        "result_dir": str(result_dir),
    }


def _build_output_config():
    """Return figure and table export defaults."""
    return {
        "save_figures": False,
        "figure_format": "png",
        "figure_dpi": 320,
        "organize_by_modality": True,
        "save_band_metrics_csv": False,
    }


def _build_dataset_config():
    """Return dataset loading, slicing, and segmentation defaults."""
    return {
        "sort_files": True,
        "recursive_search": True,
        "preferred_signal_dirs": ["EP", "EPFilter"],
        "exclude_keywords": ["event"],
        "slice_enabled": False,
        "slice_start": None,
        "slice_end": None,
        "segment_duration_seconds": 60,
        "ecg_channel_index": 3,
    }


def _build_preprocess_config():
    """Return filter defaults that are later completed by modality inference."""
    return {
        "bpfilter": True,
        "bsfilter": True,
        "bpfreq": None,
        "bsfreq": None,
        "bpfiltord": 4,
        "bsfiltord": 4,
    }


def _build_analysis_config():
    """Return analysis parameter defaults."""
    return {
        "enabled_modules": [],
        "fft_type": "log",
        "stft_overlap": 0.5,
        "band_freq_limit": 60,
        "rms_time": 1.0,
        "rms_gap": 0.5,
        "mdf_trend_seconds": 5.0,
        "calorie_power_ratio": 25,
    }


def _build_display_config():
    """Return visualization toggle defaults."""
    return {
        "preprocess_show": True,
        "heart_rate_show": True,
        "fft_show": True,
        "stft_show": True,
        "band_show": True,
        "freq_analysis_show": True,
        "calorie_show": True,
    }


def nm_config():
    """Build the default runtime configuration."""
    result_dir = Path("./result")
    result_dir.mkdir(exist_ok=True)

    return {
        "fileinfo": _build_fileinfo(result_dir),
        "output": _build_output_config(),
        "dataset": _build_dataset_config(),
        "preprocess": _build_preprocess_config(),
        "analysis": _build_analysis_config(),
        "display": _build_display_config(),
    }
