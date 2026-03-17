# 只保留 4-author

"""
Purpose:
- Keep only rows with exactly four authors from the main abstract dataset.
- Replace any known old affiliation names with simplified names from the dictionary.
- Recount separators after replacement.
- For rows with and_count_new == 1 and comma_count_new == 2, split affiliations into
  four parts by first splitting on two commas and then splitting the last part on "and".
- Match split affiliations against the dictionary first and the ROR API second.
- Append new author old names to dictionary.csv without duplicating existing old names.

Input:
- outputs/db_info_abstract.csv
- outputs/dictionary.csv

Output:
- outputs/db_info_abstract_four_authors_ror.csv
- updated outputs/dictionary.csv
"""

import os
import sys
import pandas as pd
import requests
import urllib.parse
import re
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from path_config import apply_dataset_mode, get_dataset_mode

# ---------- paths ----------
base_file_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract.csv"
base_output_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_four_authors_ror.csv"
dict_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/dictionary.csv"
dataset_mode = get_dataset_mode()
file_path = apply_dataset_mode(base_file_path, dataset_mode)
output_path = apply_dataset_mode(base_output_path, dataset_mode)

# ---------- load ----------
df = pd.read_csv(file_path, sep=";", engine="python")
dictionary = pd.read_csv(dict_path, sep=";", engine="python")
dictionary.columns = dictionary.columns.str.strip()
df.columns = df.columns.str.strip()

# normalize dictionary column names if needed
rename_map = {}
if "affiliations" in dictionary.columns and "old names" not in dictionary.columns:
    rename_map["affiliations"] = "old names"
if "author_1_institution" in dictionary.columns and "ror_name" not in dictionary.columns:
    rename_map["author_1_institution"] = "ror_name"
if "author_1_ror_id" in dictionary.columns and "ror_id" not in dictionary.columns:
    rename_map["author_1_ror_id"] = "ror_id"
if rename_map:
    dictionary = dictionary.rename(columns=rename_map)

# ---------- clean affiliations ----------
df["affiliations"] = df["affiliations"].replace(
    {
        r"(?i)^independent$": np.nan,
        r"(?i)^affiliation not provided to ssrn$": np.nan
    },
    regex=True
)

# ---------- keep exactly 4 authors ----------
df = df[(df["author_4_id"].notna()) & (df["author_5_id"].isna())].copy()

# ---------- count separators before dictionary replacement ----------
df["and_count_old"] = (
    df["affiliations"]
    .fillna("")
    .str.lower()
    .str.count(r"\sand\s")
)

df["comma_count_old"] = (
    df["affiliations"]
    .fillna("")
    .astype(str)
    .str.count(r",")
)

# ---------- dictionary mappings ----------
affi_to_simplified = dict(
    sorted(
        zip(dictionary["old names"], dictionary["simplified name"]),
        key=lambda x: len(str(x[0])),
        reverse=True
    )
)

def replace_affiliation(text):
    if pd.isna(text):
        return text
    text = str(text)
    for affi, simplified in affi_to_simplified.items():
        if pd.notna(affi) and affi in text:
            text = text.replace(affi, str(simplified))
    return text

df["affiliations_replaced"] = df["affiliations"].apply(replace_affiliation)

# ---------- recount separators after dictionary replacement ----------
df["and_count_new"] = (
    df["affiliations_replaced"]
    .fillna("")
    .str.lower()
    .str.count(r"\sand\s")
)

df["comma_count_new"] = (
    df["affiliations_replaced"]
    .fillna("")
    .astype(str)
    .str.count(r",")
)

def simplify_name(text):
    if pd.isna(text):
        return None
    text = str(text).lower()
    text = re.sub(r"\band\b", "", text)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", "", text).strip()
    return text

# ---------- split rows with two commas and one "and" ----------
df["author1_affi_raw"] = None
df["author2_affi_raw"] = None
df["author3_affi_raw"] = None
df["author4_affi_raw"] = None

mask_split = (df["and_count_new"] == 1) & (df["comma_count_new"] == 2)

