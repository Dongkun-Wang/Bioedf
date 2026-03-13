from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from nm_config import nm_config
from utils.LoadDataset import util_load_dataset


def _write_signal_csv(path, start_dt, values):
    """Create a minimal headerless CSV test signal."""
    rows = []
    for index, value in enumerate(values):
        timestamp = int((start_dt + timedelta(seconds=index)).timestamp() * 1000)
        rows.append([timestamp, index, value])
    pd.DataFrame(rows).to_csv(path, header=False, index=False)


def test_load_dataset_reads_headerless_csv_without_losing_first_row(tmp_path):
    data_dir = tmp_path / "ecg"
    data_dir.mkdir()
    start_dt = datetime(2026, 1, 1, 12, 0, 0)
    _write_signal_csv(data_dir / "single.csv", start_dt, [1.0, 2.0, 3.0])

    config = nm_config()
    config["fileinfo"]["fullpath"] = str(data_dir)
    config["dataset"]["source_sampling_rate"] = 1
    config["dataset"]["sampling_rate_scale"] = 1
    config["dataset"]["segment_duration_seconds"] = 0
    dataset, updated_config = util_load_dataset(config)

    assert len(dataset) == 1
    assert np.allclose(dataset[0], np.array([1.0, 2.0, 3.0]))
    assert updated_config["datainfo"]["segment_labels"] == ["single_segment_1"]
    assert updated_config["datainfo"]["signal_type"] == "ecg"
    assert "datalen" not in updated_config["datainfo"]


def test_load_dataset_supports_time_slice_and_segmentation(tmp_path):
    data_dir = tmp_path / "eeg"
    data_dir.mkdir()
    start_dt = datetime(2026, 1, 1, 17, 17, 9)
    for idx in range(5):
        _write_signal_csv(data_dir / f"ch{idx + 1}.csv", start_dt, [idx + 1, idx + 2, idx + 3, idx + 4])

    config = nm_config()
    config["fileinfo"]["fullpath"] = str(data_dir)
    config["dataset"]["source_sampling_rate"] = 1
    config["dataset"]["sampling_rate_scale"] = 1
    config["dataset"]["slice_enabled"] = True
    config["dataset"]["slice_start"] = "17:17:10"
    config["dataset"]["slice_end"] = "17:17:12"
    config["dataset"]["segment_duration_seconds"] = 2
    dataset, updated_config = util_load_dataset(config)

    assert len(dataset) == 2
    assert np.allclose(dataset[0], np.array([4.0, 5.0]))
    assert np.allclose(dataset[1], np.array([6.0]))
    assert updated_config["datainfo"]["signal_type"] == "eeg"
    assert updated_config["datainfo"]["chcnt"] == 1
    assert updated_config["datainfo"]["source_channels"] == ["ch1", "ch2", "ch3", "ch4", "ch5"]
    assert "datalen" not in updated_config["datainfo"]


def test_load_dataset_auto_detects_eeg_and_averages_to_single_channel(tmp_path):
    data_dir = tmp_path / "eeg"
    data_dir.mkdir()
    start_dt = datetime(2026, 1, 1, 9, 0, 0)
    for idx in range(5):
        _write_signal_csv(data_dir / f"ch{idx + 1}.csv", start_dt, [idx + 1, idx + 2, idx + 3])

    config = nm_config()
    config["fileinfo"]["fullpath"] = str(data_dir)
    config["dataset"]["source_sampling_rate"] = 100
    config["dataset"]["sampling_rate_scale"] = 1
    config["dataset"]["segment_duration_seconds"] = 0
    dataset, updated_config = util_load_dataset(config)

    assert len(dataset) == 1
    assert updated_config["datainfo"]["signal_type"] == "eeg"
    assert updated_config["datainfo"]["chcnt"] == 1
    assert updated_config["preprocess"]["bpfreq"] == [1, 60]
    assert updated_config["datainfo"]["chname"] == ["eeg_mean"]
    assert np.allclose(dataset[0], np.array([3.0, 4.0, 5.0]))


def test_load_dataset_auto_detects_ecg_and_emg_profiles(tmp_path):
    ecg_dir = tmp_path / "ecg"
    emg_dir = tmp_path / "emg"
    ecg_dir.mkdir()
    emg_dir.mkdir()
    start_dt = datetime(2026, 1, 1, 10, 0, 0)

    _write_signal_csv(ecg_dir / "ecg.csv", start_dt, [1.0, 2.0, 1.5])
    _write_signal_csv(emg_dir / "emg.csv", start_dt, [3.0, 4.0, 5.0])

    ecg_config = nm_config()
    ecg_config["fileinfo"]["fullpath"] = str(ecg_dir)
    ecg_config["dataset"]["source_sampling_rate"] = 1000
    ecg_config["dataset"]["sampling_rate_scale"] = 1
    ecg_config["dataset"]["segment_duration_seconds"] = 0
    ecg_dataset, ecg_updated = util_load_dataset(ecg_config)

    emg_config = nm_config()
    emg_config["fileinfo"]["fullpath"] = str(emg_dir)
    emg_config["dataset"]["source_sampling_rate"] = 1000
    emg_config["dataset"]["sampling_rate_scale"] = 1
    emg_config["dataset"]["segment_duration_seconds"] = 0
    emg_dataset, emg_updated = util_load_dataset(emg_config)

    assert len(ecg_dataset) == 1
    assert ecg_updated["datainfo"]["signal_type"] == "ecg"
    assert ecg_updated["preprocess"]["bpfreq"] == [1, 10]

    assert len(emg_dataset) == 1
    assert emg_updated["datainfo"]["signal_type"] == "emg"
    assert emg_updated["preprocess"]["bpfreq"] == [1, 250]
