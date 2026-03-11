"""
The aim of this script is to create a list of key words to retrieve a maximum nomber of articles in the 10 000 last articles published
"""

import requests
import pandas as pd
import time
from collections import Counter
import re


"""
                                        CREATING OF A LIST OF 10 000 ARTICLES
"""



# Creation of a list of link with pages containing 200 articles

list_index = list(range(0, 10000, 200))

list_link = []

for index in list_index:
    link = f"https://api.ssrn.com/content/v1/bindings/205/papers?index={index}&count=200&sort=0"
    list_link.append(link)

# # Fonction that collects the title of all the articles on each page

def fonction(i):
    response_abs = requests.get(i)
    if response_abs.status_code == 200:
        data = response_abs.json()
        return [{'titre': paper.get('title', 'No title').strip()} for paper in data.get('papers', [])]
    return []

# Retrieve requested titles (min and max indexes correspond to the first and last indexes requested in the list list_link = [0, 200, 400, ..., 9 800])

titles = []

for j in list_link:
    print(j)
    titles.extend(fonction(j))
    time.sleep(11)

# Organisation of the titles in a data frame and in an excel spreadsheet 

pd.set_option('display.max_colwidth', None) # pour ne pas couper les titres trop longs

df = pd.DataFrame(titles)

df.to_excel('db_first_10000.xlsx', index=False)


print(df)



keywords = ['accounting', 'adam', 'administration', 'agriculture', 'agricultural', 'aid', 'allocative', 'analysis', 'ancient', 'anthropology',
        'antitrust', 'approaches', 'asset', 'associations', 'auctions', 'austrian', 'bayesian', 'behavior', 'behavioral', 'biotechnology',
        'bureaucracy', 'business', 'capital', 'capitalist', 'censored', 'change', 'choice', 'classical', 'classification', 'climate', 'clubs',
        'collaborative', 'collective', 'committees', 'commodity', 'comparative', 'compensation', 'competition', 'computational', 'conditions',
        'consumption', 'contract', 'contracts', 'corporate', 'cost-benefit', 'costs', 'crises', 'cross-sectional', 'cultural', 'current', 'cycle',
        'data', 'debt', 'demographic', 'demographics', 'design', 'development', 'disability', 'discrete', 'discrimination', 'disequilibrium',
        'distribution', 'duration', 'dynamic', 'ecological', 'econometric', 'econometrics', 'economic', 'economics', 'economists', 'economy',
        'education', 'effect', 'efficiency', 'elections', 'energy', 'entrepreneurship', 'environment', 'environmental', 'equation', 'equilibrium',
        'equity', 'estate', 'estimation', 'evolutionary', 'exchange', 'externalities', 'factor', 'family', 'fertility', 'finance', 'financial',
        'financing', 'fiscal', 'force', 'forecasting', 'foreign', 'forests', 'games', 'gender', 'general', 'graduate', 'growth', 'health',
        'historical', 'history', 'household', 'hypothesis', 'impact', 'income', 'index', 'individuals', 'industrialization', 'inequality', 'inequalities',
        'infrastructure', 'innovation', 'input', 'institutional', 'institutions', 'insurance', 'integration', 'international', 'investment',
        'issues', 'justice', 'labor', 'land', 'large', 'law', 'legislatures', 'licensing', 'life', 'literacy', 'lobbying', 'macro', 'macroeconomics',
        'management', 'market', 'marketing', 'markets', 'marriage', 'marshallian', 'mathematical', 'medieval', 'method', 'methodological',
        'methodology', 'methods', 'micro', 'microeconomic', 'microeconomics', 'mobility', 'modeling', 'models', 'modern', 'monetary', 'monopoly',
        'national', 'natural', 'neoclassical', 'neural', 'operations', 'optimization', 'organization', 'organizational', 'output', 'panel',
        'personal', 'personnel', 'policy', 'political', 'pollution', 'prediction', 'pricing', 'principal', 'principles', 'production',
        'productivity', 'property', 'protection', 'public', 'qualitative', 'quantile', 'quantitative', 'rates', 'rationing', 'real', 'regional',
        'regression', 'regressions', 'regulation', 'relation', 'renewable', 'research', 'resource', 'resources', 'retirement', 'risk', 'role',
        'rural', 'safety', 'satisfaction', 'saving', 'sectoral', 'security', 'services', 'simulation', 'smith', 'social', 'sociology', 'outcomes',
        'governance', 'pay', 'strategic', 'framework', 'field', 'selection', 'uncertainty', 'decision', 'fund', 'funds', 'among', 'spatial',
        'spatio-temporal', 'sports', 'standards', 'statistical', 'studies', 'study', 'sustainability', 'sustainable', 'level', 'rights', 'right',
        'switching', 'teaching', 'techniques', 'technological', 'technologies', 'testing', 'theory', 'thought', 'threshold', 'how', 'time',
        'power', 'money', 'review', 'control', 'system', 'between', 'china', 'healthcare', 'india', 'against', 'under', 'time-series',
        'total', 'tourism', 'trade', 'transfers', 'transportation', 'treatment', 'truncated', 'through', 'states', 'usa', 'us', 'america', 'preferences',
        'industry', 'level', 'local', 'firms', 'firm', 'risk', 'trading', 'countries', 'bank', 'banks', 'turnover', 'undergraduate',
        'unemployment', 'unions', 'urban', 'value', 'values', 'variables', 'voting', 'wage', 'wages', 'eu', 'future', 'technology', 'immigration',
        'perspective', 'water', 'welfare', 'working', 'works', 'global', 'optimal', 'performance', 'credit', 'debit', 'strategies',
        'strategy', 'dynamics', 'returns', 'intelligence', 'inflation', 'recession', 'conflict', 'tax', 'male', 'men', 'info', 'term', 'trad',
        'omic', 'gap', 'price', 'valuation', 'approach', 'model', 'information', 'carbon', 'new', 'what', 'central', 'school', 'span',
        'evidence', 'learn', 'perform', 'why', 'ai', 'from', 'learning', 'effects', 'problem', 'problems', 'case','during', 'covid', 'people', 
        'challenges', 'network', 'war', 'demand','investors', 'investor', 'consequences', 'consumers', 'consume', 'work', 'prices', 'price', 'implications', 
        'job', 'measuring', 'supply','rate','experience','based', 'level', 'high', 'earnings', 'post', 'digital','government','with', 'self','transition',
        'success','unveiling','lending', 'who', 'exposure', 'based', 'networks', 'persuasion', 'rules', 'return','trade', 'opportunities','systems', 'critical',
        'influence', 'green', 'cost', 'part','moral','tax', 'formation', 'world', 'determinants', 'banking', 'cooperation', 'collusion', 'investing', 'limits', 
        'platform', 'human', 'regulatory', 'africa', 'random', 'state', 'nigeria', 'post', 'economy', 'understanding', 'examination', 'student', 'report', 
        'momentum', 'introduction', 'century', 'mechanism', 'process', 'financial', 'housing', 'speculation', 'minimum', 'migration', 'blockchain', 'violence', 
        'media', 'reporting', 'country', 'restrictions', 'europe', 'versus','city','incentives', 'assessing', 'revisited', 'quality', 'stable', 'matter',
        'years', 'legal', 'federal', 'order', 'implementation', 'after']

