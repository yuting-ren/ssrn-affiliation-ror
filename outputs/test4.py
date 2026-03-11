# 只保留 2-author



import pandas as pd
import requests
import urllib.parse
import re
import numpy as np

# ---------- paths ----------
file_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract.csv"
output_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_two_authors_ror.csv"
dict_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/dictionary.csv"

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

# ---------- clean affiliations ----------
df["affiliations"] = df["affiliations"].replace(
    {
        r"(?i)^independent$": np.nan,
        r"(?i)^affiliation not provided to ssrn$": np.nan
    },
    regex=True
)

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

# ---------- update dictionary old names using author1_affi_raw + author_1_ror_id ----------
author1_lookup = (
    df[["author1_affi_raw", "author_1_ror_id"]]
    .dropna(subset=["author1_affi_raw", "author_1_ror_id"])
    .drop_duplicates()
)

if "ror_id" in dictionary.columns:
    dictionary = dictionary.merge(
        author1_lookup,
        on="ror_id",
        how="left"
    )

    if "old names" in dictionary.columns:
        dictionary["old names"] = dictionary["author1_affi_raw"].combine_first(dictionary["old names"])
    else:
        dictionary["old names"] = dictionary["author1_affi_raw"]

    dictionary = dictionary.drop(columns=["author1_affi_raw"])
else:
    print("Warning: dictionary does not contain 'ror_id'; skipping dictionary update.")

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