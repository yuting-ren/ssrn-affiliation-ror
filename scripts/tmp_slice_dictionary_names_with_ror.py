import os
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def process_v2(input_path, output_path, anomalies_path):
    df = pd.read_csv(input_path, sep=";")

    for c in ["ror_name", "ror_link", "country", "ror_status", "cleaned_name"]:
        df[c] = df[c].astype("string").str.strip()

    matched = df["ror_status"].fillna("").str.lower().eq("matched")

    # 每个 cleaned_name 取第一条 matched 记录作为回填来源
    source = (
        df[matched]
        .dropna(subset=["cleaned_name"])
        .groupby("cleaned_name", sort=False)[["ror_name", "ror_link", "country"]]
        .first()
    )

    for col in ["ror_name", "ror_link", "country"]:
        src_col = f"__src_{col}"
        df = df.join(source[[col]].rename(columns={col: src_col}), on="cleaned_name")
        miss = df[col].isna() | (df[col].astype("string").str.strip() == "")
        df.loc[miss, col] = df.loc[miss, src_col]
        df.drop(columns=[src_col], inplace=True)

    # 异常：同一 cleaned_name 下 matched 超过 1 条
    anomalies = (
        df[matched]
        .groupby("cleaned_name", dropna=False)
        .agg(
            matched_count=("ror_status", "size"),
            distinct_ror_link=("ror_link", lambda s: s.dropna().nunique()),
            distinct_ror_name=("ror_name", lambda s: s.dropna().nunique()),
            distinct_country=("country", lambda s: s.dropna().nunique()),
            ror_links=("ror_link", lambda s: " | ".join(pd.unique(s.dropna().astype(str)))),
            ror_names=("ror_name", lambda s: " | ".join(pd.unique(s.dropna().astype(str)))),
            countries=("country", lambda s: " | ".join(pd.unique(s.dropna().astype(str)))),
        )
        .reset_index()
    )
    anomalies = anomalies[anomalies["matched_count"] > 1].sort_values(
        ["matched_count", "cleaned_name"], ascending=[False, True]
    )

    for c in ["ror_name", "ror_link", "country", "ror_status", "cleaned_name"]:
        df[c] = df[c].astype(object)

    df.to_csv(output_path, sep=";", index=False)
    anomalies.to_csv(anomalies_path, sep=";", index=False)
    return len(df), len(anomalies)


if __name__ == "__main__":
    v2_input_path = os.path.join(PROJECT_ROOT, "outputs", "dictionary_names_with_ror_v2.csv")
    v2_path = os.path.join(PROJECT_ROOT, "outputs", "dictionary_names_with_ror_v2.csv")
    anomalies_path = os.path.join(
        PROJECT_ROOT,
        "outputs",
        "dictionary_names_with_ror_v2_anomalies_multi_matched_cleaned_name.csv",
    )

    v2_rows, anomaly_count = process_v2(v2_input_path, v2_path, anomalies_path)

    print("Saved v2:", v2_path)
    print("V2 rows:", v2_rows)
    print("Saved anomalies:", anomalies_path)
    print("Anomaly cleaned_name count:", anomaly_count)
