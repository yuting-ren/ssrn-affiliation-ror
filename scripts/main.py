import os
import sys

from scripts.info_abstractt import info_abstract
#from scripts.info_abstract import info_abstract
from scripts.aff_1_author import aff_1_author
from scripts.computations import computations
from scripts.analysis import analysis

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from path_config import apply_dataset_mode


def main():
    mode = 'full'  # switch to 'toy' to use toydata outputs
    output_info_abstract = apply_dataset_mode('outputs/db_info_abstract.csv', mode)
    output_aff_1_author = apply_dataset_mode('outputs/aff_1_author.csv', mode)
    output_computations = apply_dataset_mode('outputs/computations.csv', mode)
    output_analysis_1 = apply_dataset_mode('outputs/analysis_all_papers.xlsx', mode)
    output_analysis_2 = apply_dataset_mode('outputs/analysis_by_cle.xlsx', mode)
    begin_date = '2015-12-01' # 'YYYY--MM-DD'
    end_date = '2025-07-06'
    interest_name = 'ChatGPT'
    interest_year = 2022
    interest_month = 11
    interest_day = 30

    os.environ["DATASET_MODE"] = mode

    info_abstract('outputs/db_info_abstract.csv', begin_date, end_date, use_toydata=(mode == 'toy'))
    aff_1_author(output_info_abstract,output_aff_1_author)
    computations(output_aff_1_author,output_computations)
    analysis(output_computations,output_analysis_1,output_analysis_2,interest_name,interest_year,interest_month,interest_day)



if __name__ == "__main__":
    main()
