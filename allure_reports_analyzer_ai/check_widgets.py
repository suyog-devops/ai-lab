#!/usr/bin/env python3
"""Check widgets.json or summary files for test counts."""

import json
from pathlib import Path

results_dir = Path('./allure-results')

# Look for summary/widget files
summary_files = ['widgets.json', 'summary.json', 'test-cases.json']

for filename in summary_files:
    filepath = results_dir / filename
    if filepath.exists():
        print(f"\n{'='*60}")
        print(f"Found: {filename}")
        print(f"{'='*60}")
        try:
            data = json.loads(filepath.read_text(encoding='utf-8'))
            print(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Error reading: {e}")

# Also check the 6 "other" files
print(f"\n{'='*60}")
print("Checking 'other' JSON files:")
print(f"{'='*60}")

for p in results_dir.rglob('*.json'):
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        
        # Skip known files
        if 'container' in p.name.lower() or p.name in ['executor.json', 'categories.json']:
            continue
            
        # Skip files with 'status' (already counted)
        if isinstance(data, dict) and 'status' in data:
            continue
            
        # This is an "other" file
        print(f"\nFile: {p.name}")
        print(f"Type: {type(data)}")
        if isinstance(data, dict):
            print(f"Keys: {list(data.keys())[:10]}")
        elif isinstance(data, list):
            print(f"List length: {len(data)}")
            if len(data) > 0:
                print(f"First item type: {type(data[0])}")
                if isinstance(data[0], dict):
                    print(f"First item keys: {list(data[0].keys())[:10]}")
    except Exception as e:
        print(f"Error reading {p.name}: {e}")