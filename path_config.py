import os

VALID_DATASET_MODES = {"full", "toy"}


def get_dataset_mode(default="full"):
    mode = os.getenv("DATASET_MODE", default).strip().lower()
    if mode not in VALID_DATASET_MODES:
        raise ValueError(f"Unsupported DATASET_MODE: {mode}")
    return mode


def apply_dataset_mode(path, mode=None):
    mode = mode or get_dataset_mode()
    root, ext = os.path.splitext(path)
    if mode == "toy":
        return f"{root}_toydata{ext}"
    return path
