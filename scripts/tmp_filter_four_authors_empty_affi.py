import os
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
input_path = os.path.join(PROJECT_ROOT, "outputs", "db_info_abstract_four_authors_dic_names_all.csv")
output_path = os.path.join(PROJECT_ROOT, "outputs", "db_info_abstract_four_authors_empty_affi_affiliations_original.csv")

df = pd.read_csv(input_path, sep=";")

for c in ["author1_affi", "author2_affi", "author3_affi", "author4_affi", "affiliations_original"]:
    if c not in df.columns:
        raise ValueError(f"Missing required column: {c}")

mask = (
    df["author1_affi"].isna()
    | (df["author1_affi"].astype(str).str.strip() == "")
    | df["author2_affi"].isna()
    | (df["author2_affi"].astype(str).str.strip() == "")
    | df["author3_affi"].isna()
    | (df["author3_affi"].astype(str).str.strip() == "")
    | df["author4_affi"].isna()
    | (df["author4_affi"].astype(str).str.strip() == "")
)

out = df.loc[mask, ["affiliations_original"]].copy()
out.to_csv(output_path, sep=";", index=False)

print("Saved:", output_path)
print("Input rows:", len(df))
print("Filtered rows:", len(out))
