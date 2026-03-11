from scripts.info_abstractt import info_abstract
#from scripts.info_abstract import info_abstract
from scripts.aff_1_author import aff_1_author
from scripts.computations import computations
from scripts.analysis import analysis


def main():
    output_info_abstract = 'outputs/db_info_abstract.csv'
    output_aff_1_author = 'outputs/aff_1_author.csv'
    output_computations = 'outputs/computations.csv'
    output_analysis_1 = 'outputs/analysis_all_papers.xlsx'
    output_analysis_2 = 'outputs/analysis_by_cle.xlsx'
    begin_date = '2015-12-01' # 'YYYY--MM-DD'
    end_date = '2017-07-06'
    interest_name = 'ChatGPT'
    interest_year = 2022
    interest_month = 11
    interest_day = 30

    info_abstract(output_info_abstract, begin_date, end_date)
    aff_1_author(output_info_abstract,output_aff_1_author)
    computations(output_aff_1_author,output_computations)
    analysis(output_computations,output_analysis_1,output_analysis_2,interest_name,interest_year,interest_month,interest_day)



if __name__ == "__main__":
    main()


