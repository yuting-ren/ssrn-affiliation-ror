"""
Purpose:
- Keep only rows with exactly two authors from the main abstract dataset.
- Save a tagged two-author sample dataset.
- If affiliations matches dictionary_names.raw_name exactly,
  replace it with dictionary_names.cleaned_name and save the cleaned result.
- Count "and" in affiliations, and when there is exactly one "and",
  split affiliations into two institutions.

Input:
- outputs/db_info_abstract.csv
- outputs/dictionary_names.csv

Output:
- outputs/db_info_abstract_two_authors_<scope>.csv
- outputs/db_info_abstract_two_authors_dic_names_<scope>.csv
- outputs/db_info_abstract_two_authors_dic_names_loop_report_<scope>.csv
"""

import argparse
import os
import re
import sys

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from path_config import apply_dataset_mode, get_dataset_mode

# ---------- processing switch ----------
# SAMPLE_ONLY:
# - "Y": process only the first 1000 two-author records
# - "N": process all two-author records
SAMPLE_ONLY = "Y"
SAMPLE_SIZE = 1000
MAX_LOOP_ITERATIONS = 10

# ---------- paths ----------
base_file_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract.csv"
base_dictionary_names_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/dictionary_names.csv"
base_sample_output_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_two_authors.csv"
base_output_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_two_authors_dic_names.csv"
base_report_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_two_authors_dic_names_loop_report.csv"

dataset_mode = get_dataset_mode()
file_path = apply_dataset_mode(base_file_path, dataset_mode)
dictionary_names_path = apply_dataset_mode(base_dictionary_names_path, dataset_mode)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Keep two-author rows and replace matched affiliations using dictionary_names."
    )
    parser.add_argument(
        "--scope",
        choices=["Y", "N", "sample_1000", "all"],
        default=SAMPLE_ONLY,
        help='Use "Y" for sample_1000, "N" for all. "sample_1000" and "all" are also supported.',
    )
    return parser.parse_args()


def normalize_scope(scope_value):
    normalized = str(scope_value).strip()
    if normalized.upper() == "Y":
        return "sample_1000"
    if normalized.upper() == "N":
        return "all"
    if normalized in {"sample_1000", "all"}:
        return normalized
    raise ValueError(f"Unsupported scope: {scope_value}")


def add_scope_tag_to_path(path, scope_tag):
    root, ext = os.path.splitext(path)
    return f"{root}_{scope_tag}{ext}"