print(len(keywords))


#Choice of the list used
keywords_set = set(keywords)


# Using a pre-existing dataframe to go quicker

df = pd.read_excel('titles_list.xlsx')



"""
                                            RETRIEVING THE ARTICLES COUNTAINING AT LEAST ONE KEYWORD
"""



# Counting the number/rate of articles retrieved or not

count = 0
not_count = 0
used_words = []

title_found = []
title_not_found = []
key_word_found = []

for i in range(0,len(df)):
    used_words = []

    for word in df['titre'].loc[i].split():
        if any(re.search(r'\b' + re.escape(l_word.lower()) + r'\b', word.lower()) for l_word in keywords_set):
            used_words.append(word)
    
    if used_words:
        count+=1
        title_found.append(df['titre'].loc[i])
        key_word_found.append(', '.join(used_words))
    else:
        not_count = not_count + 1
        title_not_found.append(df['titre'].loc[i])

success_rate = count/len(df)

failure_rate = not_count/len(df)

total = success_rate + failure_rate



print(f'''

      
The rate of retieved artciles is {round(success_rate * 100,2)}% and the rate of non retrieved articles is {round(failure_rate * 100,2)}%.

In total, {total * 100}% of the articles have been checked if they had key-words or not.

''')



# Creation of a dataframe with the titles found and their key-word and of a data frame for the titles not found

df_found = pd.DataFrame({'Title': title_found, 'Key words found':key_word_found})
                        
df_not_found = pd.DataFrame(title_not_found, columns=["Title"])


# Saving the data frames as Excels

df_found.to_excel("titles_found.xlsx", index=False)
df_not_found.to_excel("titles_not_found.xlsx", index=False)





"""
                                    CHECKING HOW MANY TIMES EACH KEYWORD IS USED
"""




# Counting how many times each key word was used

word_counts_non_used_titles = {word: 0 for word in keywords_set}

for title in key_word_found: 
    if isinstance(title, str):  # Ensure the title is a string
        for word in keywords_set:
            word_counts_non_used_titles[word] += title.lower().count(word.lower())  # Count substrings, case-insensitive

col1 = [] # keyword
col2 = [] # nber of time the keyword appears

for word, count in word_counts_non_used_titles.items():
        col1.append(word)
        col2.append(count)

df_nber_time_keywords = pd.DataFrame({'Keyword':col1, 'Frequency':col2})

df_nber_time_keywords.to_excel('Nber_times_keywords.xlsx',index=False)

# Showing the non used keywords in an excel

key_word_non_used = []

for k in range (0, len(col1)):
    if (df_nber_time_keywords['Frequency'].loc[k]) == 0:
        key_word_non_used.append(df_nber_time_keywords['Keyword'].loc[k])

if len(key_word_non_used)==0:
    print('All the keywords were used')
else:
    print(f"Not all the keywords were used, the list of non-used keywords is: {key_word_non_used}")




"""
                                                FINDING OTHER WORDS TO ADD TO THE KEYORDS LIST
"""



# Verifying if other words could be added to the keywords, by counting the occurence of each word in the list of non selected titles

all_non_used_titles = " ".join(df_not_found['Title'].dropna()).lower()

words_non_used_titles = re.findall(r'\b\w+\b', all_non_used_titles)

word_counts_non_used_titles = Counter(words_non_used_titles)

df_word_counts_non_used_titles = pd.DataFrame(word_counts_non_used_titles.items(), columns=['Word', 'Count'])

df_word_counts_non_used_titles = df_word_counts_non_used_titles.sort_values(by='Count', ascending=False)

df_word_counts_non_used_titles.to_excel("Nber_non_selected_words.xlsx", index=False)