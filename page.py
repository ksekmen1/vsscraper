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
                    return
            except Exception:
                continue


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

    return status


def _extract_price(text: str) -> str:
    match = re.search(r"(?:EUR|€|\\$|£)\\s?\\d[\\d,\\. ]*", text)
    return match.group(0).strip() if match else ""


def _first_non_empty(*values: Optional[str]) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return ""


def collect_items_from_current_page(page: Page, seen_urls: Set[str], per_page_item_limit: int) -> List[Dict[str, str]]:
    cards = page.locator("a[href*='/women-bags/']")
    count = cards.count()
    items: List[Dict[str, str]] = []

    for idx in range(min(count, per_page_item_limit)):
        try:
            card = cards.nth(idx)
            href = card.get_attribute("href")
            if not href:
                continue
            url = href if href.startswith("http") else f"{BASE_URL}{href}"
            if url in seen_urls:
                continue

            image = card.locator("img").first
            image_url = _first_non_empty(
                image.get_attribute("src"),
                image.get_attribute("data-src"),
                image.get_attribute("srcset"),
            )
            if "," in image_url:
                image_url = image_url.split(",")[0].split(" ")[0].strip()
            if image_url.startswith("//"):
                image_url = f"https:{image_url}"
            if image_url.startswith("/"):
                image_url = f"{BASE_URL}{image_url}"

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
    per_page_item_limit: int = 200,
    headless: bool = False,
) -> List[Dict[str, str]]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()
        results: List[Dict[str, str]] = []
        seen_urls: Set[str] = set()

        for page_num in range(1, max_pages + 1):
            page_url = URL if page_num == 1 else f"{URL}?page={page_num}"
            print(f"Opening {page_url}")
            page.goto(page_url, wait_until="domcontentloaded")
            wait_and_accept_cookies(page)

            if "Just a moment" in page.title():
                print("Bot check detected. Solve it in browser and press Enter in terminal.")
                input()
                wait_and_accept_cookies(page)

            status = apply_filters(page, designer=designer, condition=condition)
            print(f"Filters applied: {status}")

            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)
            scroll_to_load_more(page, rounds=scroll_rounds)
            results.extend(collect_items_from_current_page(page, seen_urls, per_page_item_limit))
            print(f"Collected {len(results)} items total")

        browser.close()
        return results


def save_to_csv(items: List[Dict[str, str]], output_path: str = "items.csv") -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["title", "price", "url", "image_url"])
        writer.writeheader()
        writer.writerows(items)


if __name__ == "__main__":
    scraped = scrape(designer="Balenciaga", condition="Very good condition", max_pages=3, headless=False)
    save_to_csv(scraped)
    print(f"Saved {len(scraped)} listings to items.csv")