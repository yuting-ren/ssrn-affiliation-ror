"""
Purpose:
- Read the single-author ROR results file.
- Keep only rows where author_1_ror_id is still empty.
- Save those unmatched rows to a CSV for follow-up review.
- Count affiliation frequencies among unmatched rows.
- Build a simplified affiliation string to help manual grouping/cleaning.
- Export the frequency table to Excel.

Input:
- outputs/db_info_abstract_single_author_ror.csv

Output:
- outputs/db_info_single_empty_ror.csv
- outputs/affiliation_freq_simplified.xlsx
"""

import re

import pandas as pd

INPUT_PATH = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_single_author_ror.csv"
FILTERED_OUTPUT_PATH = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_single_empty_ror.csv"
OUTPUT_PATH = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/affiliation_freq_simplified.xlsx"


def simplify_affiliation(text):
    if pd.isna(text):
        return None
    text = str(text).lower()
    text = re.sub(r"\band\b", "", text)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", "", text).strip()
    return text


df = pd.read_csv(INPUT_PATH, sep=";", engine="python")

if "affiliations" not in df.columns:
    raise KeyError("Column 'affiliations' not found in db_info_abstract_single_author_ror.csv")
if "author_1_ror_id" not in df.columns:
    raise KeyError("Column 'author_1_ror_id' not found in db_info_abstract_single_author_ror.csv")

df = df[df["author_1_ror_id"].fillna("").astype(str).str.strip() == ""].copy()
df.to_csv(FILTERED_OUTPUT_PATH, sep=";", index=False)

df_freq = (
    df[["affiliations"]]
    .dropna(subset=["affiliations"])
    .assign(affiliations=lambda x: x["affiliations"].astype(str).str.strip())
)
df_freq = df_freq[df_freq["affiliations"] != ""]
df_freq = (
    df_freq.value_counts(subset=["affiliations"])
    .rename("frequency")
    .reset_index()
    .sort_values("frequency", ascending=False)
)
df_freq["affiliations_simplified"] = df_freq["affiliations"].apply(simplify_affiliation)
df_freq.to_excel(OUTPUT_PATH, index=False)

print("Saved to:", OUTPUT_PATH)
print("Filtered rows saved to:", FILTERED_OUTPUT_PATH)
print("Rows:", len(df_freq))
