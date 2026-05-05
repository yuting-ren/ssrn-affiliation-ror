import re
import os
import sys
import argparse

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from path_config import apply_dataset_mode, get_dataset_mode

# ---------- processing switch ----------
# SAMPLE_ONLY:
# - "Y": use sample_1000 input
# - "N": use all/full input
SAMPLE_ONLY = "N"

base_sample_input_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_single_author_ror_sample_1000.csv"
base_all_input_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_single_author_ror_all.csv"
base_output_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/dictionary_names.csv"


def simplify_affiliation(text):
    if pd.isna(text):
        return None
    text = str(text).lower()
    text = re.sub(r"\band\b", "", text)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", "", text).strip()
    return text


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create dictionary_names from single-author sample_1000 or all output."
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


dataset_mode = get_dataset_mode()
args = parse_args()
process_scope = normalize_scope(args.scope)

if process_scope == "sample_1000":
    input_path = apply_dataset_mode(base_sample_input_path, dataset_mode)
else:
    input_path = apply_dataset_mode(base_all_input_path, dataset_mode)

output_path = add_scope_tag_to_path(
    apply_dataset_mode(base_output_path, dataset_mode),
    process_scope,
)

if not os.path.exists(input_path):
    raise FileNotFoundError(
        f"Input file not found: {input_path}. "
        "Please generate the corresponding single-author input file first."
    )

df = pd.read_csv(input_path, sep=";")

df_names = pd.DataFrame()
df_names["raw_name"] = df["affiliations"]
df_names = df_names.dropna()
df_names = df_names.drop_duplicates()

df_names["cleaned_name"] = df_names["raw_name"].apply(simplify_affiliation)

df_names.to_csv(output_path, sep=";", index=False)

print("Dictionary names created.")
print(f"Processing mode: {process_scope}")
print("Saved to:", output_path)
print("Number of rows:", len(df_names))
