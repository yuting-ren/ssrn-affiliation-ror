import pandas as pd
import requests
import urllib.parse
import re
import time

dict_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/dictionary.csv"
data_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_two_authors_ror.csv"
output_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/affiliation_substituted.csv"

# ---------- read files ----------
dictionary = pd.read_csv(dict_path, sep=";")
df = pd.read_csv(data_path, sep=";")

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

df["affiliations"] = df["affiliations"].astype(str)

# ---------- dictionary mappings ----------
# affiliations -> short ror id
affi_to_ror = dict(
    sorted(
        zip(dictionary["old names"], dictionary["ror_id"]),
        key=lambda x: len(str(x[0])),
        reverse=True
    )
)

# short ror id -> institution
ror_to_inst = dict(zip(dictionary["ror_id"], dictionary["ror_name"]))

# ---------- replace known affiliations with short ror ids ----------
mask_replace = df["and_count"] != 1

def replace_affiliation(text):
    if pd.isna(text):
        return text
    text = str(text)
    for affi, ror in affi_to_ror.items():
        if pd.notna(affi) and affi in text:
            text = text.replace(affi, str(ror))
    return text

df.loc[mask_replace, "affiliations"] = df.loc[mask_replace, "affiliations"].apply(replace_affiliation)

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

# ---------- first pass: fill institutions from dictionary ----------
def find_institution(text):
    if pd.isna(text):
        return None
    text = str(text).strip()
    for ror, inst in ror_to_inst.items():
        if pd.notna(ror) and str(ror) in text:
            return inst
    return None

author1_inst_dict = df["author1_affi_raw"].apply(find_institution)
author2_inst_dict = df["author2_affi_raw"].apply(find_institution)

if "author_1_institution" in df.columns:
    df["author_1_institution"] = df["author_1_institution"].combine_first(author1_inst_dict)
else:
    df["author_1_institution"] = author1_inst_dict

if "author_2_institution" in df.columns:
    df["author_2_institution"] = df["author_2_institution"].combine_first(author2_inst_dict)
else:
    df["author_2_institution"] = author2_inst_dict

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

# ---------- second pass: ROR match raw affiliation fields ----------
match_1 = df["author1_affi_raw"].apply(ror_match)
match_2 = df["author2_affi_raw"].apply(ror_match)

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
df["author_1_ror_url"] = match_1.apply(lambda x: x["ror_id"])
df["author_1_country"] = match_1.apply(lambda x: x["country"])
df["author_1_ror_status"] = match_1.apply(lambda x: x["status"])
df["author_1_ror_id"] = (
    df["author_1_ror_url"]
    .fillna("")
    .str.replace("https://ror.org/", "", regex=False)
)

# author 2 outputs
df["author_2_ror_url"] = match_2.apply(lambda x: x["ror_id"])
df["author_2_country"] = match_2.apply(lambda x: x["country"])
df["author_2_ror_status"] = match_2.apply(lambda x: x["status"])
df["author_2_ror_id"] = (
    df["author_2_ror_url"]
    .fillna("")
    .str.replace("https://ror.org/", "", regex=False)
)

# ---------- save ----------
df.to_csv(output_path, sep=";", index=False)

print("Replacement + ROR matching finished.")
print("Saved to:", output_path)
print("\nAuthor 1 status:")
print(df["author_1_ror_status"].value_counts(dropna=False))
print("\nAuthor 2 status:")
print(df["author_2_ror_status"].value_counts(dropna=False))
