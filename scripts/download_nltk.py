Python 3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)] on win32
Enter "help" below or click "Help" above for more information.
>>> 
= RESTART: C:\Users\Utente\Desktop\Nuova cartella\abstract_analysis-main\main.py
Traceback (most recent call last):
  File "C:\Users\Utente\Desktop\Nuova cartella\abstract_analysis-main\main.py", line 1, in <module>
    from scripts.info_abstract import info_abstract
  File "C:\Users\Utente\Desktop\Nuova cartella\abstract_analysis-main\scripts\info_abstract.py", line 12, in <module>
    import pandas as pd
ModuleNotFoundError: No module named 'pandas'
>>> import nltk
... nltk.download('punkt')
... nltk.download('stopwords')
SyntaxError: multiple statements found while compiling a single statement
>>> import nltk
>>> nltk.download('punkt')
[nltk_data] Downloading package punkt to
[nltk_data]     C:\Users\Utente\AppData\Roaming\nltk_data...
[nltk_data]   Unzipping tokenizers\punkt.zip.
True
>>> nltk.download('stopwords')
[nltk_data] Downloading package stopwords to
[nltk_data]     C:\Users\Utente\AppData\Roaming\nltk_data...
[nltk_data]   Unzipping corpora\stopwords.zip.
True
