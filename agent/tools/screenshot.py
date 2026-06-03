import logging
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from pydantic import BaseModel
from config.loader import load_settings

logger = logging.getLogger(__name__)


class Screenshot(BaseModel):
    url: str
    path: str
    width: int
    height: int
    timestamp: str
    success: bool
    error: str | None = None


def _output_dir() -> Path:
    path = Path("output/screenshots")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _filename(url: str) -> str:
    clean = url.replace("https://", "").replace("http://", "")
    clean = "".join(c if c.isalnum() else "_" for c in clean)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{clean[:50]}_{timestamp}.png"


def take_screenshot(url: str, full_page: bool = True) -> Screenshot:
    settings = load_settings()
    timeout = settings["scraper"]["timeout"]
    timestamp = datetime.now().isoformat()
    output_path = _output_dir() / _filename(url)

    logger.info(f"Taking screenshot of {url}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})

            try:
                page.goto(url, wait_until="networkidle", timeout=timeout)
            except PlaywrightTimeout:
                logger.warning("networkidle timeout, retrying with domcontentloaded")
                page.goto(url, wait_until="domcontentloaded", timeout=timeout)

            # wait for page to settle visually
            page.wait_for_timeout(2000)

            page.screenshot(path=str(output_path), full_page=full_page)

            # get actual page dimensions
            dimensions = page.evaluate("""() => ({
                width: document.documentElement.scrollWidth,
                height: document.documentElement.scrollHeight
            })""")

            browser.close()

        logger.info(f"Screenshot saved to {output_path}")

        return Screenshot(
            url=url,
            path=str(output_path),
            width=dimensions["width"],
            height=dimensions["height"],
            timestamp=timestamp,
            success=True
        )

    except PlaywrightTimeout:
        logger.error(f"Timeout taking screenshot of {url}")
        return Screenshot(
            url=url, path="", width=0, height=0,
            timestamp=timestamp, success=False,
            error=f"Timeout after {timeout/1000}s"
        )
    except Exception as e:
        logger.error(f"Screenshot failed for {url}: {e}")
        return Screenshot(
            url=url, path="", width=0, height=0,
            timestamp=timestamp, success=False,
            error=str(e)
        )