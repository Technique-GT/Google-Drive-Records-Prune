import os
import shutil
from datetime import timedelta

from googleTakeoutPrune.main import delete_by_date, extract_records


def test_extract_records_name_top_level():
    # Test extract_records extracts zips and combines drive folders
    shutil.rmtree("tests/test_data/temp", ignore_errors=True)
    os.makedirs("tests/test_data/temp", exist_ok=True)
    extract_records(
        "tests/test_data/test_extract_records_name_top_level", "tests/test_data/temp"
    )

    drive_files = {entry.name for entry in os.scandir("tests/test_data/temp/drive")}
    assert drive_files == {
        "2024-2025 (Cole and Alec)",
        "2025-2025 (Alec and Sanika)",
        "2026-2027 (Kingston and Parker)",
    }

    shutil.rmtree("tests/test_data/temp")


def test_extract_records_name_recursion():
    # Test extract_records extracts zips and combines drive folders
    shutil.rmtree("tests/test_data/temp", ignore_errors=True)
    os.makedirs("tests/test_data/temp", exist_ok=True)
    extract_records(
        "tests/test_data/test_extract_records_name_recursion", "tests/test_data/temp"
    )

    drive_files = {
        entry.name
        for entry in os.scandir(
            "tests/test_data/temp/drive/2026-2027 (Kingston and Parker)"
        )
    }
    assert drive_files == {
        "Website",
        "Master Project List-info.json",
        "Master Project List.xlsx",
        "Fall 2026 Content-info.json",
        "Archives-info.json",
    }

    shutil.rmtree("tests/test_data/temp")


def test_delete_by_date_large():
    # Test delete_by_date deletes appropriate files based on created date
    os.makedirs("tests/test_data/temp", exist_ok=True)

    delete_by_date(
        "tests/test_data/test_delete_by_date_large",
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


def test_delete_by_date_remove_recent_finances():
    # Test delete_by_date deletes appropriate files based on created date
    shutil.rmtree("tests/test_data/temp", ignore_errors=True)
    os.makedirs("tests/test_data/temp", exist_ok=True)

    delete_by_date(
        "tests/test_data/test_delete_by_date_remove_recent_finances",
        "tests/test_data/temp",
        timedelta(days=365 * 1.5),
    )

    drive_files = {
        entry.name
        for entry in os.scandir(
            "tests/test_data/temp/drive/2026-2027 (Kingston and Parker)/Finances"
        )
    }
    assert drive_files == set()

    shutil.rmtree("tests/test_data/temp")
