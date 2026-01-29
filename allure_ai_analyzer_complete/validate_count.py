#!/usr/bin/env python3
"""Quick validation script to understand test count differences."""

import json
from pathlib import Path
from collections import Counter

results_dir = Path('./allure-results')

# Count all JSON files by type
all_json = list(results_dir.rglob('*.json'))
print(f"Total JSON files: {len(all_json)}\n")

# Categorize files
containers = []
results = []
metadata = []
others = []

for p in all_json:
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        
        if p.name in ['categories.json', 'environment.json', 'executor.json', 'widgets.json']:
            metadata.append(p.name)
        elif 'container' in p.name.lower():
            containers.append(p.name)
        elif isinstance(data, dict) and 'status' in data:
            status = data.get('status', 'unknown')
            results.append((p.name, status))
        else:
            others.append(p.name)
    except:
        pass

print(f"Container files: {len(containers)}")
print(f"Test result files: {len(results)}")
print(f"Metadata files: {len(metadata)}")
print(f"Other files: {len(others)}\n")

# Count by status
status_counter = Counter([status for _, status in results])
print("Test results by status:")
for status, count in status_counter.most_common():
    print(f"  {status}: {count}")

print(f"\nTotal test results with status: {len(results)}")