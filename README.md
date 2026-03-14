# Bioprocess

Bioprocess is a lightweight offline biosignal analysis pipeline for EEG, ECG, and EMG recordings stored as headerless CSV files. It loads raw signals, infers the signal modality automatically, applies modality-specific filtering, runs the appropriate analyses, and optionally visualizes or saves the results.

## Fast Onboarding

If you need to understand the project quickly, read the files in this order:

1. [main.py](/Users/teddy/Desktop/Bioprocess/main.py)
2. [nm_config.py](/Users/teddy/Desktop/Bioprocess/nm_config.py)
3. [utils/LoadDataset.py](/Users/teddy/Desktop/Bioprocess/utils/LoadDataset.py)
4. [utils/Preprocess.py](/Users/teddy/Desktop/Bioprocess/utils/Preprocess.py)
5. [utils/Analysis.py](/Users/teddy/Desktop/Bioprocess/utils/Analysis.py)

That sequence gives the full runtime flow from input selection to analysis dispatch.

## What The System Does

- Loads one directory of CSV recordings at a time.
- Automatically infers whether the incoming data is EEG, ECG, or EMG.
- Applies the correct default filter ranges for the detected modality.
- Supports optional time-window slicing when you only want to inspect part of a long recording.
- Splits long recordings into fixed-length segments for downstream analysis.
- Runs the matching analysis modules automatically:
  - EEG -> band analysis
  - ECG -> heart-rate and HRV analysis
  - EMG -> FFT, STFT, and sliding-window frequency metrics

## Pipeline Overview

The runtime pipeline is:

1. `main.py` selects the data directory and optional time window.
2. `LoadDataset.py` reads all CSV files in that directory.
3. The signal modality is inferred automatically from folder and file names.
4. Modality-specific defaults are injected into the config:
   - filter band
   - channel handling strategy
   - enabled analysis modules
5. EEG is averaged from five channels to a single analysis channel.
6. The signal is sliced, segmented, filtered, and then dispatched to the enabled analyses.
7. Figures and tables are shown or saved based on `display` and `output`.

## Highlights

- Automatic modality inference with support for both English folder names and legacy directory names.
- EEG multi-channel averaging to a single analysis channel before downstream processing.
- Structured analysis outputs returned from every module.
- Consistent terminal reporting and plot styling through shared UI helpers instead of ad hoc formatting.
- Plotting and result saving controlled through a single configuration object.
- Figure export goes through one shared output pipeline, so saved plots land in a predictable result tree.
- Regression tests covering config defaults, dataset loading, analysis dispatch, and ECG peak detection.

## Project Structure

```text
Bioprocess/
├── data/                  # Input signal directories (gitignored)
├── docs/                  # Local planning notes (gitignored)
├── result/                # Saved plots and CSV outputs (gitignored)
├── tests/                 # Regression tests
├── utils/
│   ├── Analysis.py
│   ├── BandAnalysis.py
│   ├── FFT.py
│   ├── FreqAnalysis.py
│   ├── Heartrate.py
│   ├── LoadDataset.py
│   ├── Preprocess.py
│   ├── STFT.py
│   └── ui.py
├── main.py                # Entry point
├── nm_config.py           # Defaults and modality inference
└── requirements.txt
```

## Installation

## Clone The Repository

Clone the project:


```bash
git clone git@github.com:Dongkun-Wang/Bioprocess.git
```

Then create and activate a virtual environment, and install dependencies:

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Data Format

Each CSV file is expected to be headerless and contain at least three columns:

- Column 0: timestamp in milliseconds
- Column 1: auxiliary index or unused value
- Column 2: signal amplitude

The loader reads column `0` for time and column `2` for signal by default. You can change these in `nm_config.py` if needed.

If you need sample data, please contact the author Teddy at `Dongkun.wang@outlook.com`.

## How To Run

Edit [main.py](/Users/teddy/Desktop/Bioprocess/main.py) and set the data directory you want to analyze. By default it points to the EEG directory directly:

```python
config["fileinfo"]["fullpath"] = "./data/脑电"
```

Then run:

```bash
python main.py
```

## Selecting A Time Window

If a recording is long and you only want a slice of it, enable the time window in [main.py](/Users/teddy/Desktop/Bioprocess/main.py):

```python
config["dataset"]["slice_enabled"] = True
config["dataset"]["slice_start"] = "17:17:10"
config["dataset"]["slice_end"] = "17:19:30"
```

Supported formats:

- Time only: `"17:17:10"`
- Full datetime: `"2024-06-26 17:17:10"`

## Automatic Modality Rules

The system uses directory names and file names to infer the signal type:

