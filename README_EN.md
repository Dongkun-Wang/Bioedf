<p align="center">
  <img src=".github/assets/bioedf-banner.svg" alt="Bioedf banner" width="100%" />
</p>

<p align="center">
  <a href="README_CN.md">中文</a>
  ·
  <strong>English</strong>
  ·
  <a href="README.md">Home</a>
</p>

# Bioedf

Bioedf is a local EDF biosignal analysis project for EEG, ECG, and EMG. It supports both command-line execution and a local web frontend. The pipeline automatically infers signal modality, applies modality-specific preprocessing, and generates result figures for downstream review.

## Quick Start

### 1. Get the code

```bash
git clone git@github.com:Dongkun-Wang/Bioedf.git Bioedf
cd Bioedf
```

### 2. Install `uv`

If `uv` is not installed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify the installation:

```bash
uv --version
```

### 3. Create the environment

```bash
uv venv
uv sync
```

### 4. Start the frontend

```bash
.venv/bin/python frontend_server.py
```

Open:

[http://127.0.0.1:8765](http://127.0.0.1:8765)

### 5. Frontend workflow

1. Fill in the basic user information.
2. Select EEG, ECG, or EMG.
3. Upload one EDF file.
4. Keep all modules enabled by default, or disable any module manually.
5. Start the analysis and review the summary and result figures.

### 6. Input rules

- EEG: upload one EDF file containing five channels; the system averages them before analysis.
- ECG: upload one EDF file; if it contains multiple channels, channel 3 is analyzed by default.
- EMG: upload one EDF file and analyze the available channel directly.

## Highlights

- One project for EEG, ECG, and EMG EDF analysis
- Local web UI for upload, module selection, and figure review
- EDF-aware channel handling for all supported modalities
- Built-in preprocessing, segmentation, plotting, and export
- Ready-to-run sample EDF data under `data_example/`

## Data Rules

The loader accepts:

- one EDF file directly
- one modality directory such as `data_example/脑电`
- one directory containing `EP`, `EPFilter`, and `EVENT` subfolders

When multiple subfolders exist, the loader prioritizes `EP`, then `EPFilter`, and ignores `EVENT`.

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

Run tests:

```bash
.venv/bin/python -m pytest -q
```

## Select a Time Window

To analyze only a slice of a recording:

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

## Default Analysis Settings

Default band-pass ranges:

- EEG: `0.4-60 Hz`
- ECG: `5-25 Hz`
- EMG: `20-250 Hz`

Default module mapping:

- EEG: `BandAnalysis`
- ECG: `Heartrate`
- EMG: `FFT`, `STFT`, `FreqAnalysis`

Important behavior:

- EEG is intentionally reduced to one averaged analysis channel.
- ECG defaults to the third channel when multiple channels are present.
- Modality inference is automatic.

## Main Modules

- `utils/LoadDataset.py`: EDF discovery, modality inference, channel selection, segmentation
- `utils/Preprocess.py`: band-pass and band-stop filtering
- `utils/BandAnalysis.py`: EEG band power and derived indices
- `utils/Heartrate.py`: ECG heart-rate and HRV analysis
- `utils/FFT.py`: EMG FFT spectrum analysis
- `utils/STFT.py`: EMG time-frequency analysis
- `utils/FreqAnalysis.py`: EMG RMS, MPF, and MDF trend analysis
- `frontend_server.py`: local API and result-image serving

## Project Structure

```text
Bioedf/
├── data_example/         # EDF sample data
├── tests/                # Regression tests
├── utils/                # Loading, preprocessing, and analysis modules
├── webui/                # Frontend static files
├── frontend_server.py    # Local frontend server
├── main.py               # CLI entry point
├── nm_config.py          # Runtime defaults
└── pyproject.toml        # Project dependencies
```

## Output

Generated figures are typically saved under:

```text
result/
└── <MODALITY>/
    └── <module>/
```

Typical runtime options live in [`nm_config.py`](/Users/teddy/Desktop/Bioedf/nm_config.py):

- `dataset`: discovery, slicing, segmentation
- `preprocess`: filter toggles, ranges, and orders
- `analysis`: module parameters
- `display`: interactive plotting switches
- `output`: export settings

## Notes

- Python `3.12` is recommended.
- `uv sync` installs dependencies from `pyproject.toml` and `uv.lock`.
- The frontend runs fully locally after dependencies are installed.
- `data/`, `docs/`, and `result/` are intentionally ignored in git.
- If reproducibility matters, avoid changing the EEG averaging rule and ECG peak-detection logic casually.
