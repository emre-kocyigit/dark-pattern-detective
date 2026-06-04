from pathlib import Path
from llm.analyst import AnalysisReport, DarkPatternFinding
from report.formatter import print_report, _save_json


def _sample_report() -> AnalysisReport:
    return AnalysisReport(
        dark_patterns_found=[
            DarkPatternFinding(
                pattern="Countdown Timer",
                level="low",
                high_level_strategy="Social Engineering",
                severity="HIGH",
                evidence="Offer ends in 09:59",
                location="homepage",
                gdpr_risk=False,
                legal_reference="Consumer Protection",
                recommendation="Remove fake countdown or ensure it reflects real deadline"
            ),
            DarkPatternFinding(
                pattern="Bad Defaults",
                level="meso",
                high_level_strategy="Interface Interference",
                severity="HIGH",
                evidence="Newsletter pre-checked by default",
                location="registration form",
                gdpr_risk=True,
                legal_reference="GDPR",
                recommendation="Require explicit opt-in for marketing communications"
            )
        ],
        overall_risk="HIGH",
        overall_summary="Two high-severity dark patterns detected including a fake countdown timer and GDPR-violating pre-checked newsletter consent.",
        gdpr_concerns=True,
        pattern_count=2,
        language_detected="en",
        ontology_reference="Gray, Santos, Bielova & Mildner (2024). CHI 2024.",
        analysis_success=True
    )


def test_print_report_terminal():
    report = _sample_report()
    result = print_report(report, "https://example.com", output="terminal")
    assert result is None


def test_print_report_json():
    report = _sample_report()
    path = print_report(report, "https://example.com", output="json")
    assert path is not None
    assert Path(path).exists()


def test_print_report_both():
    report = _sample_report()
    path = print_report(report, "https://example.com", output="both")
    assert path is not None
    assert Path(path).exists()


def test_save_json_structure():
    report = _sample_report()
    path = _save_json(report, "https://example.com")
    import json
    with open(path) as f:
        data = json.load(f)
    assert "overall_risk" in data
    assert "dark_patterns_found" in data
    assert len(data["dark_patterns_found"]) == 2
    assert data["dark_patterns_found"][0]["pattern"] == "Countdown Timer"


def test_clean_report():
    report = AnalysisReport(
        dark_patterns_found=[],
        overall_risk="CLEAN",
        overall_summary="No dark patterns detected.",
        gdpr_concerns=False,
        pattern_count=0,
        language_detected="en",
        ontology_reference="Gray, Santos, Bielova & Mildner (2024). CHI 2024.",
        analysis_success=True
    )
    result = print_report(report, "https://example.com", output="terminal")
    assert result is None