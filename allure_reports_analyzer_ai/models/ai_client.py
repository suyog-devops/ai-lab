"""AI Client for analyzing Allure test failures using OpenAI API."""
import os
import json
import re
from openai import OpenAI

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEFAULT_MODEL = os.getenv('OPENAI_MODEL') or 'gpt-4o-mini'

def _sanitize_text(s: str) -> str:
    """Remove sensitive data and truncate."""
    if not s:
        return ''
    
    # Redact secrets
    secret_patterns = [
        (re.compile(r'api[_-]?key\s*=\s*\S+', re.IGNORECASE), '[REDACTED_API_KEY]'),
        (re.compile(r'Bearer\s+[A-Za-z0-9\-\._~\+/]+', re.IGNORECASE), '[REDACTED_TOKEN]'),
        (re.compile(r'password\s*=\s*\S+', re.IGNORECASE), '[REDACTED_PASSWORD]')
    ]
    
    out = s
    for pattern, replacement in secret_patterns:
        out = pattern.sub(replacement, out)
    
    # Truncate
    if len(out) > 5000:
        out = out[:5000] + '\n...[truncated]'
    
    return out

def _extract_error_details(test: dict) -> tuple:
    """Extract error message and trace from test object."""
    error_message = ''
    error_trace = ''
    
    # Try to get from root level
    error_message = test.get('statusMessage', '')
    error_trace = test.get('statusTrace', '')
    
    # If not found, try statusDetails
    if not error_message:
        status_details = test.get('statusDetails', {})
        error_message = status_details.get('message', '')
        error_trace = status_details.get('trace', '')
    
    # If still not found, look in testStage steps (for failed steps)
    if not error_message:
        test_stage = test.get('testStage', {})
        steps = test_stage.get('steps', [])
        
        for step in steps:
            if step.get('status') in ['failed', 'broken']:
                error_message = step.get('statusMessage', '')
                error_trace = step.get('statusTrace', '')
                if error_message:
                    break
    
    return error_message, error_trace

