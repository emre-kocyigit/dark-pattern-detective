from agent.tools.navigator import navigate, NavigationResult


def test_navigate_returns_model():
    result = navigate("https://example.com", action="scroll", target="500")
    assert isinstance(result, NavigationResult)


def test_navigate_scroll():
    result = navigate("https://example.com", action="scroll", target="500")
    assert result.success is True
    assert result.visible_text_after != ""


def test_navigate_goto():
    result = navigate(
        "https://example.com",
        action="goto",
        target="https://example.com"
    )
    assert result.success is True
    assert result.url_after == "https://example.com/"


def test_navigate_click_by_text():
    result = navigate(
        "https://example.com",
        action="click",
        target="a[href]"  # click first link by CSS selector
    )
    assert result.success is True
    assert result.url_after != "https://example.com/"


def test_navigate_bad_action():
    result = navigate("https://example.com", action="fly", target="moon")
    assert result.success is False
    assert result.error is not None


def test_navigate_bad_url():
    result = navigate(
        "https://this-does-not-exist-xyz123.com",
        action="scroll",
        target="500"
    )
    assert result.success is False
    assert result.error is not None