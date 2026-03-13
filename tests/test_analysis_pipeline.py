from utils import Analysis as analysis_module


def test_analysis_dispatches_only_enabled_modules(monkeypatch):
    called = []

    def _make_stub(name):
        def _stub(dataset, *args):
            called.append(name)
            return {"segments": [{"label": name, "count": len(dataset)}]}

        return _stub

    monkeypatch.setattr(analysis_module, "heartrate_analysis", _make_stub("heart_rate"))
    monkeypatch.setattr(analysis_module, "util_fft", _make_stub("fft"))
    monkeypatch.setattr(analysis_module, "util_stft", _make_stub("stft"))
    monkeypatch.setattr(analysis_module, "util_band_analysis", _make_stub("band"))
    monkeypatch.setattr(analysis_module, "util_freq_analysis", _make_stub("freq_alg"))

    config = {
        "analysis": {
            "enabled_modules": ["fft", "band"],
        },
        "datainfo": {
            "segment_labels": ["seg_1"],
        },
    }

    result = analysis_module.util_analysis([[1.0, 2.0, 3.0]], "demo", config)

    assert called == ["fft", "band"]
    assert set(result["modules"].keys()) == {"fft", "band"}
