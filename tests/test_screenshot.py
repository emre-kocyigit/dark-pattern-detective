from pathlib import Path
from agent.tools.screenshot import take_screenshot, Screenshot


def test_screenshot_returns_model():
    result = take_screenshot("https://example.com")
    assert isinstance(result, Screenshot)


def test_screenshot_success():
    result = take_screenshot("https://example.com")
    assert result.success is True
    assert result.path != ""
    assert result.width > 0
    assert result.height > 0


def test_screenshot_file_exists():
    result = take_screenshot("https://example.com")
    assert result.success is True
    assert Path(result.path).exists()


def test_screenshot_bad_url():
    result = take_screenshot("https://this-does-not-exist-xyz123.com")
    assert result.success is False
    assert result.error is not None