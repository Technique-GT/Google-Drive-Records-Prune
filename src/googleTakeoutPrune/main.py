import filecmp
import json
import re
import shutil
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath


def _drive_directory(path: Path) -> Path | None:
    if path.name.lower() == "drive" and path.is_dir():
        return path

    if path.is_dir():
        for child in path.iterdir():
            if child.is_dir() and child.name.lower() == "drive":
                return child
    return None


def _drive_directories(records: Path, output: Path) -> list[Path]:
    output = output.resolve()
    candidates = [records, *records.rglob("*")]
    return sorted(
        (
            candidate
            for candidate in candidates
            if candidate.is_dir()
            and candidate.name.lower() == "drive"
            and output not in candidate.resolve().parents
            and candidate.resolve() != output
        ),
        key=lambda candidate: candidate.as_posix(),
    )


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    suffix = path.suffix
    stem = path.name[: -len(suffix)] if suffix else path.name
    index = 2
    while True:
        candidate = path.with_name(f"{stem} ({index}){suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def _merge_directory(source: Path, destination: Path) -> None:
    if destination.exists() and not destination.is_dir():
        destination = _unique_path(destination)
    destination.mkdir(parents=True, exist_ok=True)

    for source_entry in sorted(source.iterdir(), key=lambda entry: entry.name):
        destination_entry = destination / source_entry.name
        if source_entry.is_dir():
            _merge_directory(source_entry, destination_entry)
            continue

        if destination_entry.is_file() and filecmp.cmp(
            source_entry, destination_entry, shallow=False
        ):
            continue
        if destination_entry.exists():
            destination_entry = _unique_path(destination_entry)
        shutil.copy2(source_entry, destination_entry)


def _remove_ds_store_files(directory: Path) -> None:
    for path in directory.rglob("*"):
        if path.is_file() and re.fullmatch(
            r"(?:\.DS_Store(?: \(\d+\))?|\._(?: \(\d+\))?\.DS_Store)",
            path.name,
        ):
            path.unlink()


def _streams_match(source, destination) -> bool:
    while True:
        source_chunk = source.read(1024 * 1024)
        destination_chunk = destination.read(1024 * 1024)
        if source_chunk != destination_chunk:
            return False
        if not source_chunk:
            return True


def _copy_archive_file(
    contents: zipfile.ZipFile,
    member: zipfile.ZipInfo,
    destination: Path,
) -> None:
    if destination.is_file() and destination.stat().st_size == member.file_size:
        with contents.open(member) as source, destination.open("rb") as existing:
            if _streams_match(source, existing):
                return
    if destination.exists():
        destination = _unique_path(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)
    with contents.open(member) as source, destination.open("wb") as target:
        shutil.copyfileobj(source, target)


def _copy_drive_archive(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as contents:
        for member in contents.infolist():
            archive_path = PurePosixPath(member.filename.replace("\\", "/"))
            if archive_path.is_absolute() or ".." in archive_path.parts:
                raise ValueError(f"Unsafe path in archive {archive}: {member.filename}")

            drive_index = next(
                (
                    index
                    for index, part in enumerate(archive_path.parts)
                    if part.lower() == "drive"
                ),
                None,
            )
            if drive_index is None or drive_index == len(archive_path.parts) - 1:
                continue

            relative_path = PurePosixPath(*archive_path.parts[drive_index + 1 :])
            if not relative_path.parts:
                continue

            target = destination.joinpath(*relative_path.parts)
            if member.is_dir():
                if target.exists() and not target.is_dir():
                    target = _unique_path(target)
                target.mkdir(parents=True, exist_ok=True)
            else:
                _copy_archive_file(contents, member, target)


def extract_records(records_path: str | Path, output_path: str | Path) -> None:
    records = Path(records_path)
    if not records.is_dir():
        raise FileNotFoundError(f"Records directory does not exist: {records}")

    output = Path(output_path)
    output.mkdir(parents=True, exist_ok=True)
    drive = output / "drive"
    drive.mkdir(parents=True, exist_ok=True)

    source_drives = _drive_directories(records, output)
    for source_drive in source_drives:
        _merge_directory(source_drive, drive)

    archives = sorted(
        archive
        for archive in records.rglob("*.zip")
        if "drive"
        not in {part.lower() for part in archive.relative_to(records).parts[:-1]}
    )
    for archive in archives:
        _copy_drive_archive(archive, drive)

    if not source_drives and not archives:
        raise FileNotFoundError(f"No Drive folder or ZIP archives found in {records}")
    _remove_ds_store_files(drive)


def delete_by_date(
    records_path: str | Path,
    output_path: str | Path,
    max_age: timedelta,
) -> None:
    records = Path(records_path)
    if not records.exists():
        raise FileNotFoundError(f"Records path does not exist: {records}")
    if max_age < timedelta(0):
        raise ValueError("max_age must not be negative")

    output = Path(output_path)
    drive = _drive_directory(output)
    if drive is None:
        source_drive = _drive_directory(records)
        if source_drive is None:
            raise FileNotFoundError(f"Drive directory does not exist in {records}")
        output.mkdir(parents=True, exist_ok=True)
        drive = output / "drive"
        shutil.copytree(source_drive, drive)

    cutoff = datetime.now(UTC) - max_age
    info_paths = sorted(
        set(drive.rglob("*-info.json")) | set(drive.rglob("*-i.json"))
    )
    for info_path in info_paths:
        metadata = json.loads(info_path.read_text(encoding="utf-8"))
        created = metadata.get("created")
        if not isinstance(created, str):
            continue

        created_at = datetime.fromisoformat(created)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if created_at < cutoff:
            continue

        title = metadata.get("title")
        if not isinstance(title, str) or Path(title).name != title:
            suffix = (
                "-info.json"
                if info_path.name.endswith("-info.json")
                else "-i.json"
            )
            title = info_path.name.removesuffix(suffix)

        originals = [
            candidate
            for candidate in info_path.parent.iterdir()
            if candidate.is_file()
            and candidate != info_path
            and (
                candidate.name == title
                or candidate.name.startswith(f"{title}.")
            )
        ]
        for original in originals:
            original.unlink()

        original_names = {title, *(original.name for original in originals)}
        comments = [
            candidate
            for candidate in info_path.parent.iterdir()
            if candidate.is_file()
            and candidate.name.endswith("-comments.html")
            and candidate.name.removesuffix("-comments.html") in original_names
        ]
        if not comments:
            truncated_comments = [
                candidate
                for candidate in info_path.parent.iterdir()
                if candidate.is_file()
                and candidate.name.endswith("-comments.html")
                and any(
                    Path(original_name).stem.startswith(
                        Path(
                            candidate.name.removesuffix("-comments.html")
                        ).stem
                    )
                    and Path(original_name).suffix
                    == Path(
                        candidate.name.removesuffix("-comments.html")
                    ).suffix
                    for original_name in original_names
                )
            ]
            if len(truncated_comments) > 1:
                raise ValueError(f"Ambiguous comment sidecars for {info_path}")
            comments = truncated_comments
        for comment in comments:
            comment.unlink()
        info_path.unlink()


def main() -> None:
    shutil.rmtree("records_out", ignore_errors=True)
    Path("records_out/unpruned").mkdir(parents=True, exist_ok=True)
    Path("records_out/pruned").mkdir(parents=True, exist_ok=True)

    extract_records("records", "records_out/unpruned")

    delete_by_date(
        "records_out/unpruned",
        "records_out/pruned",
        timedelta(days=365 * 2),
    )

    shutil.make_archive(
        "records_out/pruned",
        "zip",
        root_dir="records_out/pruned",
    )


if __name__ == "__main__":
    main()
