import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
VIENNA_TZ = ZoneInfo("Europe/Vienna")


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
    service_account_info = json.loads(service_account_json)

    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES,
    )
    return gspread.authorize(credentials)


def get_worksheet(sheet_name: str):
    """
    Open Google Sheet by SHEET_ID env var and return the named worksheet.
    Expects worksheet/tab names:
      - summary
      - locations
    """
    client = _get_client()
    spreadsheet_id = _require_env("SHEET_ID")

    spreadsheet = client.open_by_key(spreadsheet_id)

    try:
        return spreadsheet.worksheet(sheet_name)
    except Exception as e:
        raise RuntimeError(
            f"Worksheet '{sheet_name}' not found. "
            f"Check tab name spelling/case in the Google Sheet."
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

    ws.append_row(row, value_input_option="USER_ENTERED")


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

    if rows:
        ws.append_rows(rows, value_input_option="USER_ENTERED")
