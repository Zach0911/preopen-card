from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("PREOPEN_OFFLINE", "1")

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def fixtures_dir(repo_root: Path) -> Path:
    return repo_root / "tests" / "fixtures"


@pytest.fixture(scope="session")
def fonts_dir(repo_root: Path) -> Path:
    return repo_root / "fonts"
