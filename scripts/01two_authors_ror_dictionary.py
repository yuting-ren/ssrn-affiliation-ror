# 只保留 2-author

"""
Purpose:
- Keep only rows with exactly two authors from the main abstract dataset.
- Split affiliations when there is exactly one "and" between two affiliations.
- Query the ROR API for author 1 and author 2 affiliation matches.
- Append new author1/author2 old names to dictionary.csv without duplicating existing
  old names, and refresh the simplified name column.

Input:
- outputs/db_info_abstract.csv
- outputs/dictionary.csv

Output:
- outputs/db_info_abstract_two_authors_ror.csv
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
base_output_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_two_authors_ror.csv"
dict_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/dictionary_new.csv"
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
if "author_1_ror_id" in dictionary.columns and "ror_id" not in dictionary.columns:
    rename_map["author_1_ror_id"] = "ror_id"
if rename_map:
    dictionary = dictionary.rename(columns=rename_map)

# ---------- keep exactly 2 authors ----------
df = df[(df["author_2_id"].notna()) & (df["author_3_id"].isna())].copy()

# ---------- count " and " ----------
df["and_count"] = (
    df["affiliations"]
    .fillna("")
    .str.lower()
    .str.count(r"\sand\s")
)

# ---------- split raw affiliations when and_count == 1 ----------
df["author1_affi_raw"] = None
df["author2_affi_raw"] = None

mask = df["and_count"] == 1

def split_affi(text):
    if pd.isna(text):
        return (None, None)
    parts = re.split(r"\sand\s", str(text), maxsplit=1, flags=re.IGNORECASE)
    return (parts[0].strip(), parts[1].strip()) if len(parts) == 2 else (None, None)

def simplify_name(text):
    if pd.isna(text):
        return None
    text = str(text).lower()
    text = re.sub(r"\band\b", "", text)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", "", text).strip()
    return text

pairs = df.loc[mask, "affiliations"].apply(split_affi)
df.loc[mask, "author1_affi_raw"] = pairs.apply(lambda x: x[0]).values
df.loc[mask, "author2_affi_raw"] = pairs.apply(lambda x: x[1]).values

# ---------- ROR matcher with cache ----------
cache = {}

def ror_match(text):
    if pd.isna(text) or str(text).strip() == "":
        return {
            "institution": None,
            "ror_id": None,
            "country": None,
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
                "country": None,
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

            locations = org.get("locations") or []
            geo = locations[0].get("geonames_details", {}) if locations else {}
            country = geo.get("country_name") or geo.get("country_code")

            result = {
                "institution": institution,
                "ror_id": org.get("id"),
                "country": country,
                "status": "matched"
            }

    except Exception as e:
        result = {
            "institution": None,
            "ror_id": None,
            "country": None,
            "status": f"error: {e}"
        }

    cache[text] = result
    return result

# ---------- apply ROR ----------
m1 = df["author1_affi_raw"].apply(ror_match)
m2 = df["author2_affi_raw"].apply(ror_match)

df["author_1_institution"] = m1.apply(lambda x: x["institution"])
df["author_1_ror_url"] = m1.apply(lambda x: x["ror_id"])
df["author_1_country"] = m1.apply(lambda x: x["country"])
df["author_1_ror_status"] = m1.apply(lambda x: x["status"])

df["author_1_ror_id"] = (
    df["author_1_ror_url"]
    .fillna("")
    .str.replace("https://ror.org/", "", regex=False)
)


df["author_2_institution"] = m2.apply(lambda x: x["institution"])
df["author_2_ror_url"] = m2.apply(lambda x: x["ror_id"])
df["author_2_country"] = m2.apply(lambda x: x["country"])
df["author_2_ror_status"] = m2.apply(lambda x: x["status"])

df["author_2_ror_id"] = (
    df["author_2_ror_url"]
    .fillna("")
    .str.replace("https://ror.org/", "", regex=False)
)

# ---------- append only new author1/author2 old names to dictionary ----------
author1_lookup = (
    df[["author1_affi_raw", "author_1_institution", "author_1_ror_id"]]
    .dropna(subset=["author1_affi_raw", "author_1_institution", "author_1_ror_id"])
    .drop_duplicates()
    .rename(columns={
        "author1_affi_raw": "old names",
        "author_1_institution": "ror_name",
        "author_1_ror_id": "ror_id"
    })
)

author2_lookup = (
    df[["author2_affi_raw", "author_2_institution", "author_2_ror_id"]]
    .dropna(subset=["author2_affi_raw", "author_2_institution", "author_2_ror_id"])
    .drop_duplicates()
    .rename(columns={
        "author2_affi_raw": "old names",
        "author_2_institution": "ror_name",
        "author_2_ror_id": "ror_id"
    })
)

author_lookup = (
    pd.concat([author1_lookup, author2_lookup], ignore_index=True)
    .drop_duplicates()
)

print("Dictionary columns:", dictionary.columns.tolist())
print("author lookup columns:", author_lookup.columns.tolist())

required_dict_cols = {"old names", "ror_name", "ror_id"}
if required_dict_cols.issubset(dictionary.columns):
    existing_old_names = set(
        dictionary["old names"]
        .dropna()
        .astype(str)
        .str.strip()
    )

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
else:
    print("Warning: dictionary does not contain required columns; skipping dictionary update.")

if "ror_name" in dictionary.columns:
    dictionary["simplified name"] = dictionary["ror_name"].apply(simplify_name)

visible_cols = [
    c for c in df.columns
    if not re.match(r"author_(?:[5-9]|[1-5][0-9]|60)_(id|last_name|first_name|url)$", c)
]

df_view = df[visible_cols]


# ---------- save ----------
df_view.to_csv(output_path, sep=";", index=False)
dictionary.to_csv(dict_path, sep=";", index=False)
print("Updated dictionary:", dict_path)

print("Saved to:", output_path)
print("\nAuthor 1 status:")
print(df["author_1_ror_status"].value_counts(dropna=False))
print("\nAuthor 2 status:")
print(df["author_2_ror_status"].value_counts(dropna=False))
