"""Dataset loading and normalization helpers for EDF recordings."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from pathlib import Path

import numpy as np
import pyedflib

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


def _segment_signal(signal, fs, segment_seconds):
    """Split one 1D signal into equally sized analysis segments."""
    if not segment_seconds or segment_seconds <= 0:
        return [signal]

    max_length = max(1, int(round(fs * segment_seconds)))
    if len(signal) <= max_length:
        return [signal]

    segment_count = int(np.ceil(len(signal) / max_length))
    return [segment for segment in np.array_split(signal, segment_count) if len(segment) > 0]


def _is_event_file(path: Path, exclude_keywords: list[str]) -> bool:
    searchable_parts = [path.name, path.stem] + list(path.parts)
    searchable = " ".join(part.lower() for part in searchable_parts)
    return any(keyword.lower() in searchable for keyword in exclude_keywords)


def _resolve_edf_files(config):
    """Resolve the EDF signal files to load from a file path or directory."""
    target = Path(config["fileinfo"]["fullpath"]).expanduser().resolve()
    suffix = config["fileinfo"].get("filetype", ".edf").lower()
    exclude_keywords = list(config["dataset"].get("exclude_keywords", ["event"]))
    preferred_dirs = [item.lower() for item in config["dataset"].get("preferred_signal_dirs", ["EP", "EPFilter"])]

    if target.is_file():
        if target.suffix.lower() != suffix:
            raise FileNotFoundError(f"Expected an {suffix} file, got: {target}")
        if _is_event_file(target, exclude_keywords):
            raise ValueError(f"The selected EDF appears to be an event file, not a signal file: {target}")
        return [target]

    if not target.is_dir():
        raise FileNotFoundError(f"Data path does not exist: {target}")

    if config["dataset"].get("recursive_search", True):
        candidates = sorted(path for path in target.rglob(f"*{suffix}") if path.is_file())
    else:
        candidates = sorted(path for path in target.glob(f"*{suffix}") if path.is_file())

    signal_candidates = [path for path in candidates if not _is_event_file(path, exclude_keywords)]
    if not signal_candidates:
        raise FileNotFoundError(f"No signal {suffix} files were found in {target}.")

    lower_part_lists = [[part.lower() for part in path.parts] for path in signal_candidates]
    for preferred_dir in preferred_dirs:
        matched = [
            path
            for path, parts in zip(signal_candidates, lower_part_lists, strict=False)
            if preferred_dir in parts
        ]
        if matched:
            return matched

    return signal_candidates


def _read_edf_file(path: Path):
    """Read one EDF file into aligned channel arrays."""
    reader = pyedflib.EdfReader(str(path))
    try:
        signal_count = reader.signals_in_file
        channel_names = [str(label).strip() or f"CH{i + 1}" for i, label in enumerate(reader.getSignalLabels())]
        sample_rates = np.asarray([float(reader.getSampleFrequency(i)) for i in range(signal_count)], dtype=float)
        sample_counts = np.asarray([int(value) for value in reader.getNSamples()], dtype=int)
        signals = [np.asarray(reader.readSignal(i), dtype=float) for i in range(signal_count)]
        start_datetime = reader.getStartdatetime()
    finally:
        reader.close()

    if len(signals) == 0:
        raise ValueError(f"No signals were found in EDF file: {path}")

    min_len = int(sample_counts.min())
    signals = [signal[:min_len] for signal in signals]
    sample_rates = sample_rates[: len(signals)]
    if not np.allclose(sample_rates, sample_rates[0], rtol=0, atol=1e-6):
        raise ValueError(f"Signal channels in {path.name} do not share the same sampling rate.")

    return {
        "path": path,
        "signals": signals,
        "channel_names": channel_names,
        "sample_rate_hz": float(sample_rates[0]),
        "sample_count": min_len,
        "start_datetime": start_datetime,
    }


def _apply_channel_strategy(signals, channel_names, config):
    """Apply the modality-specific channel handling policy."""
    strategy = config["datainfo"].get("channel_strategy", "single")
    signal_type = config["datainfo"].get("signal_type", "signal")

    if strategy == "average_to_single":
        averaged_signal = np.mean(np.vstack(signals), axis=0)
        config["datainfo"]["selected_channel_indices"] = list(range(1, len(channel_names) + 1))
        config["datainfo"]["selected_channel_names"] = list(channel_names)
        return [averaged_signal], [f"{signal_type}_mean"]

    if strategy == "ecg_third_or_single":
        preferred_index = max(0, int(config["dataset"].get("ecg_channel_index", 3)) - 1)
        selected_index = preferred_index if len(signals) > preferred_index else 0
        config["datainfo"]["selected_channel_indices"] = [selected_index + 1]
        config["datainfo"]["selected_channel_names"] = [channel_names[selected_index]]
        return [signals[selected_index]], [channel_names[selected_index]]

    config["datainfo"]["selected_channel_indices"] = list(range(1, len(channel_names) + 1))
    config["datainfo"]["selected_channel_names"] = list(channel_names)
    return signals, channel_names


def _build_datetime_axis(start_datetime, sample_count, fs):
    """Build per-sample datetimes from an EDF start time and sampling rate."""
    return np.array(
        [start_datetime + timedelta(seconds=index / fs) for index in range(sample_count)],
        dtype=object,
    )


def _build_timestamp_ms(start_datetime, sample_count, fs):
    """Build millisecond timestamps for saved metadata."""
    start_timestamp = start_datetime.timestamp()
    seconds = np.arange(sample_count, dtype=float) / fs
    return np.rint((start_timestamp + seconds) * 1000).astype(np.int64)


def load_dataset(config):
    """Load EDF recordings and normalize them into 1D analysis segments."""
    config.setdefault("datainfo", {})
    edf_files = _resolve_edf_files(config)
    if config["dataset"].get("sort_files", True):
        edf_files = sorted(edf_files)

    signal_descriptors = [_read_edf_file(path) for path in edf_files]
    modality_hints = []
    for descriptor in signal_descriptors:
        modality_hints.append(descriptor["path"].stem)
        modality_hints.extend(descriptor["channel_names"])

    modality, profile = infer_signal_modality(str(Path(config["fileinfo"]["fullpath"])), modality_hints)
    config["datainfo"]["signal_type"] = modality
    config["datainfo"]["signal_display_name"] = profile["display_name"]
    config["datainfo"]["channel_strategy"] = profile["channel_strategy"]
    config["analysis"]["enabled_modules"] = list(profile["analysis_modules"])
    config["preprocess"]["bpfreq"] = list(profile["bandpass"])
    config["preprocess"]["bsfreq"] = list(profile["bandstop"])

    print_section("LOAD DATASET")
    print_subsection("Resolved Profile")
    print_kv("Signal modality", f"{config['datainfo']['signal_display_name']} ({modality})")
    print_kv("EDF files", ", ".join(path.name for path in edf_files))
    print_kv("Band-pass", config["preprocess"]["bpfreq"])

    dataset = []
    segment_labels = []
    source_channels = []
    analysis_channels = []
    recording_windows = []
    resolved_fs = None

    multiple_files = len(signal_descriptors) > 1
    for descriptor in signal_descriptors:
        path = descriptor["path"]
        signals = descriptor["signals"]
        channel_names = descriptor["channel_names"]
        fs = float(descriptor["sample_rate_hz"])
        if resolved_fs is None:
            resolved_fs = fs
        elif not np.isclose(resolved_fs, fs, rtol=0, atol=1e-6):
            raise ValueError("All EDF recordings in one run must share the same sampling rate.")

        datetime_objects = _build_datetime_axis(descriptor["start_datetime"], descriptor["sample_count"], fs)
        timestamp_ms = _build_timestamp_ms(descriptor["start_datetime"], descriptor["sample_count"], fs)
        experiment_start = datetime_objects[0]
        experiment_end = datetime_objects[-1]

        print_subsection(f"Recording: {path.name}")
        print_kv("Start time", _format_datetime(experiment_start))
        print_kv("End time", _format_datetime(experiment_end))
        print_kv("Duration", experiment_end - experiment_start)
        print_kv("Source channels", ", ".join(channel_names))
        print_kv("Sampling rate", f"{fs:.4f} Hz")

        if config["dataset"].get("slice_enabled", False):
            time_mask = _build_time_mask(
                datetime_objects,
                config["dataset"].get("slice_start"),
                config["dataset"].get("slice_end"),
            )
            if not np.any(time_mask):
                raise ValueError(f"The selected slice window did not match any samples in {path.name}.")

            signals = [signal[time_mask] for signal in signals]
            datetime_objects = datetime_objects[time_mask]
            timestamp_ms = timestamp_ms[time_mask]

            print_kv("Slice start", _format_datetime(datetime_objects[0]))
            print_kv("Slice end", _format_datetime(datetime_objects[-1]))
            print_kv("Slice samples", len(datetime_objects))

        processed_channels, processed_names = _apply_channel_strategy(signals, channel_names, config)
        source_channels.extend(channel_names)
        analysis_channels.extend(processed_names)
        recording_windows.append(
            {
                "file_name": path.name,
                "experiment_start": _format_datetime(experiment_start),
                "experiment_end": _format_datetime(experiment_end),
                "slice_start": _format_datetime(datetime_objects[0]),
                "slice_end": _format_datetime(datetime_objects[-1]),
                "sample_count": len(datetime_objects),
                "timestamps_ms": {
                    "start": int(timestamp_ms[0]),
                    "end": int(timestamp_ms[-1]),
                },
            }
        )

        label_prefix = f"{path.stem}_" if multiple_files else ""
        segment_seconds = config["dataset"].get("segment_duration_seconds", 60)
        for channel_name, signal in zip(processed_names, processed_channels, strict=False):
            for segment_idx, segment in enumerate(_segment_signal(signal, fs, segment_seconds), start=1):
                dataset.append(np.asarray(segment, dtype=float))
                segment_labels.append(f"{label_prefix}{channel_name}_segment_{segment_idx}")

    config["datainfo"]["Fs"] = resolved_fs
    config["datainfo"]["chcnt"] = len(analysis_channels)
    config["datainfo"]["chname"] = analysis_channels
    config["datainfo"]["source_channels"] = source_channels
    config["datainfo"]["source_files"] = [path.name for path in edf_files]
    config["datainfo"]["segment_count"] = len(dataset)
    config["datainfo"]["segment_labels"] = segment_labels
    config["datainfo"]["recording_windows"] = recording_windows
    if recording_windows:
        config["datainfo"]["time_range"] = recording_windows[0]

    print_subsection("Analysis Channels")
    print_kv("Analysis channels", ", ".join(analysis_channels))
    if modality == "ecg":
        selected_index = config["datainfo"]["selected_channel_indices"][0]
        selected_name = config["datainfo"]["selected_channel_names"][0]
        print_kv("ECG selected channel", f"第 {selected_index} 通道 ({selected_name})")
    print_kv("Segment count", len(dataset))
    print_kv("Segment labels", ", ".join(segment_labels))
    print_status("Dataset loading finished.")
    print_success()

    return dataset, config
