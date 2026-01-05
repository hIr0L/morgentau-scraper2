import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+

import gspread
from google.oauth2.service_account import Credentials

# Write scope (NOT readonly)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
VIENNA_TZ = ZoneInfo("Europe/Vienna")


def _debug_enabled() -> bool:
    return os.getenv("DEBUG", "").strip().lower() in ("1", "true", "yes", "y", "on")


def _log(*args):
    if _debug_enabled():
        print("[sheets]", *args)


def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(
            f"Missing env var: {name}. "
            f"Make sure it exists locally or is set in GitHub Actions Secrets."
        )
    return val


def _get_client():
    """
    Create gspread client from Service Account JSON stored in env var
    GOOGLE_SERVICE_ACCOUNT_JSON (usually a GitHub Actions secret).
    """
    service_account_json = _require_env("GOOGLE_SERVICE_ACCOUNT_JSON")

    try:
        service_account_info = json.loads(service_account_json)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON. "
            "Paste the FULL service account JSON into the secret (including { })."
        ) from e

    client_email = service_account_info.get("client_email", "")
    if not client_email:
        raise RuntimeError(
            "Service account JSON is missing 'client_email'. "
            "Make sure you pasted the correct service account JSON."
        )

    _log("Using service account:", client_email)

    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES,
    )

    client = gspread.authorize(credentials)
    _log("Google Sheets client created")
    return client


def get_worksheet(sheet_name: str):
    """
    Open Google Sheet by SHEET_ID env var and return the named worksheet.
    Expects worksheet/tab names:
      - summary
      - locations
    """
    client = _get_client()
    spreadsheet_id = _require_env("SHEET_ID")

    _log("Opening spreadsheet ID:", spreadsheet_id)

    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
    except Exception as e:
        raise RuntimeError(
            "Failed to open spreadsheet by SHEET_ID. "
            "Most common causes:\n"
            "1) SHEET_ID is wrong (not the /d/<ID>/ part)\n"
            "2) The Google Sheet is NOT shared with the service account email as Editor\n"
            "3) Wrong Google project/service account JSON\n"
        ) from e

    try:
        titles = [ws.title for ws in spreadsheet.worksheets()]
        _log("Available worksheets:", titles)
    except Exception:
        # Not fatal; continue.
        pass

    try:
        ws = spreadsheet.worksheet(sheet_name)
        _log("Using worksheet:", sheet_name)
        return ws
    except Exception as e:
        raise RuntimeError(
            f"Worksheet '{sheet_name}' not found. "
            f"Check tab name spelling/case in the Google Sheet. "
            f"(Expected: 'summary' and 'locations')"
        ) from e


def _now_vienna():
    return datetime.now(VIENNA_TZ)


def append_summary_row(summary_dict: dict):
    """
    Append one row to the 'summary' sheet.
    summary_dict example:
    {
      "total_fields": 120,
      "total_booked": 80,
      "total_free": 40,
    }
    """
    ws = get_worksheet("summary")
    now = _now_vienna()

    row = [
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M"),
        int(summary_dict.get("total_fields", 0)),
        int(summary_dict.get("total_booked", 0)),
        int(summary_dict.get("total_free", 0)),
    ]

    _log("Appending summary row:", row)

    # Make failures visible: confirm row count changes
    before = len(ws.get_all_values())
    ws.append_row(row, value_input_option="USER_ENTERED")
    after = len(ws.get_all_values())

    _log("Summary rows before/after:", before, after)

    if after <= before:
        raise RuntimeError("Summary append did not change sheet (no new row detected).")


def append_location_rows(locations: list):
    """
    Append multiple rows to the 'locations' sheet.

    locations: list of dicts, e.g.
    [
      {"name":"...", "total_fields":..., "booked_fields":..., "free_fields":...},
      ...
    ]
    """
    ws = get_worksheet("locations")
    now = _now_vienna()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    rows = []
    for loc in locations:
        rows.append([
            date_str,
            time_str,
            str(loc.get("name", "")),
            int(loc.get("total_fields", 0)),
            int(loc.get("booked_fields", 0)),
            int(loc.get("free_fields", 0)),
        ])

    _log("Prepared location rows:", len(rows))
    if rows:
        _log("First location row preview:", rows[0])

    # IMPORTANT: Fail loudly if no data, so Actions doesn't say "Success" with empty output
    if not rows:
        raise RuntimeError("No location rows to write (locations list was empty).")

    before = len(ws.get_all_values())
    ws.append_rows(rows, value_input_option="USER_ENTERED")
    after = len(ws.get_all_values())

    _log("Locations rows before/after:", before, after)

    if after <= before:
        raise RuntimeError("Locations append did not change sheet (no new rows detected).")
