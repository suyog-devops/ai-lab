#!/usr/bin/env python3
"""Entry point for Allure AI Analyzer.
Usage:
  python analyze_allure.py --results-dir ./allure-results --out-dir ./analysis_out
  python analyze_allure.py --from-report --report-dir ./allure-report --out-dir ./analysis_out
"""
import argparse
import os
import json
from dotenv import load_dotenv
from utils.parser import load_allure_results, _read_attachment_text
from models.ai_client import AIClient
from report_generators.md_report import MarkdownReport
from pathlib import Path

load_dotenv()

def load_from_report(report_dir, results_dir=None):
    """Load tests from allure-report/data/test-cases/ for exact UI matching.
    
    Args:
        report_dir: Path to allure-report directory
        results_dir: Optional path to allure-results for attachment resolution
    """
    report_dir = Path(report_dir)
    test_cases_dir = report_dir / 'data' / 'test-cases'
    
    if not test_cases_dir.exists():
        raise FileNotFoundError(f"Report test-cases directory not found: {test_cases_dir}\nHave you run 'allure generate'?")
    
    print(f"Loading from allure-report/data/test-cases/...\n")
    
    # Try to find allure-results for attachments
    if results_dir:
        results_path = Path(results_dir)
    else:
        # Try default location (sibling to allure-report)
        results_path = report_dir.parent / 'allure-results'
    
    if results_path.exists():
        print(f"Found allure-results at: {results_path}")
        print("Will attempt to resolve attachment paths from allure-results\n")
    else:
        print(f"Warning: allure-results not found at {results_path}")
        print("Attachments will not be loaded\n")
        results_path = None
    
    # Deduplicate by historyId (same as Allure UI does)
    by_history = {}
    total_files = 0
    
    for tc_file in test_cases_dir.glob('*.json'):
        total_files += 1
        try:
            tc = json.loads(tc_file.read_text(encoding='utf-8'))
            history_id = tc.get('historyId')
            key = history_id or tc.get('fullName') or tc.get('name') or tc_file.stem
            
            # Process attachments if results_path exists
            if results_path and 'testStage' in tc:
                test_stage = tc.get('testStage', {})
                attachments = test_stage.get('attachments', [])
                processed_attachments = []
                
                for att in attachments:
                    source = att.get('source')
                    if source:
                        # Try to find attachment in allure-results
                        att_path = results_path / source
                        if att_path.exists():
                            processed_attachments.append({
                                'name': att.get('name', source),
                                'source': str(att_path),
                                'type': att.get('type', ''),
                                'snippet': _read_attachment_text(att_path) if 'text' in att.get('type', '') else None
                            })
                        else:
                            # Keep reference even if file not found
                            processed_attachments.append({
                                'name': att.get('name', source),
                                'source': source,
                                'type': att.get('type', ''),
                                'snippet': f"[Attachment not found: {source}]"
                            })
                
                tc['testStage']['attachments'] = processed_attachments
            
            # Keep latest execution by stop timestamp
            if key not in by_history or tc.get('stop', 0) > by_history[key].get('stop', 0):
                by_history[key] = tc
        except Exception as e:
            print(f"Warning: Failed to parse {tc_file.name}: {e}")
    
    unique_tests = list(by_history.values())
    
    print(f"{'='*60}")
    print(f"ALLURE REPORT PARSING SUMMARY")
    print(f"{'='*60}")
    print(f"Total test case files: {total_files}")
    print(f"Retries removed: {total_files - len(unique_tests)}")
    print(f"Unique tests (final): {len(unique_tests)}")
    print(f"{'='*60}\n")
    
    return unique_tests

