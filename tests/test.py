import os
import shutil
from datetime import timedelta

from googleTakeoutPrune.main import delete_by_date, extract_records


def test_extract_records():
    # Test extract_records extracts zips and combines drive folders
    os.makedirs("tests/test_data/temp", exist_ok=True)
    extract_records("tests/test_data/test_extract_records", "tests/test_data/temp")

    assert len(list(os.scandir("tests/test_data/temp/drive"))) == 2 * 159

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
