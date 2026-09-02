from __future__ import annotations

from datetime import date
from pathlib import Path

from PIL import Image

from preopen_card.cli import main


def test_cli_offline_writes_png(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PREOPEN_OFFLINE", "1")
    monkeypatch.setenv("PREOPEN_NOW", "2026-09-02T07:30:00+08:00")
    out = tmp_path / "out" / "card.png"
    rc = main(["--date", "2026-09-02", "--out", str(out)])
    assert rc == 0
    assert out.is_file()
    img = Image.open(out)
    assert img.size == (1080, 1440)


def test_cli_bad_out_dir_exit_2(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PREOPEN_OFFLINE", "1")
    # path that cannot be created: a file used as parent
    blocker = tmp_path / "file"
    blocker.write_text("x")
    rc = main(["--date", "2026-09-02", "--out", str(blocker / "card.png")])
    assert rc == 2
