import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("HOME", "/tmp")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/mplconfig")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig")
os.environ.setdefault("MPLBACKEND", "Agg")

from nm_config import nm_config
from utils.Analysis import run_analysis
from utils.LoadDataset import load_dataset
from utils.Preprocess import preprocess_dataset


MODALITY_CONFIG = {
    "eeg": {
        "path": "./著作权材料/示例数据/脑电",
        "title": "copyright_eeg_demo",
    },
    "ecg": {
        "path": "./著作权材料/示例数据/心电",
        "title": "copyright_ecg_demo",
    },
    "emg": {
        "path": "./著作权材料/示例数据/右腿",
        "title": "copyright_emg_demo",
    },
}


def run_demo(modality: str) -> None:
    if modality not in MODALITY_CONFIG:
        raise SystemExit(f"Unsupported modality: {modality}")

    profile = MODALITY_CONFIG[modality]
    Path("/tmp/mplconfig").mkdir(parents=True, exist_ok=True)

    config = nm_config()
    config["fileinfo"]["fullpath"] = profile["path"]
    config["fileinfo"]["result_dir"] = "著作权材料/运行结果_示例"
    config["dataset"]["slice_enabled"] = False
    config["output"]["save_figures"] = True

    for key in list(config["display"].keys()):
        config["display"][key] = False

    dataset, config = load_dataset(config)
    filtered_dataset = preprocess_dataset(config, dataset)
    run_analysis(filtered_dataset, profile["title"], config)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python 著作权材料/generate_demo_assets.py <eeg|ecg|emg>")
    run_demo(sys.argv[1].strip().lower())
