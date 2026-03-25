from playwright.sync_api import sync_playwright

from page import apply_filters, handle_popups


def main() -> None:
    url = "https://www.vestiairecollective.com/women-bags/"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")
        handle_popups(page)
        page.wait_for_timeout(7000)

        print("title:", page.title())
        print("womenbags_links:", page.locator("a[href*='/women-bags/']").count())
        print(
            "filtered status:",
            apply_filters(page, designer="Balenciaga", condition="Very good condition"),
        )
        page.wait_for_timeout(2000)
        print("after filters title:", page.title())
        print("womenbags_links_after:", page.locator("a[href*='/women-bags/']").count())
        print("items_links_after:", page.locator("a[href*='/items/']").count())
        print("product_links_after:", page.locator("a[href*='/products/']").count())
        print("any_links:", page.locator("a").count())
        print("imgs:", page.locator("img").count())

        page.screenshot(path="debug.png", full_page=True)
        print("saved debug.png")
        browser.close()


if __name__ == "__main__":
    main()

