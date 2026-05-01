"""
Purpose:
- Read the requested author-count dataset directly from existing author-specific ROR files.
- Save a tagged sample/full dataset for that author count.
- Iteratively replace affiliations using dictionary_names.
- Recount separators each round and split affiliations using author-count-specific rules.
- Append newly split institution names into dictionary_names until no new rows are added.

Rules:
- 2 authors: and_count == 1
- 3 authors: and_count == 1 and comma_count == 1
- 4 authors: and_count == 1 and comma_count == 2

Examples:
- python scripts/01multi_authors_dic_names.py
- python scripts/01multi_authors_dic_names.py --authors 2 --scope Y
- python scripts/01multi_authors_dic_names.py --authors 3 --scope N
"""

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

SAMPLE_ONLY = "N"
SAMPLE_SIZE = 1000
MAX_LOOP_ITERATIONS = 10
AUTHOR_WORD = {2: "two", 3: "three", 4: "four"}

base_dictionary_names_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/dictionary_names.csv"
base_dic_new_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/dic_new.csv"
BASE_INPUT_PATHS = {
    2: "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_two_authors_ror.csv",
    3: "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_three_authors_ror.csv",
    4: "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_four_authors_ror.csv",
}

dataset_mode = get_dataset_mode()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Iteratively replace and split affiliations for 2/3/4 author rows."
    )
    parser.add_argument(
        "--authors",
        type=int,
        choices=[2, 3, 4],
        help="Target author count to process. If omitted, run 2, 3, and 4 authors in sequence.",
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


def simplify_affiliation(text):
    if pd.isna(text):
        return None
    text = str(text).lower()
    text = re.sub(r"\band\b", "", text)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", "", text).strip()
    return text


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


def resolve_dictionary_names_path(scope_tag):
    scoped_path = add_scope_tag_to_path(
        apply_dataset_mode(base_dictionary_names_path, dataset_mode),
        scope_tag,
    )
    if os.path.exists(scoped_path):
        return scoped_path
    return apply_dataset_mode(base_dictionary_names_path, dataset_mode)


def resolve_input_path(target_authors):
    base_input_path = BASE_INPUT_PATHS[target_authors]
    return apply_dataset_mode(base_input_path, dataset_mode)


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

        # Support malformed export where all columns are packed into one comma-separated column.
        if len(df.columns) == 1:
            packed_col = df.columns[0]
            packed_lines = df[packed_col].astype(str).tolist()
            parsed_rows = []
            for line in packed_lines:
                # Parse each packed line as a proper CSV row to respect quoted commas.
                row = next(csv.reader([line], delimiter=",", quotechar='"'))
                parsed_rows.append(row)

            if parsed_rows:
                max_len = max(len(r) for r in parsed_rows)
                if max_len >= 6:
                    normalized_rows = []
                    for row in parsed_rows:
                        if len(row) < 6:
                            row = row + [None] * (6 - len(row))
                        elif len(row) > 6:
                            # Keep rightmost canonical fields; merge the overflow into raw_name.
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


def enrich_authors_from_dic_new(df, dic_new, target_authors):
    cleaned_lookup = build_first_value_lookup(dic_new, "cleaned_name")
    raw_lookup = build_first_value_lookup(dic_new, "raw_name")

    for i in range(1, target_authors + 1):
        affi_col = f"author{i}_affi"
        legacy_inst_col = f"author_{i}_institution"
        inst_col = f"author{i}_institution"
        ror_link_col = f"author{i}_ror_link"
        country_col = f"author{i}_country"
        status_col = f"author{i}_ror_status"

        if inst_col not in df.columns and legacy_inst_col in df.columns:
            df[inst_col] = df[legacy_inst_col]
        if inst_col not in df.columns:
            df[inst_col] = None
        if affi_col not in df.columns:
            df[affi_col] = None

        # Match only with author{i}_affi (no fallback to institution).
        source_series = df[affi_col]

        tqdm.pandas(desc=f"Author{i} affi cleaned_name key")
        clean_keys = (
            source_series
            .progress_apply(simplify_affiliation)
            .progress_apply(normalize_match_key)
        )
        tqdm.pandas(desc=f"Author{i} affi raw_name key")
        raw_keys = source_series.progress_apply(normalize_match_key)

        tqdm.pandas(desc=f"Author{i} match cleaned_name")
        matched_clean = clean_keys.progress_apply(lambda x: cleaned_lookup.get(x))
        tqdm.pandas(desc=f"Author{i} match raw_name fallback")
        matched_raw = raw_keys.progress_apply(lambda x: raw_lookup.get(x))
        resolved = matched_clean.where(matched_clean.notna(), matched_raw)

        df[ror_link_col] = resolved.apply(
            lambda x: x[0] if isinstance(x, tuple) and len(x) > 0 else None
        )
        df[country_col] = resolved.apply(
            lambda x: x[1] if isinstance(x, tuple) and len(x) > 1 else None
        )
        df[status_col] = resolved.apply(
            lambda x: x[2] if isinstance(x, tuple) and len(x) > 2 else None
        )

    return df


def load_author_data(input_path, scope, sample_size):
    df_all = pd.read_csv(input_path, sep=";")
    df_all.columns = df_all.columns.str.strip()
    if scope == "sample_1000":
        return df_all.head(sample_size).copy()
    return df_all.copy()


def get_visible_author_columns(frame, target_authors):
    start_remove = target_authors + 1
    hidden_patterns = [
        rf"author_(?:[{start_remove}-9]|[1-9][0-9]|1[0-9]{{2,}})_(id|last_name|first_name|url)$",
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


def compute_separator_counts(series):
    and_count = (
        series.fillna("")
        .astype(str)
        .str.lower()
        .str.count(r"\sand\s")
    )
    comma_count = (
        series.fillna("")
        .astype(str)
        .str.count(",")
    )
    return and_count, comma_count


def get_split_mask(and_count, comma_count, target_authors):
    if target_authors == 2:
        return and_count == 1
    if target_authors == 3:
        return (and_count == 1) & (comma_count == 1)
    if target_authors == 4:
        return (and_count == 1) & (comma_count == 2)
    raise ValueError(f"Unsupported target_authors: {target_authors}")


def split_affiliations(text, target_authors):
    if pd.isna(text):
        return [None] * target_authors

    text = str(text).strip()
    if text == "":
        return [None] * target_authors

    if target_authors == 2:
        parts = re.split(r"\sand\s", text, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) != 2:
            return [None] * 2
        return [part.strip() for part in parts]

    parts = re.split(r"\sand\s", text, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        return [None] * target_authors

    left, last = parts[0].strip(), parts[1].strip()
    left_parts = [part.strip() for part in left.split(",") if part.strip()]
    all_parts = left_parts + [last]

    if len(all_parts) != target_authors:
        return [None] * target_authors

    return all_parts


def build_author_affi_from_rounds(df, target_authors):
    for i in range(1, target_authors + 1):
        base_col = f"author{i}_affi_split"
        raw_col = f"author{i}_affi_raw"
        round_pattern = re.compile(rf"^author{i}_affi_split_round(\d+)$")

        round_cols = []
        for col in df.columns:
            m = round_pattern.match(col)
            if m:
                round_cols.append((int(m.group(1)), col))
        round_cols.sort(key=lambda x: x[0], reverse=True)

        candidate_cols = [col for _, col in round_cols]
        if base_col in df.columns:
            candidate_cols.append(base_col)
        if raw_col in df.columns:
            candidate_cols.append(raw_col)

        target_col = f"author{i}_affi"
        if not candidate_cols:
            df[target_col] = None
            continue

        # Treat empty strings as missing, then pick first non-null from left to right.
        candidate_frame = (
            df[candidate_cols]
            .replace(r"^\s*$", pd.NA, regex=True)
            .bfill(axis=1)
        )
        df[target_col] = candidate_frame.iloc[:, 0]

    return df


args = parse_args()
process_scope = normalize_scope(args.scope)


def process_author_count(target_authors, process_scope):
    author_word = AUTHOR_WORD[target_authors]

    base_sample_output_path = (
        f"/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/"
        f"db_info_abstract_{author_word}_authors.csv"
    )
    base_output_path = (
        f"/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/"
        f"db_info_abstract_{author_word}_authors_dic_names.csv"
    )
    base_report_path = (
        f"/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/"
        f"db_info_abstract_{author_word}_authors_dic_names_loop_report.csv"
    )

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
    dictionary_names_path = resolve_dictionary_names_path(process_scope)
    dic_new_path = apply_dataset_mode(base_dic_new_path, dataset_mode)

    input_path = resolve_input_path(target_authors)
    if not os.path.exists(input_path):
        raise FileNotFoundError(
            f"Input file not found: {input_path}. "
            f"Please generate db_info_abstract_{AUTHOR_WORD[target_authors]}_authors_ror.csv first."
        )
    if not os.path.exists(dic_new_path):
        raise FileNotFoundError(f"dic_new file not found: {dic_new_path}")

    df = load_author_data(input_path, process_scope, SAMPLE_SIZE)
    dictionary_names = pd.read_csv(dictionary_names_path, sep=";")
    dic_new = load_dic_new(dic_new_path)
    dictionary_names.columns = dictionary_names.columns.str.strip()
    dictionary_names = normalize_dictionary_names(dictionary_names)

    print(f"\n=== Processing {target_authors} authors ===")
    print("Input path:", input_path)
    if process_scope == "sample_1000":
        print(
            f"Processing mode: first {min(len(df), SAMPLE_SIZE)} {target_authors}-author rows"
        )
    else:
        print(f"Processing mode: all {target_authors}-author rows ({len(df)} rows)")

    df["process_scope"] = process_scope
    df["target_authors"] = target_authors

    df_sample_view = df[get_visible_author_columns(df, target_authors)]
    df_sample_view.to_csv(sample_output_path, sep=";", index=False)
    print("Saved author-count sample to:", sample_output_path)

    df["affiliations_original"] = df["affiliations"]
    df["and_count_original"], df["comma_count_original"] = compute_separator_counts(
        df["affiliations_original"]
    )

    loop_iterations_run = 0
    total_new_dictionary_rows_added = 0
    last_replaced_sum = 0
    last_split_mask_sum = 0
    loop_report = []

    for iteration in range(1, MAX_LOOP_ITERATIONS + 1):
        raw_to_cleaned = build_raw_to_cleaned_mapping(dictionary_names)

        cleaned_col = (
            "affiliations_dic_names_cleaned"
            if iteration == 1
            else f"affiliations_dic_names_cleaned_round{iteration}"
        )
        replaced_col = (
            "dic_names_replaced"
            if iteration == 1
            else f"dic_names_replaced_round{iteration}"
        )
        and_count_col = "and_count" if iteration == 1 else f"and_count_round{iteration}"
        comma_count_col = (
            "comma_count" if iteration == 1 else f"comma_count_round{iteration}"
        )

        split_cols = [
            (
                f"author{i}_affi_split"
                if iteration == 1
                else f"author{i}_affi_split_round{iteration}"
            )
            for i in range(1, target_authors + 1)
        ]

        print(
            f"Round {iteration}: replacing affiliations with dictionary "
            f"({len(df)} rows, {len(raw_to_cleaned)} dictionary entries)..."
        )
        tqdm.pandas(desc=f"{target_authors}a round{iteration} replace")
        df[cleaned_col] = df["affiliations_original"].progress_apply(
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

        df[and_count_col], df[comma_count_col] = compute_separator_counts(df[cleaned_col])
        split_mask = get_split_mask(df[and_count_col], df[comma_count_col], target_authors)

        split_parts = df.loc[split_mask, cleaned_col].apply(
            lambda x: split_affiliations(x, target_authors)
        )

        for idx, split_col in enumerate(split_cols):
            df[split_col] = None
            df.loc[split_mask, split_col] = split_parts.apply(lambda x: x[idx]).values

        split_series_list = [df.loc[split_mask, split_col] for split_col in split_cols]
        split_names = pd.concat(split_series_list, ignore_index=True).dropna()
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
        last_replaced_sum = int(df[replaced_col].sum())
        last_split_mask_sum = int(split_mask.sum())
        loop_report.append(
            {
                "iteration": iteration,
                "target_authors": target_authors,
                "scope": process_scope,
                "dic_names_replaced": int(df[replaced_col].sum()),
                "and_count_eq_1": int((df[and_count_col] == 1).sum()),
                "comma_count_eq_target": int(
                    (df[comma_count_col] == max(target_authors - 1, 0)).sum()
                ),
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
    df = build_author_affi_from_rounds(df, target_authors)
    df = enrich_authors_from_dic_new(df, dic_new, target_authors)

    df_output_view = df[get_visible_author_columns(df, target_authors)]
    df_output_view.to_csv(output_path, sep=";", index=False)
    pd.DataFrame(loop_report).to_csv(report_path, sep=";", index=False)

    print("Dictionary names path:", dictionary_names_path)
    print("Saved cleaned output to:", output_path)
    print("Saved loop report to:", report_path)
    print("Rows processed:", len(df))
    print("Loop iterations run:", int(loop_iterations_run))
    print("Affiliations replaced in final round:", int(last_replaced_sum))
    print("Rows split in final round:", int(last_split_mask_sum))
    print("Total new dictionary_names rows added:", int(total_new_dictionary_rows_added))
    print("\nLoop report:")
    for item in loop_report:
        print(
            f"Round {item['iteration']}: "
            f"dic_names_replaced={item['dic_names_replaced']}, "
            f"and_count_eq_1={item['and_count_eq_1']}, "
            f"comma_count_eq_target={item['comma_count_eq_target']}, "
            f"rows_split={item['rows_split']}, "
            f"new_dictionary_names_rows_added={item['new_dictionary_names_rows_added']}"
        )

    return loop_report


author_counts = [args.authors] if args.authors is not None else [2, 3, 4]
all_loop_reports = []
for author_count in author_counts:
    all_loop_reports.extend(process_author_count(author_count, process_scope))

print("\n=== Combined rows split report ===")
for item in all_loop_reports:
    print(
        f"{item['target_authors']} authors, "
        f"round {item['iteration']}: "
        f"rows_split={item['rows_split']}"
    )
