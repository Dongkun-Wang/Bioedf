# Bioedf

Bioedf is a local EDF biosignal analysis project for EEG, ECG, and EMG. It supports command-line analysis and a local web frontend, automatically infers signal modality, applies modality-specific preprocessing, and generates result figures for downstream review.

## Quick Start

### 1. Get The Code

If you received a zip package:

```bash
cd Bioedf
```

If you are cloning from git:

```bash
git clone git@github.com:Dongkun-Wang/Bioedf.git Bioedf
cd Bioedf
```

### 2. Install `uv`

If `uv` is not installed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Check that it is available:

```bash
uv --version
```

### 3. Create The Environment

```bash
uv venv
uv sync
```

### 4. Start The Frontend

```bash
.venv/bin/python frontend_server.py
```

Open:

[http://127.0.0.1:8765](http://127.0.0.1:8765)

### 5. Frontend Workflow

1. Fill in name, gender, and age.
2. Select EEG, ECG, or EMG.
3. Upload one EDF file.
4. Keep or disable the analysis modules you want to run.
5. Start analysis and review the generated figures.

### 6. Input Rules

- EEG: upload one EDF file containing five channels. The system averages the five channels before analysis.
- ECG: upload one EDF file. If it contains multiple channels, channel 3 is analyzed by default.
- EMG: upload one EDF file and analyze the available channel directly.

### 7. If `uv` Is Not Available

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m ensurepip --upgrade
python -m pip install numpy scipy matplotlib pandas pytest pyedflib
python frontend_server.py
```

## Project Structure

```text
Bioedf/
├── data_example/         # EDF sample data
├── result/               # Generated figures
├── tests/                # Regression tests
├── utils/                # Load, preprocess, and analysis modules
├── webui/                # Frontend static files
├── frontend_server.py    # Local web server
├── main.py               # Command-line entry point
├── nm_config.py          # Runtime defaults and modality inference
└── pyproject.toml        # Project dependencies
```

## What The System Does

- Loads one EDF file or one EDF directory at a time.
- Automatically infers EEG, ECG, or EMG from the input path and channel names.
- Applies the correct default filter ranges for the detected modality.
- Supports optional time slicing for long recordings.
- Splits long recordings into fixed-length segments.
- Runs the matching analysis modules automatically:
  - EEG -> band analysis
  - ECG -> heart-rate and HRV analysis
  - EMG -> FFT, STFT, and sliding-window frequency metrics

## Data Format

The loader accepts:

- one EDF file directly
- one modality directory such as `data_example/脑电`
- one directory containing `EP`, `EPFilter`, and `EVENT` subfolders

When multiple EDF subfolders are present, the loader prioritizes `EP`, falls back to `EPFilter`, and ignores `EVENT`.

Channel rules:

- EEG: one EDF contains five channels and is averaged to `eeg_mean`
- ECG: multi-channel EDF defaults to channel 3
- EMG: available channels are used directly

## Common Commands

Run a custom EDF file:

```bash
.venv/bin/python main.py --input /path/to/your_signal.edf --no-display --save-figures
```

Start the frontend:

```bash
.venv/bin/python frontend_server.py
```

## Selecting A Time Window

You can limit analysis to a time slice:

```bash
.venv/bin/python main.py \
  --input ./data_example/脑电 \
  --slice-start "13:48:12" \
  --slice-end "13:48:20" \
  --no-display \
  --save-figures
```

Supported formats:

- Time only: `"17:17:10"`
- Full datetime: `"2024-06-26 17:17:10"`

## Modality Defaults

Default band-pass ranges:

- EEG -> `0.4-60 Hz`
- ECG -> `5-25 Hz`
- EMG -> `20-250 Hz`

Default module mapping:

- EEG -> `BandAnalysis`
- ECG -> `Heartrate`
- EMG -> `FFT`, `STFT`, `FreqAnalysis`

Important behavior:

- EEG is intentionally reduced to one averaged analysis channel.
- ECG defaults to the third channel when multiple channels are present.
- Modality inference is automatic by design.

## Main Modules

- `utils/LoadDataset.py`: EDF discovery, modality inference, channel selection, segmentation
- `utils/Preprocess.py`: band-pass and band-stop filtering
- `utils/BandAnalysis.py`: EEG band power and derived indices
- `utils/Heartrate.py`: ECG heart rate and HRV metrics
- `utils/FFT.py`: EMG FFT spectrum
- `utils/STFT.py`: EMG spectrogram and energy estimate
- `utils/FreqAnalysis.py`: EMG RMS, MPF, MDF trend analysis
- `frontend_server.py`: local API and result-image serving

## Output

Saved figures are organized under:

```text
result/
└── <MODALITY>/
    └── <module>/
```

Typical runtime options live in [`nm_config.py`](/Users/teddy/Desktop/Bioedf/nm_config.py):

- `dataset`: input discovery, slicing, segmentation
- `preprocess`: filter toggles, ranges, and orders
- `analysis`: module parameters
- `display`: interactive plotting switches
- `output`: figure export settings

## Notes

- Python `3.12` is recommended.
- `uv sync` installs dependencies from `pyproject.toml` and `uv.lock`.
- The frontend is fully local after dependencies are installed.
- `data/`, `docs/`, and `result/` are intentionally ignored in git.
- Historical behavior such as EEG averaging and ECG peak detection should not be changed lightly if reproducibility matters.
