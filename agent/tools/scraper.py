import logging
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from pydantic import BaseModel
from config.loader import load_settings

logger = logging.getLogger(__name__)


class FormField(BaseModel):
    name: str
    field_type: str
    preselected: bool


class Form(BaseModel):
    action: str
    method: str
    fields: list[FormField]
    has_preselected: bool


class ScrapedPage(BaseModel):
    # identity
    url: str
    title: str
    meta_description: str

    # content
    visible_text: str
    html: str

    # structure
    forms: list[Form]
    links: list[str]
    buttons: list[str]
    prices: list[str]

    # structural red flags (observable facts, no interpretation)
    preselected_checkboxes: list[dict]
    hidden_inputs: list[dict]
    popup_detected: bool
    sticky_elements: list[str]
    small_print: list[str]

    # metadata
    scrape_success: bool
    scrape_error: str | None = None


def _extract_forms(soup: BeautifulSoup) -> list[Form]:
    forms = []
    for form in soup.find_all("form"):
        fields = []
        for inp in form.find_all("input"):
            fields.append(FormField(
                name=inp.get("name", ""),
                field_type=inp.get("type", "text"),
                preselected=inp.get("checked") is not None
            ))
        forms.append(Form(
            action=form.get("action", ""),
            method=form.get("method", "get"),
            fields=fields,
            has_preselected=any(f.preselected for f in fields)
        ))
    return forms


def _extract_prices(soup: BeautifulSoup) -> list[str]:
    pattern = re.compile(r'[\$\€\£₺]\s?\d+[\.,]?\d*|\d+[\.,]\d+\s?(?:USD|EUR|GBP|TRY)')
    return list(set(pattern.findall(soup.get_text(separator=" "))))[:20]


def _extract_sticky_elements(soup: BeautifulSoup) -> list[str]:
    sticky = []
    for tag in soup.find_all(True, style=True):
        style = tag.get("style", "").lower().replace(" ", "")
        if "position:fixed" in style or "position:sticky" in style:
            text = tag.get_text(strip=True)[:100]
            if text:
                sticky.append(text)
    return list(set(sticky))[:5]


def _extract_small_print(soup: BeautifulSoup) -> list[str]:
    small = []
    for tag in soup.find_all(["small", "sup", "sub"]):
        text = tag.get_text(strip=True)
        if len(text) > 10:
            small.append(text[:200])
    for tag in soup.find_all(True, style=True):
        match = re.search(r'font-size:\s*(\d+)px', tag.get("style", "").lower())
        if match and int(match.group(1)) <= 11:
            text = tag.get_text(strip=True)
            if len(text) > 10:
                small.append(text[:200])
    return list(set(small))[:10]


def _empty_page(url: str, error: str) -> ScrapedPage:
    return ScrapedPage(
        url=url, title="", meta_description="",
        visible_text="", html="",
        forms=[], links=[], buttons=[], prices=[],
        preselected_checkboxes=[], hidden_inputs=[],
        popup_detected=False, sticky_elements=[], small_print=[],
        scrape_success=False, scrape_error=error
    )


def scrape(url: str) -> ScrapedPage:
    settings = load_settings()
    timeout = settings["scraper"]["timeout"]

    logger.info(f"Scraping {url}")

    # — fetch —
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                page.goto(url, wait_until="networkidle", timeout=timeout)
            except PlaywrightTimeout:
                logger.warning("networkidle timeout, retrying with domcontentloaded")
                page.goto(url, wait_until="domcontentloaded", timeout=timeout)

            html = page.content()
            popup_detected = page.locator(
                "[class*='modal'],[class*='overlay'],[class*='popup'],[id*='modal']"
            ).count() > 0

            browser.close()

    except PlaywrightTimeout:
        logger.error(f"Timeout loading {url}")
        return _empty_page(url, f"Timeout after {timeout/1000}s")
    except Exception as e:
        logger.error(f"Failed to load {url}: {e}")
        return _empty_page(url, str(e))

    # — parse —
    try:
        settings_scraper = settings["scraper"]
        soup = BeautifulSoup(html, "html.parser")

        meta_tag = soup.find("meta", attrs={"name": "description"})
        meta_description = meta_tag["content"] if meta_tag else ""

        # extract title and meta BEFORE removing head
        title = soup.title.string.strip() if soup.title else ""

        for tag in soup(["script", "style", "meta", "head"]):
            tag.decompose()

        visible_text = soup.get_text(separator=" ", strip=True)
        visible_text = visible_text[:settings_scraper["max_visible_text"]]

        buttons = [
            b.get_text(strip=True)
            for b in soup.find_all("button")
            if b.get_text(strip=True)
        ][:settings_scraper["max_buttons"]]

        links = [
            a.get("href", "")
            for a in soup.find_all("a", href=True)
        ][:settings_scraper["max_links"]]

        forms = _extract_forms(soup)

        preselected = [
            {"name": f.name, "type": f.field_type}
            for form in forms
            for f in form.fields
            if f.preselected
        ]

        hidden_inputs = [
            {"name": f.name}
            for form in forms
            for f in form.fields
            if f.field_type == "hidden"
        ]

        logger.info(
            f"Scraped — title: {title!r} |  "
            f"forms: {len(forms)} | buttons: {len(buttons)} | "
            f"popup: {popup_detected}"
        )

        return ScrapedPage(
            url=url,
            title=title,
            meta_description=str(meta_description)[:300],
            visible_text=visible_text,
            html=html[:5000],
            forms=forms,
            links=links,
            buttons=buttons,
            prices=_extract_prices(soup),
            preselected_checkboxes=preselected,
            hidden_inputs=hidden_inputs,
            popup_detected=popup_detected,
            sticky_elements=_extract_sticky_elements(soup),
            small_print=_extract_small_print(soup),
            scrape_success=True,
            scrape_error=None
        )

    except Exception as e:
        logger.error(f"Parsing failed for {url}: {e}")
        return _empty_page(url, f"Parsing error: {e}")