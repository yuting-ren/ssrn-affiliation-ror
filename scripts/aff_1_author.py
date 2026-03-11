# Importation of libraries

import pandas as pd
import html
import unicodedata
import re
from tqdm import tqdm
tqdm.pandas()
from collections import Counter
from rapidfuzz import process, fuzz
from joblib import Parallel, delayed
import ast



def aff_1_author(output_info_abstract,output_aff_1_author):

    ##################### STEP 1 : KEEPING ONLY ARTICLES WITH ONE AUTHOR

    # Open the file
    print(output_info_abstract)
    df = pd.read_csv(output_info_abstract, sep=";", engine="python")



    # Delete the line with more than one author
    df = df[df["author_2_id"].isna() | (df["author_2_id"].astype(str).str.strip() == "")]

    # Create the author 1 column and copy the affiliation
    if "author_1_affiliation" not in df.columns:
        insert_at = df.columns.get_loc("author_1_url") + 1
        df.insert(insert_at, "author_1_affiliation", pd.NA)

    df["author_1_affiliation"] = df["affiliations"].astype(str).str.strip()

    # Delete columns empty
    df = df.loc[:, ~((df.isna() | (df == "")).all(axis=0))]


    df_affiliation = pd.DataFrame()
    df_affiliation['affiliations_full_name'] = df['affiliations']
    df_affiliation = df_affiliation.dropna()
    df_affiliation = df_affiliation.drop_duplicates()

    # List of characters needed to be removed
    unwanted_chars = ['-', '/', '.',',']

    # Cleaning the df

    df_affiliation['affiliations'] = df_affiliation['affiliations_full_name'].apply(lambda x: html.unescape(str(x)))
    for ch in unwanted_chars:
        df_affiliation['affiliations'] = df_affiliation['affiliations'].str.replace(ch, '', regex=False)

    def remove_accents(text):
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ASCII', 'ignore').decode('utf-8')
        return text

    df_affiliation['affiliations'] = df_affiliation['affiliations'].apply(remove_accents)


    # date format
    month_map = {
        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
        'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
    }

    # Converting the date to correct format
    def convert_to_date(val):
        try:
            if isinstance(val, (int, float)):
                return pd.to_datetime('1899-12-30') + pd.to_timedelta(val, unit='D')
            elif isinstance(val, str):
                val = val.strip()
                day = int(val[:2])
                month_abbr = val[3:6].upper()
                year = int(val[-4:])
                month_num = month_map.get(month_abbr)
                if month_num:
                    return pd.Timestamp(year=year, month=month_num, day=day)
            return pd.NaT
        except:
            return pd.NaT

    df['approved_date_wrong_format'] = df['approved_date']
    df['approved_date'].apply(convert_to_date)
    #df['approved_date'] = pd.to_datetime(df['approved_date'], dayfirst=True)

    ###################### STEP 2 : AFFILIATING EACH ARTICLE TO A COUNTRY

    # Cleaning the affiliation
    df_affiliation = pd.DataFrame()
    df_affiliation['affiliations_full_name'] = df['affiliations']
    df_affiliation = df_affiliation.dropna()
    df_affiliation = df_affiliation.drop_duplicates()

    # Decoding
    df_affiliation['affiliations'] = df_affiliation['affiliations_full_name'].apply(lambda x: html.unescape(str(x)))

    # Removing unwanted caracters
    unwanted_chars = ['-', '/', '.',',']
    for ch in unwanted_chars:
        df_affiliation['affiliations'] = df_affiliation['affiliations'].str.replace(ch, '', regex=False)

    def remove_accents(text):
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ASCII', 'ignore').decode('utf-8')
        return text

    df_affiliation['affiliations'] = df_affiliation['affiliations'].apply(remove_accents)

    ####################### STEP 2.1 : USING A LIBRARY  ###############

    df_step_1 = df_affiliation

    # Creation of a library with keywords for each country

    class AffiliationCountryResolver:
        def __init__(self):
            self.country_keywords = {
                'Switzerland': ['suisse', 'switzerland', 'swiss','zurich', 'geneva', 'lausanne', 'basel', 'berne','university of zurich', 'university of geneva', 'university of basel', 'university of bern','eth zurich', 'epfl', 'epfl (école polytechnique fédérale de lausanne)',
                                'university of lausanne', 'university of st. gallen', 'university of fribourg','university of neuchâtel', 'zurich university of applied sciences','università della svizzera italiana', 'university of lucerne'],
                
                'United States': ['claremont','dallas','clark','mercatus','case','auburn','morgan','cumberlands','alabama', 'point','valley','akron','syracuse','alaska', 'arizona', 'arkansas', 'california', 'colorado', 'connecticut', 'delaware', 'florida', 'georgia', 'hawaii', 'idaho', 'illinois', 'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana', 'maine', 'maryland', 'massachusetts', 'michigan', 'minnesota', 'mississippi', 'missouri', 'montana', 'nebraska', 'nevada', 'new hampshire', 'new jersey', 'new mexico', 'new york', 'north carolina', 'north dakota', 'ohio', 'oklahoma', 'oregon', 'pennsylvania', 'rhode island', 'south carolina', 'south dakota', 'tennessee', 'texas', 'utah', 'vermont', 'virginia', 'washington', 'west virginia', 'wisconsin', 'wyoming',
                                'harvard university', 'massachusetts institute of technology', 'stanford university', 'california institute of technology', 'university of california, berkeley', 'columbia university', 'university of chicago', 'princeton university', 'yale university', 'university of pennsylvania', 'johns hopkins university', 'northwestern university', 'cornell university', 'duke university', 'university of michigan', 'university of california, los angeles', 'university of washington', 'carnegie mellon university', 'georgia institute of technology', 'university of california, san diego', 'university of wisconsin–madison', 'rice university', 'brown university', 'university of california, san francisco', 'university of texas at austin', 'university of california, santa barbara', 'university of california, davis', 'emory university', 'washington university in st. louis', 'university of california, san francisco', 'university of california, irvine', 'university of minnesota', 'university of virginia', 'university of maryland, college park', 'vanderbilt university', 'university of illinois at urbana–champagne', 'pennsylvania state university', 'university of california, santa cruz', 'new york university', 'texas a&m university', 'university of florida', 'university of pittsburgh', 'university of colorado boulder', 'university of north carolina at chapel hill', 'university of california, riverside', 'university of arizona', 'university of tennessee', 'purdue university', 'ohio state university', 'university of california, sacramento', 'duke university', 'university of southern california', 'boston university', 'rutgers university–new brunswick', 'university of notre dame', 'university of georgia', 'emory university', 'oregon state university', 'iowa state university', 'university of nebraska–lincoln', 'university of oklahoma', 'university of missouri', 'university of kansas', 'iowa university', 'university of washington bothell', 'clemson university', 'louisiana state university', 'wake forest university', 'georgia state university', 'rice university', 'georgia institute of technology', 'baylor university', 'university of hawaii', 'university of connecticut', 'washington state university', 'university of utah', 'university of nevada, reno', 'university of colorado denver', 'university of arkansas', 'university of alabama', 'university of oregon', 'university of rhode island', 'university of louisiana at lafayette', 'michigan state university', 'university of mississippi', 'university of kentucky', 'university of idaho', 'university of montana', 'university of wyoming', 'university of alaska fairbanks', 'university of vermont', 'university of maine', 'university of new hampshire', 'university of delaware', 'university of vermont', 'university of arkansas for medical sciences', 'georgia southern university', 'university of south carolina',
                                'texas', 'arizona','american','united states', 'usa', 'us', 'america', 'georgetown', 'new york', 'boston', 'chicago','los angeles', 'san francisco', 'washington', 'atlanta', 'miami', 'seattle','state',
                                'houston', 'philadelphia', 'denver', 'austin', 'harvard university', 'harvard','brandeis','dartmouth','mit', 'stanford', 'ucla', 'university of california', 'uc berkeley', 'uc san diego',
                                'ucsd', 'uc irvine', 'purdue university', 'yale university', 'columbia university','tufts','princeton', 'university of chicago', 'northwestern', 'saint louis university','drexel','washburn','memphis',
                                'bloomberg', 'sacred heart university', 'penn state', 'pennsylvania state university','hiram', 'fisk university', 'cato institute', 'pace university','u.s.','chapman','u.s.','sukhadia','howard',
                                'university of south carolina', 'university of texas', 'amazon, bates college','rutgers','richmond','brigham','university of maryland','suny','cuny','fordham','nyu','rochester','tulane'],
                
                'Colombia':['colombia'],
                
                'Scotland':['scotland','scotish','strathclyde'],
                
                'Kazakhstan':['nazarbayev'],
                
                'Cyprus':['cyprus'],
                
                'Serbia':['belgrade'],
                
                'Canada': ['canada', 'canadian', 'toronto', 'montreal', 'vancouver', 'ottawa', 'calgary', 'edmonton','sherbrooke',
                                'ontario', 'québec', 'nova scotia', 'new brunswick', 'manitoba', 'british columbia', 'prince edward island', 'saskatchewan', 'alberta', 'newfoundland and labrador', 'northwest territories', 'yukon', 'nunavut',
                                'university of toronto', 'university of british columbia', 'mcgill university', 'université de montréal', 'university of alberta', 'university of waterloo', 'western university', 'university of calgary', 'queen’s university', 'mcmaster university', 'simon fraser university', 'university of ottawa', 'dalhousie university', 'university of manitoba', 'université laval', 'memorial university of newfoundland', 'university of saskatchewan', 'université du québec à montréal', 'concordia university', 'york university',
                                'university of toronto', 'mcgill', 'university of british columbia', 'ubc','laval','carleton','surrey',
                                'peter a. allard school of law, university of british columbia'],
                                'Romania':['bucharest','romanian','cuza'],

                'India': ['india', 'indian','icfai','kiit','alagappa','mysore', 'manipal','delhi', 'mumbai', 'kolkata', 'bangalore', 'chennai', 'hyderabad','indira','nadu','gujarat','nagpur','aligarh',
                                'new delhi', 'mumbai', 'kolkata', 'chennai', 'bengaluru', 'hyderabad', 'pune', 'ahmedabad', 'jaipur', 'lucknow', 'kanpur', 'kochi', 'chandigarh', 'bhopal', 'mohali',
                                'indira gandhi national open university', 'indian institute of technology delhi', 'indian institute of technology bombay', 'indian institute of technology madras', 'indian institute of science', 'indian institute of technology kharagpur', 'indian institute of technology kanpur', 'indian institute of technology guwahati', 'university of delhi', 'savitribai phule pune university', 'banaras hindu university', 'university of mumbai', 'university of calcutta', 'jawaharlal nehru university', 'university of hyderabad', 'osmania university', 'chaudhary charan singh university', 'university of mumbai', 'dr br ambedkar open university', 'sikkim manipal university',
                                'ahmedabad', 'pune', 'lucknow', 'jadavpur university', 'galgotias university','noida','nmims','kerala',
                                'indian institute of management', 'iim', 'university of delhi', 'delhi university','maharaja','karnavati',
                                'lady brabourne college', 'shaheed bhagat singh college', 'dr. ambedkar institute','rajasthan',
                                'jawaharlal nehru university', 'jnu', 'naac','gandhi','jindal','jain'],
                
                'Albania':['tirana'],
                
                'Australia': ['australia', 'australian', 'sydney', 'melbourne', 'brisbane', 'perth', 'adelaide',
                                'canberra', 'australian national university', 'anu', 'university of queensland',
                                'sydney', 'melbourne', 'brisbane', 'perth', 'adelaide', 'gold coast', 'newcastle', 'canberra', 'sunshine coast', 'wollongong',
                                'monash university', 'university of sydney', 'rmit university', 'university of new south wales', 'university of melbourne', 'university of queensland', 'curtin university', 'deakin university', 'australian national university', 'university of technology sydney', 'university of western australia', 'university of adelaide', 'macquarie university', 'university of newcastle', 'university of wollongong', 'queensland university of technology', 'grffith university', 'la trobe university', 'edith cowan university', 'james cook university',
                                'university of sydney', 'university of melbourne','tasmania'],
                
                'China': ['china', 'chinese', 'beijing', 'shanghai', 'guangzhou', 'shenzhen', 'nanjing', 'wuhan','taiwan','hong','kong','jiaotong','hunan','tianjin',
                                'beijing', 'shanghai', 'guangzhou', 'shenzhen', 'chengdu', 'wuhan', 'hangzhou', 'nanjing', 'xian', 'chongqing','zhejiang','macau',
                                'tsinghua university', 'peking university', 'fudan university', 'zhejiang university', 'shanghai jiao tong university', 'university of science and technology of china', 'nanjing university', 'harbin institute of technology', 'beijing normal university', 'wuhan university', 'tongji university', 'sun yat-sen university', 'harbin engineering university', 'beijing institute of technology', 'southeast university', 'xian jiaotong university', 'south china university of technology', 'chongqing university', 'dalian university of technology', 'huazhong university of science and technology',
                                'nankai university', 'peking university', 'tsinghua university', 'guangxi university','nanyang','xiamen','henan','shandong','chengchi',
                                'jinan university','yatsen'],

                'Singapore':['singapore','singh'],
                
                'Moldova':['moldova'],
                
                'Lituania':['vilnius'],
                
                'United Kingdom': ['united kingdom', 'uk', 'queen','britain', 'british', 'london', 'oxford', 'cambridge','essex','england','westminster','lancaster',
                                'manchester', 'birmingham', 'edinburgh', 'glasgow', 'bristol', 'leeds','liverpool','southampton','aston',
                                'university of leeds', 'university of kent', 'london school of economics', 'lse',
                                'imperial college', "king's college", 'institute of economic affairs','sussex','nottingham',
                                'london', 'manchester', 'birmingham', 'edinburgh', 'glasgow', 'leeds', 'bristol', 'cardiff', 'newcastle', 'sheffield',
                                'imperial college london', 'university of oxford','anglia', 'university of cambridge', 'university college london', 'university of edinburgh', 'university of manchester', 'king’s college london', 'london school of economics and political science', 'university of bristol', 'university of sheffield', 'university of nottingham', 'durham university', 'university of warwick', 'university of leeds', 'university of birmingham', 'university of glasgow', 'university of exeter', 'university of bath', 'university of leicester', 'university of york'],
                
                'France': ['et','universite','france','parissaclay', 'french', 'paris', 'lyon', 'marseille', 'toulouse', 'nice', 'bordeaux', 'lille','ecole',
                                'nantes', 'strasbourg', 'rennes', 'university of rouen', 'sorbonne','edhec','hec','polytechnique',
                                'paris', 'marseille', 'lyon', 'toulouse', 'nice', 'nantes', 'strasbourg', 'montpellier', 'lille', 'bordeaux',
                                'universite paris-saclay', 'sorbonne université', 'universite paris cite', 'école normale superieure', 'école polytechnique', 'université grenoble alpes', 'université de strasbourg', 'université de bordeaux', 'université de lille', 'université lyon 1 claude bernard', 'université de montpellier', 'université de toulouse', 'université de nantes', 'université de rennes 1', 'université de nice sophia antipolis', 'université de marseille (amu)', 'université de caen normandie', 'université de poitiers', 'université de dijon (bourgogne)', 'université de savoie mont blanc',
                                'école normale supérieure', 'sciences po', 'ferdi','mines','ponts'],
                
                'Ukraine':['ukraine','kyiv','vinnytsia','kharkiv','odessa'],
                
                'Chile':['chile'],
                
                'Qatar':['qatar'],
                
                'Germany': ['germany', 'german', 'mainz','berlin', 'munich', 'frankfurt', 'hamburg', 'stuttgart', 'cologne','hochschule','bochum',
                                'dresden', 'heinrich heine university', 'max planck','leibniz','universitat','ruhr','giessen',
                                'freiberg university of mining and technology', 'technical university of munich',
                                'berlin', 'munich', 'hamburg', 'cologne', 'frankfurt', 'stuttgart', 'düsseldorf', 'dresden', 'leipzig', 'nuremberg',
                                'ludwig-maximilians-universität münchen', 'technische universität münchen', 'heidelberg university', 'freie universität berlin', 'humboldt-universität zu berlin', 'university of tübingen', 'rwth aachen university', 'university of bonn', 'university of freiburg', 'university of göttingen', 'university of hamburg', 'university of mannheim', 'university of cologne', 'university of leipzig', 'university of stuttgart', 'university of düsseldorf (heinrich-heine)', 'university of erlangen-nuremberg', 'university of frankfurt (goethe)', 'university of münster', 'university of potsdam',
                                'whu - otto beisheim school of management','gmbh','munster','deutsche','hagen','bundesbank'],
                
                'Argentina':['instituto','buenos'],
                
                'Italy': ['italy', 'universita','italian', 'rome', 'pontifica','milan', 'naples', 'florence', 'bologna', 'venice','studi','degli','milano-bicocca','italiana',
                                'university of pavia', 'university of milan', 'national research council of italy', 'cnr','di','roma',
                                'university of bologna', 'university of rome','bocconi','fondazione',
                                'rome', 'milan', 'naples', 'turin', 'palermo', 'genoa', 'bologna', 'florence', 'bari', 'catania','politecnico di milano', 'sapienza university of rome', 'university of bologna', 'scuola normale superiore di pisa', 'politecnico di torino', 'university of padua', 'university of milan', 'university of pisa', 'university of rome tor vergata', 'university of naples federico ii', 'university of firenze', 'university of venezia ca’ foscari', 'university of venezia', 'university of trento', 'university of torino', 'university of perugia', 'university of salento', 'university of bari', 'university of siena', 'university of pisa scuole superiori'],
                
                'Brazil': ['brazil', 'brazilian', 'são paulo', 'university of são paulo', 'usp','sao','paulo','vargas','getulio',
                                'faculdade kennedy de minas gerais','são paulo', 'rio de janeiro', 'salvador', 'fortaleza', 'belo horizonte', 'brasilia', 'curitiba', 'manaus', 'recife', 'belém',
                                'universidade de são paulo', 'universidade estadual de campinas', 'federal university of rio de janeiro', 'federal university of são paulo', 'são paulo state university', 'pontifical catholic university of rio de janeiro', 'pontifical catholic university of são paulo', 'federal university of minas gerais', 'federal university of rio grande do sul', 'federal university of santa catarina', 'university of brasília', 'federal university of pará', 'federal university of pernambuco', 'federal university of paraná', 'federal university of são carlos', 'university of são paulo medicina', 'universidade federal de viçosa', 'university of são paulo campus', 'unicamp engineering', 'usp law'],
                
                'Iran': ['iran', 'iranian', '(IAU)','azad','tehran', 'tihan university','tehran', 'mashhad', 'isfahan', 'karaj', 'tabriz', 'shirāz', 'qom', 'ahvaz', 'kermanshah', 'rasht',
                                'university of tehran', 'islamic', 'sharif','sharif university of technology', 'amirkabir university of technology', 'iran university of science and technology', 'isfahan university of technology', 'tehran university of medical sciences', 'shiraz university', 'shahid beheshti university', 'university of tabriz', 'ferdowsi university of mashhad', 'university of kerman', 'zanjan university', 'khajeh nasir toosi university of technology', 'university of tehran', 'iau islamic azad university', 'yar university tehran', 'university of ahvaz', 'university of yazd', 'university of kermanshah'],
                
                'Israel': ['israel', 'israeli', 'jerusalem', 'tel aviv','ben-gurion university', 'hebrew university of jerusalem','tel aviv', 'jerusalem', 'haifa', 'be’er sheva', 'rishon leẔiyyon', 'petah tikva', 'ashdod', 'netanya', 'beer sheva', 'ramat gan',
                                'tel aviv university', 'hebrew university of jerusalem', 'technion – israel institute of technology', 'weizmann institute of science', 'bar-ilan university', 'ben-gurion university of the negev', 'university of haifa', 'open university of israel', 'eastern university of jerusalem', 'sharif university of technology', 'peres academic center', 'jerusalem school of business administration', 'haidoka university', 'ort braude college', 'israel institute of technology', 'asuta university', 'interdisciplinary center herzliya', 'tel hefer institute', 'colel hastedim', 'metropolitan college of haifa'],
                
                'Costa Rica': ['costa rica', 'universidad de costa rica','san josé', 'heredia', 'alajuela', 'limón', 'puntarenas', 'liberia', 'cartago', 'san isidro de el general', 'quepos', 'curridabat','national university of costa rica', 'tec – costa rica institute of technology', 'university for peace', 'university of costa rica', 'university of san josé', 'costa rican christian university', 'latin university of costa rica', 'fidélitas university', 'amaru university', 'barataria university', 'la salle university', 'university of pacific', 'university of cartago', 'university of alajuela', 'university of puntarenas', 'international university of costa rica', 'central american university for international studies', 'facultad latinoamericana de ciencias sociales – sede costa rica', 'manuel antonio university', 'university of marine sciences', 'tropical university of costa rica' ],
                
                'Greece': ['greece', 'greek', 'athens', 'thessaloniki', 'university of piraeus', 'university of ioannina','athens', 'thessaloniki', 'patrai', 'piraeus', 'larissa', 'heraklion', 'volos', 'ioannina', 'iraklio', 'chania',
                                'national and kapodistrian university of athens', 'national technical university of athens', 'aristotle university of thessaloniki', 'university of crete', 'university of patras', 'athens university of economics and business', 'university of ioannina', 'democritus university of thrace', 'technical university of crete', 'harokopio university of athens', 'university of macedonia', 'panteion university of social and political sciences', 'university of peloponnese', 'technological university of western macedonia', 'university of thessaly', 'athens school of fine arts', 'university of piraeus', 'ionian university', 'university of the aegean', 'metropolitan college athens'],
                
                'Ecuador': ['ecuador', 'university of guayaquil','guayaquil', 'quito', 'cuenca', 'santo domingo de los colorados', 'machala', 'durán', 'manta', 'portoviejo', 'loja', 'ambato',
                                'universidad san francisco de quito', 'pontificia universidad católica del ecuador', 'universidad de guayaquil', 'escuela politécnica nacional', 'universidad de las américas', 'espol – escuela superior politécnica del litoral', 'uees – universidad de especialidades espiritu santo', 'universidad central del ecuador', 'escuela superior politécnica de chimborazo', 'universidad politécnica salesiana', 'universidad católica de santiago de guayaquil', 'universidad técnica de machala', 'universidad estatal de milagro', 'universidad del pacífico ecuador', 'facultad latinoamericana de ciencias sociales – sede ecuador', 'flacso ecuador', 'casa grande university', 'ecotec university', 'universidad regional autónoma de los andes'],
                
                'South Korea': ['south korea', 'korea', 'korean', 'seoul', 'busan', 'incheon', 'daegu',
                                'jeju national university', 'korea development institute', 'kdi','séoul', 'busan', 'incheon', 'daegu', 'daejeon', 'gwangju', 'suwon', 'ujin', 'changwon', 'seongnam',
                                'seoul national university', 'korea advanced institute of science and technology', 'yonsei university', 'korea university', 'postech', 'sungkyunkwan university', 'hanyang university', 'ewha womans university', 'kaist', 'kyunghee university', 'incheon national university', 'pohang university of science and technology', 'korea institute of science and technology', 'konkuk university', 'changwon national university', 'chungnam national university', 'konyang university', 'sungshin women’s university', 'dongguk university', 'sejong university'],
                
                'Spain': ['spain', 'spanish', 'madrid', 'barcelona', 'valencia', 'sevilla', 'bilbao','navarra','universitaria','escuela','universidad','facultad','ciencias',
                                'national distance education university', 'uned','madrid', 'barcelona', 'valencia', 'sevilla', 'zaragoza', 'málaga', 'murcia', 'palma', 'las palmas de gran canaria', 'bilbao',
                                'universidad de barcelona', 'universidad autónoma de madrid', 'universidad complutense de madrid', 'universidad de valencia', 'universitat de barcelona', 'universidad politécnica de madrid', 'universidad de granada', 'universitat politècnica de valència', 'universidad de sevilla', 'universidad de zaragoza', 'universidad de alicante', 'universidad de murcia', 'universidad de oviedo', 'universidad de tenerife', 'universidad del país vasco', 'universidad de navarra', 'universidad de salamanca', 'universidad de santiago de compostela', 'universidad de la laguna', 'universidad pontificia comillas', 'universidad carlos iii de madrid', 'universidad de cantabria'],
                
                'Russia': ['russia', 'russian', 'moscow', 'saint petersburg', 'novosibirsk', 'yekaterinburg',
                                'moscow state institute', 'mgimo', 'russian academy of national economy','moscow', 'saint petersburg', 'novosibirsk', 'yekaterinburg', 'nizhny novgorod', 'kazan', 'chelyabinsk', 'omsk', 'samara', 'ufa',
                                'lomonosov moscow state university', 'bauman moscow state technical university', 'peoples’ friendship university of russia (rudn)', 'saint petersburg university', 'kazan federal university', 'higher school of economics', 'tomsk state university', 'novosibirsk state university', 'moscow institute of physics and technology (mipt)', 'national research nuclear university mephi', 'ural federal university', 'peter the great st. petersburg polytechnic university', 'mgimo university', 'tomsk polytechnic university', 'itmo university', 'far eastern federal university', 'plekhanov russian university of economics', 'financial university under the government of the russian federation', 'sechenov university', 'immanuel kant baltic federal university'],
                
                'Philippines': ['philippines', 'filipino', 'manila', 'j. h. cerilles state college','manila', 'quezon city', 'ceb ucity', 'davao', 'caloocan', 'zamboanga', 'taguig', 'pasig', 'antipolo', 'pasay',
                                'university of the philippines', 'ateneo de manila university', 'de la salle university', 'university of santo tomas', 'university of san carlos', 'adamson university', 'mapúa university', 'polytechnic university of the philippines', 'silliman university', 'far eastern university', 'mindanao state university – iligan it', 'saint louis university', 'cebu technological university', 'central luzon state university', 'central mindanao university', 'central philippine university', 'xavier university', 'philippine normal university', 'philippine state college of aeronautics', 'philippine women’s university'],
                
                'Pakistan': ['pakistan', 'pakistani', 'lahore', 'karachi', 'islamabad',
                                'international islamic university islamabad','islamabad', 'karachi', 'lahore', 'faisalabad', 'rawalpindi', 'multan', 'peshawar', 'quetta', 'sialkot', 'gujranwala',
                                'national university of sciences & technology (nust)', 'quaid-i-azam university', 'university of the punjab', 'lums', 'comsats university islamabad', 'pieas', 'government college university lahore', 'agha khan university', 'university of agriculture faisalabad', 'university of engineering and technology lahore', 'university of peshawar', 'islamic international university islamabad', 'lahore school of economics', 'bahauddin zakariya university', 'virtual university of pakistan', 'air university', 'institute of space technology', 'university of karachi', 'pakistan institute of engineering and applied sciences', 'nawaz sharif medical university', 'quaid-e-awam university of engineering science & technology'],
                
                'Indonesia': ['indonesia', 'indonesian', 'jakarta', 'bandung','universitas','padjadjaran',
                                'politeknik indotec kendari', 'syiah kuala university','jakarta', 'surabaya', 'bandung', 'medan', 'semarang', 'depok', 'tangerang', 'bekasi', 'palembang', 'makassar',
                                'universitas indonesia', 'universitas gadjah mada', 'institut teknologi bandung', 'airlangga university', 'ipb university', 'universitas diponegoro', 'universitas padjadjaran', 'universitas brawijaya', 'universitas udayana', 'universitas muhammadiyah surakarta', 'universitas negera yogyakarta', 'telkom university', 'universitas kristen petra', 'universitas lampung', 'universitas mataram', 'universitas hasanuddin', 'universitas pendidikan indonesia', 'binus university', 'universitas islam indonesia', 'universitas sebelas maret'],
                
                'Nepal': ['nepal', 'kathmandu', 'kathmandu university','kathmandu', 'biratnagar', 'bharatpur', 'नेपालगञ्ज (nepalgunj)', 'birgunj', 'pokhara', 'dharan', 'butwal', 'dhangadhi', 'janakpur',
                                'tribhuvan university', 'kathmandu university', 'purbanchal university', 'pokhara university', 'mid-western university', 'lumbini buddhist university', 'nepal open university', 'mahendra multiple campus', 'far-western university', 'far-western university doti', 'nepal academy', 'godawari institute', 'constituent campus tu', 'school of arts tu', 'institute of engineering tu', 'college of management tu', 'premier college', 'asian college of higher studies', 'national academy of medical sciences', 'nepal medical college', 'bheri multiple campus'],
                
                'Hungaria':['hungarian','hungaria','budapest'],
                
                'Belgium': ['belgium', 'belgian', 'brussels', 'antwerp', 'ghent', 'liege', 'namur','bruxelles',
                                'lfin/lidam, uclouvain', 'uclouvain','brussels', 'antwerp', 'ghent', 'charleroi', 'bruges', 'liège', 'liege', 'brugge', 'namur', 'leuven',
                                'katholieke universiteit leuven', 'universiteit gent', 'université catholique de louvain', 'vrije universiteit brussel', 'universiteit antwerpen', 'université libre de bruxelles', 'université de liège', 'hasselt university', 'universiteit mons', 'université de namur', 'université saint-louis bruxelles', 'uclouvain bruxelles', 'institut catholique des arts et métiers', 'haute école bruxelloise', 'haute école de namur', 'university college ghent', 'university college leuven', 'haute école charlemagne', 'university college antwerp', 'haute école leonard de vinci', 'university college brussels'],
                
                'Ghana': ['ghana', 'university of cape coast','accra', 'kumasi', 'tamale', 'sekondi-takoradi', 'sunyani', 'tema', 'cape coast', 'obuasi', 'teshie', 'ho',
                                'university of ghana', 'kwame nkrumah university of science and technology', 'university of cape coast', 'university for development studies', 'ghana institute of management and public administration', 'ashesi university', 'central university', 'university of education winneba', 'valley view university', 'knust', 'university of mines and technology', 'university of professional studies accra', 'university of ghana medical school', 'st. augustine’s college of education', 'accra technical university', 'tamale technical university', 'wisconsin international university ghana', 'ghanaians', 'prestea', 'texas college', 'pacific university college'],
                
                'Bahrain': ['bahrain', 'kingdom university','manama', 'riffa', 'muharraq', 'hamad town', 'aali', 'sitra', 'jidhafs', 'isa town', 'budaiya', 'diraz',
                                'arabian gulf university', 'university of bahrain', 'ahlia university', 'applied science university', 'university college of bahrain', 'royal college of surgeons in ireland-bahrain', 'gulf university', 'royal university for women', 'ama international university bahrain', 'talal abu-ghazaleh university college of business', 'delmon university for science and technology', 'faculty of business studies arab open university'],
                
                'Zimbabwe': ['zimbabwe', 'university of zimbabwe','harare', 'bulawayo', 'chitungwiza', 'mutare', 'gweru', 'epworth', 'kwekwe', 'kadoma', 'masvingo', 'chinhoyi',
                                'university of zimbabwe', 'national university of science and technology', 'midlands state university', 'great zimbabwe university', 'chinhoyi university of technology', 'bindura university of science education', 'africa university', 'lupane state university', 'harare institute of technology', 'solusi university', 'zimbabwe open university', 'manicaland state universi', 'marondera university of agric science', 'midlands state medical faculty', 'ili university', 'university of zimbabwe college', 'zheb anthony college', 'zimre', 'mount pleasant technical college', 'zimtech'],
                
                'Netherlands': ['netherlands','amsterdam', 'rotterdam', 'the hague', 'utrecht', 'eindhoven',
                                'delft university of technology', 'university of amsterdam', 'utrecht university', 'eindhoven university of technology', 'leiden university', 'wageningen university & research', 'erasmus university rotterdam', 'university of groningen', 'vrije universiteit amsterdam', 'maastricht university', 'university of twente', 'radboud university nijmegen', 'tilburg university', 'ghent university', 'tilburg university', 'hanze university of applied sciences', 'delft', 'twente'],
                
                'Sweden': ['sweden','gothenburg','Jonkoping','stockholm', 'goteborg', 'malmo', 'uppsala', 'lund',
                                'stockholm university', 'lund university', 'uppsala university', 'kth royal institute of technology', 'chalmers university of technology', 'linköping university', 'umeå university', 'uppsala', 'lund', 'karolinska institutet', 'lund university', 'kungliga tekniska högskolan', 'örebro university', 'jönköping university', 'mid sweden university', 'swedish university of agricultural sciences', 'linnaeus university', 'dalarna university', 'södertörn university', 'högskolan i gävle'],
                
                'Austria': ['austria','vienna', 'graz', 'linz', 'salzburg', 'innsbruck','vienna university of economics and business (wu wien)', 'university of vienna', 'graz university of technology', 'university of graz', 'vienna university of technology', 'university of innsbruck', 'kepler university linz', 'university of music and performing arts vienna', 'medical university of vienna', 'salzburg university', 'university of veterinary medicine vienna', 'johannes kepler university linz', 'modul university vienna', 'danubius university krems', 'fh bfi vienna', 'fh campus wien', 'fh grafenau', 'fh salzburg', 'fh josef ruhl', 'fh vienna'],
                
                'Denmark': ['denmark','copenhagen', 'aarhus', 'odense', 'aalborg', 'esbjerg','university of copenhagen', 'aarhus university', 'technical university of denmark', 'aalborg university', 'copenhagen business school', 'roskilde university', 'university of southern denmark', 'copenhagen', 'aarhus', 'odense', 'aalborg', 'roskilde', 'copenhagen school of design and technology', 'denmarks technical university', 'university college sealand', 'university college copenhagen', 'university college sjælland', 'university college north denmark'],
                
                'Slovenia':['ljubljana'],
                
                'Norway': ['norway','norwegian','oslo', 'bergen', 'trondheim', 'stavanger', 'tromsø','university of oslo', 'norwegian university of science and technology (ntnu)', 'university of bergen', 'uie (school of architecture and design)', 'university of stavanger', 'nmbu (norwegian university of life sciences)', 'norwegian school of economics', 'oslo metropolitan university', 'university of agder', 'vikersund folk academy', 'nord university', 'ntnu', 'university of norway', 'university of life sciences', 'bergen university college', 'norwegian school of theology', 'nordic institute of artificial', 'oslo school of architecture', 'oslo and akershus'],
                
                'Finland': ['finland','jyvaskyla','helsinki', 'espoo', 'tampere', 'turku', 'oulu',
                                'university of helsinki', 'aalto university', 'university of turku', 'university of eastern finland', 'tampere university', 'university of jyväskylä', 'university of oulu', 'university of lapland', 'lappeenranta-lahti university of technology (lappeenranta campus)', 'university of vaasa', 'hanken school of economics', 'åbo akademi university', 'savonia university of applied sciences', 'saimaa university of applied sciences', 'satakunta university of applied sciences', 'tampere university of applied sciences', 'metropolia university of applied sciences', 'haaga-helia university of applied sciences', 'lahti university of applied sciences', 'jamk university of applied sciences'],
                
                'Mexico': ['mexico','mexico city', 'guadalajara', 'monterrey', 'puebla', 'tijuana', 'león', 'ecatepec', 'juárez', 'zapopan', 'nezahualcóyotl','national autonomous university of mexico', 'monterrey institute of technology and higher education', 'university autonoma metropolitana', 'universidad panamericana', 'national polytechnic institute', 'universidad de las americas', 'benemerita universidad autonoma de puebla', 'universidad autonoma de nuevo leon', 'universidad de guadalajara', 'instituto tecnologico y de estudios superiores de chihuahua', 'universidad veracruzana', 'universidad autonoma del estado de mexico', 'universidad michoacana de san nicolas de hidalgo', 'universidad autonoma de san luis potosi', 'universidad de colima', 'universidad autonoma de yucatan', 'universidad de sonora', 'universidad de zacatecas', 'universidad de guerrero', 'universidad de nayarit', 'universidad de chihuahua'],
                
                'Ireland': ['ireland','dublin', 'cork', 'galway', 'limerick', 'waterford', 'kilkenny', 'sligo', 'mayo', 'wexford', 'clare',
                                'trinity college dublin', 'university college dublin', 'university college cork', 'university of galway', 'dublin city university', 'maynooth university', 'technological university dublin', 'royal college of surgeons in ireland', 'institute of technology carlow', 'institute of technology tallaght', 'institute of technology tralee', 'griffith college dublin', 'national university of ireland galway', 'munster technological university', 'atlantic teknological university', 'south east technological university', 'ulster university ireland', 'irish council for science technology', 'international university of ireland', 'irish management institute', 'limerick institute of technology'],
                
                'Poland': ['poland','polish','warsaw', 'kraków', 'łódź', 'wrocław', 'poznan', 'gdańsk', 'szczecin', 'byszków', 'rzeszów', 'toruń',
                                'university of warsaw', 'jagiellonian university', 'warsaw university of technology', 'wroclaw university of science and technology', 'adam mickiewicz university', 'gdańsk university of technology', 'wrocław university', 'pedagogical university of kraków', 'technical university of łódź', 'poznań university of technology', 'uniwersytet łódzki', 'university of silesia in katowice', 'nicolaus copernicus university toruń', 'university of wrocław', 'university of gdańsk', 'medical university of warsaw', 'university of economy in katowice', 'sggw', 'european university foundation poland', 'academy of fine arts warsaw', 'university of bialystok'],
                
                'Egypt': ['egypt','cairo', 'alexandria', 'giza', 'shubra el-kheima', 'port said', 'suez', 'luxor', 'mansoura', 'tanta', 'fayyum',
                                'cairo university', 'al-azhar university', 'alexandria university', 'american university in cairo', 'ain shams university', 'assuit university', 'suez canal university', 'mansoura university', 'zagm university', 'helwan university', 'minia university', 'banha university', 'damanhour university', 'kafrelsheikh university', 'south valley university', 'beni suef university', 'al-azhar university (assyut)', 'al-azhar university (mansoura)', 'modern sciences and arts university', 'german university in cairo'],
                
                'Saudi Arabia': ['saudi arabia','riyadh', 'jeddah', 'mecca', 'medina', 'dammam', 'taif', 'buraydah', 'khamis mushait', 'al khobar', 'tabuk',
                                'king saud university', 'king fahd university of petroleum & minerals', 'king abdulaziz university', 'king abdullah university of science and technology', 'king khalid university', 'imam muhammad ibn saud islamic university', 'alfaisal university', 'prince sultan university', 'taif university', 'qassim university', 'uj university', 'najran university', 'jazan university', 'northern border university', 'hajj university', 'taiba university', 'riyadh elm university', 'mist university', 'riyadh tech university', 'king abdulaziz city science technology'],
                
                'UAE': ['uae','dubai', 'abu dhabi', 'sharjah', 'ajman', 'ras al khaimah', 'fujairah', 'umm al quwain', 'al ain',
                                'united arab emirates university', 'khalifa university', 'american university of sharjah', 'american university in dubai', 'university of sharjah', 'zayed university', 'hult international business school dubai', 'university of birmingham dubai', 'masdar institute', 'manipal academy of higher education dubai', 'american university in ras al khaimah', 'canadian university dubai', 'gulf medical university', 'university of dubai', 'american university of ras al khaimah', 'murdoch university dubai', 'institute of management technology dubai', 'hult dubai', 'university of toronto dubai', 'new york university abu dhabi', 'mbzuai'],

                'Thailand': ['thailand','bangkok', 'chiang mai', 'pattaya', 'phuket', 'kon kaen', 'udon thani', 'nakhon ratchasima', 'songkhla', 'nakhon si thammarat', 'hua hin',
                                'chulalongkorn university', 'mahidol university', 'thammasat university', 'king mongkut’s university of technology thonburi', 'king mongkut’s institute of technology ladkrabang', 'kasetsart university', 'surat thani university', 'maharat university', 'mae fah luang university', 'burapha university', 'khon kaen university', 'king mongkut’s university of technology north bangkok', 'ramkhamhaeng university', 'rajamangala university of technology', 'thailand science research and innovation', 'university of thailand', 'silpakorn university', 'srinakharinwirot university', 'southeastern region universities alliance'],
        
                'Malaysia': ['malaysia','kuala lumpur', 'penang', 'johor bahru', 'ipoh', 'shah alam', 'petaling jaya', 'seremban', 'kuantan', 'malacca', 'alor setar',
                                'university of malaya', 'universiti kebangsaan malaysia', 'universiti putra malaysia', 'universiti teknologi malaysia', 'universiti sains malaysia', 'multimedia university', 'universiti teknologi petronas', 'university of nottingham malaysia', 'international islamic university malaysia', 'taj mahal ui', 'taylors university', 'university of cyberjaya', 'science university of malaysia', 'monash university malaysia', 'sunway university', 'intl islamic university malaysia', 'university putra', 'university utm', 'university utp', 'university taylor'],

                'Vietnam': ['vietnam','ho chi minh city', 'hanoi', 'hai phong', 'danang', 'can tho', 'bien hoa', 'nha trang', 'vu tod', 'vinh', 'ha long',
                                'vietnam national university hanoi', 'vietnam national university ho chi minh city', 'ha noi national university', 'ho chi minh city university of technology', 'phen university', 'foreign trade university', 'can tho university', 'dai hoc su pham thanh pho ho chi minh', 'dai hoc bach khoa', 'university of economics ho chi minh city', 'university of science hcmc', 'national economics university', 'hong bang international university', 'dai hoc xay dung', 'dai hoc yen bai', 'dai hoc hue', 'dai hoc dalat', 'dai hoc hue', 'dai hoc khoa hoc tu nhien', 'university of science ha noi'],

                'Nigeria': ['nigeria','nigerian','odumegwu','ojukwu','lagos', 'abuja', 'kaduna', 'port harcourt', 'kano', 'ibadan', 'benin city', 'calabar', 'ilorin', 'oshogbo',
                                'university of lagos', 'obafemi awolowo university', 'university of nigeria nsukka', 'ahmadu bello university', 'covenant university', 'babcock university', 'lagos state university', 'university of ibadan', 'nnamdi azikiwe university', 'federal university of technology minna', 'yaba college of technology', 'federal university of agriculture abeokuta', 'university of benin', 'university of jos', 'university of uyo', 'niger delta university', 'landmark university', 'redeemers university', 'federal university lokoja', 'pan-atlantic university'],

                'South Africa': ['south africa','johannesburg', 'cape town', 'durban', 'pretoria', 'port elizabeth', 'bloemfontein', 'nelspruit', 'kimberley', 'mafic', 'east london',
                                'university of cape town', 'university of the witwatersrand', 'university of pretoria', 'stellenbosch university', 'university of kwazulu-natal', 'university of johannesburg', 'rhodes university', 'north-west university', 'university of south africa', 'cape peninsula university of technology', 'nelson mandela university', 'university of fort hare', 'university of free state', 'university of zimbabwe', 'cape tech', 'university of kwazulu natal', 'central university of technology', 'durban university of technology', 'university of stellenbosch', 'university of limpopo'],

                'Kenya': ['kenya','nairobi', 'mombasa', 'kisumu', 'nakuru', 'eldoret', 'thika', 'embu', 'kitale', 'nyeri', 'malindi',
                                'university of nairobi', 'jomo kenyatta university of agriculture and technology', 'kenyatta university', 'maseno university', 'masinde muliro university of science and technology', 'strathmore university', 'university of eastern africa baraton', 'mount kenya university', 'university of eldoret', 'technological university of kenya', 'united states international university africa', 'president university of africa', 'kabarak university', 'kenya methodist', 'university of nakuru', 'great lakes university of kisumu', 'multimedia university of kenya', 'zetech university', 'kenya polytechnic', 'kuco'],
    
                'Jordan':['jordan'],'Malta':['malta'],

                'New Zealand': ['new zealand','waikato','auckland', 'wellington', 'christchurch', 'hamilton', 'tauranga', 'napier', 'palmerston north', 'dunedin', 'new plymouth', 'whangarei',
                                'university of auckland', 'university of otago', 'university of canterbury', 'victoria university of wellington', 'waikato university', 'massey university', 'unitec institute of technology', 'auckland university of technology', 'lincoln university', 'eastern institute of technology', 'christchurch polytechnic institute', 'nelson marlborough institute of technology', 'western institute of technology at tatu', 'manukau institute of technology', 'university of south pacific', 'manawa institute of technology', 'otago polytechnic', 'university of waikato postgrad', 'new zealand college of business'],
        
                'Czech Republic': ['czech', 'czech republic', 'ceska republika', 'czechia','prague', 'praha', 'ostrava', 'brno', 'plzen', 'pardubice','masaryk university', 'charles university', 'czech technical university','brno university of technology', 'university of economics prague',
                                    'czech academy of sciences', 'palacky university', 'university of west bohemia','vut', 'cvut', 'vse', 'cuni', 'cz', '.cz'],

                'Bangladesh': ['bangladesh','dhaka','chittagong'],

                'Portugal': ['universitade','lisbon','porto','universidade','lisboa','minho'],
                
                'Sri Lanka': ['sri','lanka','wellassa'],
                
                'Azerbaijan':['azerbaijan'],
                
                'Turkey':['istanbul','turkey','ankara','koc'],
                
                'Luxembourg':['luxembourg'],
                
                'Japan': ['japan', 'japanese', 'nippon', 'nihon', '.jp','gakuin','hitotsubashi',
                                'tokyo', 'osaka', 'kyoto', 'nagoya', 'sapporo', 'fukuoka', 'hiroshima', 'sendai', 'kobe', 'yokohama', 'nara', 'kanazawa',
                                'university of tokyo', 'tokyo university', 'kyoto university', 'osaka university', 'tohoku university',
                                'nagoya university', 'kyushu university', 'hokkaido university', 'keio university', 'waseda university',
                                'tokyo institute of technology', 'tokyo tech', 'tokyo university of science', 'nara institute of science and technology',
                                'oita university', 'shibaura institute of technology', 'kobe university', 'hiroshima university',
                                'chiba university', 'kanazawa university', 'tokyo medical and dental university', 'tokyo metropolitan university',
                                'toyo university', 'meiji university', 'hosei university', 'osaka prefecture university', 'osaka metropolitan university'],

            'Autre': ['world bank', 'united nations', 'unesco', 'oecd', 'independant','europe','european','world']
            }

        def identify_country(self, affiliation):


            if pd.isna(affiliation) or str(affiliation).strip() == '':
                return 'Unspecified'

            def clean_text(text):
                text = html.unescape(str(text)).lower()
                text = ''.join(
                    c for c in unicodedata.normalize('NFD', text)
                    if unicodedata.category(c) != 'Mn'
                )
                return text

            def contains_keyword(text, keyword_list):
                text = str(text)  # fix for the bytes issue
                for kw in keyword_list:
                    pattern = r'\b' + re.escape(kw.lower()) + r'\b'
                    if re.search(pattern, text):
                        return True
                return False

            cleaned_affiliation = clean_text(affiliation)

            for country, keywords in self.country_keywords.items():
                if contains_keyword(cleaned_affiliation, keywords):
                    return country

            return 'Unspecified'

    # Using the library to find the countries
    finder = AffiliationCountryResolver()
    tqdm.pandas(desc="Matching affiliations and countries with library (step 3/6) : ")
    df_step_1['country'] = df_step_1['affiliations'].progress_apply(finder.identify_country)

    # Saving the found and unfound countries

    df_found_1 = df_step_1[(df_step_1['country'] != 'Unspecified') & (df_step_1['country'] != 'Autre')]

    df_not_found_1 = df_step_1[df_step_1['country'] == 'Unspecified']
    df_not_found_1 = df_not_found_1.copy()
    df_not_found_1['affiliations'] = df_not_found_1['affiliations'].astype(str)

    ####################### STEP 2.2 : USING ROR API  ###############

    # Charging the data ans cleaning it
    df_step_2 = df_not_found_1.copy()
    ror_df_full = pd.read_csv('data/v1.67-2025-06-24-ror-data.csv', usecols=['id', 'name', 'country.country_name', 'country.country_code']).dropna(subset=['name'])
    ror_df_schema = pd.read_csv('data/v1.67-2025-06-24-ror-data_schema_v2.csv', low_memory=False)

    df_step_2['affiliations_clean'] = df_step_2['affiliations'].str.upper().str.replace(r'[^A-Z ]', '', regex=True).str.strip()

    # Using both datasets to map the countries and affiliations
    name_to_info = {}

    for _, row in ror_df_full.iterrows():
        main_name = str(row['name']).upper().strip()
        name_to_info[main_name] = {
            'country': row.get('country.country_name', 'Unspecified'),
            'country_code': row.get('country.country_code', 'Unspecified'),
            'ror_id': row.get('id', ''),
            'main_name': row.get('name', '')
        }

    for _, row in ror_df_schema.iterrows():
        names = set()
        # Principal name
        if pd.notnull(row.get('name')):
            names.add(str(row['name']).upper().strip())
        # Aliases
        aliases = row.get('aliases')
        if pd.notnull(aliases):
            try:
                alias_list = ast.literal_eval(aliases) if aliases.startswith('[') else aliases.split('|')
                for alias in alias_list:
                    names.add(str(alias).upper().strip())
            except:
                pass
        # Labels
        labels = row.get('labels')
        if pd.notnull(labels):
            try:
                label_list = ast.literal_eval(labels) if labels.startswith('[') else labels.split('|')
                for label in label_list:
                    names.add(str(label).upper().strip())
            except:
                pass
        # Infos
        for name in names:
            if name not in name_to_info:
                name_to_info[name] = {
                    'country': row.get('country.country_name', 'Unspecified'),
                    'country_code': row.get('country.country_code', 'Unspecified'),
                    'ror_id': row.get('id', ''),
                    'main_name': row.get('name', '')
                }

    # Using fuzzy matching
    all_names = list(name_to_info.keys())

    def fast_find_country(affil):
        match = process.extractOne(affil, all_names, scorer=fuzz.token_sort_ratio)
        if match and match[1] >= 85:
            info = name_to_info[match[0]]
            return (info['country'], info['country_code'], info['ror_id'], info['main_name'])
        else:
            return ('Unspecified', 'Unspecified', '', '')
    print("")
    # Using parallel to go faster
    results = Parallel(n_jobs=-1)(
        delayed(fast_find_country)(affil) for affil in tqdm(df_step_2['affiliations_clean'], desc="Matching affiliations and country with ROR API (step 4/6)")
    )

    # Saving the results
    df_step_2.loc[:, ['matched_country', 'matched_country_code', 'matched_ror_id', 'matched_ror_name']] = pd.DataFrame(results, index=df_step_2.index)
    df_step_2 = df_step_2.replace({'T√ºrkiye': 'Turkey'})
    step2 = df_step_2[['affiliations_full_name','affiliations','matched_country']]
    step2 = step2.rename(columns={'matched_country':'country'})
    df_step_2_found = step2[(step2['country'] != 'Unspecified') & (step2['country'] != 'Autre')]
    df_step_2_not_found = step2[step2['country']=='Unspecified']

    # Merging the found affiliations and making it a dictionnary and saving the results
    affiliations_found = pd.concat([df_found_1,df_step_2_found],axis=0).reset_index(drop=True)
    final_df = pd.read_csv(output_info_abstract, sep=';', low_memory=False)
    affil_to_country = dict(zip(affiliations_found['affiliations_full_name'],affiliations_found['country']))
    final_df['country'] = final_df['affiliations'].map(affil_to_country)
    final_df = final_df[final_df['country']!='NaN']
    final_df = final_df[final_df['country']!='Autre']
    final_df = final_df.dropna(subset=['country'])

    final_df.to_csv(output_aff_1_author,sep=';',index=False)

    # couting the not found words
    all_words = []
    for row in df_step_2_not_found['affiliations']:
        words = row.split()
        all_words.extend(words)

    word_counts = Counter(all_words)

    # Convert to DataFrame and saving
    word_df = pd.DataFrame(word_counts.items(), columns=['word', 'count']).sort_values(by='count', ascending=False)
    word_df.to_csv('outputs/affiliations_not_found_word_count.csv', sep=';',index=False)


