import re
import requests
import urllib.parse
import pandas as pd

raw_affiliation = "Comenius University, affiliation not provided to SSRN and Hungarian Academy of Sciences (HAS) - Centre for Social Sciences"


def clean_text(text: str) -> str:
    """Basic text cleaning."""
    text = str(text).strip()
    text = re.sub(r'affiliation not provided to SSRN', '', text, flags=re.I)
    text = re.sub(r"\s+", " ", text)
    return text


def generate_candidates(text: str):
    """
    Generate candidate institution spans.
    Current test version:
    1. keep full string
    2. split conservatively on top-level ' and '
    """
    candidates = set()
    text = clean_text(text)

    # full string as one candidate
    candidates.add(text)

    # conservative split on ' and '
    parts = re.split(r"\s+\band\b\s+", text, flags=re.IGNORECASE)
    parts = [p.strip(" ,;") for p in parts if p.strip(" ,;")]

    for p in parts:
        candidates.add(p)

    return list(candidates)


def ror_match(candidate: str):
    """
    Match one candidate string against ROR affiliation endpoint.
    """
    q = urllib.parse.quote(candidate)
    url = f"https://api.ror.org/v2/organizations?affiliation={q}&single_search"

    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()

    items = data.get("items", [])
    if not items:
        return {
            "candidate": candidate,
            "matched": False,
            "ror_id": None,
            "ror_name": None,
            "country": None,
            "score": None
        }

    top = items[0]
    org = top.get("organization", top)

    country = None
    locations = org.get("locations") or []
    if locations:
        geo = locations[0].get("geonames_details") or {}
        country = geo.get("country_name") or geo.get("country_code")

    return {
        "candidate": candidate,
        "matched": True,
        "ror_id": org.get("id"),
        "ror_name": org.get("name"),
        "country": country,
        "score": top.get("score")
    }


def extract_institutions_from_affiliation(raw_text: str):
    """
    Full test pipeline:
    raw affiliation
      -> clean text
      -> generate candidate institution spans
      -> match each candidate to ROR
      -> return results
    """
    cleaned = clean_text(raw_text)
    candidates = generate_candidates(cleaned)

    results = []
    for cand in candidates:
        try:
            results.append(ror_match(cand))
        except Exception as e:
            results.append({
                "candidate": cand,
                "matched": False,
                "ror_id": None,
                "ror_name": None,
                "country": None,
                "score": None,
                "error": str(e)
            })

    df = pd.DataFrame(results)

    # optional: sort by matched first, then score descending
    if "score" in df.columns:
        df = df.sort_values(by=["matched", "score"], ascending=[False, False], na_position="last")

    return df


if __name__ == "__main__":
    df_result = extract_institutions_from_affiliation(raw_affiliation)

    print("=== RAW AFFILIATION ===")
    print(raw_affiliation)
    print()

    print("=== TEST RESULTS ===")
    print(df_result.to_string(index=False))


    df_result = extract_institutions_from_affiliation(raw_affiliation)

    print(df_result)

    # 保存为 Excel
    output_file = "ror_test_result.xlsx"
    df_result.to_excel(output_file, index=False)

    print(f"\nResult saved to: {output_file}")