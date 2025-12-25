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


async def select_location_js(page, value):
    """Set select value via JSF-safe JS (no Playwright select_option)."""
    await page.evaluate(
        """
        (sel, val) => {
            const el = document.querySelector(sel);
            if (!el) return false;
            el.value = val;
            el.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
        }
        """,
        LOCATION_SELECT_SELECTOR,
        value,
    )


async def scrape_location(page, label, value):
    print(f"\n--- {label} ({value}) ---")

    await page.wait_for_selector(LOCATION_SELECT_SELECTOR, timeout=60000)

    # JS-based select (robust)
    success = await select_location_js(page, value)
    if not success:
        print(f"SKIP: select element missing for {label}")
        return {"name": label, "total_fields": 0, "booked_fields": 0, "free_fields": 0}

    await page.wait_for_timeout(2000)

    map_frame = None
    for f in page.frames:
        if "/faces/map/" in f.url:
            map_frame = f
            break

    if not map_frame:
        print(f"ERROR: No map iframe for {label}")
        return {"name": label, "total_fields": 0, "booked_fields": 0, "free_fields": 0}

    await map_frame.wait_for_selector("svg rect", timeout=10000)

    booked = await map_frame.locator(BOOKED_SELECTOR).count()
    free = await map_frame.locator(FREE_SELECTOR).count()

    print(f"DEBUG {label}: booked={booked}, free={free}")

    return {
        "name": label,
        "total_fields": booked + free,
        "booked_fields": booked,
        "free_fields": free,
    }


async def scrape_all_locations():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        results = []

        for label, value in LOCATION_OPTIONS:
            page = await browser.new_page()
            await page.goto(URL, wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")

            stats = await scrape_location(page, label, value)
            results.append(stats)

            await page.close()

        await browser.close()

        summary = {
            "total_fields": sum(r["total_fields"] for r in results),
            "total_booked": sum(r["booked_fields"] for r in results),
            "total_free": sum(r["free_fields"] for r in results),
        }

        return summary, results


def main():
    summary, locations = asyncio.run(scrape_all_locations())
    print("Summary:", summary)
    append_summary_row(summary)
    append_location_rows(locations)


if __name__ == "__main__":
    main()
