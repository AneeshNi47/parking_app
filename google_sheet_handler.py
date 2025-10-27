import gspread
from oauth2client.service_account import ServiceAccountCredentials
import csv
import os

# Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("car-counter-raspberry-pi-e70dcd8164ab.json", scope)
client = gspread.authorize(creds)
sheet = client.open("CarCounterLogs").sheet1


def sync_csv_to_sheet(csv_file):
    if not os.path.exists(csv_file):
        return 0

    unsynced_rows = []
    all_rows = []

    # Step 1: Load all rows and filter unsynced
    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        headers = next(reader)
        for row in reader:
            all_rows.append(row)
            if len(row) < 7 or row[6].strip().lower() != "yes":
                unsynced_rows.append(row[:6])  # exclude 'synced' column for upload

    if not unsynced_rows:
        return 0

    # Step 2: Upload all unsynced rows in one API call
    sheet.append_rows(unsynced_rows, value_input_option="USER_ENTERED")

    # Step 3: Mark synced rows in CSV
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)  # re-write header
        for row in all_rows:
            if len(row) < 7 or row[6].strip().lower() != "yes":
                # Add or update 'synced' column
                new_row = row[:6] + ["Yes"]
                writer.writerow(new_row)
            else:
                writer.writerow(row)

    return len(unsynced_rows)