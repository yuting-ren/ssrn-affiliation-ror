"""
Purpose:
- Read db_info_abstract_three_authors_dic_names_all.csv
- Build per-author institution columns (author1-3_institution)
- For each author, pick institution by priority:
  highest round -> ... -> round1(author*_affi_split) -> author*_affi_raw

Example:
- python scripts/014merge_author_affi_split.py
- python scripts/014merge_author_affi_split.py --input outputs/db_info_abstract_three_authors_dic_names_all.csv
"""

import argparse
import os
import re
from typing import Dict, List, Optional

import pandas as pd


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INPUT = os.path.join(
    PROJECT_ROOT,
    "outputs",
    "db_info_abstract_three_authors_dic_names_all.csv",
)
DEFAULT_OUTPUT = os.path.join(
    PROJECT_ROOT,
    "outputs",
    "db_info_abstract_three_authors_dic_names_all_with_author_institution.csv",
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Build author{n}_institution columns from author{n}_affi_split_round*, "
            "author{n}_affi_split, and author{n}_affi_raw."
        )
    )
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input CSV path")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output CSV path")
    return parser.parse_args()


def clean_text(value: object) -> Optional[str]:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def get_author_indices(columns: List[str]) -> List[int]:
    indices = set()
    pattern = re.compile(r"^author_?(\d+)_(?:id|first_name|last_name|url)$")
    for col in columns:
        m = pattern.match(col)
        if m:
            indices.add(int(m.group(1)))

    if indices:
        return sorted(indices)

    split_pattern = re.compile(r"^author(\d+)_affi_split(?:_round\d+)?$")
    for col in columns:
        m = split_pattern.match(col)
        if m:
            indices.add(int(m.group(1)))

    raw_pattern = re.compile(r"^author(\d+)_affi_raw$")
    for col in columns:
        m = raw_pattern.match(col)
        if m:
            indices.add(int(m.group(1)))

    return sorted(indices)


def get_affi_priority_columns(columns: List[str], idx: int) -> List[str]:
    round_pattern = re.compile(rf"^author{idx}_affi_split_round(\d+)$")
    round_candidates = []
    for col in columns:
        m = round_pattern.match(col)
        if m:
            round_candidates.append((int(m.group(1)), col))

    round_candidates.sort(key=lambda x: x[0], reverse=True)
    ordered = [col for _, col in round_candidates]

    round1_col = f"author{idx}_affi_split"
    raw_col = f"author{idx}_affi_raw"

    if round1_col in columns:
        ordered.append(round1_col)
    if raw_col in columns:
        ordered.append(raw_col)

    return ordered


def pick_institution_value(row: pd.Series, ordered_columns: List[str]) -> Optional[str]:
    for col in ordered_columns:
        value = clean_text(row.get(col))
        if value:
            return value
    return None


def main():
    args = parse_args()

    df = pd.read_csv(args.input, sep=";")
    df.columns = df.columns.str.strip()

    author_indices = get_author_indices(df.columns.tolist())

    priority_map: Dict[int, List[str]] = {
        idx: get_affi_priority_columns(df.columns.tolist(), idx)
        for idx in author_indices
    }

    for idx in author_indices:
        target_col = f"author{idx}_institution"
        ordered_cols = priority_map.get(idx, [])
        df[target_col] = df.apply(
            lambda row: pick_institution_value(row, ordered_cols),
            axis=1,
        )

    df.to_csv(args.output, sep=";", index=False)

    print(f"Saved: {args.output}")
    print(f"Rows: {len(df)}")
    print(f"Authors detected: {author_indices}")
    print(f"Affiliation priority columns: {priority_map}")


if __name__ == "__main__":
    main()
