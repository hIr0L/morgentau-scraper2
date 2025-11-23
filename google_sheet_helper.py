import datetime
import gspread
from google.oauth2.service_account import Credentials

# Path to your service account JSON file
SERVICE_ACCOUNT_FILE = "/Users/roli/.keys/morgentau-location-monitoring-021aa2d9368f.json"

# Your Google Sheets spreadsheet ID (replace this!)
SPREADSHEET_ID = "1vwToMFfuHx8I96oXbHYZPAIkcwRRjHgwzPkz8GpTbLs"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_worksheet(sheet_name: str):
    """Return a worksheet object by name."""
    credentials = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return spreadsheet.worksheet(sheet_name)

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

    now = datetime.datetime.now()
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

    now = datetime.datetime.now()
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
