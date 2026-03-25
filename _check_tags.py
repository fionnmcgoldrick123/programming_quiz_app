import pandas as pd, re
from collections import Counter

df = pd.read_csv('ml_models/tag_classifier/leetcode.csv')
df = df.dropna(subset=['problem_description', 'topic_tags']).copy()
df['tags'] = df['topic_tags'].apply(lambda raw: re.findall(r"'([^']+)'", str(raw)))
df = df[df['tags'].apply(len) > 0]

tag_counts = Counter()
for t in df['tags']:
    tag_counts.update(t)

print(f'Rows: {len(df)}  Unique tags: {len(tag_counts)}  Avg tags/q: {df["tags"].apply(len).mean():.2f}')
for tag, count in tag_counts.most_common():
    print(f'  {tag:<35} {count:>4}')
