
# Importation of libraries

import os
import re
import time
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import xml.etree.ElementTree as ET

import pandas as pd
import cloudscraper
from tqdm import tqdm


def clean_html_text(raw_html):
    if pd.isna(raw_html):
        return ""

    x = str(raw_html)

    # 🔁 关键：反复 unescape（解决 &amp;#39; → &#39; → '）
    for _ in range(5):
        y = html_module.unescape(x)
        if y == x:
            break
        x = y


    return text.strip()


def info_abstract(output_info_abstract,begin_date, end_date):

    ##################### STEP 1 : GETIING THE ARTICLES AND THEIR INFO #################

    # Creation of the scraper to be fast
    scraper = cloudscraper.create_scraper(browser={'custom': 'ScraperBot/1.0'})

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Referer': 'https://www.ssrn.com/',
    }

    keyword_list = ['accounting', 'adam', 'administration', 'agriculture', 'agricultural', 'aid', 'allocative', 'analysis',
            'ancient', 'anthropology', 'antitrust', 'approaches', 'asset', 'associations', 'auctions', 'austrian',
            'bayesian', 'behavior', 'behavioral', 'biotechnology', 'bureaucracy', 'business', 'capital', 'capitalist',
            'censored', 'change', 'choice', 'classical', 'classification', 'climate', 'clubs', 'collaborative',
            'collective', 'committees', 'commodity', 'comparative', 'compensation', 'competition', 'computational',
            'conditions', 'consumption', 'contract', 'contracts', 'corporate', 'cost-benefit', 'costs', 'crises',
            'cross-sectional', 'cultural', 'current', 'cycle', 'data', 'debt', 'demographic', 'demographics', 'design',
            'development', 'disability', 'discrete', 'discrimination', 'disequilibrium', 'distribution', 'duration',
            'dynamic', 'ecological', 'econometric', 'econometrics', 'economic', 'economics', 'economists', 'economy',
            'education', 'effect', 'efficiency', 'elections', 'energy', 'entrepreneurship', 'environment',
            'environmental', 'equation', 'equilibrium', 'equity', 'estate', 'estimation', 'evolutionary', 'exchange',
            'externalities', 'factor', 'family', 'fertility', 'finance', 'financial', 'financing', 'fiscal', 'force',
            'forecasting', 'foreign', 'forests', 'games', 'gender', 'general', 'graduate', 'growth', 'health',
            'historical', 'history', 'household', 'hypothesis', 'impact', 'income', 'index', 'individuals',
            'industrialization', 'inequality', 'inequalities', 'infrastructure', 'innovation', 'input', 'institutional',
            'institutions', 'insurance', 'integration', 'international', 'investment', 'issues', 'justice', 'labor',
            'land', 'large', 'law', 'legislatures', 'licensing', 'life', 'literacy', 'lobbying', 'macro',
            'macroeconomics', 'management', 'market', 'marketing', 'markets', 'marriage', 'marshallian',
            'mathematical', 'medieval', 'method', 'methodological', 'methodology', 'methods', 'micro',
            'microeconomic', 'microeconomics', 'mobility', 'modeling', 'models', 'modern', 'monetary', 'monopoly',
            'national', 'natural', 'neoclassical', 'neural', 'operations', 'optimization', 'organization',
            'organizational', 'output', 'panel', 'personal', 'personnel', 'policy', 'political', 'pollution',
            'prediction', 'pricing', 'principal', 'principles', 'production', 'productivity', 'property',
            'protection', 'public', 'qualitative', 'quantile', 'quantitative', 'rates', 'rationing', 'real',
            'regional', 'regression', 'regressions', 'regulation', 'relation', 'renewable', 'research', 'resource',
            'resources', 'retirement', 'risk', 'role', 'rural', 'safety', 'satisfaction', 'saving', 'sectoral',
            'security', 'services', 'simulation', 'smith', 'social', 'sociology', 'outcomes', 'governance', 'pay',
            'strategic', 'framework', 'field', 'selection', 'uncertainty', 'decision', 'fund', 'funds', 'among',
            'spatial', 'spatio-temporal', 'sports', 'standards', 'statistical', 'studies', 'study', 'sustainability',
            'sustainable', 'level', 'rights', 'right', 'switching', 'teaching', 'techniques', 'technological',
            'technologies', 'testing', 'theory', 'thought', 'threshold', 'how', 'time', 'power', 'money', 'review',
            'control', 'system', 'between', 'china', 'healthcare', 'india', 'against', 'under', 'time-series',
            'total', 'tourism', 'trade', 'transfers', 'transportation', 'treatment', 'truncated', 'through',
            'states', 'usa', 'us', 'america', 'preferences', 'industry', 'level', 'local', 'firms', 'firm',
            'risk', 'trading', 'countries', 'bank', 'banks', 'turnover', 'undergraduate', 'unemployment', 'unions',
            'urban', 'value', 'values', 'variables', 'voting', 'wage', 'wages', 'eu', 'future', 'technology',
            'immigration', 'perspective', 'water', 'welfare', 'working', 'works', 'global', 'optimal', 'performance',
            'credit', 'debit', 'strategies', 'strategy', 'dynamics', 'returns', 'intelligence', 'inflation',
            'recession', 'conflict', 'tax', 'male', 'men', 'info', 'term', 'trad', 'omic', 'gap', 'price',
            'valuation', 'approach', 'model', 'information', 'carbon', 'new', 'what', 'central', 'school', 'span',
            'evidence', 'learn', 'perform', 'why', 'ai', 'from', 'learning', 'effects', 'problem', 'problems',
            'case', 'during', 'covid', 'people', 'challenges', 'network', 'war', 'demand', 'investors',
            'investor', 'consequences', 'consumers', 'consume', 'work', 'prices', 'price', 'implications', 'job',
            'measuring', 'supply', 'rate', 'experience', 'based', 'level', 'high', 'earnings', 'post', 'digital',
            'government', 'with', 'self', 'transition', 'success', 'unveiling', 'lending', 'who', 'exposure',
            'networks', 'persuasion', 'rules', 'return', 'trade', 'opportunities', 'systems', 'critical',
            'influence', 'green', 'cost', 'part', 'moral', 'tax', 'formation', 'world', 'determinants',
            'banking', 'cooperation', 'collusion', 'investing', 'limits', 'platform', 'human', 'regulatory',
            'africa', 'random', 'state', 'nigeria', 'post', 'economy', 'understanding', 'examination',
            'student', 'report', 'momentum', 'introduction', 'century', 'mechanism', 'process', 'financial',
            'housing', 'speculation', 'minimum', 'migration', 'blockchain', 'violence', 'media', 'reporting',
            'country', 'restrictions', 'europe', 'versus', 'city', 'incentives', 'assessing', 'revisited',
            'quality', 'stable', 'matter', 'years', 'legal', 'federal', 'order', 'implementation', 'after']
    N_KEYWORDS = 20
    keyword_list = keyword_list[:N_KEYWORDS]

    list_index = [0]

    # Creation of a list of all the indexes we are going to use

    list_link = []
    for word in keyword_list:
        for index in list_index:
            link = f"https://api.ssrn.com/content/v1/bindings/205/papers/search?index={index}&count=5000&sort=0&term={word}"
            list_link.append(link)

    # Getting the information of the articles with a keyword in the title
    def fetch_url(url):
        try:
            response = scraper.get(url, headers=headers, timeout=10)
            content = response.text.strip()

            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                return []

            result = []

            for paper in data.get('papers', []):
                approved_date = paper.get('approved_date', '').strip()
                try:
                    formatted = datetime.strptime(approved_date, "%d %b %Y").strftime("%Y-%m-%d")
                except ValueError:
                    continue

                if formatted >= begin_date and formatted <= end_date:
                    authors = paper.get('authors', [])
                    author_data = {}
                    for idx, author in enumerate(authors, start=1):
                        author_data[f'author_{idx}_id'] = author.get('id', '')
                        author_data[f'author_{idx}_last_name'] = author.get('last_name', '')
                        author_data[f'author_{idx}_first_name'] = author.get('first_name', '')
                        author_data[f'author_{idx}_url'] = author.get('url', '')

                    result.append({
                        'titre': paper.get('title', '').strip(),
                        'id': paper.get('id', ''),
                        'abstract_type': paper.get('abstract_type', '').strip(),
                        'publication_status': paper.get('publication_status', '').strip(),
                        'is_paid': paper.get('is_paid', False),
                        'reference': paper.get('reference', '').strip(),
                        'page_count': paper.get('page_count', None),
                        'url': paper.get('url', '').strip(),
                        'affiliations': paper.get('affiliations', '').strip(),
                        'is_approved': paper.get('is_approved', False),
                        'approved_date': approved_date,
                        'downloads': paper.get('downloads', 0),
                        **author_data
                    })
            return result

        except Exception as e:
            print(f"Error for URL {url} : {e}")
            return []

    # Running the parallel

    max_threads = 8
    all_results = []

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {executor.submit(fetch_url, url): url for url in list_link}

        for future in tqdm(as_completed(futures), total=len(futures), desc="Downloading the articles (step 1/6)"):
            try:
                data_chunk = future.result()
                if data_chunk:
                    all_results.extend(data_chunk)
            except Exception as e:
                print(f"Erreur lors du traitement d’un lien : {e}")

    if all_results:
        db_info = pd.DataFrame(all_results)

        # Cleaning the special caracters
        db_info = db_info.map(lambda s: re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', ' ', s) if isinstance(s, str) else s)
        
        for col in db_info.select_dtypes(include='object').columns:
            db_info[col] = db_info[col].str.replace(';', ',', regex=False)

        db_info = db_info.drop_duplicates()
        print(f"File created with {len(db_info)} articles")
    else:
        print("⚠️ No result found")





    ##################### STEP 2 : GETIING THE ABSTRACTS ######################






    # Using a scraper to go fast
    scraper = cloudscraper.create_scraper()
    db_info['id'] = db_info['id'].astype(str)
    ids_to_fetch = db_info['id']


    # Getting the abstracts
    base_url = "https://api.ssrn.com/papers/v1/papers/"

    def fetch_paper(paper_id):
        url = base_url + paper_id
        for attempt in range(retries):
            try:
                response = scraper.get(url, timeout=10)
                if response.status_code == 200:
                    root = ET.fromstring(response.text)
                    paper_date = root.findtext('paperDate', default='')
                    abstract = root.findtext('abstract', default='')
                    return {'id': paper_id, 'paperDate': paper_date, 'abstract': abstract}
            except Exception:
                time.sleep(1)
        return {'id': paper_id, 'paperDate': '', 'abstract': ''}

    # Using parallel to go fast

    max_threads = 8             # simultaneous threads to get the abstracts
    delay_between_calls = 0.01   # delay between each thread to get the abstracts
    retries = 2                 # max number of tries per article id

    results = []
    failed_ids = []

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        future_to_id = {}
        for pid in ids_to_fetch :
            future = executor.submit(fetch_paper, pid)
            future_to_id[future] = pid

        for future in tqdm(as_completed(future_to_id), total=len(future_to_id), desc="Getting the abstracts (step 2/6)"):
            pid = future_to_id[future]
            try:
                result = future.result()
                results.append(result)
                time.sleep(delay_between_calls)
                if result['abstract'] == '' and result['paperDate'] == '':
                    failed_ids.append(pid)
            except Exception:
                failed_ids.append(pid)


    # Saving the results
    df_new = pd.DataFrame(results)
    df_new['id'] = df_new['id'].astype(str)

    df_combined = pd.concat([df_new], ignore_index=True)
    df_combined = df_combined.drop_duplicates(subset='id', keep='last')
    df_result = pd.merge(db_info, df_combined, on='id', how='left')

    from bs4 import BeautifulSoup
    import html
    def clean_abstract(raw_html):
        if pd.isna(raw_html):
            return ""
        raw_html = html.unescape(raw_html)
        soup = BeautifulSoup(raw_html, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        return text
    

    
    # 1) clean HTML tags from abstracts and
    df_result['abstract'] = df_result['abstract'].apply(clean_abstract)
    df_result['abstract'] = df_result['abstract'].str.replace('\n', ' ').str.replace('\r', ' ')
    
    

    # ✅ Unified HTML cleaning (titles + abstracts)
    df_result['titre'] = df_result['titre'].apply(clean_html_text)

    

    # Cleaning the special caracters

    for col in df_result.select_dtypes(include='object').columns:
        df_result[col] = df_result[col].str.replace(';', ',', regex=False)








    ##################### STEP 3 : MERGING ALL INFO FROM SSRN ######################




   




    # Deleting any duplicates
    db_abstract = df_result.drop_duplicates(subset='id')

    # Merging the info and the abstracts
    db_info_abstract = db_abstract

    # Exporting the resuting csv
    db_info_abstract.to_csv(output_info_abstract, sep=";", index=False)





import fasttext
model = fasttext.load_model("lid.176.bin")

def detect_lang(text):
    if not isinstance(text, str) or text.strip() == "":
        return None, None
    labels, probs = model.predict(text, k=1)
    return labels[0].replace("__label__", ""), probs[0]

df_result[["lang", "lang_prob"]] = (
    df_result["titre"]
    .apply(lambda x: pd.Series(detect_lang(x)))
)
df_non_en = df_result[df_result["lang"] != "en"]