def split_four_affiliations(text):
    if pd.isna(text):
        return (None, None, None, None)

    comma_parts = [part.strip() for part in str(text).split(",", maxsplit=2)]
    if len(comma_parts) != 3:
        return (None, None, None, None)

    first, second, third = comma_parts
    third_parts = re.split(r"\sand\s", third, maxsplit=1, flags=re.IGNORECASE)
    if len(third_parts) != 2:
        return (None, None, None, None)

    return (
        first,
        second,
        third_parts[0].strip(),
        third_parts[1].strip()
    )

split_result = df.loc[mask_split, "affiliations_replaced"].apply(split_four_affiliations)
df.loc[mask_split, "author1_affi_raw"] = split_result.apply(lambda x: x[0]).values
df.loc[mask_split, "author2_affi_raw"] = split_result.apply(lambda x: x[1]).values
df.loc[mask_split, "author3_affi_raw"] = split_result.apply(lambda x: x[2]).values
df.loc[mask_split, "author4_affi_raw"] = split_result.apply(lambda x: x[3]).values

# ---------- first pass: fill institutions and ror ids from dictionary ----------
simplified_to_inst = dict(zip(dictionary["simplified name"], dictionary["ror_name"]))
simplified_to_ror = dict(zip(dictionary["simplified name"], dictionary["ror_id"]))

def find_dictionary_value(text, lookup):
    if pd.isna(text):
        return None
    text = str(text).strip()
    for simplified, value in lookup.items():
        if pd.notna(simplified) and str(simplified) in text:
            return value
    return None

author1_inst_dict = df["author1_affi_raw"].apply(lambda x: find_dictionary_value(x, simplified_to_inst))
author2_inst_dict = df["author2_affi_raw"].apply(lambda x: find_dictionary_value(x, simplified_to_inst))
author3_inst_dict = df["author3_affi_raw"].apply(lambda x: find_dictionary_value(x, simplified_to_inst))
author4_inst_dict = df["author4_affi_raw"].apply(lambda x: find_dictionary_value(x, simplified_to_inst))

author1_ror_dict = df["author1_affi_raw"].apply(lambda x: find_dictionary_value(x, simplified_to_ror))
author2_ror_dict = df["author2_affi_raw"].apply(lambda x: find_dictionary_value(x, simplified_to_ror))
author3_ror_dict = df["author3_affi_raw"].apply(lambda x: find_dictionary_value(x, simplified_to_ror))
author4_ror_dict = df["author4_affi_raw"].apply(lambda x: find_dictionary_value(x, simplified_to_ror))

df["author_1_institution"] = author1_inst_dict
df["author_2_institution"] = author2_inst_dict
df["author_3_institution"] = author3_inst_dict
df["author_4_institution"] = author4_inst_dict

df["author_1_ror_id"] = author1_ror_dict
df["author_2_ror_id"] = author2_ror_dict
df["author_3_ror_id"] = author3_ror_dict
df["author_4_ror_id"] = author4_ror_dict

# ---------- ROR matcher with cache ----------
cache = {}

def ror_match(text):
    if pd.isna(text) or str(text).strip() == "":
        return {
            "institution": None,
            "ror_id": None,
            "status": "empty_affiliation"
        }

    text = re.sub(r"\s+", " ", str(text)).strip()

    if text in cache:
        return cache[text]

    url = f"https://api.ror.org/v2/organizations?affiliation={urllib.parse.quote(text)}&single_search"

    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        items = r.json().get("items", [])

        if not items:
            result = {
                "institution": None,
                "ror_id": None,
                "status": "no_match"
            }
        else:
            org = items[0].get("organization", items[0])
            names = org.get("names", [])
            institution = None

            for n in names:
                if "ror_display" in n.get("types", []):
                    institution = n.get("value")
                    break

            if institution is None and names:
                institution = names[0].get("value")

            result = {
                "institution": institution,
                "ror_id": org.get("id"),
                "status": "matched"
            }

    except Exception as e:
        result = {
            "institution": None,
            "ror_id": None,
            "status": f"error: {e}"
        }

    cache[text] = result
    return result

def skipped_match_result(reason):
    return {
        "institution": None,
        "ror_id": None,
        "status": reason
    }

