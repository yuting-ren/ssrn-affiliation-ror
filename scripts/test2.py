# 只保留 single-author


import pandas as pd
import requests
import urllib.parse
import re
import numpy as np
import time

file_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract.csv"

df = pd.read_csv(file_path, sep=";", engine="python")
df.columns = df.columns.str.strip()

# 清理 affiliation
df["affiliations"] = df["affiliations"].replace(
    {
        r"(?i)^independent$": np.nan,
        r"(?i)^affiliation not provided to ssrn$": np.nan
    },
    regex=True
)

# 只保留 single-author
df_single = df[df["author_2_id"].isna()].copy()

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

    # 优先找 ror_display
    for n in names:
        if "ror_display" in n.get("types", []):
            institution = n.get("value")
            break

    # 如果没有，再退回第一个名字
    if institution is None and names:
        institution = names[0].get("value")

    return institution

def ror_match_debug(text):
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
    time.sleep(0.1)   # 稍微放慢一点，避免打 API 太快
    return result

# 跑匹配
match_results = df_single["affiliations"].apply(ror_match_debug)

df_single["author_1_institution"] = match_results.apply(lambda x: x["institution"])
df_single["author_1_ror_url"] = match_results.apply(lambda x: x["ror_id"])
df_single["author_1_country"] = match_results.apply(lambda x: x["country"])
df_single["ror_status"] = match_results.apply(lambda x: x["status"])

df_single["author_1_ror_id"] = (
    df_single["author_1_ror_url"]
    .fillna("")
    .str.replace("https://ror.org/", "", regex=False)
)

visible_cols = [
    c for c in df_single.columns
    if not re.match(r"author_(?:[5-9]|[1-5][0-9]|60)_(id|last_name|first_name|url)$", c)
]

df_view = df_single[visible_cols]
# 保存
output_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_single_author_institution_debug.csv"
df_view.to_csv(output_path, sep=";", index=False)

print("Done.")
print("Saved to:", output_path)

# 看看统计
print(df_single["ror_status"].value_counts(dropna=False))