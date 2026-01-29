# 🤖 Allure AI Analyzer

**Intelligent test failure analysis powered by AI** - Automatically classify, diagnose, and get actionable insights for your Allure test failures.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-green.svg)](https://openai.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Classification Categories](#classification-categories)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Output Reports](#output-reports)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Cost Considerations](#cost-considerations)
- [Security & Privacy](#security--privacy)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## 🎯 Overview

Allure AI Analyzer is an intelligent tool that analyzes your Allure test results using AI to provide:
- **Automated root cause analysis** for test failures
- **Evidence-based classification** (Application Bug, Automation Issue, Flaky Test, etc.)
- **Actionable suggestions** for fixing failures
- **Confidence scoring** to indicate analysis reliability
- **Comprehensive reports** in both JSON and Markdown formats

Say goodbye to manual test failure triage! 🚀

---

## ✨ Features

### 🔍 **Intelligent Analysis**
- Analyzes failed, broken, and skipped tests
- Extracts error messages, stack traces, and test steps
- Reads attachment content (logs, stdout, stderr)
- Zero hallucination - evidence-based reasoning only

### 📊 **Accurate Classification**
- 7+ failure categories with strict criteria
- Confidence scoring (0.0 - 1.0)
- Anti-hallucination rules to prevent false diagnoses
- Handles edge cases (missing logs, skipped tests, retries)

### 📈 **Flexible Input Sources**
- Parse from `allure-results/` (raw test data)
- Parse from `allure-report/` (processed data - matches UI exactly)
- Automatic attachment resolution
- Retry detection and deduplication

### 📝 **Rich Reports**
- Human-friendly Markdown reports
- Raw JSON output for automation
- Original error messages alongside AI analysis
- Confidence indicators (🟢 🟡 🟠 🔴 ⚫)
- Summary statistics by classification

### 🔒 **Security First**
- Automatic credential sanitization (API keys, tokens, passwords)
- Configurable log truncation
- Local processing - only analysis sent to AI
- No sensitive data in prompts

---

## 🏷️ Classification Categories

The AI classifies test failures into one of the following categories:

### 1. **Application Bug** 🐛
**What:** Failures caused by incorrect application logic, business rules, or API responses.

**Characteristics:**
- Clear assertion mismatch (expected vs actual)
- Wrong business logic or incorrect API payload
- Backend/application stack traces
- Consistent failures (no retry passes)

**Example:**
```
AssertionError: Expected status 200 but got 500
ValidationError: Email format is invalid
```

---

### 2. **Automation Script Issue** 🔧
**What:** Failures caused by defects in the test code or automation framework.

**Characteristics:**
- Element locator errors (not found, stale element)
- Wrong assertion logic in test
- Test framework failures (Playwright/Selenium/PyTest)
- beforeAll/beforeEach teardown failures

**Example:**
```
Error: locator.click: Timeout 30000ms exceeded
Element not found: button[data-testid="submit"]
BeforeAll hook failed
```

---

### 3. **Flaky Test** 🎲
**What:** Tests that pass and fail inconsistently without code changes.

**Strict Requirements:**
- MUST have retry history showing BOTH pass AND fail
- MUST show inconsistent results

**Characteristics:**
- Timing-sensitive failures
- Race conditions
- Non-deterministic behavior

**Example:**
```
Test passed on retry 2, failed on retry 1 and 3
Animation still in progress
```

⚠️ **Important:** A single failure with timing keywords is NOT classified as flaky without retry evidence.

---

### 4. **Network/Timeout Issue** 🌐
**What:** Failures caused by connectivity or transport errors.

**Characteristics:**
- Connection refused/timeout errors
- SSL handshake failures
- HTTP 5xx errors (502, 503, 504)
- API request timeouts

**Example:**
```
Error: connect ECONNREFUSED 127.0.0.1:3000
HTTP 503 Service Unavailable
TimeoutError: API request timed out after 30s
```

---

### 5. **Environment/Infrastructure Issue** 🏗️
**What:** Failures caused by misconfigured or unavailable infrastructure.

**Characteristics:**
- Database/service unreachable
- Missing environment variables
- Service not running (Redis, Kafka, backend)
- Permission/authentication issues

**Example:**
```
Error: Cannot connect to database at localhost:5432
Redis connection lost
AWS credentials not configured
```

---

### 6. **Test Data Issue** 📦
**What:** Failures caused by missing, invalid, or polluted test data.

**Characteristics:**
- Required data missing
- Duplicate key or constraint violations
- Invalid or expired tokens
- State pollution from previous tests

**Example:**
```
Error: User with email 'test@example.com' already exists
Foreign key constraint violation
Expected product ID 123 to exist
```

---

### 7. **Blocked/Dependent Test** 🚫
**What:** Tests skipped due to upstream failures, not test code issues.

**Characteristics:**
- Previous test in suite failed
- beforeAll in different test file failed
- Critical dependency failed before test ran
- Test runner aborted due to upstream failure

**Example:**
```
Test skipped: previous test failed
Blocked by failure in beforeAll
Suite aborted due to earlier errors
```

---

### 8. **Unknown** ❓
**What:** Insufficient evidence to classify (honest assessment when uncertain).

**When Used:**
- Missing error messages/logs
- Ambiguous evidence
- Multiple interpretations possible
- Low confidence (<0.3)

---

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- OpenAI API key
- Allure test results (from Playwright, Selenium, pytest-allure, etc.)
- Allure command-line tool (optional, for generating `allure-report/`)

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/allure-ai-analyzer.git
   cd allure-ai-analyzer
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   
   # On Windows
   .venv\Scripts\activate
   
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
   Verify installation:
   ```bash
   # Check if packages are installed
   pip list | findstr "openai python-dotenv"  # Windows
   pip list | grep "openai\|python-dotenv"    # macOS/Linux
   ```

4. **Set up configuration**
   ```bash
   cp config/example.env .env
   ```
   
   Edit `.env` and add your OpenAI API key:
   ```env
   OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
   OPENAI_MODEL=gpt-4o-mini  # Optional, defaults to gpt-4o-mini
   ```

5. **Generate Allure Report (if using `--from-report` mode)**
   
   If you only have `allure-results/` directory:
   ```bash
   # Install Allure CLI first (if not already installed)
   # See: https://docs.qameta.io/allure/#_installing_a_commandline
   
   # Generate the report
   allure generate ./allure-results -o ./allure-report
   ```
   
   > **Note:** The `--from-report` mode is recommended as it matches the Allure UI test counts exactly.

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Required
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx

# Optional
OPENAI_MODEL=gpt-4o-mini           # AI model to use (default: gpt-4o-mini)
AI_MODEL=gpt-4o-mini               # Alternative env var name
```

### Supported Models
- `gpt-4o-mini` (default, cost-effective)
- `gpt-4o` (more powerful, higher cost)
- `gpt-4-turbo`
- `gpt-3.5-turbo`

---

## 🚀 Usage

### Quick Start (30 seconds)

```bash
# 1. Set your API key
echo "OPENAI_API_KEY=sk-proj-xxxxx" > .env

# 2. Run analysis
python analyze_allure.py --from-report --report-dir ./allure-report --results-dir ./allure-results

# 3. View report
# Open analysis_out/ai_allure_analysis.md
```

### Basic Usage

**Analyze from `allure-results/` directory:**
```bash
python analyze_allure.py --results-dir ./allure-results --out-dir ./analysis_out
```

**Analyze from `allure-report/` (recommended - matches UI exactly):**
```bash
python analyze_allure.py --from-report --report-dir ./allure-report --results-dir ./allure-results --out-dir ./analysis_out
```

### Command-Line Options

```bash
python analyze_allure.py [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--results-dir PATH` | Path to allure-results folder | `allure-results` |
| `--report-dir PATH` | Path to allure-report folder | `allure-report` |
| `--from-report` | Load from allure-report instead of allure-results (matches UI counts) | `False` |
| `--out-dir PATH` | Output directory for analysis | `analysis_out` |
| `--model NAME` | AI model to use (overrides env) | `gpt-4o-mini` |
| `--max-tests N` | Maximum failed tests to analyze (cost control) | `50` |
| `--debug` | Enable debug output | `False` |

### Examples

**1. Analyze all failures with default settings:**
```bash
python analyze_allure.py
```

**2. Analyze from report (exact UI match) with custom output:**
```bash
python analyze_allure.py --from-report --report-dir ./allure-report --out-dir ./ai_analysis_2024
```

**3. Limit analysis to first 10 tests (cost control):**
```bash
python analyze_allure.py --max-tests 10
```

**4. Use GPT-4 for higher accuracy:**
```bash
python analyze_allure.py --model gpt-4o
```

**5. Debug mode to see parsing details:**
```bash
python analyze_allure.py --debug
```

---

## 📄 Output Reports

### 1. **Markdown Report** (`ai_allure_analysis.md`)

Human-friendly report with:
- Summary statistics
- Individual test analysis
- Original error messages
- AI classification and suggestions
- Confidence indicators

**Example:**
```markdown
## ❌ PCPX-564 - cp-dataplane details - delete developer hub capability

**Test ID:** `2aaeb76d2164e0b9`  
**Status:** `broken`

### 📋 Original Error
```
Error: Test timeout of 300000ms exceeded.

Stack Trace:
at Timeout._onTimeout (internal/timers.js:456:7)
...
```

### 🤖 AI Analysis
- **Classification:** `Network/Timeout Issue`
- **Confidence:** 🟢 `0.90`
- **Root Cause:** Test timeout of 300000ms exceeded.
- **Suggestion:** Investigate network connectivity and increase timeout threshold if necessary.
- **Rationale:** Clear timeout error indicates network or response time issue.
```

### 2. **JSON Report** (`ai_analysis.json`)

Machine-readable format for automation:
```json
[
  {
    "test": {
      "name": "Test name",
      "status": "failed",
      "statusMessage": "Error message",
      "testStage": {...}
    },
    "analysis": {
      "classification": "Application Bug",
      "confidence": 0.9,
      "root_cause": "AssertionError: Expected 200 but got 500",
      "suggestion": "Check API endpoint implementation",
      "rationale": "Clear HTTP status mismatch indicates server-side issue"
    }
  }
]
```

### Confidence Indicators

| Emoji | Range | Meaning |
|-------|-------|---------|
| 🟢 | 0.9-1.0 | Very High - Strong evidence, clear classification |
| 🟡 | 0.7-0.89 | High - Solid evidence, minor uncertainty |
| 🟠 | 0.5-0.69 | Medium - Moderate evidence |
| 🔴 | 0.3-0.49 | Low - Weak evidence |
| ⚫ | <0.3 | Very Low - Insufficient data, needs investigation |

---

## 📁 Project Structure

```
allure_ai_analyzer_complete/
├── analyze_allure.py          # Main entry point
├── requirements.txt           # Python dependencies
├── .env                       # Configuration (create from example.env)
├── README.md                  # This file
│
├── config/
│   └── example.env           # Example configuration
│
├── models/
│   └── ai_client.py          # OpenAI integration & prompt engineering
│
├── utils/
│   └── parser.py             # Allure results parser
│
├── report_generators/
│   └── md_report.py          # Markdown report generator
│
├── docs/
│   └── classification_criteria.md  # Detailed classification rules
│
├── allure-results/           # Your Allure test results (input)
├── allure-report/            # Generated Allure report (input option)
└── analysis_out/             # AI analysis output (generated)
    ├── ai_analysis.json      # Raw JSON output
    └── ai_allure_analysis.md # Human-readable report
```

---

## 🔬 How It Works

### Workflow

```
┌─────────────────────┐
│  Allure Results     │
│  (JSON files)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Parser             │
│  - Extract tests    │
│  - Read attachments │
│  - Deduplicate      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Filter Failures    │
│  (failed/broken/    │
│   skipped)          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  AI Analysis        │
│  - Extract errors   │
│  - Build context    │
│  - Classify         │
│  - Generate insights│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Report Generation  │
│  - Markdown         │
│  - JSON             │
└─────────────────────┘
```

### Parsing Logic

1. **From `allure-results/`:**
   - Scans all `*.json` files
   - Filters out containers and metadata
   - Extracts test results with status, steps, attachments
   - Deduplicates by `historyId` (keeps latest retry)

2. **From `allure-report/`:**
   - Reads `data/test-cases/*.json`
   - Matches Allure UI counts exactly
   - Resolves attachments from `allure-results/`
   - Deduplicates retries

### AI Analysis Process

1. **Extract Context:**
   - Error message from `statusMessage` or `statusDetails`
   - Stack trace from `statusTrace`
   - Failed step details
   - Attachment content (logs, stdout, stderr)

2. **Build Prompt:**
   - Classification criteria (7 categories)
   - Decision rules and examples
   - Anti-hallucination rules
   - Confidence scoring guidelines
   - Test context

3. **AI Processing:**
   - Sends to OpenAI API
   - Temperature: 0.2 (deterministic)
   - Max tokens: 700
   - JSON-only response

4. **Validation:**
   - Verify classification category
   - Clamp confidence to 0.0-1.0
   - Ensure all required fields
   - Fallback to "Unknown" if invalid

---

## 💰 Cost Considerations

### Token Usage

**Per test analysis:**
- Prompt: ~1,000-2,000 tokens (depending on error length)
- Response: ~200-400 tokens
- **Total per test: ~1,500 tokens average**

### Estimated Costs (GPT-4o-mini)

| Tests Analyzed | Input Tokens | Output Tokens | Est. Cost |
|----------------|--------------|---------------|-----------|
| 10 tests | 15,000 | 3,000 | ~$0.003 |
| 50 tests | 75,000 | 15,000 | ~$0.014 |
| 100 tests | 150,000 | 30,000 | ~$0.027 |

*Rates: $0.150 per 1M input tokens, $0.600 per 1M output tokens (GPT-4o-mini)*

### Cost Control Tips

1. **Use `--max-tests` flag:**
   ```bash
   python analyze_allure.py --max-tests 20
   ```

2. **Filter by status:**
   - Only failed/broken tests are analyzed
   - Passed tests are skipped automatically

3. **Use GPT-4o-mini (default):**
   - 80% cheaper than GPT-4
   - Sufficient for most analysis

4. **Batch processing:**
   - Analyze in batches during off-hours
   - Review results before analyzing more

---

## 🔒 Security & Privacy

### Data Sanitization

The tool automatically sanitizes sensitive data before sending to AI:

```python
# Redacted patterns:
- api_key=...
- Bearer tokens
- password=...
```

### What Gets Sent to OpenAI

✅ **Sent:**
- Test names and status
- Error messages and stack traces (sanitized)
- Test step names
- Log excerpts (truncated to 5000 chars)

❌ **NOT Sent:**
- Full attachment files (only text excerpts)
- Binary files (screenshots, videos)
- Your actual test code
- Environment-specific secrets (auto-redacted)

### Best Practices

1. **Review logs before analysis** for sensitive data
2. **Use environment variables** for credentials
3. **Don't commit `.env`** to version control
4. **Test with sanitized data first** in dev/staging
5. **Audit prompts** in `models/ai_client.py` if needed

---

## 🐛 Troubleshooting

### Issue: "No tests found"

**Cause:** Parser not finding test result files

**Solution:**
```bash
# Check if files exist
ls allure-results/*.json

# Try from-report mode
python analyze_allure.py --from-report --report-dir ./allure-report

# Enable debug
python analyze_allure.py --debug
```

---

### Issue: "16 tests classified as Unknown"

**Cause:** Missing error messages or attachment content

**Solution:**
1. Ensure `allure-results/` directory exists
2. Check attachments are readable:
   ```bash
   ls -la allure-results/*.txt allure-results/*.log
   ```
3. Use `--from-report` with `--results-dir`:
   ```bash
   python analyze_allure.py --from-report --report-dir ./allure-report --results-dir ./allure-results
   ```

---

### Issue: "OPENAI_API_KEY not set"

**Solution:**
1. Create `.env` file:
   ```bash
   cp config/example.env .env
   ```
2. Add your API key:
   ```env
   OPENAI_API_KEY=sk-proj-xxxxx
   ```

---

### Issue: "Test counts don't match Allure UI"

**Explanation:**
- `allure-results/` may have incomplete data (78 tests)
- `allure-report/` matches UI exactly (116 tests)

**Solution:**
```bash
# Use from-report mode
python analyze_allure.py --from-report --report-dir ./allure-report
```

---

### Issue: "Rate limit exceeded"

**Cause:** Too many API requests

**Solution:**
1. Reduce `--max-tests`:
   ```bash
   python analyze_allure.py --max-tests 10
   ```
2. Add delays between requests (modify `ai_client.py` if needed)
3. Upgrade OpenAI plan for higher limits

---

### Issue: "All tests have confidence 0.1"

**Cause:** AI not receiving proper error context

**Solution:**
1. Check if attachments are being read:
   ```bash
   python analyze_allure.py --debug
   ```
2. Verify `allure-results/` contains log files
3. Look at `ai_analysis.json` - check if test objects have `statusMessage`

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Add tests** if applicable
5. **Update documentation**
6. **Submit a pull request**

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Format code
black .
flake8 .
```

---

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Allure Framework** - For the excellent test reporting framework
- **OpenAI** - For GPT models powering the analysis
- **Community** - For feedback and contributions

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/allure-ai-analyzer/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/allure-ai-analyzer/discussions)
- **Email:** your.email@example.com

---

## 🗺️ Roadmap

- [ ] Support for other AI providers (Azure OpenAI, Anthropic, etc.)
- [ ] Web UI for interactive analysis
- [ ] Historical trend analysis
- [ ] Integration with CI/CD pipelines
- [ ] Custom classification rules
- [ ] Multi-language support
- [ ] Batch analysis optimization
- [ ] Cost tracking dashboard

---

*Happy Testing! 🚀*

---