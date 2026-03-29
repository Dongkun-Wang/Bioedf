from datetime import datetime

import numpy as np
from pyedflib import highlevel

from nm_config import nm_config
from utils.LoadDataset import load_dataset


def _write_signal_edf(path, start_dt, labels, values_by_channel, sample_frequency=1):
    """Create a minimal EDF test signal with one or more channels."""
    signals = [np.asarray(values, dtype=float) for values in values_by_channel]
    signal_headers = []
    for label, signal in zip(labels, signals, strict=False):
        minimum = float(np.min(signal))
        maximum = float(np.max(signal))
        if np.isclose(minimum, maximum):
            minimum -= 1.0
            maximum += 1.0
        signal_headers.append(
            highlevel.make_signal_header(
                label=label,
                sample_frequency=sample_frequency,
                physical_min=minimum - 1.0,
                physical_max=maximum + 1.0,
            )
        )

    header = highlevel.make_header(startdate=start_dt, patientname="unit-test")
    assert highlevel.write_edf(str(path), signals, signal_headers, header=header)


def test_load_dataset_reads_single_channel_edf_without_losing_first_row(tmp_path):
    data_dir = tmp_path / "ecg"
    data_dir.mkdir()
    start_dt = datetime(2026, 1, 1, 12, 0, 0)
    _write_signal_edf(data_dir / "single.edf", start_dt, ["LeadI"], [[1.0, 2.0, 3.0]])

    config = nm_config()
    config["fileinfo"]["fullpath"] = str(data_dir)
    config["dataset"]["segment_duration_seconds"] = 0
    dataset, updated_config = load_dataset(config)

    assert len(dataset) == 1
    assert np.allclose(dataset[0], np.array([1.0, 2.0, 3.0]), atol=0.05)
    assert updated_config["datainfo"]["segment_labels"] == ["LeadI_segment_1"]
    assert updated_config["datainfo"]["signal_type"] == "ecg"
    assert "datalen" not in updated_config["datainfo"]


def test_load_dataset_supports_time_slice_and_segmentation(tmp_path):
    data_dir = tmp_path / "eeg"
    data_dir.mkdir()
    start_dt = datetime(2026, 1, 1, 17, 17, 9)
    channels = []
    for idx in range(5):
        channels.append([idx + 1, idx + 2, idx + 3, idx + 4])
    _write_signal_edf(
        data_dir / "multi.edf",
        start_dt,
        ["F7", "Fp1", "Fpz", "Fp2", "F8"],
        channels,
    )

    config = nm_config()
    config["fileinfo"]["fullpath"] = str(data_dir)
    config["dataset"]["slice_enabled"] = True
    config["dataset"]["slice_start"] = "17:17:10"
    config["dataset"]["slice_end"] = "17:17:12"
    config["dataset"]["segment_duration_seconds"] = 2
    dataset, updated_config = load_dataset(config)

    assert len(dataset) == 2
    assert np.allclose(dataset[0], np.array([4.0, 5.0]), atol=0.05)
    assert np.allclose(dataset[1], np.array([6.0]), atol=0.05)
    assert updated_config["datainfo"]["signal_type"] == "eeg"
    assert updated_config["datainfo"]["chcnt"] == 1
    assert updated_config["datainfo"]["source_channels"] == ["F7", "Fp1", "Fpz", "Fp2", "F8"]
    assert "datalen" not in updated_config["datainfo"]


def test_load_dataset_auto_detects_eeg_and_averages_to_single_channel(tmp_path):
    data_dir = tmp_path / "eeg"
    data_dir.mkdir()
    start_dt = datetime(2026, 1, 1, 9, 0, 0)
    channels = []
    for idx in range(5):
        channels.append([idx + 1, idx + 2, idx + 3])
    _write_signal_edf(
        data_dir / "multi.edf",
        start_dt,
        ["F7", "Fp1", "Fpz", "Fp2", "F8"],
        channels,
        sample_frequency=3,
    )

    config = nm_config()
    config["fileinfo"]["fullpath"] = str(data_dir)
    config["dataset"]["segment_duration_seconds"] = 0
    dataset, updated_config = load_dataset(config)

    assert len(dataset) == 1
    assert updated_config["datainfo"]["signal_type"] == "eeg"
    assert updated_config["datainfo"]["chcnt"] == 1
    assert updated_config["preprocess"]["bpfreq"] == [0.4, 60]
    assert updated_config["datainfo"]["chname"] == ["eeg_mean"]
    assert np.allclose(dataset[0], np.array([3.0, 4.0, 5.0]), atol=0.05)


def test_load_dataset_auto_detects_ecg_and_emg_profiles(tmp_path):
    ecg_dir = tmp_path / "ecg"
    emg_dir = tmp_path / "emg"
    ecg_dir.mkdir()
    emg_dir.mkdir()
    start_dt = datetime(2026, 1, 1, 10, 0, 0)

    _write_signal_edf(
        ecg_dir / "ecg.edf",
        start_dt,
        ["RA", "LA", "F", "V3", "V5"],
        [
            [1.0, 1.5, 1.0],
            [2.0, 2.5, 2.0],
            [7.0, 8.0, 9.0],
            [3.0, 3.5, 3.0],
            [4.0, 4.5, 4.0],
        ],
        sample_frequency=3,
    )
    _write_signal_edf(emg_dir / "emg.edf", start_dt, ["R_BB"], [[3.0, 4.0, 5.0]], sample_frequency=3)

    ecg_config = nm_config()
    ecg_config["fileinfo"]["fullpath"] = str(ecg_dir)
    ecg_config["dataset"]["segment_duration_seconds"] = 0
    ecg_dataset, ecg_updated = load_dataset(ecg_config)

    emg_config = nm_config()
    emg_config["fileinfo"]["fullpath"] = str(emg_dir)
    emg_config["dataset"]["segment_duration_seconds"] = 0
    emg_dataset, emg_updated = load_dataset(emg_config)

    assert len(ecg_dataset) == 1
    assert np.allclose(ecg_dataset[0], np.array([7.0, 8.0, 9.0]), atol=0.05)
    assert ecg_updated["datainfo"]["signal_type"] == "ecg"
    assert ecg_updated["datainfo"]["selected_channel_indices"] == [3]
    assert ecg_updated["preprocess"]["bpfreq"] == [5, 25]

    assert len(emg_dataset) == 1
    assert emg_updated["datainfo"]["signal_type"] == "emg"
    assert emg_updated["preprocess"]["bpfreq"] == [20, 250]