def _extract_attachment_content(test: dict, results_dir: str = None) -> str:
    """Extract text content from attachments (stdout, stderr, logs)."""
    attachment_text = ''
    
    # Get attachments from testStage
    test_stage = test.get('testStage', {})
    attachments = test_stage.get('attachments', [])
    
    if not results_dir:
        return attachment_text
    
    for attachment in attachments[:3]:  # Limit to first 3 attachments
        att_type = attachment.get('type', '')
        att_source = attachment.get('source', '')
        
        # Only read text files
        if 'text/plain' in att_type and att_source:
            try:
                att_path = os.path.join(results_dir, att_source)
                if os.path.exists(att_path):
                    with open(att_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        attachment_text += f"\n--- {attachment.get('name', 'Attachment')} ---\n"
                        attachment_text += _sanitize_text(content)
            except Exception as e:
                print(f"Warning: Could not read attachment {att_source}: {e}")
    
    return attachment_text

class AIClient:
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            raise EnvironmentError('OPENAI_API_KEY not set')
        self.client = OpenAI(api_key=self.api_key)
        self.model = model or DEFAULT_MODEL

    def _build_prompt(self, test: dict, results_dir: str = None) -> str:
        # Extract test data
        name = test.get('name', 'Unknown')
        status = test.get('status', 'unknown')
        
        # Extract error details properly
        error_message, error_trace = _extract_error_details(test)
        
        # Extract attachment content
        attachment_content = _extract_attachment_content(test, results_dir)
        
        # Extract steps
        test_stage = test.get('testStage', {})
        steps = test_stage.get('steps', [])
        steps_text = '\n'.join([
            f"- {s.get('name')} ({s.get('status')}) {s.get('statusMessage', '')[:100]}" 
            for s in steps[:20]
        ])
        
        # Build context
        context = f"""
Test Name: {name}
Status: {status}

Error Message:
{_sanitize_text(error_message) if error_message else 'No error message'}

Stack Trace:
{_sanitize_text(error_trace) if error_trace else 'No stack trace'}

Test Steps (first 20):
{steps_text}

Attachments Content:
{attachment_content if attachment_content else 'No attachment content available'}

Total Steps: {len(steps)}
Total Attachments: {len(test_stage.get('attachments', []))}
"""

        prompt = f"""You are an expert Senior Test Automation Engineer responsible for analyzing automated test failures with strict accuracy, zero hallucination, and evidence-based reasoning only.

Your task: Classify the test failure into one category, determine confidence, identify the exact root cause (quoted from logs), and provide an actionable suggestion.

────────────────────────────────────────────────────────────
CLASSIFICATION CRITERIA (DESCRIPTIVE — STRICT — NO GUESSING)
────────────────────────────────────────────────────────────

1. APPLICATION BUG
   Failures caused by incorrect application logic, business rules, API responses, or application-side exceptions.
   Characteristics:
     - Clear assertion mismatch: expected vs actual
     - Wrong business logic or incorrect API payload
     - Backend or application stack trace
     - Consistent failures (no retry passes)
   Evidence:
     - "AssertionError: expected X but got Y"
     - Application stack traces (Java/Node/Python/.NET)

   Rule:
     - Do NOT classify as Application Bug unless the evidence explicitly shows application-side failure.

2. AUTOMATION SCRIPT ISSUE
   Failures caused by defects in the test code or automation framework.
   Characteristics:
     - Locator errors (not found, stale element)
     - Wrong assertion logic written in test
     - Test framework failures (Playwright/Selenium/PyTest/JUnit)
     - beforeAll/beforeEach teardown failures
     - Explicitly skipped test (tags, annotations, config-based skip)
   Evidence:
     - "locator(…) not found"
     - Errors from test files or test framework stack traces
     - Explicit skip markers such as "test skipped by condition"

   Rule:
     - Only classify if test code/framework errors are explicitly shown.

3. FLAKY TEST
   Failures caused by inconsistent behavior.
   STRICT REQUIREMENTS:
     - MUST have retry history showing BOTH pass AND fail.
     - MUST show inconsistent results.
   Characteristics:
     - Timing-sensitive failures that pass on retry
     - Different errors across attempts

   Rule:
     - A single failure with timing keywords is NOT flaky.
     - No retry history = cannot classify as flaky.

4. NETWORK/TIMEOUT ISSUE
   Failures caused by connectivity or transport errors.
   Characteristics:
     - ECONNREFUSED, ETIMEDOUT, DNS failures
     - SSL handshake issues
     - Gateway 5xx errors (502/503/504)
     - API request timeouts
   Evidence:
     - "ECONNREFUSED"
     - "ENOTFOUND"
     - "Request timed out"

   Rule:
     - Only classify if network or timeout keywords are explicitly present.

5. ENVIRONMENT / INFRASTRUCTURE ISSUE
   Failures caused by misconfigured or unavailable infrastructure.
   Characteristics:
     - Database/service unreachable
     - Missing environment variables
     - Service not running (Redis, Kafka, backend)
     - Wrong environment loaded
   Evidence:
     - "Connection refused to postgres"
     - "Environment variable X not set"
     - "Service unavailable"

   Rule:
     - Must be explicitly stated; no assumptions.

6. TEST DATA ISSUE
   Failures caused by missing, invalid, or polluted test data.
   Characteristics:
     - Required data missing
     - Duplicate key or constraint errors
     - Invalid or expired tokens
     - State pollution from previous tests
   Evidence:
     - "duplicate key violates constraint"
     - "record not found"
     - "missing required field"

   Rule:
     - Only classify if logs mention data problems explicitly.

7. BLOCKED / DEPENDENT TEST (NEW — STRICT)
   A test was skipped NOT because of test code issues, but because:
     - A previous test in the suite failed
     - A beforeAll/beforeEach in a different test file failed
     - A critical dependency failed before this test ran
     - The test runner aborted due to upstream failure
   Characteristics:
     - Skip message includes dependency, upstream failure, or suite abort
     - Test never executed, so no test logic or assertion ran
   Evidence:
     - "skipped because previous test failed"
     - "blocked by failure in beforeAll"
     - "test skipped due to earlier errors"

   Rule:
     - This is NOT an Automation Script Issue unless the skip comes from the test file itself.
     - Use ONLY when skip reason points to upstream failure.

────────────────────────────────────────────────────────────
DECISION RULES (STRICT)
────────────────────────────────────────────────────────────

- If test is SKIPPED:
    - If skipped due to previous test failure, suite abort, or dependency → **Blocked / Dependent Test**
    - If skipped due to test-level annotation, tag, or conditional skip → **Automation Script Issue**
    - If skipped because the test file's own setup/teardown failed → **Automation Script Issue**

- If clear business logic assertion mismatch → Application Bug  
- If locator failure → Automation Script Issue  
- If explicit network keywords → Network/Timeout Issue  
- Only classify as Flaky with explicit retry data showing mixed outcomes  
- If evidence is missing, unclear, or ambiguous → classification = "Unknown" with low confidence  

────────────────────────────────────────────────────────────
ANTI-HALLUCINATION RULES (MANDATORY)
────────────────────────────────────────────────────────────

1. You MUST NOT invent logs, errors, or messages.
2. Root cause MUST quote an exact string from the provided context.
3. You MUST NOT infer retry history — only use what is shown.
4. You MUST NOT assume application behavior not present in logs.
5. You MUST NOT assume environment variables, services, or data states.
6. If multiple interpretations are possible, choose "Unknown".
7. Confidence must reflect evidence strength — no unjustified high scores.
8. If unsure, classify with low confidence (<0.3) and explain uncertainty.
9. You MUST NOT add extra fields or modify the JSON schema.
10. Keep the output concise, factual, and strictly evidence-based.

────────────────────────────────────────────────────────────
CONFIDENCE SCORING RULES
────────────────────────────────────────────────────────────
- 0.9–1.0 → Strong explicit evidence, no ambiguity  
- 0.7–0.89 → Solid evidence but some minor uncertainty  
- 0.5–0.69 → Moderate evidence  
- 0.3–0.49 → Weak evidence  
- <0.3 → Insufficient data, ambiguous, or no clear category  

────────────────────────────────────────────────────────────
TEST DATA
────────────────────────────────────────────────────────────
{context}

────────────────────────────────────────────────────────────
REQUIRED OUTPUT FORMAT (STRICT JSON ONLY)
────────────────────────────────────────────────────────────
Respond with ONLY valid JSON (no markdown, no comments, no explanation outside JSON):

{{
  "classification": "One of: Application Bug | Automation Script Issue | Flaky Test | Network/Timeout Issue | Environment Issue | Test Data Issue | Blocked/Dependent Test | Unknown",
  "confidence": <number between 0.0 and 1.0>,
  "root_cause": "Exact quoted error message snippet from logs",
  "suggestion": "Concrete, actionable next step",
  "rationale": "Short, factual explanation referencing specific evidence from the logs"
}}

Do not output anything else.
"""
        return prompt

    def analyze_failure(self, test: dict, results_dir: str = None) -> dict:
        """Analyze a failed test with proper error extraction."""
        prompt = self._build_prompt(test, results_dir)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': 'You are an expert test automation engineer. Respond ONLY with valid JSON, no markdown.'},
                    {'role': 'user', 'content': prompt}
                ],
                temperature=0.2,
                max_tokens=700,
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
                content = content.strip()
            
            # Try to find JSON object
            m = re.search(r'\{.*\}', content, re.DOTALL)
            json_text = m.group(0) if m else content
            result = json.loads(json_text)
            
            # Validate classification
            valid_classifications = [
                'Application Bug', 'Automation Script Issue', 'Flaky Test',
                'Network/Timeout Issue', 'Environment Issue', 'Test Data Issue',
                'Blocked/Dependent Test', 'Unknown'
            ]
            
            if result.get('classification') not in valid_classifications:
                result['classification'] = 'Unknown'
                result['confidence'] = 0.2
            
            # Ensure confidence is float
            if 'confidence' in result:
                try:
                    result['confidence'] = float(result['confidence'])
                    result['confidence'] = max(0.0, min(1.0, result['confidence']))
                except:
                    result['confidence'] = 0.5
            
            # Ensure all required fields exist
            required_fields = ['classification', 'root_cause', 'suggestion', 'confidence', 'rationale']
            for field in required_fields:
                if field not in result:
                    result[field] = 'N/A'
            
            return result
            
        except json.JSONDecodeError as e:
            return {
                'classification': 'Unknown',
                'root_cause': f'Failed to parse AI response: {str(e)}',
                'suggestion': 'Manual investigation required - AI response was not valid JSON',
                'confidence': 0.1,
                'rationale': 'AI output was not parseable JSON'
            }
        except Exception as e:
            return {
                'classification': 'Unknown',
                'root_cause': f'Analysis error: {str(e)}',
                'suggestion': 'Manual investigation required - unexpected error',
                'confidence': 0.1,
                'rationale': f'Error during AI analysis: {type(e).__name__}'
            }