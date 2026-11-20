import os
import shutil
from datetime import timedelta

from googleTakeoutPrune.main import delete_by_date, extract_records


def test_extract_records_files():
    # Test extract_records extracts zips and combines drive folders
    os.makedirs("tests/test_data/temp", exist_ok=True)
    extract_records(
        "tests/test_data/test_extract_records_names", "tests/test_data/temp"
    )

    drive_files = {entry.name for entry in os.scandir("tests/test_data/temp/drive")}
    assert drive_files == {
        "-2021",
        "2021-2022 (Taylor)",
        "2022-2023 (Hope)",
        "2023-2024",
        "2024-2025 (Cole and Alec)",
        "2024-2025 (Cole and Alec)-info.json",
        "2025-2025 (Alec and Sanika)",
        "2026-2027 (Kingston and Parker)",
        "24_wraparound_back.indd",
        "24_wraparound_back.indd-info.json",
        "2_wraparound_front.indd-info.json",
        "Comics_9.11RJ.pdf",
        "Front HR.indd-info.json",
        "IMG_3973.JPG",
        "Loose Files",
        "Old Accounts",
        "Some2027-2018TechniqueStuff-at-2026-08-25T19_00.zip",
        "Trash",
        "Unorganized",
    }

    shutil.rmtree("tests/test_data/temp")


def test_delete_by_date():
    # Test delete_by_date deletes appropriate files based on created date
    os.makedirs("tests/test_data/temp", exist_ok=True)
    extract_records("tests/test_data/test_delete_by_date", "tests/test_data/temp")

    delete_by_date(
        "tests/test_data/test_delete_by_date",
        "tests/test_data/temp",
        timedelta(days=365 * 1.5),
    )

    drive_files = {entry.name for entry in os.scandir("tests/test_data/temp/drive")}
    assert drive_files == {
        "2013 Fall Semester Advertising-comments.html",
        "2013 Fall Semester Advertising-info.json",
        "2013 Fall Semester Advertising.xlsx",
        "2014 tower cover.jpg",
        "2014 tower cover.jpg-info.json",
    }

    shutil.rmtree("tests/test_data/temp")
