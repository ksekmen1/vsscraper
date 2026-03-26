import csv
import re
from typing import Dict, List, Optional, Set

from playwright.sync_api import Page, sync_playwright

BASE_URL = "https://www.vestiairecollective.com"
CATEGORY_PATH = "/women-bags/"
URL = f"{BASE_URL}{CATEGORY_PATH}"


def accept_cookies_if_present(page: Page) -> None:
    selector_candidates = [
        "#onetrust-accept-btn-handler",
        "button#onetrust-accept-btn-handler",
        "button[data-testid*='accept']",
        "button[id*='accept']",
        "button[class*='accept']",
        "[aria-label*='accept' i]",
    ]
    text_candidates = [
        "Accept all",
        "Accept All",
        "Accept",
        "I agree",
        "Allow all",
        "Agree",
        "Accept cookies",
    ]

    for frame in page.frames:
        for selector in selector_candidates:
            try:
                loc = frame.locator(selector).first
                if loc.count() > 0 and loc.is_visible():
                    loc.click(timeout=2500, force=True)
                    page.wait_for_timeout(800)
                    return
            except Exception:
                continue

        for text in text_candidates:
            try:
                by_role = frame.get_by_role("button", name=text, exact=True).first
                if by_role.count() > 0 and by_role.is_visible():
                    by_role.click(timeout=2500, force=True)
                    page.wait_for_timeout(800)
                    print(f"Cookie accepted via button text: {text}", flush=True)
                    return
            except Exception:
                continue

        # Fallback: some consent UIs don't expose a good accessible name.
        # Click the first visible button whose text is exactly "Accept" or "Accept all".
        try:
            buttons = frame.locator("button")
            for i in range(min(buttons.count(), 30)):
                b = buttons.nth(i)
                if not b.is_visible():
                    continue
                try:
                    label = (b.inner_text() or "").strip()
                except Exception:
                    continue
                if label in ("Accept", "Accept all", "Accept All"):
                    b.click(timeout=2500, force=True)
                    page.wait_for_timeout(800)
                    print(f"Cookie accepted via fallback button scan: {label}", flush=True)
                    return
        except Exception:
            pass

        # Fallback: sometimes it's rendered as a non-button element.
        try:
            accept_text = frame.get_by_text("Accept", exact=True).first
            if accept_text.count() > 0 and accept_text.is_visible():
                accept_text.click(timeout=2500, force=True)
                page.wait_for_timeout(800)
                print("Cookie accepted via fallback text click: Accept", flush=True)
                return
        except Exception:
            pass


def _click_button_text_any_frame(page: Page, button_texts: List[str]) -> bool:
    for frame in page.frames:
        for text in button_texts:
            try:
                btn = frame.get_by_role("button", name=text, exact=True).first
                if btn.count() > 0 and btn.is_visible():
                    btn.click(timeout=2500, force=True)
                    page.wait_for_timeout(800)
                    return True
            except Exception:
                continue
    return False


def handle_country_modal_if_present(page: Page) -> None:
    # Vestiaire sometimes shows a "country you are shopping from" modal.
    continue_texts = [
        "Continue",
        "Continue shopping",
        "Continue to site",
    ]
    _click_button_text_any_frame(page, continue_texts)


def handle_popups(page: Page) -> None:
    # Order matters: country modal first, cookies after (often delayed).
    for delay_ms in (0, 1500, 3500, 6000):
        if delay_ms:
            page.wait_for_timeout(delay_ms)
        handle_country_modal_if_present(page)
        accept_cookies_if_present(page)


def wait_and_accept_cookies(page: Page) -> None:
    for delay_ms in (0, 2000, 5000):
        if delay_ms:
            page.wait_for_timeout(delay_ms)
        accept_cookies_if_present(page)


