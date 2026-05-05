import argparse
import os
import re
import sys

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from path_config import apply_dataset_mode, get_dataset_mode

SAMPLE_ONLY = "N"
SAMPLE_SIZE = 1000

base_input_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_single_author_ror.csv"
base_output_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_single_author_ror.csv"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create single-author sample_1000 or all output."
    )
    parser.add_argument(
        "--scope",
        choices=["Y", "N", "sample_1000", "all"],
        default=SAMPLE_ONLY,
        help='Use "Y" for sample_1000, "N" for all. "sample_1000" and "all" are also supported.',
    )
    return parser.parse_args()


def add_scope_tag_to_path(path, scope_tag):
    root, ext = os.path.splitext(path)
    return f"{root}_{scope_tag}{ext}"


def normalize_scope(scope_value):
    normalized = str(scope_value).strip()
    if normalized.upper() == "Y":
        return "sample_1000"
    if normalized.upper() == "N":
        return "all"
    if normalized in {"sample_1000", "all"}:
        return normalized
    raise ValueError(f"Unsupported scope: {scope_value}")


def get_visible_single_author_columns(frame):
    hidden_patterns = [
        r"author_(?:[2-9]|[1-9][0-9]|1[0-9]{2,})_(id|last_name|first_name|url)$",
        r"author_\d+_institution$",
        r"author_\d+_ror_url$",
        r"author_\d+_ror_id$",
        r"author_\d+_ror_status$",
        r"author_\d+_country$",
        r"^ror_status$",
    ]

    visible_columns = []
    for column in frame.columns:
        if any(re.match(pattern, column) for pattern in hidden_patterns):
            continue
        visible_columns.append(column)
    return visible_columns


dataset_mode = get_dataset_mode()
input_path = apply_dataset_mode(base_input_path, dataset_mode)
args = parse_args()
process_scope = normalize_scope(args.scope)
output_path = add_scope_tag_to_path(
    apply_dataset_mode(base_output_path, dataset_mode),
    process_scope,
)

df_view = pd.read_csv(input_path, sep=";")
if process_scope == "sample_1000":
    df_output = df_view.head(SAMPLE_SIZE).copy()
else:
    df_output = df_view.copy()

df_output = df_output[get_visible_single_author_columns(df_output)]
df_output.to_csv(output_path, sep=";", index=False)

print(f"Processing mode: {process_scope}")
print("Saved to:", output_path)
print("Number of rows:", len(df_output))
