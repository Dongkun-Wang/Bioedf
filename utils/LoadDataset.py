"""Dataset loading and normalization helpers."""

import os
from datetime import datetime, time

import numpy as np
import pandas as pd

from nm_config import infer_signal_modality
from utils.ui import print_kv, print_section, print_status, print_subsection, print_success


def _format_datetime(value):
    """Format datetimes with millisecond precision for console output."""
    return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def _parse_slice_boundary(value):
    """Parse either a time-only boundary or a full datetime boundary."""
    if value in (None, ""):
        return None
    if isinstance(value, time):
        return ("time", value)
    if isinstance(value, datetime):
        return ("datetime", value)

    text = str(value).strip()
    try:
        return ("datetime", datetime.fromisoformat(text))
    except ValueError:
        return ("time", time.fromisoformat(text))


def _build_time_mask(datetime_objects, slice_start, slice_end):
    """Build a boolean mask for the requested time window."""
    if slice_start is None and slice_end is None:
        return np.ones(len(datetime_objects), dtype=bool)

    start_kind = _parse_slice_boundary(slice_start)
    end_kind = _parse_slice_boundary(slice_end)
    if start_kind is None or end_kind is None:
        raise ValueError("When slice_enabled is True, both slice_start and slice_end must be set.")
    if start_kind[0] != end_kind[0]:
        raise ValueError("slice_start and slice_end must use the same time format.")

    if start_kind[0] == "datetime":
        start_value, end_value = start_kind[1], end_kind[1]
        return np.array([start_value <= dt <= end_value for dt in datetime_objects], dtype=bool)

    start_value, end_value = start_kind[1], end_kind[1]
    return np.array([start_value <= dt.time() <= end_value for dt in datetime_objects], dtype=bool)


def _resolve_sampling_rate(config):
    """Resolve the final sampling rate using the original project scaling formula."""
    raw_fs = float(config["dataset"].get("source_sampling_rate", 1000))
    scale = float(config["dataset"].get("sampling_rate_scale", 1.0))
    return max(1, round(raw_fs * scale))


def _segment_signal(signal, fs, segment_seconds):
    """Split one 1D signal into equally sized analysis segments."""
    if not segment_seconds or segment_seconds <= 0:
        return [signal]

    max_length = max(1, int(round(fs * segment_seconds)))
    if len(signal) <= max_length:
        return [signal]

    segment_count = int(np.ceil(len(signal) / max_length))
    return [segment for segment in np.array_split(signal, segment_count) if len(segment) > 0]


def _apply_channel_strategy(signals, channel_names, config):
    """Apply the modality-specific channel handling policy."""
    strategy = config["datainfo"].get("channel_strategy", "single")
    if strategy == "average_to_single":
        averaged_signal = np.mean(np.vstack(signals), axis=0)
        averaged_name = f"{config['datainfo']['signal_type']}_mean"
        return [averaged_signal], [averaged_name]
    return signals, channel_names


