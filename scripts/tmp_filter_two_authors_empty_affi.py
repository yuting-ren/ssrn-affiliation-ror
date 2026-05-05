import os
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
input_path = os.path.join(PROJECT_ROOT, "outputs", "db_info_abstract_two_authors_dic_names_all.csv")
full_output_path = os.path.join(PROJECT_ROOT, "outputs", "db_info_abstract_two_authors_empty_affi_full_rows.csv")
output_path = os.path.join(PROJECT_ROOT, "outputs", "db_info_abstract_two_authors_empty_affi_affiliations_original.csv")

df = pd.read_csv(input_path, sep=";")

for c in ["author1_affi", "author2_affi", "affiliations_original"]:
    if c not in df.columns:
        raise ValueError(f"Missing required column: {c}")

mask = (
    df["author1_affi"].isna()
    | (df["author1_affi"].astype(str).str.strip() == "")
    | df["author2_affi"].isna()
    | (df["author2_affi"].astype(str).str.strip() == "")
)

full_out = df.loc[mask].copy()
full_out.to_csv(full_output_path, sep=";", index=False)

out = full_out.loc[:, ["affiliations_original"]].copy()
out.to_csv(output_path, sep=";", index=False)

print("Saved:", full_output_path)
print("Saved:", output_path)
print("Input rows:", len(df))
print("Filtered rows:", len(full_out))
