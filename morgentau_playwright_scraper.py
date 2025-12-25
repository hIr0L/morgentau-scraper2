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


async def scrape_location(page, label, value):
    print(f"\n--- {label} ({value}) ---")

    await page.wait_for_selector(LOCATION_SELECT_SELECTOR, timeout=60000)

    # JS-based select (Playwright Python: only one arg -> pass dict)
    success = await select_location_js(page, value)
    if not success:
        print(f"SKIP: select element missing for {label}")
        return {"name": label, "total_fields": 0, "booked_fields": 0, "free_fields": 0}

    # Give JSF time to update iframe/map after location change
    await page.wait_for_timeout(2000)

    map_frame = None
    for f in page.frames:
        if "/faces/map/" in f.url:
            map_frame = f
            break

    if not map_frame:
        print(
