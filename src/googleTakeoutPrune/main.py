import json
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


def _copy_drive_archive(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as contents:
        members = []
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
            members.append((member, relative_path))

        top_level_paths: dict[str, Path] = {}
        for member, relative_path in members:
            top_level = relative_path.parts[0]
            if top_level not in top_level_paths:
                target = destination / top_level
                if target.exists():
                    target = _unique_path(destination / f"{archive.stem}__{top_level}")
                top_level_paths[top_level] = target

            target_path = top_level_paths[top_level].joinpath(*relative_path.parts[1:])
            if member.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
                continue

            target_path.parent.mkdir(parents=True, exist_ok=True)
            with contents.open(member) as source, target_path.open("wb") as target:
                shutil.copyfileobj(source, target)


def extract_records(records_path: str | Path, output_path: str | Path) -> None:
    records = Path(records_path)
    if not records.is_dir():
        raise FileNotFoundError(f"Records directory does not exist: {records}")

    output = Path(output_path)
    output.mkdir(parents=True, exist_ok=True)
    drive = output / "drive"
    drive.mkdir(exist_ok=True)

    source_drive = _drive_directory(records)
    if source_drive is not None:
        for source in source_drive.iterdir():
            target = drive / source.name
            if target.exists():
                target = _unique_path(target)
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)

    archives = sorted(records.glob("*.zip"))
    for archive in archives:
        _copy_drive_archive(archive, drive)

    if source_drive is None and not archives:
        raise FileNotFoundError(f"No Drive folder or ZIP archives found in {records}")


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
    for info_path in sorted(drive.rglob("*-info.json")):
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
            title = info_path.name.removesuffix("-info.json")

        original_path = info_path.with_name(title)
        originals = [original_path] if original_path.is_file() else []
        originals.extend(
            candidate
            for candidate in info_path.parent.glob(f"{title}.*")
            if candidate.is_file() and candidate != info_path
        )
        for original in originals:
            original.unlink()

        info_path.with_name(f"{title}-comments.html").unlink(missing_ok=True)
        info_path.unlink()


def main() -> None:
    extract_records("records", "records_out/unpruned")

    delete_by_date(
        "records_out/unpruned",
        "records_out/pruned",
        timedelta(days=365 * 2),
    )


if __name__ == "__main__":
    main()
