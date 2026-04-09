import pandas as pd
import requests
import urllib.parse
import re
import numpy as np
import time

file_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract.csv"

# 读取数据
df = pd.read_csv(file_path, sep=";", engine="python")
df.columns = df.columns.str.strip()

# 清理 affiliations
df["affiliations"] = df["affiliations"].replace(
    {
        r"(?i)^independent$": np.nan,
        r"(?i)^affiliation not provided to ssrn$": np.nan
    },
    regex=True
)

# 只保留 2 位作者的论文：author_2_id 非空，author_3_id 为空
df_two_authors = df[
    (df["author_2_id"].notna()) &
    (df["author_3_id"].isna())
].copy()

# 统计 " and " 出现次数
df_two_authors["and_count"] = (
    df_two_authors["affiliations"]
    .fillna("")
    .str.lower()
    .str.count(r"\sand\s")
)

# 只对 and_count == 1 的情况做拆分
df_two_authors["author1_affi_raw"] = np.nan
df_two_authors["author2_affi_raw"] = np.nan

mask_split = df_two_authors["and_count"] == 1

split_result = df_two_authors.loc[mask_split, "affiliations"].str.split(
    r"\sand\s", n=1, expand=True
)

df_two_authors.loc[mask_split, "author1_affi_raw"] = split_result[0].str.strip()
df_two_authors.loc[mask_split, "author2_affi_raw"] = split_result[1].str.strip()

# 缓存，避免重复请求
cache = {}

def clean_text(text):
    if pd.isna(text):
        return ""
    text = str(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

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
        r = requests.get(url, timeout=20)
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
                "institution": org.get("name"),
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

# 分别匹配两个 raw affiliation
match_1 = df_two_authors["author1_affi_raw"].apply(ror_match_debug)
match_2 = df_two_authors["author2_affi_raw"].apply(ror_match_debug)

# 生成 author 1 变量
df_two_authors["author_1_institution"] = match_1.apply(lambda x: x["institution"])
df_two_authors["author_1_ror_id"] = match_1.apply(lambda x: x["ror_id"])
df_two_authors["author_1_country"] = match_1.apply(lambda x: x["country"])
df_two_authors["author_1_ror_status"] = match_1.apply(lambda x: x["status"])

# 生成 author 2 变量
df_two_authors["author_2_institution"] = match_2.apply(lambda x: x["institution"])
df_two_authors["author_2_ror_id"] = match_2.apply(lambda x: x["ror_id"])
df_two_authors["author_2_country"] = match_2.apply(lambda x: x["country"])
df_two_authors["author_2_ror_status"] = match_2.apply(lambda x: x["status"])

# 保存结果
output_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_two_authors_ror.csv"
df_two_authors.to_csv(output_path, sep=";", index=False)

print("Done.")
print("Saved to:", output_path)

print("\nAuthor 1 ROR status:")
print(df_two_authors["author_1_ror_status"].value_counts(dropna=False))

print("\nAuthor 2 ROR status:")
print(df_two_authors["author_2_ror_status"].value_counts(dropna=False))