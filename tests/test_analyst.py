from llm.analyst import analyze, AnalysisReport

SAMPLE_SUMMARY = """
Investigation of: https://example-shop.com
Steps taken: 5
Pages visited: ['https://example-shop.com', 'https://example-shop.com/checkout']

=== Accumulated signals ===
Urgency texts: ['Only 2 left!', 'Offer ends in 10 minutes']
Subscription keywords: ['auto-renews monthly', 'free trial']
Prices found: ['$9.99', '$99.99']
Preselected checkboxes: [{'name': 'newsletter', 'type': 'checkbox'}]
Consent accept buttons: ['Accept all']
Consent reject buttons: []
Reject button missing: True
Popup detected: True
Dark pattern hints: ['You must register to continue']
"""


def test_analyze_returns_model():
    result = analyze(SAMPLE_SUMMARY, [])
    assert isinstance(result, AnalysisReport)


def test_analyze_has_summary():
    result = analyze(SAMPLE_SUMMARY, [])
    assert result.overall_summary != ""


def test_analyze_risk_level_valid():
    result = analyze(SAMPLE_SUMMARY, [])
    assert result.overall_risk in ["HIGH", "MEDIUM", "LOW", "CLEAN", "UNKNOWN"]


def test_analyze_findings_structure():
    result = analyze(SAMPLE_SUMMARY, [])
    if result.analysis_success and result.dark_patterns_found:
        finding = result.dark_patterns_found[0]
        assert finding.pattern != ""
        assert finding.level in ["low", "meso"]
        assert finding.severity in ["HIGH", "MEDIUM", "LOW"]


def test_analyze_empty_evidence():
    result = analyze("No signals found.", [])
    assert isinstance(result, AnalysisReport)
    assert result.overall_risk in ["CLEAN", "LOW", "MEDIUM", "HIGH", "UNKNOWN"]


def test_analyze_success_flag():
    result = analyze(SAMPLE_SUMMARY, [])
    assert isinstance(result.analysis_success, bool)