def load_dataset(config):
    """Load headerless CSV recordings and normalize them into 1D segments."""
    config.setdefault("datainfo", {})
    file_dir = config["fileinfo"]["fullpath"]
    file_type = config["fileinfo"]["filetype"]
    if not os.path.isdir(file_dir):
        raise FileNotFoundError(f"Data directory does not exist: {file_dir}")

    file_list = [file_name for file_name in os.listdir(file_dir) if file_name.endswith(file_type)]
    if config["dataset"].get("sort_files", True):
        file_list.sort()
    if not file_list:
        raise FileNotFoundError(f"No {file_type} files were found in {file_dir}.")

    timestamp_column = int(config["dataset"].get("timestamp_column", 0))
    signal_column = int(config["dataset"].get("signal_column", 2))

    raw_signals = []
    raw_timestamps = []
    channel_names = []
    for file_name in file_list:
        full_path = os.path.join(file_dir, file_name)
        frame = pd.read_csv(full_path, header=None)
        if frame.shape[1] <= max(timestamp_column, signal_column):
            raise ValueError(
                f"{file_name} is missing an expected column. Only {frame.shape[1]} columns were found."
            )

        raw_timestamps.append(frame.iloc[:, timestamp_column].to_numpy(dtype=np.int64))
        raw_signals.append(frame.iloc[:, signal_column].to_numpy(dtype=float))
        channel_names.append(os.path.splitext(file_name)[0])

    modality, profile = infer_signal_modality(file_dir, channel_names)
    config["datainfo"]["signal_type"] = modality
    config["datainfo"]["signal_display_name"] = profile["display_name"]
    config["datainfo"]["channel_strategy"] = profile["channel_strategy"]
    config["analysis"]["enabled_modules"] = list(profile["analysis_modules"])
    config["preprocess"]["bpfreq"] = list(profile["bandpass"])
    config["preprocess"]["bsfreq"] = list(profile["bandstop"])

    # Truncate every channel to the shortest one to preserve alignment before averaging.
    min_len = min(len(signal) for signal in raw_signals)
    raw_signals = [signal[:min_len] for signal in raw_signals]
    raw_timestamps = [timestamps[:min_len] for timestamps in raw_timestamps]

    reference_timestamps = raw_timestamps[0]
    datetime_objects = np.array(
        [datetime.fromtimestamp(timestamp / 1000.0) for timestamp in reference_timestamps],
        dtype=object,
    )
    experiment_start = datetime_objects[0]
    experiment_end = datetime_objects[-1]

    print_section("LOAD DATASET")
    print_subsection("Experiment Window")
    print_kv("Start time", _format_datetime(experiment_start))
    print_kv("End time", _format_datetime(experiment_end))
    print_kv("Duration", experiment_end - experiment_start)

    if config["dataset"].get("slice_enabled", False):
        time_mask = _build_time_mask(
            datetime_objects,
            config["dataset"].get("slice_start"),
            config["dataset"].get("slice_end"),
        )
        if not np.any(time_mask):
            raise ValueError("The selected slice window did not match any samples.")

        raw_signals = [signal[time_mask] for signal in raw_signals]
        datetime_objects = datetime_objects[time_mask]
        reference_timestamps = reference_timestamps[time_mask]

        print_subsection("Slice Window")
        print_kv("Slice start", _format_datetime(datetime_objects[0]))
        print_kv("Slice end", _format_datetime(datetime_objects[-1]))
        print_kv("Slice samples", len(datetime_objects))

    processed_channels, processed_names = _apply_channel_strategy(raw_signals, channel_names, config)
    resolved_fs = _resolve_sampling_rate(config)
    segment_seconds = config["dataset"].get("segment_duration_seconds", 60)

    dataset = []
    segment_labels = []
    for channel_name, signal in zip(processed_names, processed_channels):
        for segment_idx, segment in enumerate(_segment_signal(signal, resolved_fs, segment_seconds), start=1):
            dataset.append(np.asarray(segment, dtype=float))
            segment_labels.append(f"{channel_name}_segment_{segment_idx}")

    config["datainfo"]["Fs"] = resolved_fs
    config["datainfo"]["chcnt"] = len(processed_channels)
    config["datainfo"]["chname"] = processed_names
    config["datainfo"]["source_channels"] = channel_names
    config["datainfo"]["segment_count"] = len(dataset)
    config["datainfo"]["segment_labels"] = segment_labels
    config["datainfo"]["time_range"] = {
        "experiment_start": _format_datetime(experiment_start),
        "experiment_end": _format_datetime(experiment_end),
        "slice_start": _format_datetime(datetime_objects[0]),
        "slice_end": _format_datetime(datetime_objects[-1]),
        "sample_count": len(datetime_objects),
        "timestamps_ms": {
            "start": int(reference_timestamps[0]),
            "end": int(reference_timestamps[-1]),
        },
    }

    print_subsection("Resolved Profile")
    print_kv("Signal modality", f"{config['datainfo']['signal_display_name']} ({modality})")
    print_kv("Source channels", ", ".join(channel_names))
    print_kv("Analysis channels", ", ".join(processed_names))
    print_kv("Band-pass", config["preprocess"]["bpfreq"])
    print_kv("Sampling rate", f"{config['datainfo']['Fs']:.4f} Hz")
    print_kv("Segment count", len(dataset))
    print_kv("Segment labels", ", ".join(segment_labels))
    print_status("Dataset loading finished.")
    print_success()

    return dataset, config
