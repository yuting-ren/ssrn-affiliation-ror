import pandas as pd

# 输入文件
input_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_single_author_institution_debug.csv"

# 输出文件
output_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/dictionary.csv"

# 读取数据
df = pd.read_csv(input_path, sep=";", engine="python")

# 只保留需要的列
df = df[["affiliations", "author_1_institution", "author_1_ror_id"]]
df = df.rename(columns={
    "affiliations": "old names",
    "author_1_institution": "ror_name",
    "author_1_ror_id": "ror_id"
})

# 删除 ror_name 为空的行
df = df[df["ror_name"].notna() & (df["ror_name"].str.strip() != "")]

# 追加固定映射
manual_rows = pd.DataFrame([
    {"old names": "Independent", "ror_name": "unknown", "ror_id": None},
    {"old names": "affiliation not provided to SSRN", "ror_name": "unknown", "ror_id": None},
])

df = pd.concat([df, manual_rows], ignore_index=True)

# 删除重复行
df = df.drop_duplicates()


# 保存
df.to_csv(output_path, sep=";", index=False)

print("Dictionary created.")
print("Saved to:", output_path)
print("Number of rows:", len(df))
