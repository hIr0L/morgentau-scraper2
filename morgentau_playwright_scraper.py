import asyncio
import re

from playwright.async_api import async_playwright
from google_sheet_helper import append_summary_row, append_location_rows

# Booking URL
URL = "https://reservierung.platzhalter.cc/Morgentau/faces/index.xhtml"

# Location dropdown selector (JSF id needs escaping)
LOCATION_SELECT_SELECTOR = "select#j_idt24\\:selectLocationCombobox"

# Keep your curated list (since you removed the missing one)
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

# The map SVG uses these classes
BOOKED_SELECTOR = "rect.reservationMapItem"
FREE_SELECTOR = "rect.emptyLotMapItem"


async def scrape_location(page, location_label, location_value):
    """Select a location and count booked/free fields inside the map iframe."""

    print(f"\n--- Selecting: {location_label} ({location_value}) ---")

    # 1) Select location in dropdown (robust against JSF/select2 partial refresh)
    await page.wait_for_selector(LOCATION_SELECT_SELECTOR, state="visible", timeout=60000)

    for attempt in (1, 2):
        opt = page.locator(f"{LOCATION_SELECT_SELECTOR} option[value='{location_value}']")
        if await opt.count() > 0:
            await page.select_option(LOCATION_SELECT_SELECTOR, value=location_value)
            break

        if attempt == 1:
            print(
                f"WARNING: Option missing for {location_label} ({location_value}) "
                f"-> reloading page and retrying..."
            )
            await page.reload(wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_selector(LOCATION_SELECT_SELECTOR, state="visible", timeout=60000)
        else:
            print(f"SKIP: Option still missing for {location_label} ({location_value})")
            return {
                "name": location_label,
                "total_fields": 0,
                "booked_fields": 0,
                "free_fields": 0,
            }

    # 2) Wait a bit for the map iframe to reload
    await page.wait_for_timeout(2000)

    # 3) Find the map iframe (URL contains '/faces/map/')
    map_frame = None
    for f in page.frames:
        if "/faces/map/" in f.url:
            map_frame = f
            break

    if not map_frame:
        print(f"ERROR: No map iframe found for {location_label}")
        return {
            "name": location_label,
            "total_fields": 0,
            "booked_fields": 0,
            "free_fields": 0,
        }

    # 4) Wait until there is at least one <rect> in the SVG
    await map_frame.wait_for_selector("svg rect", timeout=10000)

    # 5) DEBUG: see what the frame contains
    svg_count = await map_frame.locator("svg").count()
    rect_count = await map_frame.locator("rect").count()
    empty_count = await map_frame.locator(FREE_SELECTOR).count()
    reserved_count = await map_frame.locator(BOOKED_SELECTOR).count()
    print(
        f"DEBUG {location_label}: svg={svg_count}, rect={rect_count}, "
        f"empty={empty_count}, reserved={reserved_count}"
    )

    # 6) Use the classes we discovered from the SVG
    booked = reserved_count
    free = empty_count
    total = booked + free

    return {
        "name": location_label,
        "total_fields": total,
        "booked_fields": booked,
        "free_fields": free,
    }


async def scrape_all_locations():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        locations = []

        # ✅ Most reliable approach with JSF/select2: fresh page per location
        for label, value in LOCATION_OPTIONS:
            page = await browser.new_page()
            await page.goto(URL, wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")

            loc_stats = await scrape_location(page, label, value)
            print(f"{label}: {loc_stats}")
            locations.append(loc_stats)

            await page.close()

        await browser.close()

        # build summary
        total_fields = sum(l["total_fields"] for l in locations)
        total_booked = sum(l["booked_fields"] for l in locations)
        total_free = sum(l["free_fields"] for l in locations)

        summary = {
            "total_fields": total_fields,
            "total_booked": total_booked,
            "total_free": total_free,
        }

        return summary, locations


def main():
    summary, locations = asyncio.run(scrape_all_locations())

    print("Summary:", summary)
    print("Locations:", locations)

    append_summary_row(summary)
    append_location_rows(locations)


if __name__ == "__main__":
    main()
