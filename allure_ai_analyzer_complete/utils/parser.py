"""Utilities to parse allure-results JSON files into a normalized Python structure.
The parser is designed to be forgiving because Allure result filenames and structures may vary.
It looks for JSON files that represent individual test results and extracts:
 - name
 - status
 - steps (list of dicts)
 - statusDetails (message/trace)
 - attachments (list)
"""
import json
from pathlib import Path
import os

TEXT_ATTACHMENT_EXTS = {'.txt', '.log', '.json', '.xml', '.py', '.java', '.html'}
MAX_ATTACHMENT_BYTES = 4096  # read up to this many bytes for context

def _read_attachment_text(path: Path):
    try:
        ext = path.suffix.lower()
        if ext in TEXT_ATTACHMENT_EXTS:
            with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                data = fh.read(MAX_ATTACHMENT_BYTES)
                return data
        else:
            # binary (image etc) - return small placeholder
            return f"[binary attachment: {path.name} - size={path.stat().st_size} bytes]"
    except Exception as e:
        return f"[error reading attachment: {e}]"

def load_allure_results(results_dir, debug=False):
    """Load from allure-results directory."""
    results_dir = Path(results_dir)
    if not results_dir.exists():
        raise FileNotFoundError(f"Allure results directory not found: {results_dir}")

    all_tests = []
    skipped_files = {
        'container_only': 0,
        'metadata': 0,
        'parse_error': 0,
        'no_relevant_data': 0
    }
    
    # Look for ALL .json files, not just *-result.json
    json_files = list(results_dir.glob('*.json'))
    
    for p in json_files:
        filename = p.name.lower()
        
        # Skip known metadata files by name
        if filename in ['categories.json', 'environment.json', 'executor.json']:
            skipped_files['metadata'] += 1
            if debug:
                print(f"  [SKIP] Metadata file: {p.name}")
            continue
            
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
        except Exception as e:
            skipped_files['parse_error'] += 1
            if debug:
                print(f"  [SKIP] Parse error in {p.name}: {e}")
            continue
            
        if not isinstance(data, dict):
            skipped_files['no_relevant_data'] += 1
            if debug:
                print(f"  [SKIP] Not a dict: {p.name}")
            continue
        
        # Determine if this is a test result or pure container
        is_container = filename.endswith('-container.json') or 'children' in data
        has_status = 'status' in data
        has_name = 'name' in data or 'fullName' in data
        
        # Skip pure containers (no status, just orchestration)
        if is_container and not has_status:
            skipped_files['container_only'] += 1
            if debug:
                print(f"  [SKIP] Pure container: {p.name}")
            continue
        
        # Must have either status or name to be considered a test
        if not has_status and not has_name:
            skipped_files['no_relevant_data'] += 1
            if debug:
                print(f"  [SKIP] No status/name: {p.name}")
            continue
        
        # This looks like a test result - extract data
        name = data.get('name') or data.get('fullName') or data.get('title') or p.stem
        status = data.get('status', 'unknown')
        steps = data.get('steps') or []
        statusDetails = data.get('statusDetails', {})
        historyId = data.get('historyId')
        uuid = data.get('uuid') or data.get('testCaseId')
        
        # Some files might have nested result structure
        if not status or status == 'unknown':
            nested_result = data.get('result', {})
            if nested_result:
                status = nested_result.get('status', status)
                if not statusDetails:
                    statusDetails = nested_result.get('statusDetails', {})
        
        attachments = []
        for a in data.get('attachments', []) or []:
            source = a.get('source') or a.get('file')
            if source:
                att_path = results_dir / source
                if not att_path.exists():
                    att_path = p.parent / source
                attachments.append({
                    'name': a.get('name') or source,
                    'source': str(att_path) if att_path.exists() else source,
                    'snippet': _read_attachment_text(att_path) if att_path.exists() else None
                })
        
        test_obj = {
            'file': str(p),
            'uuid': uuid,
            'name': name,
            'status': status,
            'steps': steps,
            'statusDetails': statusDetails,
            'attachments': attachments,
            'historyId': historyId,
            'stop': data.get('stop', 0),
            'start': data.get('start', 0),
            'fullName': data.get('fullName')
        }
        
        all_tests.append(test_obj)
        
        if debug:
            print(f"  [LOAD] {name[:50]} - status: {status} - uuid: {uuid or 'None'}")
    
    # Group by historyId to handle retries - keep only the LAST execution
    grouped = {}
    retry_count = 0
    
    for test in all_tests:
        history_id = test.get('historyId')
        
        # Primary key: historyId, fallback to fullName, name, uuid, or file
        key = history_id or test.get('fullName') or test.get('name') or test.get('uuid') or test.get('file')
        
        if key not in grouped:
            grouped[key] = test
        else:
            # Keep the test with the latest timestamp (last retry)
            existing_stop = grouped[key].get('stop', 0)
            current_stop = test.get('stop', 0)
            
            if current_stop > existing_stop:
                if debug:
                    print(f"  [RETRY] Replacing older execution: {grouped[key].get('name')}")
                grouped[key] = test
                retry_count += 1
            else:
                if debug:
                    print(f"  [RETRY] Skipping older execution: {test.get('name')}")
                retry_count += 1
    
    out = list(grouped.values())
    
    print(f"\n{'='*60}")
    print(f"ALLURE RESULTS PARSING SUMMARY")
    print(f"{'='*60}")
    print(f"Total JSON files found: {len(json_files)}")
    print(f"Skipped files:")
    print(f"  - Pure containers: {skipped_files['container_only']}")
    print(f"  - Metadata files: {skipped_files['metadata']}")
    print(f"  - Parse errors: {skipped_files['parse_error']}")
    print(f"  - No relevant data: {skipped_files['no_relevant_data']}")
    print(f"Test result files loaded: {len(all_tests)}")
    print(f"Retries/duplicates removed: {retry_count}")
    print(f"Unique tests (final): {len(out)}")
    print(f"{'='*60}\n")
    
    return out