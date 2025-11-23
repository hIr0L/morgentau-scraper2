import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+

import gspread
from google.oauth2.service_account import Credentials

# Google Sheets API Scope
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Unsere Standard-Zeitzone
VIENNA_TZ = ZoneInfo("Europe/Vienna")


def _get_client():
    """
    Erzeuge einen gspread-Client auf Basis des Service-Account-JSONs,
    das in der Umgebungsvariable GOOGLE_SERVICE_ACCOUNT_JSON steckt.
    (Kommt in GitHub Actions aus dem Secret gleichen Namens.)
    """
    service_account_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    service_account_info = json.loads(service_account_json)

    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES,
    )
    return gspread.authorize(credentials)


def get_worksheet(sheet_name: str):
    """
    Öffnet das Google Sheet über die SHEET_ID (aus Umgebungsvariable/Secret)
    und gibt das Worksheet mit dem gegebenen Namen zurück.
    """
    client = _get_client()

    # SHEET_ID kommt in GitHub Actions aus dem Secret SHEET_ID
    spreadsheet_id = os.environ["SHEET_ID"]
    spreadsheet = client.open_by_key(spreadsheet_id)

    return spreadsheet.worksheet(sheet_name)


def _now_vienna():
    """Aktuelle Zeit in Europe/Vienna als datetime-Objekt."""
    return datetime.now(VIENNA_TZ)


def append_summary_row(summary_dict: dict):
    """
    Write one summary row into the 'summary' sheet.

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
        summary_dict.get("total_fields", 0),
        summary_dict.get("total_booked", 0),
        summary_dict.get("total_free", 0),
    ]

    ws.append_row(row, value_input_option="USER_ENTERED")


def append_location_rows(locations: list):
    """
    Write multiple location rows into the 'locations' sheet.

    locations: list of dicts, e.g.
    [
        {
            "name": "Location 1",
            "total_fields": 15,
            "booked_fields": 10,
            "free_fields": 5,
        },
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
            loc.get("name", ""),
            loc.get("total_fields", 0),
            loc.get("booked_fields", 0),
            loc.get("free_fields", 0),
        ])

    if rows:
        ws.append_rows(rows, value_input_option="USER_ENTERED")
