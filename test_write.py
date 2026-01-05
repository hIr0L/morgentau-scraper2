import os
from google_sheet_helper import append_summary_row, append_location_rows

# Turn on debug logs for this test run
os.environ["DEBUG"] = "1"

def main():
    # Write a summary row
    append_summary_row({
        "total_fields": 999,
        "total_booked": 111,
        "total_free": 888,
    })

    # Write one location row
    append_location_rows([
        {
            "name": "TEST: write_check",
            "total_fields": 10,
            "booked_fields": 3,
            "free_fields": 7,
        }
    ])

    print("✅ test_write.py finished: wrote to Google Sheet successfully.")

if __name__ == "__main__":
    main()