def main():
    parser = argparse.ArgumentParser(description='Analyze Allure results with AI and generate report')
    parser.add_argument('--results-dir', default='allure-results', help='Path to allure-results folder')
    parser.add_argument('--report-dir', default='allure-report', help='Path to allure-report folder')
    parser.add_argument('--from-report', action='store_true', 
                       help='Load from allure-report instead of allure-results (matches UI exactly)')
    parser.add_argument('--out-dir', default='analysis_out', help='Output folder for analysis')
    parser.add_argument('--model', default=None, help='Model name to use for AI (overrides env)')
    parser.add_argument('--max-tests', type=int, default=50, help='Max failed tests to send to AI (sampling)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output for parsing')
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load tests from either allure-results or allure-report
    if args.from_report:
        print(f"Loading tests from allure-report: {args.report_dir}")
        tests = load_from_report(args.report_dir, args.results_dir)
        report_dir_for_screenshots = args.report_dir
    else:
        print(f"Loading tests from allure-results: {args.results_dir}")
        tests = load_allure_results(args.results_dir, debug=args.debug)
        report_dir_for_screenshots = None
    
    # Count by status
    status_counts = {}
    for t in tests:
        status = (t.get('status') or 'unknown').lower()
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"{'='*60}")
    print(f"TEST RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Total unique tests: {len(tests)}")
    for status in ['passed', 'failed', 'broken', 'skipped', 'unknown']:
        count = status_counts.get(status, 0)
        if count > 0:
            print(f"  {status.capitalize()}: {count}")
    print(f"{'='*60}\n")

    # Filter for failed/broken/skipped tests (not passed)
    failed = [t for t in tests if t.get('status') and t['status'].lower() not in ['passed', 'unknown']]
    print(f"Tests to analyze (failed/broken/skipped): {len(failed)}")

    if len(failed) == 0:
        print("No failed tests to analyze. Exiting.")
        return

    # Limit tests to analyze to avoid huge cost
    failed_to_analyze = failed[:args.max_tests]
    if len(failed) > args.max_tests:
        print(f"Limiting analysis to first {args.max_tests} tests (use --max-tests to change)\n")

    ai_model = args.model or os.getenv('AI_MODEL') or os.getenv('OPENAI_MODEL') or 'gpt-4o-mini'
    api_key = os.getenv('OPENAI_API_KEY') or os.getenv('API_KEY')
    if not api_key:
        raise SystemExit("OPENAI_API_KEY not set in environment or .env file. Put it in config/.env or export it.")

    ai = AIClient(api_key=api_key, model=ai_model)

    analyses = []
    for i, t in enumerate(failed_to_analyze, 1):
        test_name = t.get('name', 'Unknown')
        print(f"[{i}/{len(failed_to_analyze)}] Analyzing: {test_name}")
        
        # Pass results_dir to AI client for attachment resolution
        analysis = ai.analyze_failure(t, results_dir=args.results_dir)
        analyses.append({'test': t, 'analysis': analysis})

    # Save raw JSON analysis
    out_json = out_dir / 'ai_analysis.json'
    with open(out_json, 'w', encoding='utf-8') as fh:
        json.dump(analyses, fh, indent=2, ensure_ascii=False)
    print(f"\nWrote AI analysis JSON to {out_json}")

    # Generate markdown report with screenshots
    md_path = out_dir / 'ai_allure_analysis.md'
    report = MarkdownReport(analyses, report_dir=report_dir_for_screenshots)
    report.save(md_path)
    print(f"Wrote markdown report to {md_path}")
    
    # Check if screenshots were copied
    screenshots_dir = out_dir / 'screenshots'
    if screenshots_dir.exists():
        screenshot_count = len(list(screenshots_dir.glob('*.png')))
        if screenshot_count > 0:
            print(f"Copied {screenshot_count} screenshots to {screenshots_dir}")
    
    # Print summary
    summary = report.summary()
    print(f"\n{'='*60}")
    print(f"AI ANALYSIS SUMMARY")
    print(f"{'='*60}")
    print(f"Total analyzed: {summary['total_analyzed']}")
    print("By classification:")
    for cls, count in sorted(summary['by_classification'].items(), key=lambda x: -x[1]):
        print(f"  {cls}: {count}")
    print(f"{'='*60}")
    print(f"\n✅ Analysis complete!")
    print(f"📄 Open report: {md_path}")
    print(f"   View in VS Code, GitHub, or any markdown viewer")

if __name__ == '__main__':
    main()