"""Package an allowlisted source checkpoint; excludes secrets, caches and videos."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile
import io
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from harness.credentials import load_credentials
FILES = ["README.md", "pyproject.toml", "uv.lock", ".python-version", ".env.example", ".gitignore"]
DIRECTORIES = ["configs", "tasks", "reference", "graders", "harness", "tests", "docs", "scripts", "results", "transcripts"]
SUFFIXES = {".py", ".json", ".jsonl", ".md", ".sql", ".csv", ".txt", ".toml", ".xml", ".zip"}


def package(destination: Path):
    credentials=[value.encode() for value in load_credentials(ROOT/".env").values() if value]
    def check_payload(name,data,depth=0):
        if any(secret in data for secret in credentials):
            raise ValueError(f"Credential value detected in {name}; refusing package.")
        if re.search(rb"(?:sk-[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{30,})",data):
            raise ValueError(f"Potential credential in {name}; refusing package.")
        if name.endswith(".zip"):
            if depth>=3:raise ValueError("Unexpected archive nesting.")
            with zipfile.ZipFile(io.BytesIO(data)) as nested:
                for member in nested.namelist():
                    if member.split("/")[-1]==".env":raise ValueError("Nested .env is forbidden.")
                    check_payload(member,nested.read(member),depth+1)
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
            check_payload(str(path.relative_to(ROOT)),data)
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
