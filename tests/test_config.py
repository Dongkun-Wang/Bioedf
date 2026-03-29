from nm_config import nm_config


def test_config_contains_required_defaults():
    config = nm_config()

    assert config["fileinfo"]["filetype"] == ".edf"
    assert config["dataset"]["preferred_signal_dirs"] == ["EP", "EPFilter"]
    assert config["dataset"]["ecg_channel_index"] == 3
    assert config["analysis"]["enabled_modules"] == []
    assert config["analysis"]["rms_time"] > 0
    assert config["analysis"]["rms_gap"] > 0
    assert config["display"]["preprocess_show"] is True