# ---------- second pass: ROR match only rows not found in dictionary ----------
match_1 = pd.Series([skipped_match_result("not_processed")] * len(df), index=df.index)
match_2 = pd.Series([skipped_match_result("not_processed")] * len(df), index=df.index)
match_3 = pd.Series([skipped_match_result("not_processed")] * len(df), index=df.index)
match_4 = pd.Series([skipped_match_result("not_processed")] * len(df), index=df.index)

author1_matched_dict = author1_inst_dict.notna()
author2_matched_dict = author2_inst_dict.notna()
author3_matched_dict = author3_inst_dict.notna()
author4_matched_dict = author4_inst_dict.notna()

match_1.loc[author1_matched_dict] = [skipped_match_result("matched_in_dictionary")] * int(author1_matched_dict.sum())
match_2.loc[author2_matched_dict] = [skipped_match_result("matched_in_dictionary")] * int(author2_matched_dict.sum())
match_3.loc[author3_matched_dict] = [skipped_match_result("matched_in_dictionary")] * int(author3_matched_dict.sum())
match_4.loc[author4_matched_dict] = [skipped_match_result("matched_in_dictionary")] * int(author4_matched_dict.sum())

author1_needs_ror = author1_inst_dict.isna() & df["author1_affi_raw"].notna()
author2_needs_ror = author2_inst_dict.isna() & df["author2_affi_raw"].notna()
author3_needs_ror = author3_inst_dict.isna() & df["author3_affi_raw"].notna()
author4_needs_ror = author4_inst_dict.isna() & df["author4_affi_raw"].notna()

match_1.loc[author1_needs_ror] = df.loc[author1_needs_ror, "author1_affi_raw"].apply(ror_match)
match_2.loc[author2_needs_ror] = df.loc[author2_needs_ror, "author2_affi_raw"].apply(ror_match)
match_3.loc[author3_needs_ror] = df.loc[author3_needs_ror, "author3_affi_raw"].apply(ror_match)
match_4.loc[author4_needs_ror] = df.loc[author4_needs_ror, "author4_affi_raw"].apply(ror_match)

df["author_1_institution"] = df["author_1_institution"].combine_first(match_1.apply(lambda x: x["institution"]))
df["author_2_institution"] = df["author_2_institution"].combine_first(match_2.apply(lambda x: x["institution"]))
df["author_3_institution"] = df["author_3_institution"].combine_first(match_3.apply(lambda x: x["institution"]))
df["author_4_institution"] = df["author_4_institution"].combine_first(match_4.apply(lambda x: x["institution"]))

df["author_1_ror_status"] = match_1.apply(lambda x: x["status"])
df["author_2_ror_status"] = match_2.apply(lambda x: x["status"])
df["author_3_ror_status"] = match_3.apply(lambda x: x["status"])
df["author_4_ror_status"] = match_4.apply(lambda x: x["status"])

match_1_ror_url = match_1.apply(lambda x: x["ror_id"])
match_2_ror_url = match_2.apply(lambda x: x["ror_id"])
match_3_ror_url = match_3.apply(lambda x: x["ror_id"])
match_4_ror_url = match_4.apply(lambda x: x["ror_id"])

existing_author_1_ror_url = df["author_1_ror_id"].apply(lambda x: f"https://ror.org/{x}" if pd.notna(x) and str(x).strip() != "" else None)
existing_author_2_ror_url = df["author_2_ror_id"].apply(lambda x: f"https://ror.org/{x}" if pd.notna(x) and str(x).strip() != "" else None)
existing_author_3_ror_url = df["author_3_ror_id"].apply(lambda x: f"https://ror.org/{x}" if pd.notna(x) and str(x).strip() != "" else None)
existing_author_4_ror_url = df["author_4_ror_id"].apply(lambda x: f"https://ror.org/{x}" if pd.notna(x) and str(x).strip() != "" else None)

df["author_1_ror_url"] = match_1_ror_url.combine_first(existing_author_1_ror_url)
df["author_2_ror_url"] = match_2_ror_url.combine_first(existing_author_2_ror_url)
df["author_3_ror_url"] = match_3_ror_url.combine_first(existing_author_3_ror_url)
df["author_4_ror_url"] = match_4_ror_url.combine_first(existing_author_4_ror_url)

