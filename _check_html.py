import pandas as pd
df = pd.read_csv('ml_models/tag_classifier/leetcode.csv')
df = df.dropna(subset=['problem_description'])
sample = df['problem_description'].iloc[0]
print("SAMPLE 1:")
print(sample[:500])
print("\n\nSAMPLE 2:")
sample2 = df['problem_description'].iloc[10]
print(sample2[:500])
print("\n\nChecking for HTML tags:")
import re
html_count = df['problem_description'].str.contains('<[^>]+>', regex=True).sum()
print(f"Rows with HTML: {html_count}/{len(df)}")
