from nm_config import nm_config
from utils.Analysis import run_analysis
from utils.LoadDataset import load_dataset
from utils.Preprocess import preprocess_dataset


def main():
    """Run the end-to-end signal analysis pipeline."""
    config = nm_config()
    config["fileinfo"]["fullpath"] = "./data/右腿"

    # Enable these lines when you want to inspect only part of a recording.
    config["dataset"]["slice_enabled"] = True
    config["dataset"]["slice_start"] = "17:17:10"
    config["dataset"]["slice_end"] = "17:19:50"

    dataset, config = load_dataset(config)
    filtered_dataset = preprocess_dataset(config, dataset)
    return run_analysis(filtered_dataset, "filtered_dataset", config)


if __name__ == "__main__":
    main()