def _click_filter_button(page: Page, filter_name: str) -> bool:
    for candidate in (filter_name, f"{filter_name}s"):
        try:
            btn = page.get_by_role("button", name=candidate, exact=False).first
            if btn.count() > 0 and btn.is_visible():
                btn.click(timeout=3000)
                page.wait_for_timeout(600)
                return True
        except Exception:
            pass
        try:
            fallback = page.locator(f"text={candidate}").first
            if fallback.count() > 0 and fallback.is_visible():
                fallback.click(timeout=3000)
                page.wait_for_timeout(600)
                return True
        except Exception:
            pass
    return False


def _click_apply_if_present(page: Page) -> None:
    for apply_text in ("Apply", "Show results", "See results", "Done"):
        try:
            btn = page.get_by_role("button", name=apply_text, exact=False).first
            if btn.count() > 0 and btn.is_visible():
                btn.click(timeout=2500, force=True)
                page.wait_for_timeout(1000)
                return
        except Exception:
            continue


def _select_option(page: Page, option_text: str) -> bool:
    option_selectors = [
        f"label:has-text('{option_text}')",
        f"button:has-text('{option_text}')",
        f"[role='option']:has-text('{option_text}')",
        f"text={option_text}",
    ]
    for selector in option_selectors:
        try:
            loc = page.locator(selector).first
            if loc.count() == 0:
                continue
            try:
                loc.scroll_into_view_if_needed(timeout=2000)
            except Exception:
                pass
            if loc.is_visible():
                loc.click(timeout=3000, force=True)
                page.wait_for_timeout(600)
                return True
        except Exception:
            continue
    return False


def apply_filters(page: Page, designer: Optional[str], condition: Optional[str]) -> Dict[str, bool]:
    status = {"designer": False, "condition": False}

    if designer and _click_filter_button(page, "Designer"):
        try:
            search_candidates = [
                page.get_by_role("textbox", name="Search", exact=False).first,
                page.get_by_placeholder("Search", exact=False).first,
                page.locator("input[type='search']").first,
                page.locator("input[placeholder*='Search' i]").first,
            ]
            for search_box in search_candidates:
                if search_box.count() > 0 and search_box.is_visible():
                    search_box.fill(designer)
                    search_box.press("Enter")
                    page.wait_for_timeout(700)
                    break
        except Exception:
            pass
        status["designer"] = _select_option(page, designer)
        _click_apply_if_present(page)

    if condition and _click_filter_button(page, "Condition"):
        status["condition"] = _select_option(page, condition)
        _click_apply_if_present(page)

    # Close any open filter panel/drawer that might block scrolling.
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
    except Exception:
        pass

    return status


def _extract_price(text: str) -> str:
    t = (text or "").replace("\n", " ")

    # Pattern A: currency before number (e.g. "€ 120", "USD 120")
    m = re.search(
        r"(?:(?:EUR|USD|GBP|DKK|SEK|NOK|CHF|PLN)|[€$£])\s*\d[\d.,\u00A0 ]*",
        t,
    )
    if m:
        return m.group(0).strip()

    # Pattern B: number before currency (e.g. "1.284 DKK")
    m = re.search(
        r"\d[\d.,\u00A0 ]*\s*(?:EUR|USD|GBP|DKK|SEK|NOK|CHF|PLN)",
        t,
    )
    return m.group(0).strip() if m else ""


def _first_non_empty(*values: Optional[str]) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return ""


