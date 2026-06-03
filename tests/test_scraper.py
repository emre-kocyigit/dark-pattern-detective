from agent.tools.scraper import scrape, ScrapedPage


def test_scrape_returns_model():
    result = scrape("https://example.com")
    assert isinstance(result, ScrapedPage)
    assert result.scrape_success is True
    assert result.url == "https://example.com"


def test_scrape_has_content():
    result = scrape("https://example.com")
    assert result.title != ""
    assert result.visible_text != ""


def test_scrape_bad_url_returns_error():
    result = scrape("https://this-url-does-not-exist-xyz123.com")
    assert result.scrape_success is False
    assert result.scrape_error is not None


def test_scrape_structural_fields_present():
    result = scrape("https://example.com")
    assert isinstance(result.forms, list)
    assert isinstance(result.buttons, list)
    assert isinstance(result.prices, list)
    assert isinstance(result.preselected_checkboxes, list)
    assert isinstance(result.sticky_elements, list)
    assert isinstance(result.small_print, list)
    assert isinstance(result.popup_detected, bool)