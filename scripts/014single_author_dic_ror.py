import argparse
import csv
import os
import re
import sys

import pandas as pd
from tqdm import tqdm

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from path_config import apply_dataset_mode, get_dataset_mode

SAMPLE_ONLY = "Y"

base_sample_input_path = os.path.join(
    PROJECT_ROOT, "outputs", "db_info_abstract_single_author_ror_sample_1000.csv"
)
base_all_input_path = os.path.join(
    PROJECT_ROOT, "outputs", "db_info_abstract_single_author_ror_all.csv"
)
base_dic_new_path = os.path.join(PROJECT_ROOT, "outputs", "dic_new.csv")


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Fill single-author ROR info from dic_new.csv using affiliations "
            "(cleaned_name first, raw_name fallback)."
        )
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


def simplify_affiliation(text):
    if pd.isna(text):
        return None
    text = str(text).lower()
    text = re.sub(r"\band\b", "", text)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", "", text).strip()
    return text


def normalize_match_key(value):
    if pd.isna(value):
        return None
    text = str(value).strip().lower()
    if text == "":
        return None
    return text


def load_dic_new(dic_new_path):
    required_cols = {"raw_name", "cleaned_name", "ror_link", "country", "ror_status"}

    attempts = [
        {"sep": ";", "encoding": "utf-8"},
        {"sep": ";", "encoding": "utf-8-sig"},
        {"sep": ";", "encoding": "latin1"},
        {"sep": ",", "encoding": "utf-8"},
        {"sep": ",", "encoding": "utf-8-sig"},
        {"sep": ",", "encoding": "latin1"},
    ]

    for option in attempts:
        try:
            df = pd.read_csv(dic_new_path, sep=option["sep"], encoding=option["encoding"])
        except Exception:
            continue

        df.columns = df.columns.astype(str).str.strip()
        if required_cols.issubset(set(df.columns)):
            return df

        if len(df.columns) == 1:
            packed_col = df.columns[0]
            packed_lines = df[packed_col].astype(str).tolist()
            parsed_rows = [next(csv.reader([line], delimiter=",", quotechar='"')) for line in packed_lines]

            if parsed_rows:
                max_len = max(len(r) for r in parsed_rows)
                if max_len >= 6:
                    normalized_rows = []
                    for row in parsed_rows:
                        if len(row) < 6:
                            row = row + [None] * (6 - len(row))
                        elif len(row) > 6:
                            overflow = ",".join(row[: len(row) - 5])
                            row = [overflow] + row[len(row) - 5 :]
                        normalized_rows.append(row[:6])

                    expected = ["raw_name", "cleaned_name", "ror_name", "ror_link", "country", "ror_status"]
                    if [str(x).strip().lower() for x in normalized_rows[0]] == expected:
                        normalized_rows = normalized_rows[1:]

                    expanded = pd.DataFrame(normalized_rows, columns=expected)
                    if required_cols.issubset(set(expanded.columns)):
                        return expanded

    raise ValueError(
        f"Unable to parse dic_new.csv with required columns {sorted(required_cols)}: {dic_new_path}"
    )


def build_first_value_lookup(dic_frame, key_col):
    frame = dic_frame.copy()
    frame[key_col] = frame[key_col].apply(normalize_match_key)
    frame = frame[frame[key_col].notna()].copy()
    frame = frame.drop_duplicates(subset=[key_col], keep="first")
    return {
        row[key_col]: (
            row.get("ror_link"),
            row.get("country"),
            row.get("ror_status"),
        )
        for _, row in frame.iterrows()
    }


def derive_output_path_from_input(input_path):
    folder, filename = os.path.split(input_path)
    if "_ror_" in filename:
        out_name = filename.replace("_ror_", "_dic_names_")
    elif filename.endswith("_ror.csv"):
        out_name = filename.replace("_ror.csv", "_dic_names.csv")
    else:
        root, ext = os.path.splitext(filename)
        out_name = f"{root}_dic_names{ext}"
    return os.path.join(folder, out_name)


def main():
    dataset_mode = get_dataset_mode()
    args = parse_args()
    process_scope = normalize_scope(args.scope)

    if process_scope == "sample_1000":
        input_path = apply_dataset_mode(base_sample_input_path, dataset_mode)
    else:
        input_path = apply_dataset_mode(base_all_input_path, dataset_mode)

    dic_new_path = apply_dataset_mode(base_dic_new_path, dataset_mode)
    output_path = derive_output_path_from_input(input_path)

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if not os.path.exists(dic_new_path):
        raise FileNotFoundError(f"dic_new file not found: {dic_new_path}")

    df = pd.read_csv(input_path, sep=";")
    df.columns = df.columns.str.strip()

    if "affiliations" not in df.columns:
        raise ValueError("Input must contain 'affiliations' column")

    df["author1_affi"] = df["affiliations"]

    dic_new = load_dic_new(dic_new_path)
    cleaned_lookup = build_first_value_lookup(dic_new, "cleaned_name")
    raw_lookup = build_first_value_lookup(dic_new, "raw_name")

    tqdm.pandas(desc="single cleaned key")
    clean_keys = (
        df["author1_affi"]
        .progress_apply(simplify_affiliation)
        .progress_apply(normalize_match_key)
    )

    tqdm.pandas(desc="single raw key")
    raw_keys = df["author1_affi"].progress_apply(normalize_match_key)

    tqdm.pandas(desc="single match cleaned")
    matched_clean = clean_keys.progress_apply(lambda x: cleaned_lookup.get(x))

    tqdm.pandas(desc="single match raw fallback")
    matched_raw = raw_keys.progress_apply(lambda x: raw_lookup.get(x))

    resolved = matched_clean.where(matched_clean.notna(), matched_raw)

    df["author1_ror_link"] = resolved.apply(
        lambda x: x[0] if isinstance(x, tuple) and len(x) > 0 else None
    )
    df["author1_country"] = resolved.apply(
        lambda x: x[1] if isinstance(x, tuple) and len(x) > 1 else None
    )
    df["author1_ror_status"] = resolved.apply(
        lambda x: x[2] if isinstance(x, tuple) and len(x) > 2 else None
    )

    df.to_csv(output_path, sep=";", index=False)

    print(f"Processing mode: {process_scope}")
    print("Input:", input_path)
    print("Saved to:", output_path)
    print("Rows:", len(df))
    print("author1_ror_link non-null:", int(df["author1_ror_link"].notna().sum()))


if __name__ == "__main__":
    main()
