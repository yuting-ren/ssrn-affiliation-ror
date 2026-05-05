import argparse
import csv
import os

import pandas as pd
import requests
from tqdm import tqdm

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_XLSX = os.path.join(PROJECT_ROOT, "outputs", "Result_table_louca.xlsx")
DEFAULT_DIC = os.path.join(PROJECT_ROOT, "outputs", "dic_new.csv")
DEFAULT_SHEET = "Sheet2"
DEFAULT_DUP_REPORT = os.path.join(
    PROJECT_ROOT, "outputs", "dic_new_duplicate_cleaned_name_report.csv"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Import Louca result table, append rows into dic_new, and report duplicated cleaned names."
        )
    )
    parser.add_argument("--xlsx", default=DEFAULT_XLSX, help="Path to Result_table_louca.xlsx")
    parser.add_argument("--sheet", default=DEFAULT_SHEET, help="Sheet name to import")
    parser.add_argument("--dic", default=DEFAULT_DIC, help="Path to dic_new.csv")
    parser.add_argument(
        "--dup-report",
        default=DEFAULT_DUP_REPORT,
        help="Path to duplicate cleaned_name report CSV",
    )
    return parser.parse_args()


def normalize_text(value):
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def normalize_ror_link(value):
    text = normalize_text(value)
    if not text:
        return None
    text = text.strip('"').strip("'")
    if text.startswith("https://ror.org/"):
        return text
    if text.startswith("http://ror.org/"):
        return "https://" + text[len("http://") :]
    if text.startswith("ror.org/"):
        return "https://" + text
    if len(text) == 9 and text.isalnum():
        return f"https://ror.org/{text}"
    return text


def parse_packed_dic_new(path):
    # dic_new may be malformed as one packed column with comma-separated records.
    df_raw = pd.read_csv(path, sep=";", encoding="latin1")
    if len(df_raw.columns) != 1:
        return df_raw

    packed_col = df_raw.columns[0]
    lines = df_raw[packed_col].astype(str).tolist()
    parsed_rows = [next(csv.reader([line], delimiter=",", quotechar='"')) for line in lines]

    if not parsed_rows:
        return pd.DataFrame(columns=["raw_name", "cleaned_name", "ror_name", "ror_link", "country", "ror_status"])

    normalized_rows = []
    for row in parsed_rows:
        if len(row) < 6:
            row = row + [None] * (6 - len(row))
        elif len(row) > 6:
            overflow = ",".join(row[: len(row) - 5])
            row = [overflow] + row[len(row) - 5 :]
        normalized_rows.append(row[:6])

    expected = ["raw_name", "cleaned_name", "ror_name", "ror_link", "country", "ror_status"]
    header = [str(x).strip().lower() for x in normalized_rows[0]]
    if header == expected:
        normalized_rows = normalized_rows[1:]

    return pd.DataFrame(normalized_rows, columns=expected)


def load_dic_new(path):
    attempts = [
        (";", "utf-8"),
        (";", "utf-8-sig"),
        (";", "latin1"),
        (",", "utf-8"),
        (",", "utf-8-sig"),
        (",", "latin1"),
    ]

    required = {"raw_name", "cleaned_name", "ror_link", "country", "ror_status"}
    for sep, enc in attempts:
        try:
            df = pd.read_csv(path, sep=sep, encoding=enc)
            df.columns = df.columns.astype(str).str.strip()
            if required.issubset(set(df.columns)):
                return df
        except Exception:
            continue

    return parse_packed_dic_new(path)


def get_ror_id_from_link(ror_link):
    link = normalize_ror_link(ror_link)
    if not link:
        return None
    return link.rstrip("/").split("/")[-1]


def fetch_ror_metadata_from_api(ror_link):
    ror_id = get_ror_id_from_link(ror_link)
    if not ror_id:
        return {"ror_name": None, "country": None, "ror_status": None}

    url = f"https://api.ror.org/v2/organizations/{ror_id}"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        org = data.get("organization", data)

        names = org.get("names", [])
        ror_name = None
        for n in names:
            if "ror_display" in n.get("types", []):
                ror_name = n.get("value")
                break
        if ror_name is None and names:
            ror_name = names[0].get("value")

        country = None
        locations = org.get("locations") or []
        if locations:
            geo = locations[0].get("geonames_details") or {}
            country = geo.get("country_name") or geo.get("country_code")

        return {"ror_name": normalize_text(ror_name), "country": normalize_text(country), "ror_status": "matched"}
    except Exception as e:
        return {"ror_name": None, "country": None, "ror_status": f"error: {e}"}


