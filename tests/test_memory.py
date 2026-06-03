from agent.tools.memory import Memory
from agent.tools.scraper import scrape
from agent.tools.extractor import extract
from agent.tools.screenshot import take_screenshot
from agent.tools.navigator import navigate


def test_memory_initializes():
    mem = Memory("https://example.com")
    assert mem.state.url == "https://example.com"
    assert mem.state.step_count == 0
    assert mem.state.findings == []


def test_memory_add_scrape():
    mem = Memory("https://example.com")
    result = scrape("https://example.com")
    mem.add_scrape(result)
    assert mem.state.step_count == 1
    assert len(mem.state.findings) == 1
    assert mem.state.findings[0].tool == "scraper"


def test_memory_add_extraction():
    mem = Memory("https://example.com")
    result = extract("Only 2 left! Free trial, auto-renews. Accept all cookies.")
    mem.add_extraction(result)
    assert mem.state.step_count == 1
    assert mem.state.findings[0].tool == "extractor"


def test_memory_add_screenshot():
    mem = Memory("https://example.com")
    result = take_screenshot("https://example.com")
    mem.add_screenshot(result)
    assert len(mem.state.screenshots) == 1
    assert mem.state.step_count == 1


def test_memory_accumulates_signals():
    mem = Memory("https://example.com")
    mem.add_extraction(extract(
        "Only 2 left! Free trial auto-renews. Accept all cookies."
    ))
    assert len(mem.state.all_urgency_texts) > 0 or \
           len(mem.state.all_subscription_keywords) > 0


def test_memory_get_summary():
    mem = Memory("https://example.com")
    mem.add_scrape(scrape("https://example.com"))
    summary = mem.get_summary()
    assert "https://example.com" in summary
    assert "scraper" in summary.lower()


def test_memory_has_enough_evidence():
    mem = Memory("https://example.com")
    mem.add_scrape(scrape("https://example.com"))
    mem.add_screenshot(take_screenshot("https://example.com"))
    mem.add_extraction(extract("Only 2 left! Accept all."))
    assert mem.has_enough_evidence() is True