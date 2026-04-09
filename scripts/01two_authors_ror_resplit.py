import os
import sys
import pandas as pd
import requests
import urllib.parse
import re
import time
from tqdm import tqdm

"""
Purpose:
- Repair two-author affiliation rows that were not cleanly split in earlier steps.
- Only process rows where author_1_ror_id or author_2_ror_id is still missing.
- Use dictionary.csv to replace known old affiliation names with simplified names.
- Re-split affiliations around a single "and", then fill institution data from the
  dictionary first and the ROR API second.
- Do not populate country fields for now, because ROR top-match geography can be noisy.

Input:
- outputs/dictionary_new.csv
- outputs/db_info_abstract_two_authors_ror.csv

Output:
- outputs/db_info_abstract_two_authors_ror_new.csv
"""

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from path_config import apply_dataset_mode, get_dataset_mode

dict_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/dictionary_new.csv"
base_data_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_two_authors_ror.csv"
base_output_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_two_authors_ror_new.csv"
dataset_mode = get_dataset_mode()
data_path = apply_dataset_mode(base_data_path, dataset_mode)
output_path = apply_dataset_mode(base_output_path, dataset_mode)

# ---------- read files ----------
dictionary = pd.read_csv(dict_path, sep=";")
df = pd.read_csv(data_path, sep=";")

dictionary.columns = dictionary.columns.str.strip()
df.columns = df.columns.str.strip()
tqdm.pandas(desc="Two-author resplit")

# Preserve the existing dictionary.csv schema while still accepting older files.
rename_map = {}
if "affiliations" in dictionary.columns and "old names" not in dictionary.columns:
    rename_map["affiliations"] = "old names"
if "author_1_institution" in dictionary.columns and "ror_name" not in dictionary.columns:
    rename_map["author_1_institution"] = "ror_name"
if "author_1_ror_id" in dictionary.columns and "ror_id" not in dictionary.columns:
    rename_map["author_1_ror_id"] = "ror_id"
if rename_map:
    dictionary = dictionary.rename(columns=rename_map)

df["affiliations"] = df["affiliations"].astype(str)

# ---------- keep only rows still missing at least one author ROR id ----------
for col in ["author_1_ror_id", "author_2_ror_id"]:
    if col not in df.columns:
        df[col] = None

author_1_missing = df["author_1_ror_id"].isna() | (df["author_1_ror_id"].astype(str).str.strip() == "")
author_2_missing = df["author_2_ror_id"].isna() | (df["author_2_ror_id"].astype(str).str.strip() == "")
df = df[author_1_missing | author_2_missing].copy()
print(f"Rows selected for resplit: {len(df)}")

# ---------- dictionary mappings ----------
# old names -> simplified name
affi_to_simplified = dict(
    sorted(
        zip(dictionary["old names"], dictionary["simplified name"]),
        key=lambda x: len(str(x[0])),
        reverse=True
    )
)

# simplified name -> institution
simplified_to_inst = dict(zip(dictionary["simplified name"], dictionary["ror_name"]))

# simplified name -> ror id
simplified_to_ror = dict(zip(dictionary["simplified name"], dictionary["ror_id"]))

# ---------- replace known affiliations with simplified names ----------
mask_replace = df["and_count"] != 1

def replace_affiliation(text):
    if pd.isna(text):
        return text
    text = str(text)
    for affi, simplified in affi_to_simplified.items():
        if pd.notna(affi) and affi in text:
            text = text.replace(affi, str(simplified))
    return text

df.loc[mask_replace, "affiliations"] = df.loc[mask_replace, "affiliations"].progress_apply(replace_affiliation)

# ---------- recount and ----------
df["and_count_new"] = (
    df["affiliations"]
    .fillna("")
    .str.lower()
    .str.count(r"\sand\s")
)

# ---------- split into two raw affiliations ----------
df["author1_affi_raw"] = None
df["author2_affi_raw"] = None

mask_split = df["and_count_new"] == 1

split_result = df.loc[mask_split, "affiliations"].str.split(
    r"\sand\s", n=1, expand=True
)

df.loc[mask_split, "author1_affi_raw"] = split_result[0].str.strip().values
df.loc[mask_split, "author2_affi_raw"] = split_result[1].str.strip().values

# ---------- first pass: fill institutions and ror ids from dictionary ----------
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
author1_ror_dict = df["author1_affi_raw"].apply(lambda x: find_dictionary_value(x, simplified_to_ror))
author2_ror_dict = df["author2_affi_raw"].apply(lambda x: find_dictionary_value(x, simplified_to_ror))

if "author_1_institution" in df.columns:
    df["author_1_institution"] = df["author_1_institution"].combine_first(author1_inst_dict)
