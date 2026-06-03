import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from pydantic import BaseModel
from config.loader import load_settings

logger = logging.getLogger(__name__)


class NavigationResult(BaseModel):
    url_before: str
    url_after: str
    action: str
    action_target: str
    html_after: str
    visible_text_after: str
    success: bool
    error: str | None = None


def _empty_result(
    url: str,
    action: str,
    target: str,
    error: str
) -> NavigationResult:
    return NavigationResult(
        url_before=url, url_after=url,
        action=action, action_target=target,
        html_after="", visible_text_after="",
        success=False, error=error
    )


def _get_content(page) -> tuple[str, str]:
    html = page.content()
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "meta", "head"]):
        tag.decompose()
    visible_text = soup.get_text(separator=" ", strip=True)[:6000]
    return html[:5000], visible_text


def navigate(
    url: str,
    action: str,
    target: str,
) -> NavigationResult:
    """
    Performs an action on a webpage and returns the result.

    Args:
        url: page to load
        action: one of "click" | "scroll" | "hover" | "goto"
        target: CSS selector, button text, or URL (for goto)
    """
    settings = load_settings()
    timeout = settings["scraper"]["timeout"]

    logger.info(f"Navigating {url} — action: {action} | target: {target!r}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})

            try:
                page.goto(url, wait_until="networkidle", timeout=timeout)
            except PlaywrightTimeout:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout)

            url_before = page.url

            # — perform action —
            if action == "goto":
                try:
                    page.goto(target, wait_until="networkidle", timeout=timeout)
                except PlaywrightTimeout:
                    page.goto(target, wait_until="domcontentloaded", timeout=timeout)

            elif action == "click":
                # try CSS selector first, then button text
                try:
                    page.click(target, timeout=5000)
                except Exception:
                    try:
                        page.get_by_text(target).first.click(timeout=5000)
                    except Exception as e:
                        browser.close()
                        return _empty_result(url, action, target, f"Click failed: {e}")

                page.wait_for_load_state("networkidle", timeout=10000)

            elif action == "scroll":
                # target is a pixel value as string e.g. "1000"
                try:
                    pixels = int(target)
                except ValueError:
                    pixels = 1000
                page.evaluate(f"window.scrollBy(0, {pixels})")
                page.wait_for_timeout(1000)

            elif action == "hover":
                try:
                    page.hover(target, timeout=5000)
                except Exception as e:
                    browser.close()
                    return _empty_result(url, action, target, f"Hover failed: {e}")
                page.wait_for_timeout(1000)

            else:
                browser.close()
                return _empty_result(
                    url, action, target,
                    f"Unknown action: {action}. Use: click | scroll | hover | goto"
                )

            url_after = page.url
            html_after, visible_text_after = _get_content(page)
            browser.close()

        logger.info(f"Navigation done — landed on {url_after}")

        return NavigationResult(
            url_before=url_before,
            url_after=url_after,
            action=action,
            action_target=target,
            html_after=html_after,
            visible_text_after=visible_text_after,
            success=True,
            error=None
        )

    except PlaywrightTimeout:
        logger.error(f"Timeout during navigation of {url}")
        return _empty_result(url, action, target, f"Timeout after {timeout/1000}s")
    except Exception as e:
        logger.error(f"Navigation failed: {e}")
        return _empty_result(url, action, target, str(e))