df["author_1_ror_id"] = df["author_1_ror_id"].combine_first(df["author_1_ror_url"].fillna("").str.replace("https://ror.org/", "", regex=False))
df["author_2_ror_id"] = df["author_2_ror_id"].combine_first(df["author_2_ror_url"].fillna("").str.replace("https://ror.org/", "", regex=False))
df["author_3_ror_id"] = df["author_3_ror_id"].combine_first(df["author_3_ror_url"].fillna("").str.replace("https://ror.org/", "", regex=False))
df["author_4_ror_id"] = df["author_4_ror_id"].combine_first(df["author_4_ror_url"].fillna("").str.replace("https://ror.org/", "", regex=False))

# ---------- append only new author old names to dictionary ----------
author1_lookup = (
    df[["author1_affi_raw", "author_1_institution", "author_1_ror_id"]]
    .dropna(subset=["author1_affi_raw", "author_1_institution", "author_1_ror_id"])
    .drop_duplicates()
    .rename(columns={"author1_affi_raw": "old names", "author_1_institution": "ror_name", "author_1_ror_id": "ror_id"})
)
author2_lookup = (
    df[["author2_affi_raw", "author_2_institution", "author_2_ror_id"]]
    .dropna(subset=["author2_affi_raw", "author_2_institution", "author_2_ror_id"])
    .drop_duplicates()
    .rename(columns={"author2_affi_raw": "old names", "author_2_institution": "ror_name", "author_2_ror_id": "ror_id"})
)
author3_lookup = (
    df[["author3_affi_raw", "author_3_institution", "author_3_ror_id"]]
    .dropna(subset=["author3_affi_raw", "author_3_institution", "author_3_ror_id"])
    .drop_duplicates()
    .rename(columns={"author3_affi_raw": "old names", "author_3_institution": "ror_name", "author_3_ror_id": "ror_id"})
)
author4_lookup = (
    df[["author4_affi_raw", "author_4_institution", "author_4_ror_id"]]
    .dropna(subset=["author4_affi_raw", "author_4_institution", "author_4_ror_id"])
    .drop_duplicates()
    .rename(columns={"author4_affi_raw": "old names", "author_4_institution": "ror_name", "author_4_ror_id": "ror_id"})
)

author_lookup = pd.concat(
    [author1_lookup, author2_lookup, author3_lookup, author4_lookup],
    ignore_index=True
).drop_duplicates()

required_dict_cols = {"old names", "ror_name", "ror_id"}
if required_dict_cols.issubset(dictionary.columns):
    existing_old_names = set(dictionary["old names"].dropna().astype(str).str.strip())
    author_lookup["old names"] = author_lookup["old names"].astype(str).str.strip()
    new_author_rows = author_lookup[
        (~author_lookup["old names"].isin(existing_old_names)) &
        (author_lookup["old names"] != "")
    ].copy()

    if not new_author_rows.empty:
        dictionary = pd.concat([dictionary, new_author_rows], ignore_index=True)
        print(f"Added {len(new_author_rows)} new old names to dictionary.")
    else:
        print("No new old names to add to dictionary.")

dictionary["simplified name"] = dictionary["ror_name"].apply(simplify_name)

# ---------- save ----------
visible_cols = [
    c for c in df.columns
    if not re.match(r"author_(?:[5-9]|[1-5][0-9]|60)_(id|last_name|first_name|url)$", c)
]

df_view = df[visible_cols]

df_view.to_csv(output_path, sep=";", index=False)
dictionary.to_csv(dict_path, sep=";", index=False)
print("Saved to:", output_path)
print("Updated dictionary:", dict_path)
print("\nand_count_old summary:")
print(df["and_count_old"].value_counts(dropna=False))
print("\ncomma_count_old summary:")
print(df["comma_count_old"].value_counts(dropna=False))
print("\nand_count_new summary:")
print(df["and_count_new"].value_counts(dropna=False))
print("\ncomma_count_new summary:")
print(df["comma_count_new"].value_counts(dropna=False))
print("\nAuthor 1 status:")
print(df["author_1_ror_status"].value_counts(dropna=False))
print("\nAuthor 2 status:")
print(df["author_2_ror_status"].value_counts(dropna=False))
print("\nAuthor 3 status:")
print(df["author_3_ror_status"].value_counts(dropna=False))
print("\nAuthor 4 status:")
print(df["author_4_ror_status"].value_counts(dropna=False))
