"""Generate a Markdown report from AI analyses with embedded screenshots."""
import json
import shutil
from pathlib import Path
from datetime import datetime

class MarkdownReport:
    def __init__(self, analyses, report_dir=None):
        """
        Args:
            analyses: List of {'test': <test dict>, 'analysis': <ai dict>}
            report_dir: Path to allure-report directory (for screenshots)
        """
        self.analyses = analyses
        self.report_dir = Path(report_dir) if report_dir else None
    
    def save(self, output_path):
        """Generate and save the markdown report."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create screenshots directory
        screenshots_dir = output_path.parent / 'screenshots'
        screenshots_dir.mkdir(exist_ok=True)
        
        content = self._generate(screenshots_dir)
        output_path.write_text(content, encoding='utf-8')
    
    def _copy_screenshot(self, attachment, screenshots_dir, test_id, screenshot_index):
        """Copy screenshot to analysis output directory with test ID naming."""
        if not self.report_dir:
            return None
        
        # Find the screenshot file
        source = self.report_dir / 'data' / 'attachments' / attachment['source']
        if not source.exists():
            return None
        
        try:
            # Get file extension
            source_path = Path(attachment['source'])
            ext = source_path.suffix or '.png'
            
            # Name format: testid_1.png, testid_2.png, etc.
            dest_filename = f"{test_id}_{screenshot_index}{ext}"
            dest = screenshots_dir / dest_filename
            
            shutil.copy2(source, dest)
            return f"screenshots/{dest_filename}"
        except Exception as e:
            print(f"Warning: Could not copy screenshot {attachment['source']}: {e}")
            return None
    
    def _extract_error_details(self, test):
        """Extract comprehensive error details from test."""
        details = {}
        
        # Status message
        details['status_message'] = test.get('statusMessage', '')
        
        # Stack trace
        status_details = test.get('statusDetails', {})
        details['stack_trace'] = status_details.get('trace', '')
        
        # Failed steps
        test_stage = test.get('testStage', {})
        failed_steps = []
        for step in test_stage.get('steps', []):
            if step.get('status') in ['failed', 'broken']:
                failed_steps.append({
                    'name': step.get('name', ''),
                    'status': step.get('status', ''),
                    'message': step.get('statusMessage', '')
                })
        details['failed_steps'] = failed_steps
        
        # Attachments (logs)
        log_attachments = []
        for att in test_stage.get('attachments', []):
            if att.get('type') == 'text/plain' and att.get('name') in ['stdout', 'stderr', 'log']:
                log_attachments.append(att)
        details['log_attachments'] = log_attachments
        
        return details
    
    def _generate(self, screenshots_dir):
        """Generate markdown content with embedded screenshots."""
        lines = []
        lines.append("# 🔍 AI Test Failure Analysis Report")
        lines.append(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
        
        # Summary section
        summary = self.summary()
        lines.append("## 📊 Summary\n")
        lines.append(f"- **Total Tests Analyzed:** `{summary['total_analyzed']}`\n")
        lines.append("### Classification Breakdown\n")
        lines.append("| Classification | Count | Percentage |")
        lines.append("|----------------|-------|------------|")
        
        total = summary['total_analyzed']
        for cls, count in sorted(summary['by_classification'].items(), key=lambda x: -x[1]):
            pct = (count / total * 100) if total > 0 else 0
            lines.append(f"| {cls} | {count} | {pct:.1f}% |")
        
        lines.append("\n---\n")
        lines.append("## 📋 Individual Test Analysis\n")
        
        # Individual test results
        for idx, item in enumerate(self.analyses, 1):
            test = item['test']
            analysis = item['analysis']
            
            test_name = test.get('name', 'Unknown')
            test_id = test.get('uid', 'unknown')
            status = test.get('status', 'unknown')
            
            lines.append(f"\n### {idx}. ❌ {test_name}\n")
            
            # Test metadata
            lines.append("| Property | Value |")
            lines.append("|----------|-------|")
            lines.append(f"| **Test ID** | `{test_id}` |")
            lines.append(f"| **Status** | `{status}` |")
            
            # AI Analysis summary
            classification = analysis.get('classification', 'Unknown')
            confidence = analysis.get('confidence', 0.0)
            confidence_emoji = self._get_confidence_emoji(confidence)
            
            lines.append(f"| **AI Classification** | `{classification}` |")
            lines.append(f"| **Confidence** | {confidence_emoji} `{confidence:.2f}` |\n")
            
            # Error details
            error_details = self._extract_error_details(test)
            
            # Status message
            if error_details['status_message']:
                lines.append("#### 📋 Error Message\n")
                lines.append("```")
                lines.append(error_details['status_message'][:500])
                if len(error_details['status_message']) > 500:
                    lines.append("...[truncated]")
                lines.append("```\n")
            
            # Screenshots
            test_stage = test.get('testStage', {})
            screenshot_attachments = [
                att for att in test_stage.get('attachments', [])
                if att.get('type') == 'image/png'
            ]
            
            if screenshot_attachments:
                lines.append("#### 📸 Failure Screenshot\n")
                for screenshot_idx, att in enumerate(screenshot_attachments[:2], 1):  # Max 2 screenshots
                    screenshot_path = self._copy_screenshot(att, screenshots_dir, test_id, screenshot_idx)
                    if screenshot_path:
                        lines.append(f"![{att.get('name', 'Screenshot')}]({screenshot_path})\n")
                    else:
                        lines.append(f"*Screenshot not available: {att.get('name', 'screenshot')}*\n")
                
                if len(screenshot_attachments) > 2:
                    lines.append(f"*{len(screenshot_attachments) - 2} more screenshot(s) not shown*\n")
            
            # Stack trace
            if error_details['stack_trace']:
                lines.append("<details>")
                lines.append("<summary>🔍 <b>Stack Trace</b> (click to expand)</summary>\n")
                lines.append("```")
                lines.append(error_details['stack_trace'][:1000])
                if len(error_details['stack_trace']) > 1000:
                    lines.append("...[truncated]")
                lines.append("```")
                lines.append("</details>\n")
            
            # Failed steps
            if error_details['failed_steps']:
                lines.append("<details>")
                lines.append("<summary>📝 <b>Failed Test Steps</b> (click to expand)</summary>\n")
                for step in error_details['failed_steps'][:5]:
                    lines.append(f"- **{step['name']}** - `{step['status']}`")
                    if step['message']:
                        lines.append(f"  - {step['message'][:200]}")
                lines.append("</details>\n")
            
            # AI Analysis
            lines.append("#### 🤖 AI Analysis\n")
            lines.append("| Aspect | Details |")
            lines.append("|--------|---------|")
            lines.append(f"| **Root Cause** | {analysis.get('root_cause', 'N/A')} |")
            lines.append(f"| **Suggestion** | {analysis.get('suggestion', 'N/A')} |")
            lines.append(f"| **Rationale** | {analysis.get('rationale', 'N/A')} |\n")
            
            lines.append("---\n")
        
        return '\n'.join(lines)
    
    def _get_confidence_emoji(self, confidence):
        """Return emoji based on confidence level."""
        if confidence >= 0.9:
            return "🟢"
        elif confidence >= 0.7:
            return "🟡"
        elif confidence >= 0.5:
            return "🟠"
        elif confidence >= 0.3:
            return "🔴"
        else:
            return "⚫"
    
    def summary(self):
        """Generate summary statistics."""
        by_classification = {}
        for item in self.analyses:
            cls = item['analysis'].get('classification', 'Unknown')
            by_classification[cls] = by_classification.get(cls, 0) + 1
        
        return {
            'total_analyzed': len(self.analyses),
            'by_classification': by_classification
        }