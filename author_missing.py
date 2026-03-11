import pandas as pd

# 读取数据
df = pd.read_csv("/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract.csv")

# 需要统计的列
cols = ["author_1_id", "author_2_id", "author_3_id"]

# 统计空值
missing_counts = df[cols].isna().sum()

print(missing_counts)