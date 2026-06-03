from agent.orchestrator import investigate, OrchestratorResult


def test_investigate_returns_model():
    result = investigate("https://example.com")
    assert isinstance(result, OrchestratorResult)


def test_investigate_success():
    result = investigate("https://example.com")
    assert result.success is True
    assert result.step_count > 0


def test_investigate_has_summary():
    result = investigate("https://example.com")
    assert result.memory_summary != ""
    assert "https://example.com" in result.memory_summary


def test_investigate_has_screenshots():
    result = investigate("https://example.com")
    assert len(result.screenshots) > 0


def test_investigate_bad_url():
    result = investigate("https://this-does-not-exist-xyz123.com")
    assert isinstance(result, OrchestratorResult)
    assert result.step_count > 0