def main():
    args = parse_args()

    if not os.path.exists(args.xlsx):
        raise FileNotFoundError(f"XLSX not found: {args.xlsx}")
    if not os.path.exists(args.dic):
        raise FileNotFoundError(f"dic_new not found: {args.dic}")

    # 1) Read Louca table
    louca = pd.read_excel(args.xlsx, sheet_name=args.sheet)
    louca.columns = louca.columns.astype(str).str.strip()

    required_source_cols = {"affiliations", "affiliations_simplified"}
    if not required_source_cols.issubset(set(louca.columns)):
        raise ValueError(
            f"Source sheet must contain {sorted(required_source_cols)}. Found: {louca.columns.tolist()}"
        )

    # 2) Rename source columns as requested
    louca = louca.rename(
        columns={
            "affiliations": "raw_name",
            "affiliations_simplified": "cleaned_name",
            "ror_id": "ror_link",
            "location(SSRN)": "country",
        }
    )

    if "ror_link" not in louca.columns:
        louca["ror_link"] = None
    if "country" not in louca.columns:
        louca["country"] = None

    louca["raw_name"] = louca["raw_name"].apply(normalize_text)
    louca["cleaned_name"] = louca["cleaned_name"].apply(normalize_text)
    louca["ror_link"] = louca["ror_link"].apply(normalize_ror_link)
    louca["country"] = louca["country"].apply(normalize_text)

    # Add minimal required dic columns.
    louca["ror_name"] = louca.get("ror_name", None)
    louca["ror_status"] = louca["ror_link"].apply(lambda x: "matched" if normalize_text(x) else None)

    # 3) Load dic_new for append target.
    dic = load_dic_new(args.dic)
    for col in ["raw_name", "cleaned_name", "ror_name", "ror_link", "country", "ror_status"]:
        if col not in dic.columns:
            dic[col] = None

    dic["ror_link"] = dic["ror_link"].apply(normalize_ror_link)
    dic["country"] = dic["country"].apply(normalize_text)

    # 4) Query ROR website API for each unique ror_link to fill ror_name/country.
    unique_links = [
        x for x in louca["ror_link"].dropna().astype(str).str.strip().unique().tolist()
        if x
    ]
    ror_meta = {}
    for link in tqdm(unique_links, desc="Query ROR by ror_link"):
        ror_meta[link] = fetch_ror_metadata_from_api(link)

    louca["ror_name"] = louca.apply(
        lambda r: (
            ror_meta.get(r["ror_link"], {}).get("ror_name") or r.get("ror_name")
            if normalize_text(r["ror_link"])
            else r.get("ror_name")
        ),
        axis=1,
    )
    louca["country"] = louca.apply(
        lambda r: (
            ror_meta.get(r["ror_link"], {}).get("country") or r["country"]
            if normalize_text(r["ror_link"])
            else r["country"]
        ),
        axis=1,
    )
    louca["ror_status"] = louca.apply(
        lambda r: (
            ror_meta.get(r["ror_link"], {}).get("ror_status") or r.get("ror_status")
            if normalize_text(r["ror_link"])
            else r.get("ror_status")
        ),
        axis=1,
    )

    # Keep rows with at least one meaningful field to append.
    louca_append = louca[["raw_name", "cleaned_name", "ror_name", "ror_link", "country", "ror_status"]].copy()
    louca_append = louca_append[
        louca_append[["raw_name", "cleaned_name", "ror_link", "country"]].notna().any(axis=1)
    ]

    # 5) Append ALL raw names from louca into dic_new (no dedupe by raw_name).
    merged = pd.concat([dic[["raw_name", "cleaned_name", "ror_name", "ror_link", "country", "ror_status"]], louca_append], ignore_index=True)

    # 6) Patch existing rows: if country is empty but ror_link exists, query ROR API and backfill.
    merged["ror_link"] = merged["ror_link"].apply(normalize_ror_link)
    merged["country"] = merged["country"].apply(normalize_text)
    merged["ror_name"] = merged["ror_name"].apply(normalize_text)

    patch_mask = merged["country"].isna() & merged["ror_link"].notna() & (
        merged["ror_link"].astype(str).str.strip() != ""
    )
    patch_links = merged.loc[patch_mask, "ror_link"].astype(str).str.strip().unique().tolist()

    patch_meta = {}
    for link in tqdm(patch_links, desc="Patch empty country by ror_link"):
        patch_meta[link] = fetch_ror_metadata_from_api(link)

    def _patch_country(row):
        if pd.notna(row["country"]) and str(row["country"]).strip() != "":
            return row["country"]
        link = normalize_text(row["ror_link"])
        if not link:
            return row["country"]
        return patch_meta.get(link, {}).get("country") or row["country"]

    def _patch_ror_name(row):
        if pd.notna(row["ror_name"]) and str(row["ror_name"]).strip() != "":
            return row["ror_name"]
        link = normalize_text(row["ror_link"])
        if not link:
            return row["ror_name"]
        return patch_meta.get(link, {}).get("ror_name") or row["ror_name"]

    merged["country"] = merged.apply(_patch_country, axis=1)
    merged["ror_name"] = merged.apply(_patch_ror_name, axis=1)

    # 7) Report duplicated cleaned_name in current dictionary
    cleaned_counts = (
        merged["cleaned_name"]
        .fillna("")
        .astype(str)
        .str.strip()
        .value_counts()
        .rename_axis("cleaned_name")
        .reset_index(name="count")
    )
    dup_clean = cleaned_counts[(cleaned_counts["cleaned_name"] != "") & (cleaned_counts["count"] > 1)].copy()
    dup_clean.to_csv(args.dup_report, sep=";", index=False)

    # Save normalized dic_new in proper semicolon format.
    merged.to_csv(args.dic, sep=";", index=False)

    patched_rows_after = int(
        (
            merged["country"].notna()
            & merged["ror_link"].notna()
            & (merged["ror_link"].astype(str).str.strip() != "")
        ).sum()
    )

    print("Imported sheet:", args.sheet)
    print("Louca rows read:", len(louca))
    print("Louca rows appended:", len(louca_append))
    print("Patched candidate links:", len(patch_links))
    print("Saved dic_new:", args.dic)
    print("Total dic_new rows now:", len(merged))
    print("Rows with non-empty country and non-empty ror_link after patch:", patched_rows_after)
    print("Duplicate cleaned_name count:", len(dup_clean))
    if len(dup_clean) > 0:
        print("Top duplicate cleaned_name:")
        print(dup_clean.head(20).to_string(index=False))
    print("Duplicate report:", args.dup_report)


if __name__ == "__main__":
    main()
