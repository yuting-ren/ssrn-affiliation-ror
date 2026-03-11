import pandas as pd
import re

dict_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/dictionary.csv"
output_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/dictionary_renamed.csv"

# 读取
df = pd.read_csv(dict_path, sep=";")

# 重命名列
df = df.rename(columns={
    "affiliations": "old names",
    "author_1_institution": "ror_name",
    "author_1_ror_id": "ror_id"
})

# 生成 simplified name
def simplify_name(text):
    if pd.isna(text):
        return None
    text = str(text).lower()
    text = re.sub(r"\band\b", "", text)          # 去掉单词 and
    text = re.sub(r"[^a-z0-9\s]", "", text)      # 去掉特殊字符
    text = re.sub(r"\s+", "", text).strip()      # 合并多余空格
    return text

df["simplified name"] = df["ror_name"].apply(simplify_name)

# 保存
df.to_csv(output_path, sep=";", index=False)

print("Done.")
print("Saved to:", output_path)
print(df.head())