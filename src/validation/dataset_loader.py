import json
import os
import random

DATASET_DIR = os.path.join(os.path.dirname(__file__), "datasets")
STATE_FILE = os.path.join(DATASET_DIR, "state.json")


def _load_json(filename):
    path = os.path.join(DATASET_DIR, filename)
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def _load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def _save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=4)


def load_dataset(filename, sample_size=10, strategy="sequential"):
    dataset_path = os.path.join(DATASET_DIR, filename)
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset '{filename}' not found.")

    dataset = _load_json(filename)
    total = len(dataset)

    if strategy == "all":
        return dataset

    if strategy == "random":
        return random.sample(dataset, min(sample_size, total))

    if strategy == "sequential":
        state = _load_state()
        start = state.get(filename, {}).get("last_index", 0)
        end = start + sample_size

        if end <= total:
            samples = dataset[start:end]
        else:
            samples = dataset[start:]
            remaining = sample_size - len(samples)
            samples.extend(dataset[:remaining])

        state[filename] = {"last_index": end % total}
        _save_state(state)
        return samples

    raise ValueError(f"Unknown strategy: {strategy}")
