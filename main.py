"""Command-line entry point for the EDF biosignal analysis pipeline."""

from __future__ import annotations

import argparse

from nm_config import nm_config
from utils.Analysis import run_analysis
from utils.LoadDataset import load_dataset
from utils.Preprocess import preprocess_dataset


def _build_parser():
    parser = argparse.ArgumentParser(description="Run EEG / ECG / EMG analysis on EDF data.")
    parser.add_argument(
        "--input",
        default="./data_example/脑电",
        help="EDF file or directory to analyze. Directories may contain EP / EPFilter / EVENT subfolders.",
    )
    parser.add_argument("--slice-start", help='Optional slice start, e.g. "13:48:10" or "2026-03-27 13:48:10".')
    parser.add_argument("--slice-end", help='Optional slice end, e.g. "13:48:20" or "2026-03-27 13:48:20".')
    parser.add_argument("--segment-seconds", type=float, default=60, help="Segment duration in seconds.")
    parser.add_argument("--save-figures", action="store_true", help="Save plots into the result directory.")
    parser.add_argument("--no-display", action="store_true", help="Disable interactive figure display.")
    return parser


def main(argv=None):
    """Run the end-to-end EDF signal analysis pipeline."""
    args = _build_parser().parse_args(argv)

    config = nm_config()
    config["fileinfo"]["fullpath"] = args.input
    config["dataset"]["segment_duration_seconds"] = args.segment_seconds
    config["output"]["save_figures"] = args.save_figures

    if args.slice_start or args.slice_end:
        if not args.slice_start or not args.slice_end:
            raise ValueError("slice-start and slice-end must be provided together.")
        config["dataset"]["slice_enabled"] = True
        config["dataset"]["slice_start"] = args.slice_start
        config["dataset"]["slice_end"] = args.slice_end

    if args.no_display:
        for key in list(config["display"].keys()):
            config["display"][key] = False

    dataset, config = load_dataset(config)
    filtered_dataset = preprocess_dataset(config, dataset)
    return run_analysis(filtered_dataset, None, config)


if __name__ == "__main__":
    main()