- EEG -> band-pass `1-60 Hz`
- ECG -> band-pass `1-10 Hz`
- EMG -> band-pass `1-250 Hz`

Automatic analysis selection is also tied to the inferred modality:

- EEG -> `BandAnalysis`
- ECG -> `Heartrate`
- EMG -> `FFT`, `STFT`, and `FreqAnalysis`

Important:

- Automatic modality inference is the only supported workflow.
- Manual modality selection is intentionally not part of the current design.
- EEG is intentionally reduced to one averaged channel before downstream analysis.

## Output Controls

Runtime behavior is configured through [nm_config.py](/Users/teddy/Desktop/Bioprocess/nm_config.py):

- `dataset`: loading, slicing, segmentation, and sampling-rate settings
- `preprocess`: filter toggles and filter orders
- `analysis`: algorithm parameters
- `display`: plotting switches
- `output`: figure export and result-file saving switches

Typical export settings:

```python
config["output"]["save_figures"] = True
config["output"]["figure_format"] = "png"
config["output"]["figure_dpi"] = 320
```

Saved figures are organized automatically under:

```text
result/
└── <MODALITY>/
    └── <module>/
```

## Common Edit Points

The most common places to change behavior are:

- [main.py](/Users/teddy/Desktop/Bioprocess/main.py)
  - change the target data directory
  - enable or disable a time slice
- [nm_config.py](/Users/teddy/Desktop/Bioprocess/nm_config.py)
  - change segmentation length
  - change figure export settings
  - adjust filter order
  - tune STFT overlap or EMG sliding-window parameters

The most common runtime settings are:

```python
config["fileinfo"]["fullpath"] = "./data/脑电"
config["dataset"]["slice_enabled"] = True
config["dataset"]["slice_start"] = "17:17:10"
config["dataset"]["slice_end"] = "17:19:30"
config["output"]["save_figures"] = True
```

## Main Analysis Modules

- `BandAnalysis.py`: EEG band power, relative power, spectral centroid, entropy, concentration, relaxation
- `Heartrate.py`: ECG R-peak detection, RR intervals, heart rate, SDNN, RMSSD
- `FFT.py`: whole-segment FFT spectrum
- `STFT.py`: spectrograms with energy and calorie estimation
- `FreqAnalysis.py`: sliding-window RMS, MPF, and MDF, mainly useful for EMG
  - The returned MDF values stay raw.
  - The plotted MDF figure adds a light smoothing trend only for visualization.

## Window Choices

The default window settings are chosen to balance temporal detail and stable frequency estimates:

- EEG `BandAnalysis`
  - Uses about a `1 s` window with `50%` overlap.
  - This is a practical default for theta/alpha/beta/gamma tracking.
- ECG `Heartrate`
  - Does not use a main sliding analysis window.
  - The core output comes from R-peak detection and RR intervals instead.
- EMG `FreqAnalysis`
  - Uses a `1.0 s` window and `0.5 s` step.
  - This is a stable default for RMS, MPF, and MDF trends.
- EMG `STFT`
  - Uses an approximately `0.5 s` window derived from the sampling rate and `50%` overlap.
  - This keeps the spectrogram responsive to short muscle-activation changes.
- MDF trend line
  - The raw MDF result is kept unchanged.
  - The plotted red trend line is a display-only moving average with a default width of `5 s`.

## Numerical And Design Notes

These details matter if you want to preserve behavior:

- The sampling-rate scaling formula is intentionally preserved from the original project.
- EEG averaging to a single channel is intentional and affects all downstream EEG analyses.
- STFT now focuses on spectrogram visualization plus energy estimation.
- `FreqAnalysis` keeps raw `RMS`, `MPF`, and `MDF`, but only `RMS + MDF` are plotted by default.
- The red MDF line is a display-only trend, not a replacement for raw MDF.
- ECG peak detection has been made more robust than the original version, so heart-rate and HRV results may differ slightly from the legacy code.

If exact historical reproduction is important, review ECG peak handling and filter settings first.

## Things Not To Change Lightly

- `dataset["sampling_rate_scale"]`
- modality keywords in `SIGNAL_PROFILES`
- EEG `channel_strategy = "average_to_single"`
- ECG R-peak detection logic in [utils/Heartrate.py](/Users/teddy/Desktop/Bioprocess/utils/Heartrate.py)
- automatic module mapping in `SIGNAL_PROFILES`

## Testing

Run the regression suite with:

```bash
python -m pytest -q
```

## Notes

- `data/`, `docs/`, and `result/` are intentionally ignored in git.
- The project keeps compatibility with the current on-disk dataset naming scheme.
- The sampling-rate scaling formula is preserved from the original project so historical results remain comparable.
- Results are shown interactively when the corresponding `display` switches are turned on.
