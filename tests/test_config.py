from nm_config import nm_config


def test_config_contains_required_defaults():
    config = nm_config()

    assert config["dataset"]["signal_column"] == 2
    assert config["analysis"]["enabled_modules"] == []
    assert config["analysis"]["rms_time"] > 0
    assert config["analysis"]["rms_gap"] > 0
    assert config["display"]["preprocess_show"] == "on"
