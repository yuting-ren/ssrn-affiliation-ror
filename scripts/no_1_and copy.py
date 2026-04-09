import pandas as pd
import requests
import urllib.parse
import re
import numpy as np
import time

# ---------- paths ----------
dict_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/dictionary.csv"
data_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_two_authors_ror.csv"
output_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/affiliation_substituted.csv"

# ---------- read files ----------
dictionary = pd.read_csv(dict_path, sep=";")
df = pd.read_csv(data_path, sep=";")

# ---------- clean column names ----------
dictionary.columns = dictionary.columns.str.strip()
df.columns = df.columns.str.strip()

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

# ---------- count " and " if not already reliable ----------
df["and_count"] = (
    df["affiliations"]
    .fillna("")
    .astype(str)
    .str.lower()
    .str.count(r"\sand\s")
)

# ---------- only process and_count == 1 ----------
mask = df["and_count"] == 1

# initialize raw affiliation columns if absent
if "author1_affi_raw" not in df.columns:
    df["author1_affi_raw"] = None
if "author2_affi_raw" not in df.columns:
    df["author2_affi_raw"] = None

# initialize institution columns if absent
if "author_1_institution" not in df.columns:
    df["author_1_institution"] = None
if "author_2_institution" not in df.columns:
    df["author_2_institution"] = None

# optional: initialize ror id columns if absent
if "author_1_ror_id" not in df.columns:
    df["author_1_ror_id"] = None
if "author_2_ror_id" not in df.columns:
    df["author_2_ror_id"] = None

# ---------- split affiliations into two parts ----------
def split_affi(text):
    if pd.isna(text):
        return (None, None)
    parts = re.split(r"\sand\s", str(text), maxsplit=1, flags=re.IGNORECASE)
    if len(parts) == 2:
        return (parts[0].strip(), parts[1].strip())
    return (None, None)

split_pairs = df.loc[mask, "affiliations"].apply(split_affi)
df.loc[mask, "author1_affi_raw"] = split_pairs.apply(lambda x: x[0]).values
df.loc[mask, "author2_affi_raw"] = split_pairs.apply(lambda x: x[1]).values

# ---------- build dictionary lookups ----------
# exact affiliation -> institution
inst_lookup = dict(zip(dictionary["old names"], dictionary["ror_name"]))

# exact affiliation -> ror id
ror_lookup = dict(zip(dictionary["old names"], dictionary["ror_id"]))

# ---------- first fill from dictionary ----------
df.loc[mask, "author_1_institution"] = df.loc[mask, "author1_affi_raw"].map(inst_lookup)
df.loc[mask, "author_2_institution"] = df.loc[mask, "author2_affi_raw"].map(inst_lookup)

df.loc[mask, "author_1_ror_id"] = df.loc[mask, "author1_affi_raw"].map(ror_lookup)
df.loc[mask, "author_2_ror_id"] = df.loc[mask, "author2_affi_raw"].map(ror_lookup)

# ---------- ROR helpers ----------
cache = {}

def clean_text(text):
    if pd.isna(text):
        return ""
    text = str(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_ror_display_name(org):
    names = org.get("names", [])
    institution = None

    for n in names:
        if "ror_display" in n.get("types", []):
            institution = n.get("value")
            break

    if institution is None and names:
        institution = names[0].get("value")

    return institution

def ror_match(text):
    text = clean_text(text)

    if text == "":
        return {
            "institution": None,
            "ror_id": None,
            "country": None,
            "status": "empty_affiliation"
        }

    if text in cache:
        return cache[text]

    q = urllib.parse.quote(text)
    url = f"https://api.ror.org/v2/organizations?affiliation={q}&single_search"

    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        data = r.json()

        items = data.get("items", [])
        if len(items) == 0:
            result = {
                "institution": None,
                "ror_id": None,
                "country": None,
                "status": "no_match"
            }
        else:
            top = items[0]
            org = top.get("organization", top)

            country = None
            locations = org.get("locations") or []
            if locations:
                geo = locations[0].get("geonames_details") or {}
                country = geo.get("country_name") or geo.get("country_code")

            result = {
                "institution": extract_ror_display_name(org),
                "ror_id": org.get("id"),
                "country": country,
                "status": "matched"
            }

    except Exception as e:
        result = {
            "institution": None,
            "ror_id": None,
            "country": None,
            "status": f"error: {str(e)}"
        }

    cache[text] = result
    time.sleep(0.1)
    return result

# ---------- fallback to ROR if still missing ----------
mask_a1_missing = mask & df["author_1_institution"].isna()
mask_a2_missing = mask & df["author_2_institution"].isna()

match_a1 = df.loc[mask_a1_missing, "author1_affi_raw"].apply(ror_match)
match_a2 = df.loc[mask_a2_missing, "author2_affi_raw"].apply(ror_match)

df.loc[mask_a1_missing, "author_1_institution"] = match_a1.apply(lambda x: x["institution"]).values
df.loc[mask_a1_missing, "author_1_ror_id"] = match_a1.apply(lambda x: x["ror_id"]).values

df.loc[mask_a2_missing, "author_2_institution"] = match_a2.apply(lambda x: x["institution"]).values
df.loc[mask_a2_missing, "author_2_ror_id"] = match_a2.apply(lambda x: x["ror_id"]).values

# ---------- save ----------
df.to_csv(output_path, sep=";", index=False)

print("Finished.")
print("Saved to:", output_path)
print("Rows processed with and_count == 1:", int(mask.sum()))
print("Author 1 still missing institution:", int((mask & df["author_1_institution"].isna()).sum()))
print("Author 2 still missing institution:", int((mask & df["author_2_institution"].isna()).sum()))
