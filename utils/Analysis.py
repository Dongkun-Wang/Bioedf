"""Analysis dispatch helpers."""

from utils.BandAnalysis import util_band_analysis
from utils.FFT import util_fft
from utils.FreqAnalysis import util_freq_analysis
from utils.Heartrate import heartrate_analysis
from utils.STFT import util_stft
from utils.console import print_section, print_status, print_success


ANALYSIS_HANDLERS = {
    "heart_rate": ("Running heart-rate analysis.", "heartrate_analysis", False),
    "fft": ("Running FFT analysis.", "util_fft", True),
    "stft": ("Running STFT analysis.", "util_stft", True),
    "band": ("Running band analysis.", "util_band_analysis", True),
    "freq_alg": ("Running frequency-domain summary analysis.", "util_freq_analysis", True),
}


def util_analysis(dataset, data_title, config):
    """Run the enabled analysis modules and collect their structured outputs."""
    print_section("ANALYSIS")
    results = {
        "data_title": data_title,
        "segment_labels": config["datainfo"].get("segment_labels", []),
        "modules": {},
    }
    enabled_modules = set(config["analysis"].get("enabled_modules", []))

    for module_name, (message, handler_name, needs_title) in ANALYSIS_HANDLERS.items():
        if module_name not in enabled_modules:
            continue

        print_status(message)
        handler = globals()[handler_name]
        if needs_title:
            results["modules"][module_name] = handler(dataset, data_title, config)
        else:
            results["modules"][module_name] = handler(dataset, config)

    print_success("Analysis finished.")
    return results
