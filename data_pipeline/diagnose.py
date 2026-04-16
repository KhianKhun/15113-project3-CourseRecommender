import json
from pathlib import Path

with open(Path(__file__).parent.parent / 'data' / 'courses.json', encoding='utf-8') as f:
    courses = json.load(f)

print(f'Total courses: {len(courses)}')

avg_len = sum(len(c.get('description', '')) for c in courses) / len(courses)
print(f'Avg description length: {avg_len:.0f} chars')

from collections import Counter
depts = Counter(c['department'] for c in courses)
for dept, count in sorted(depts.items(), key=lambda x: -x[1])[:10]:
    print(f'  {dept}: {count} courses')