def _normalize_image_url(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""

    # If it's a srcset string, take the first URL candidate.
    # Example: "https://... 300w, https://... 600w" -> "https://..."
    # Important: Vestiaire image URLs themselves contain commas, but srcset candidates
    # are separated by ", " (comma + space). Only split on that.
    first = v.split(", ")[0].strip() if ", " in v else v
    first = first.split()[0].strip()  # drop "1x", "300w", etc.

    if first.startswith("//"):
        first = f"https:{first}"
    if first.startswith("/"):
        first = f"{BASE_URL}{first}"
    return first


def collect_items_from_current_page(
    page: Page, seen_urls: Set[str], per_page_item_limit: int, debug_images: bool = False
) -> List[Dict[str, str]]:
    cards = page.locator("a[href*='/women-bags/']")
    count = cards.count()
    items: List[Dict[str, str]] = []

    for idx in range(min(count, per_page_item_limit)):
        if idx > 0 and idx % 25 == 0:
            print(f"Collecting items... {idx}/{min(count, per_page_item_limit)}", flush=True)
        try:
            card = cards.nth(idx)
            href = card.get_attribute("href")
            if not href:
                continue
            url = href if href.startswith("http") else f"{BASE_URL}{href}"
            if url in seen_urls:
                continue

            image = card.locator("img").first
            raw_src = image.get_attribute("src")
            raw_data_src = image.get_attribute("data-src")
            raw_srcset = image.get_attribute("srcset")
            raw_data_srcset = image.get_attribute("data-srcset")
            raw_image = _first_non_empty(raw_src, raw_data_src, raw_srcset, raw_data_srcset)
            image_url = _normalize_image_url(raw_image)
            if debug_images and idx < 5:
                print(
                    f"IMG[{idx}] src={raw_src} data-src={raw_data_src} srcset={raw_srcset} data-srcset={raw_data_srcset} -> {image_url}",
                    flush=True,
                )

            raw_text = card.inner_text().strip().replace("\\n", " ")
            title = raw_text[:220]
            price = _extract_price(raw_text)

            items.append(
                {
                    "title": title,
                    "price": price,
                    "url": url,
                    "image_url": image_url,
                }
            )
            seen_urls.add(url)
        except Exception:
            continue

    return items


def scroll_to_load_more(page: Page, rounds: int) -> None:
    for _ in range(rounds):
        page.mouse.wheel(0, 6000)
        page.wait_for_timeout(1000)


def scrape(
    designer: str = "",
    condition: str = "",
    max_pages: int = 3,
    scroll_rounds: int = 6,
    per_page_item_limit: int = 60,
    headless: bool = False,
    debug_images: bool = False,
) -> List[Dict[str, str]]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()
        page.set_default_timeout(15000)
        results: List[Dict[str, str]] = []
        seen_urls: Set[str] = set()

        for page_num in range(1, max_pages + 1):
            page_url = URL if page_num == 1 else f"{URL}?page={page_num}"
            print(f"Opening {page_url}", flush=True)
            page.goto(page_url, wait_until="domcontentloaded", timeout=45000)
            handle_popups(page)

            if "Just a moment" in page.title():
                print("Bot check detected. Solve it in browser and press Enter in terminal.", flush=True)
                input()
                handle_popups(page)

            status = apply_filters(page, designer=designer, condition=condition)
            print(f"Filters applied: {status}", flush=True)

            # Don't use networkidle here; Vestiaire often keeps requests open.
            try:
                page.wait_for_load_state("domcontentloaded", timeout=20000)
            except Exception:
                pass

            # Wait until some product links exist before scrolling/collecting.
            try:
                page.wait_for_selector("a[href*='/women-bags/']", timeout=20000)
            except Exception:
                print("Warning: product links not detected yet; continuing anyway.", flush=True)

            scroll_to_load_more(page, rounds=scroll_rounds)
            results.extend(
                collect_items_from_current_page(
                    page, seen_urls, per_page_item_limit, debug_images=debug_images
                )
            )
            print(f"Collected {len(results)} items total", flush=True)

        browser.close()
        return results


def save_to_csv(items: List[Dict[str, str]], output_path: str = "items.csv") -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as file:
        # Keep a stable schema for the MVP CSV export.
        # If new fields are added to the in-memory items (e.g. comps/suggestions),
        # ignore them instead of crashing the web request.
        writer = csv.DictWriter(
            file,
            fieldnames=["title", "price", "url", "image_url"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(items)


if __name__ == "__main__":
    scraped = scrape(designer="Balenciaga", condition="Very good condition", max_pages=3, headless=False)
    save_to_csv(scraped)
    print(f"Saved {len(scraped)} listings to items.csv")