else:
    df["author_1_institution"] = author1_inst_dict

if "author_2_institution" in df.columns:
    df["author_2_institution"] = df["author_2_institution"].combine_first(author2_inst_dict)
else:
    df["author_2_institution"] = author2_inst_dict

if "author_1_ror_id" in df.columns:
    df["author_1_ror_id"] = df["author_1_ror_id"].combine_first(author1_ror_dict)
else:
    df["author_1_ror_id"] = author1_ror_dict

if "author_2_ror_id" in df.columns:
    df["author_2_ror_id"] = df["author_2_ror_id"].combine_first(author2_ror_dict)
else:
    df["author_2_ror_id"] = author2_ror_dict

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
    time.sleep(0.1)
    return result

def skipped_match_result(reason):
    return {
        "institution": None,
        "ror_id": None,
        "country": None,
        "status": reason
    }

# ---------- second pass: ROR match raw affiliation fields ----------
match_1 = pd.Series(
    [skipped_match_result("matched_in_dictionary")] * len(df),
    index=df.index
)
match_2 = pd.Series(
    [skipped_match_result("matched_in_dictionary")] * len(df),
    index=df.index
)

author1_needs_ror = author1_inst_dict.isna()
author2_needs_ror = author2_inst_dict.isna()

match_1.loc[author1_needs_ror] = df.loc[author1_needs_ror, "author1_affi_raw"].progress_apply(ror_match)
match_2.loc[author2_needs_ror] = df.loc[author2_needs_ror, "author2_affi_raw"].progress_apply(ror_match)

match_1_inst = match_1.apply(lambda x: x["institution"])
match_2_inst = match_2.apply(lambda x: x["institution"])

# institution: preserve earlier filled values if present
if "author_1_institution" in df.columns:
    df["author_1_institution"] = df["author_1_institution"].combine_first(match_1_inst)
else:
    df["author_1_institution"] = match_1_inst

if "author_2_institution" in df.columns:
    df["author_2_institution"] = df["author_2_institution"].combine_first(match_2_inst)
else:
    df["author_2_institution"] = match_2_inst

# author 1 outputs
existing_author_1_ror_url = df["author_1_ror_id"].where(
    df["author_1_ror_id"].notna() & (df["author_1_ror_id"].astype(str).str.strip() != ""),
    None
)
existing_author_1_ror_url = existing_author_1_ror_url.apply(
    lambda x: f"https://ror.org/{x}" if pd.notna(x) else None
)
df["author_1_ror_url"] = match_1.apply(lambda x: x["ror_id"]).combine_first(existing_author_1_ror_url)
df["author_1_ror_status"] = match_1.apply(lambda x: x["status"])
match_1_ror_id = (
    df["author_1_ror_url"]
    .fillna("")
    .str.replace("https://ror.org/", "", regex=False)
)
df["author_1_ror_id"] = df["author_1_ror_id"].combine_first(match_1_ror_id)

# author 2 outputs
existing_author_2_ror_url = df["author_2_ror_id"].where(
    df["author_2_ror_id"].notna() & (df["author_2_ror_id"].astype(str).str.strip() != ""),
    None
)
existing_author_2_ror_url = existing_author_2_ror_url.apply(
    lambda x: f"https://ror.org/{x}" if pd.notna(x) else None
)
df["author_2_ror_url"] = match_2.apply(lambda x: x["ror_id"]).combine_first(existing_author_2_ror_url)
df["author_2_ror_status"] = match_2.apply(lambda x: x["status"])
match_2_ror_id = (
    df["author_2_ror_url"]
    .fillna("")
    .str.replace("https://ror.org/", "", regex=False)
)
df["author_2_ror_id"] = df["author_2_ror_id"].combine_first(match_2_ror_id)

# ---------- save ----------
print("Post-processing complete. Writing output CSV...")
visible_cols = [
    c for c in df.columns
    if not re.match(r"author_(?:[5-9]|[1-9][0-9]|1[0-9]{2}|200)_(id|last_name|first_name|url)$", c)
]
visible_cols = [
    c for c in visible_cols
    if not re.match(r"author_(\d+)_(id|last_name|first_name|url)$", c)
    or int(re.match(r"author_(\d+)_(id|last_name|first_name|url)$", c).group(1)) <= 4
]

df_view = df[visible_cols]
df_view.to_csv(output_path, sep=";", index=False)
print("CSV write complete.")

print("Replacement + ROR matching finished.")
print("Saved to:", output_path)
print("\nAuthor 1 status:")
print(df["author_1_ror_status"].value_counts(dropna=False))
print("\nAuthor 2 status:")
print(df["author_2_ror_status"].value_counts(dropna=False))
