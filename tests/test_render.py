from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from PIL import Image

from preopen_card.assemble import build_card_data
from preopen_card.render import BG, DISCLAIMER, HEIGHT, WIDTH, render_card, write_png


def test_offline_png_size_and_bg(monkeypatch, tmp_path: Path, fixtures_dir: Path):
    monkeypatch.setenv("PREOPEN_OFFLINE", "1")
    monkeypatch.setenv("PREOPEN_NOW", "2026-09-02T07:30:00+08:00")
    meta = json.loads((fixtures_dir / "expected_meta.json").read_text())
    data = build_card_data(card_date=date(2026, 9, 2), offline=True)
    path = write_png(data, tmp_path / "card.png")
    img = Image.open(path)
    assert img.size == (meta["width"], meta["height"]) == (WIDTH, HEIGHT)
    assert img.getpixel((0, 0)) == tuple(meta["bg"]) == BG
    assert img.getpixel((WIDTH - 1, HEIGHT - 1)) == BG
    assert DISCLAIMER == meta["disclaimer"]
    # gold title pixels exist somewhere in the header band
    gold = tuple(meta["gold"])
    header = [img.getpixel((x, 70)) for x in range(64, 300, 4)]
    assert gold in header or any(
        abs(p[0] - gold[0]) < 8 and abs(p[1] - gold[1]) < 8 and abs(p[2] - gold[2]) < 8
        for p in header
    )


def test_render_degraded_does_not_crash(monkeypatch):
    monkeypatch.setenv("PREOPEN_OFFLINE", "1")
    from preopen_card.models import CalendarItem, CardData, FxQuote, Headline, IndexQuote
    from datetime import datetime
    from zoneinfo import ZoneInfo

    missing_q = IndexQuote("^GSPC", "标普500", None, None, None, None, "none", "degraded")
    data = CardData(
        card_date=date(2026, 9, 2),
        generated_at_shanghai=datetime(2026, 9, 2, 7, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
        indices=(missing_q, missing_q, missing_q),
        fx=FxQuote("USDCNH", "美元兑离岸人民币", None, None, None, "none", "degraded", False),
        calendar_items=(
            CalendarItem("missing", "数据暂缺", "—", "—", "none"),
        ),
        headlines=(
            Headline("数据暂缺", "", "—", "degraded"),
            Headline("数据暂缺", "", "—", "degraded"),
            Headline("数据暂缺", "", "—", "degraded"),
        ),
        degrade_notes=("all",),
    )
    img = render_card(data)
    assert img.size == (1080, 1440)
