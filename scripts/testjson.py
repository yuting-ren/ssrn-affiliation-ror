# ===============================
# Import libraries
# ===============================

import re
import json
import html as html_module
import requests
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
import cloudscraper


# ===============================
# Text cleaning (与你现有 pipeline 对齐)
# ===============================

def clean_html_text(raw_html):
    if raw_html is None or (isinstance(raw_html, float) and pd.isna(raw_html)):
        return ""

    x = str(raw_html)

    # 最多两次 unescape，避免过度解码
    for _ in range(2):
        y = html_module.unescape(x)
        if y == x:
            break
        x = y

    # 删除控制字符（解决 Corrupció, 这类问题）
    x = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", x)

    return x.strip()


# ===============================
# Core function: fetch one SSRN paper
# ===============================

def fetch_single_paper(paper_id):
    paper_id = str(paper_id)

    scraper = cloudscraper.create_scraper(
        browser={'custom': 'ScraperBot/1.0'}
    )

    # ---------- STEP 1: XML API (title / abstract) ----------
    paper_url = f"https://api.ssrn.com/papers/v1/papers/{paper_id}"
    r = scraper.get(paper_url, timeout=10)
    r.raise_for_status()

    root = ET.fromstring(r.text)

    title = clean_html_text(root.findtext("title", default=""))
    abstract = clean_html_text(root.findtext("abstract", default=""))
    paper_date = root.findtext("paperDate", default="")

    # ---------- STEP 2: Search API (authors) ----------
    search_url = (
        "https://api.ssrn.com/content/v1/bindings/205/papers/search"
        "?index=0&count=50&sort=0&term=a"
    )

    authors = []
    r2 = scraper.get(search_url, timeout=10)
    content = r2.text.strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        print("⚠️ Search API blocked / non-JSON response")
        data = {}

    for paper in data.get("papers", []):
        if str(paper.get("id")) == paper_id:
            for idx, a in enumerate(paper.get("authors", []), start=1):
                authors.append({
                    "author_order": idx,
                    "author_id": a.get("id", ""),
                    "first_name": a.get("first_name", ""),
                    "last_name": a.get("last_name", ""),
                    "url": a.get("url", "")
                })
            break

    return {
        "id": paper_id,
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "paper_date": paper_date,
        "source": "SSRN",
        "retrieved_at": datetime.now().isoformat()
    }


# ===============================
# Export helper
# ===============================

def export_paper_to_json(paper_id, output_path=None):
    """
    Fetch a single paper and export it to JSON.
    """

    paper_data = fetch_single_paper(paper_id)

    if output_path is None:
        output_path = f"ssrn_{paper_id}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(paper_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved to {output_path}")

    return paper_data


# ===============================
# Example usage
# ===============================

if __name__ == "__main__":
    paper_id = 2959422
    output_path = (
        "/Users/yutingren/Library/CloudStorage/Dropbox/"
        "Mac/Documents/AI/test_nov/abstract_analysis-main/"
        "ssrn_2959422.json"
    )

    export_paper_to_json(paper_id, output_path)