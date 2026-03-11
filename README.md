# Analysis of abstracts

This Python project scrapes and analyzes academic article abstracts by extracting linguistic statistics, affiliation information, and generating visualizations. It is designed to help researchers compare readability of abstracts on a wanted period.

An example of its usage is the paper I wrote that can be found in annex.

## Features

* Extracts informations and abstracts on SSRN website (`scripts/info_abstract.py`)
* Attributes author affiliations to paper (`scripts/aff_1_author.py`)
* Performs statistical computations (`scripts/computations.py`)
* Generates visualizations and statistical summaries (`scripts/analysis.py`)
* Main script to run the full analysis pipeline (`main.py`)

## Project Structure

```
ABSTRACT_ANALYSIS/
├── annexes/
│   ├── ChatGPT_report.pdf
│   └── creation_list/
│       ├── creation_list.py
│       ├── db_first_10000.xlsx
│       ├── Nber_non_selected_words.xlsx
│       ├── Nber_times_keywords.xlsx
│       ├── titles_found.xlsx
│       └── titles_not_found.xlsx
├── data/
│   ├── ling_web.dta
│   ├── v1.67-2025-06-24-ror-data_schema.xlsx
│   └── v1.67-2025-06-24-ror-data.xlsx
├── outputs/
│   ├── graphs/
│   │   ├── all_papers/
│   │   │   ├── monthly_average_all_metrics.png
│   │   │   ├── ...
│   │   │   └── monthly_average_ttr.png
│   │   └── by_cle/
│   │       ├── comparison_monthly_average_automated_reading.png
│   │       ├── ...
│   │       └── comparison_monthly_average_ttr.png
│   ├── aff_1_author.xlsx
│   ├── affiliations_not_found_word_count.xlsx
│   ├── analysis_all_papers.xlsx
│   ├── analysis_by_cle.xlsx
│   ├── computations.xlsx
│   └── db_info_abstract.xlsx
├── scripts/
│   ├── __pycache__/
│   ├── aff_1_author.py
│   ├── analysis.py
│   ├── computations.py
│   └── info_abstract.py
├── main.py
├── .gitignore
├── README.md
└── requirements.txt
```

## Installation

1. Clone the repository:

```bash
git clone https://github.com/ela-du-75/abstract_analysis.git
cd abstract_analysis
```

2. (Optional but recommended) Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the main script to execute the full analysis pipeline:

```bash
python main.py
```

The script reads the parameters in main.py, processes the abstracts, analyzes author affiliations, computes statistical metrics, and exports results to the `outputs/` directory. It also generates graphs saved under `outputs/graphs/`.

### Example Output Files:

* `db_info_abstract.csv` – Abstracts and information of papers scraped
* `aff_1_author.csv` – Affiliations of paper with 1 author
* `computations.csv` – Detailed statistical computations
* `analysis_all_papers.xlsx` – Overall metrics across all abstracts
* `analysis_by_cle.xlsx` – Metrics broken down by group (`cle`)



## Dependencies

All required Python packages are listed in [`requirements.txt`](requirements.txt):

* `pandas`
* `numpy`
* `tqdm`
* `textstat`
* `matplotlib`
* `nltk`

You may need to download NLTK resources if prompted (e.g., `punkt` tokenizer).

## Notes

* The inputs are to be written in the `main.py`
* Graphs and statistics are automatically saved in the `outputs/` folder.
* File paths or variable names in the scripts might need to be adjusted.
* The website where the absracts are found is https://www.ssrn.com/index.cfm/en/

# ssrn-affiliation-ror
