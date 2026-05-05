import os
import re
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
input_path = os.path.join(PROJECT_ROOT, "outputs", "two_affiliations_split_manual.csv")
output_path = os.path.join(PROJECT_ROOT, "outputs", "two_affiliations_split_manual_applied.csv")
dictionary_names_path = os.path.join(PROJECT_ROOT, "outputs", "dictionary_names.csv")


def simplify_affiliation(text):
    if pd.isna(text):
        return None
    text = str(text).lower()
    text = re.sub(r"\band\b", "", text)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", "", text).strip()
    return text

df = pd.read_csv(input_path)

required_columns = [
    "affiliation_1",
    "affiliation_2",
    "confidence",
    "manual",
    "affiliation_1_manual",
    "affiliation_2_manual",
]

for c in required_columns:
    if c not in df.columns:
        raise ValueError(f"Missing required column: {c}")

confidence = pd.to_numeric(df["confidence"], errors="coerce")
manual = pd.to_numeric(df["manual"], errors="coerce")
mask = (confidence < 61) & (manual == 0)

df.loc[mask, "affiliation_1"] = df.loc[mask, "affiliation_1_manual"]
df.loc[mask, "affiliation_2"] = df.loc[mask, "affiliation_2_manual"]

df.to_csv(output_path, index=False)

dictionary_names = pd.read_csv(dictionary_names_path, sep=";")
dictionary_names.columns = dictionary_names.columns.astype(str).str.strip()

for c in ["raw_name", "cleaned_name"]:
    if c not in dictionary_names.columns:
        raise ValueError(f"Missing required dictionary_names column: {c}")

split_names = pd.concat([df["affiliation_1"], df["affiliation_2"]], ignore_index=True)
split_names = split_names.dropna().astype(str).str.strip()
split_names = split_names[split_names != ""].drop_duplicates()

existing_raw_names = set(dictionary_names["raw_name"].dropna().astype(str).str.strip())
new_split_names = split_names[~split_names.isin(existing_raw_names)].copy()

if not new_split_names.empty:
    new_dictionary_rows = pd.DataFrame({"raw_name": new_split_names})
    new_dictionary_rows["cleaned_name"] = new_dictionary_rows["raw_name"].apply(
        simplify_affiliation
    )
    dictionary_names = pd.concat(
        [dictionary_names, new_dictionary_rows],
        ignore_index=True,
    )
    dictionary_names = dictionary_names.drop_duplicates(subset=["raw_name"], keep="first")
    dictionary_names.to_csv(dictionary_names_path, sep=";", index=False)

print("Saved:", output_path)
print("Updated dictionary_names:", dictionary_names_path)
print("Input rows:", len(df))
print("Updated rows:", int(mask.sum()))
print("Split names:", int(len(split_names)))
print("New dictionary_names rows added:", int(len(new_split_names)))
