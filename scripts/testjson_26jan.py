# ===============================
# Import libraries
# ===============================

import re
import json
import html as html_module
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
import cloudscraper


# ===============================
# Text cleaning (与你主 pipeline 对齐)
# ===============================

def clean_html_text(raw_html):
    if raw_html is None or (isinstance(raw_html, float) and pd.isna(raw_html)):
        return ""

    x = str(raw_html)

    for _ in range(2):
        y = html_module.unescape(x)
        if y == x:
            break
        x = y

    x = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", x)

    return x.strip()


# ===============================
# Core function (对齐主 pipeline)
# ===============================

def fetch_single_paper(paper_id):
    paper_id = str(paper_id)

    scraper = cloudscraper.create_scraper(
        browser={'custom': 'ScraperBot/1.0'}
    )

    # --------------------------------------------------
    # STEP 1: XML API → title / abstract / paperDate
    # --------------------------------------------------

    xml_url = f"https://api.ssrn.com/papers/v1/papers/{paper_id}"
    r = scraper.get(xml_url, timeout=10)
    r.raise_for_status()

    root = ET.fromstring(r.text)

    title = clean_html_text(root.findtext("title", default=""))
    abstract = clean_html_text(root.findtext("abstract", default=""))
    paper_date = root.findtext("paperDate", default="")

    # --------------------------------------------------
    # STEP 2: Search API → authors (与主 pipeline 完全一致)
    # --------------------------------------------------

    search_url = (
        "https://api.ssrn.com/content/v1/bindings/205/papers/search"
        f"?index=0&count=1&sort=0&paper_id={paper_id}"
    )

    r2 = scraper.get(search_url, timeout=10)
    r2.raise_for_status()

    try:
        data = json.loads(r2.text)
    except json.JSONDecodeError:
        raise RuntimeError("❌ SSRN search API 返回非 JSON")

    papers = data.get("papers", [])
    if not papers:
        raise RuntimeError(f"❌ Paper {paper_id} not found in search API")

    paper = papers[0]

    authors = []
    for idx, a in enumerate(paper.get("authors", []), start=1):
        authors.append({
            "author_order": idx,
            "author_id": a.get("id", ""),
            "first_name": a.get("first_name", ""),
            "last_name": a.get("last_name", ""),
            "url": a.get("url", "")
        })

    return {
        "id": paper_id,
        "title": title,
        "abstract": abstract,
        "paper_date": paper_date,
        "authors": authors,
        "n_authors": len(authors),
        "source": "SSRN search API",
        "retrieved_at": datetime.now().isoformat()
    }


# ===============================
# Export helper
# ===============================

def export_paper_to_json(paper_id, output_path):
    paper_data = fetch_single_paper(paper_id)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(paper_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved to {output_path}")
    return paper_data


# ===============================
# Example usage
# ===============================

if __name__ == "__main__":
    paper_id = 2989524
    output_path = (
        "/Users/yutingren/Library/CloudStorage/Dropbox/"
        "Mac/Documents/AI/test_nov/abstract_analysis-main/"
        "ssrn_2989524.json"
    )

    export_paper_to_json(paper_id, output_path)