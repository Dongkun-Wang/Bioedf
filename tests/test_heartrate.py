import numpy as np

from utils.Heartrate import _detect_r_peaks, heartrate_analysis


def _make_noisy_ecg(fs, duration_seconds, beat_times):
    time_axis = np.arange(0, duration_seconds, 1 / fs)
    signal = 0.08 * np.sin(2 * np.pi * 0.35 * time_axis)
    signal += 0.04 * np.sin(2 * np.pi * 0.12 * time_axis + 0.5)

    for beat_time in beat_times:
        signal += -1.8 * np.exp(-0.5 * ((time_axis - beat_time) / 0.018) ** 2)
        signal += 0.35 * np.exp(-0.5 * ((time_axis - (beat_time - 0.16)) / 0.04) ** 2)
        signal += 0.45 * np.exp(-0.5 * ((time_axis - (beat_time + 0.22)) / 0.07) ** 2)

    rng = np.random.default_rng(42)
    signal += 0.03 * rng.standard_normal(len(time_axis))
    return signal


def test_heartrate_analysis_detects_beats_from_noisy_inverted_ecg():
    fs = 250
    beat_times = np.arange(1.0, 9.1, 1.0)
    ecg_signal = _make_noisy_ecg(fs, duration_seconds=10, beat_times=beat_times)
    config = {
        "datainfo": {
            "Fs": fs,
            "segment_labels": ["ecg_segment_1"],
        },
        "display": {
            "heart_rate_show": False,
        },
    }

    result = heartrate_analysis([ecg_signal], config)

    assert result["segments"][0]["detected"] is True
    heart_rate = result["segments"][0]["heart_rate_bpm"]
    assert len(heart_rate) >= 6
    assert np.isclose(np.median(heart_rate), 60.0, atol=6.0)


def test_detect_r_peaks_ignores_weaker_midcycle_artifacts():
    fs = 250
    time_axis = np.arange(0, 10, 1 / fs)
    beat_times = np.arange(1.0, 9.1, 1.0)
    signal = np.zeros_like(time_axis)

    for beat_time in beat_times:
        signal += 2.4 * np.exp(-0.5 * ((time_axis - beat_time) / 0.018) ** 2)
        # Add a weaker broad bump that should not be counted as another R-peak.
        signal += 0.75 * np.exp(-0.5 * ((time_axis - (beat_time + 0.34)) / 0.05) ** 2)

    peaks = _detect_r_peaks(signal, fs)

    assert len(peaks) == len(beat_times)
    detected_times = peaks / fs
    assert np.allclose(detected_times, beat_times, atol=0.05)