def split_affiliations_on_and(text):
    if pd.isna(text):
        return (None, None)

    parts = re.split(r"\sand\s", str(text), maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        return (None, None)

    return (parts[0].strip(), parts[1].strip())


def simplify_affiliation(text):
    if pd.isna(text):
        return None
    text = str(text).lower()
    text = re.sub(r"\band\b", "", text)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", "", text).strip()
    return text


def get_visible_two_author_columns(frame):
    return [
        column
        for column in frame.columns
        if not re.match(
            r"author_(?:[3-9]|[1-9][0-9]|1[0-9]{2,})_(id|last_name|first_name|url)$",
            column,
        )
    ]


def replace_from_dictionary(text, mapping):
    if pd.isna(text):
        return None

    value = str(text)
    if value.strip() == "":
        return value

    updated = value
    for raw_name, cleaned_name in mapping.items():
        if raw_name and raw_name in updated:
            updated = updated.replace(raw_name, cleaned_name)

    return updated


def build_raw_to_cleaned_mapping(dictionary_frame):
    return dict(
        sorted(
            zip(dictionary_frame["raw_name"], dictionary_frame["cleaned_name"]),
            key=lambda item: len(item[0]),
            reverse=True,
        )
    )


def normalize_dictionary_names(dictionary_frame):
    required_cols = {"raw_name", "cleaned_name"}
    if not required_cols.issubset(dictionary_frame.columns):
        raise ValueError(
            f"dictionary_names must contain columns {sorted(required_cols)}. "
            f"Found: {dictionary_frame.columns.tolist()}"
        )

    dictionary_frame = dictionary_frame.dropna(subset=["raw_name"]).copy()
    dictionary_frame["raw_name"] = dictionary_frame["raw_name"].astype(str).str.strip()
    dictionary_frame["cleaned_name"] = (
        dictionary_frame["cleaned_name"].fillna("").astype(str).str.strip()
    )
    dictionary_frame = dictionary_frame[dictionary_frame["raw_name"] != ""]
    dictionary_frame = dictionary_frame.drop_duplicates(subset=["raw_name"], keep="first")
    return dictionary_frame


def keep_two_author_rows(frame):
    return frame[(frame["author_2_id"].notna()) & (frame["author_3_id"].isna())].copy()


def load_two_author_data(input_path, scope, sample_size):
    if scope == "all":
        df_all = pd.read_csv(input_path, sep=";")
        df_all.columns = df_all.columns.str.strip()
        return keep_two_author_rows(df_all)

    chunks = []
    collected = 0

    for chunk in pd.read_csv(input_path, sep=";", chunksize=50000):
        chunk.columns = chunk.columns.str.strip()
        two_author_chunk = keep_two_author_rows(chunk)

        if two_author_chunk.empty:
            continue

        remaining = sample_size - collected
        if remaining <= 0:
            break

        sampled_chunk = two_author_chunk.head(remaining).copy()
        chunks.append(sampled_chunk)
        collected += len(sampled_chunk)

        if collected >= sample_size:
            break

    if not chunks:
        return pd.DataFrame()

    return pd.concat(chunks, ignore_index=True)


args = parse_args()
process_scope = normalize_scope(args.scope)
sample_output_path = add_scope_tag_to_path(
    apply_dataset_mode(base_sample_output_path, dataset_mode),
    process_scope,
)
output_path = add_scope_tag_to_path(
    apply_dataset_mode(base_output_path, dataset_mode),
    process_scope,
)
report_path = add_scope_tag_to_path(
    apply_dataset_mode(base_report_path, dataset_mode),
    process_scope,
)

# ---------- load ----------
df = load_two_author_data(file_path, process_scope, SAMPLE_SIZE)
dictionary_names = pd.read_csv(dictionary_names_path, sep=";")
dictionary_names.columns = dictionary_names.columns.str.strip()
dictionary_names = normalize_dictionary_names(dictionary_names)

if process_scope == "sample_1000":
    df = df.head(SAMPLE_SIZE).copy()
    print(f"Processing mode: first {min(len(df), SAMPLE_SIZE)} two-author rows")
else:
    print(f"Processing mode: all two-author rows ({len(df)} rows)")

df["process_scope"] = process_scope

# ---------- save sampled two-author database ----------
df_sample_view = df[get_visible_two_author_columns(df)]
df_sample_view.to_csv(sample_output_path, sep=";", index=False)
print("Saved two-author sample to:", sample_output_path)

# ---------- replace using dictionary_names ----------
df["affiliations_original"] = df["affiliations"]

df["and_count_original"] = (
    df["affiliations_original"]
    .fillna("")
    .str.lower()
    .str.count(r"\sand\s")
)

# ---------- iterative replace / split / dictionary update loop ----------
loop_iterations_run = 0
total_new_dictionary_rows_added = 0
last_split_mask_sum = 0
last_replaced_sum = 0
loop_report = []

for iteration in range(1, MAX_LOOP_ITERATIONS + 1):
    raw_to_cleaned = build_raw_to_cleaned_mapping(dictionary_names)

    cleaned_col = "affiliations_dic_names_cleaned" if iteration == 1 else f"affiliations_dic_names_cleaned_round{iteration}"
    replaced_col = "dic_names_replaced" if iteration == 1 else f"dic_names_replaced_round{iteration}"
    and_count_col = "and_count" if iteration == 1 else f"and_count_round{iteration}"
    split_1_col = "author1_affi_split" if iteration == 1 else f"author1_affi_split_round{iteration}"
    split_2_col = "author2_affi_split" if iteration == 1 else f"author2_affi_split_round{iteration}"

    df[cleaned_col] = df["affiliations_original"].apply(
        lambda x: replace_from_dictionary(x, raw_to_cleaned)
    )
    df[replaced_col] = (
        df["affiliations_original"].notna()
        & (df["affiliations_original"].astype(str).str.strip() != "")
        & (
            df["affiliations_original"].astype(str).str.strip()
            != df[cleaned_col].astype(str).str.strip()
        )
    )
    df[and_count_col] = (
        df[cleaned_col]
        .fillna("")
        .str.lower()
        .str.count(r"\sand\s")
    )

    df[split_1_col] = None
    df[split_2_col] = None

    split_mask = df[and_count_col] == 1
    split_pairs = df.loc[split_mask, cleaned_col].apply(split_affiliations_on_and)
    df.loc[split_mask, split_1_col] = split_pairs.apply(lambda x: x[0]).values
    df.loc[split_mask, split_2_col] = split_pairs.apply(lambda x: x[1]).values

    split_names = pd.concat(
        [
            df.loc[split_mask, split_1_col],
            df.loc[split_mask, split_2_col],
        ],
        ignore_index=True,
    ).dropna()
    split_names = split_names.astype(str).str.strip()
    split_names = split_names[split_names != ""]
    split_names = split_names.drop_duplicates()

    existing_raw_names = set(dictionary_names["raw_name"].astype(str).str.strip())
    new_split_names = split_names[~split_names.isin(existing_raw_names)].copy()

    new_rows_this_round = 0
    if not new_split_names.empty:
        new_dictionary_rows = pd.DataFrame({"raw_name": new_split_names})
        new_dictionary_rows["cleaned_name"] = new_dictionary_rows["raw_name"].apply(
            simplify_affiliation
        )
        dictionary_names = pd.concat([dictionary_names, new_dictionary_rows], ignore_index=True)
        dictionary_names = normalize_dictionary_names(dictionary_names)
        new_rows_this_round = len(new_dictionary_rows)
        total_new_dictionary_rows_added += new_rows_this_round

    loop_iterations_run = iteration
    last_split_mask_sum = int(split_mask.sum())
    last_replaced_sum = int(df[replaced_col].sum())
    loop_report.append(
        {
            "iteration": iteration,
            "target_authors": 2,
            "scope": process_scope,
            "dic_names_replaced": int(df[replaced_col].sum()),
            "and_count_eq_1": int((df[and_count_col] == 1).sum()),
            "rows_split": int(split_mask.sum()),
            "new_dictionary_names_rows_added": int(new_rows_this_round),
        }
    )

    if new_rows_this_round == 0:
        break

dictionary_names.to_csv(dictionary_names_path, sep=";", index=False)

final_cleaned_col = (
    "affiliations_dic_names_cleaned"
    if loop_iterations_run == 1
    else f"affiliations_dic_names_cleaned_round{loop_iterations_run}"
)
df["affiliations"] = df[final_cleaned_col]

# ---------- save ----------
df_output_view = df[get_visible_two_author_columns(df)]
df_output_view.to_csv(output_path, sep=";", index=False)
pd.DataFrame(loop_report).to_csv(report_path, sep=";", index=False)

print("Saved cleaned output to:", output_path)
print("Saved loop report to:", report_path)
print("Rows processed:", len(df))
print("Loop iterations run:", int(loop_iterations_run))
print("Affiliations replaced in final round:", int(last_replaced_sum))
print('Rows with exactly one "and" in final round:', int(last_split_mask_sum))
print("Total new dictionary_names rows added:", int(total_new_dictionary_rows_added))
print("\nLoop report:")
for item in loop_report:
    print(
        f"Round {item['iteration']}: "
        f"dic_names_replaced={item['dic_names_replaced']}, "
        f"and_count_eq_1={item['and_count_eq_1']}, "
        f"rows_split={item['rows_split']}, "
        f"new_dictionary_names_rows_added={item['new_dictionary_names_rows_added']}"
    )
