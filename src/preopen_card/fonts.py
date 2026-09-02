"""Font discovery, SHA awareness, and FontSet loading for Pillow."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

REGULAR_CANDIDATES = (
    "NotoSansSC-Regular.subset.ttf",
    "NotoSansSC-Regular.ttf",
    "NotoSansSC-VF.ttf",
)
BOLD_CANDIDATES = (
    "NotoSansSC-Bold.subset.ttf",
    "NotoSansSC-Bold.ttf",
    "NotoSansSC-VF.ttf",
)


def repo_root() -> Path:
    start = Path(__file__).resolve().parent
    for p in [start, *start.parents]:
        if (p / "pyproject.toml").exists():
            return p
    return Path.cwd().resolve()


FONTS_DIR = repo_root() / "fonts"
DATA_DIR = repo_root() / "data"
FIXTURES_DIR = repo_root() / "tests" / "fixtures"


@dataclass(frozen=True)
class FontSet:
    regular_path: Path
    bold_path: Path

    def regular(self, size: int) -> ImageFont.FreeTypeFont:
        return _load(self.regular_path, size)

    def bold(self, size: int) -> ImageFont.FreeTypeFont:
        return _load(self.bold_path, size)


@lru_cache(maxsize=64)
def _load(path: str | Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def _pick(directory: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        candidate = directory / name
        if candidate.is_file() and candidate.stat().st_size > 1024:
            return candidate
    return None


def find_font_files() -> tuple[Path, Path]:
    root = repo_root()
    fonts_dir = root / "fonts"
    regular = _pick(fonts_dir, REGULAR_CANDIDATES)
    bold = _pick(fonts_dir, BOLD_CANDIDATES)
    if regular is None or bold is None:
        raise FileNotFoundError(
            f"Chinese TTF not found under {fonts_dir}. "
            "See fonts/README.md and run: python scripts/fetch_fonts.py"
        )
    return regular, bold


def load_font_set() -> FontSet:
    regular, bold = find_font_files()
    return FontSet(regular_path=regular, bold_path=bold)
