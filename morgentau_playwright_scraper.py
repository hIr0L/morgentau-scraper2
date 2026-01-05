import asyncio
from playwright.async_api import async_playwright

from google_sheet_helper import append_summary_row, append_location_rows

URL = "https://reservierung.platzhalter.cc/Morgentau/faces/index.xhtml"

LOCATION_SELECT_SELECTOR = "select#j_idt24\\:selectLocationCombobox"

LOCATION_OPTIONS = [
    ("Linz: Bindermichl - Nähe Sportpark Lissfeld", "801"),
    ("Linz: Freinberg – Jägermayr – Freinbergstraße", "804"),
    ("Linz: Froschberg – Sternwartweg", "803"),
    ("Linz: Solar City – Neufelderstraße", "808"),
    ("Linz: Dornach", "822"),
    ("Leonding: Georg-Erber-Straße", "807"),
    ("Graz: Andritz – St. Veiterstraße", "816"),
    ("Graz: Mariatrost – Tannhofweg", "817"),
]

BOOKED_SELECTOR = "rect.reservationMapItem"
FREE_SELECTOR = "rect.emptyLotMapItem"


async def select_location_js(page, value: str) -> bool:
    """
    Set select value via JSF-safe JS (avoid Playwright select_option which can be flaky with JSF).
    Returns True/False for success.
    """
    return await page.evaluate(
        """
        ({ sel, val }) => {
            const el = document.querySelector(sel);
            if (!el) return false;
            el.value = val;
            el.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
        }
        """,
        {"sel": LOCATION_SELECT_SELECTOR, "val": value},
    )


async def _find_map_frame(page):
    # JSF often renders map in an iframe with /faces/map/ in URL
    for f in page.frames:
        if f.url and "/faces/map/" in f.url:
            return f
    return None


async def scrape_location(page, label: str, value: str) -> dict:
    print(f"\n--- {label} ({value}) ---")

    await page.wait_for_selector(LOCATION_SELECT_SELECTOR, timeout=60000)

    success = await select_location_js(page, value)
    if not success:
        print(f"SKIP: select element missing for {label}")
        return {"name": label, "total_fields": 0, "booked_fields": 0, "free_fields": 0}

    # give JSF time to update iframe/map after location change
    await page.wait_for_timeout(2500)

    map_frame = await _find_map_frame(page)
    if not map_frame:
        # sometimes frame appears a bit later
        await page.wait_for_timeout(2500)
        map_frame = await _find_map_frame(page)

    if not map_frame:
        print(f"SKIP: map frame not found for {label}")
        return {"name": label, "total_fields": 0, "booked_fields": 0, "free_fields": 0}

    # Wait for at least one of the SVG rect types to exist (or time out)
    # If neither exists, counts will be 0.
    try:
        await map_frame.wait_for_selector(
            f"{BOOKED_SELECTOR}, {FREE_SELECTOR}",
            timeout=30000
        )
    except Exception:
        pass

    booked = await map_frame.locator(BOOKED_SELECTOR).count()
    free = await map_frame.locator(FREE_SELECTOR).count()
    total = booked + free

    print(f"Total: {total} | Booked: {booked} | Free: {free}")

    return {
        "name": label,
        "total_fields": total,
        "booked_fields": booked,
        "free_fields": free,
    }


async def main():
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"Opening: {URL}")
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        # Ensure the location select exists
        await page.wait_for_selector(LOCATION_SELECT_SELECTOR, timeout=60000)

        for label, value in LOCATION_OPTIONS:
            try:
                res = await scrape_location(page, label, value)
            except Exception as e:
                print(f"ERROR scraping {label}: {repr(e)}")
                res = {"name": label, "total_fields": 0, "booked_fields": 0, "free_fields": 0}
            results.append(res)

        await browser.close()

    summary = {
        "total_fields": sum(r["total_fields"] for r in results),
        "total_booked": sum(r["booked_fields"] for r in results),
        "total_free": sum(r["free_fields"] for r in results),
    }

    print("\n=== SUMMARY ===")
    print(summary)

    # Write to Google Sheets (fail loudly if it doesn't work)
    try:
        append_summary_row(summary)
        append_location_rows(results)
        print("✅ Google Sheets write successful")
    except Exception as e:
        print("❌ Google Sheets write failed:", repr(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())
