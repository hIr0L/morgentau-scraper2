from google_sheet_helper import append_location_row

# Test row to verify everything works
append_location_row({
    "location": "TEST",
    "booked_fields": 5,
    "free_fields": 3,
})

print("Successfully wrote a test row to Google Sheets!")

