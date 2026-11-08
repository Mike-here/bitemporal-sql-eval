from pathlib import Path
import pytest

from harness.tasks import ROOT, load_task


@pytest.fixture(scope="session")
def task():
    return load_task("t01")


@pytest.fixture(scope="session")
def reference_sql():
    return (ROOT / "reference/t01/solution.sql").read_text()
