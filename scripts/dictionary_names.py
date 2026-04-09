import re

import pandas as pd


input_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_single_author_ror_short.csv"
output_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/dictionary_names.csv"


def simplify_affiliation(text):
    if pd.isna(text):
        return None
    text = str(text).lower()
    text = re.sub(r"\band\b", "", text)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", "", text).strip()
    return text


df = pd.read_csv(input_path, sep=";", engine="python")

df_names = pd.DataFrame()
df_names["raw_name"] = df["affiliations"]
df_names = df_names.dropna()
df_names = df_names.drop_duplicates()

df_names["cleaned_name"] = df_names["raw_name"].apply(simplify_affiliation)

df_names.to_csv(output_path, sep=";", index=False)

print("Dictionary names created.")
print("Saved to:", output_path)
print("Number of rows:", len(df_names))
