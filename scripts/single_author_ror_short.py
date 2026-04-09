import pandas as pd

input_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_single_author_ror.csv"
short_output_path = "/Users/yutingren/Library/CloudStorage/Dropbox/Mac/Documents/AI/test_nov/abstract_analysis-main/outputs/db_info_abstract_single_author_ror_short.csv"

df_view = pd.read_csv(input_path, sep=";", engine="python")
df_view.head(1000).to_csv(short_output_path, sep=";", index=False)

print("Short file created.")
print("Saved to:", short_output_path)
