"""Package an allowlisted source checkpoint; excludes secrets, caches and videos."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ["README.md", "pyproject.toml", "uv.lock", ".python-version", ".env.example", ".gitignore"]
DIRECTORIES = ["configs", "tasks", "reference", "graders", "harness", "tests", "docs", "scripts", "results", "transcripts"]
SUFFIXES = {".py", ".json", ".jsonl", ".md", ".sql", ".csv", ".txt", ".toml", ".xml"}


def package(destination: Path):
    paths = [ROOT / name for name in FILES]
    for directory in DIRECTORIES:
        paths.extend(path for path in (ROOT / directory).rglob("*")
                     if path.is_file() and path.suffix in SUFFIXES
                     and "__pycache__" not in path.parts and not path.name.startswith("."))
    paths = sorted(set(paths))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            data = path.read_bytes()
            if re.search(rb"sk-[A-Za-z0-9_-]{20,}", data):
                raise ValueError(f"Potential credential in {path.relative_to(ROOT)}; refusing package.")
            info = zipfile.ZipInfo(str(path.relative_to(ROOT)), date_time=(2026, 11, 8, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None or "README.md" not in archive.namelist():
            raise ValueError("Archive validation failed.")
        count = len(archive.namelist())
    if destination.stat().st_size >= 50_000_000:
        raise ValueError("Archive must be below 50 MB.")
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    manifest = dict(filename=destination.name, bytes=destination.stat().st_size,
                    files=count, sha256=digest, status="development_checkpoint_not_final_submission")
    destination.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/t01-checkpoint.zip")
    package(parser.parse_args().output)
