from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from preopen_card.assemble import build_card_data, load_calendar, resolve_card_date
from preopen_card.calendar_util import next_a_share_trading_day
from preopen_card.models import CardData


def test_resolve_override_weekend():
    now = datetime(2026, 9, 2, 7, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
    d = resolve_card_date(now, date(2026, 9, 5))
    assert d == date(2026, 9, 5)


def test_resolve_skips_weekend_to_next_session():
    now = datetime(2026, 9, 5, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    assert resolve_card_date(now, None) == next_a_share_trading_day(date(2026, 9, 5))
    assert resolve_card_date(now, None) == date(2026, 9, 7)


def test_offline_build_complete(monkeypatch):
    monkeypatch.setenv("PREOPEN_OFFLINE", "1")
    monkeypatch.setenv("PREOPEN_NOW", "2026-09-02T07:30:00+08:00")
    data = build_card_data(card_date=date(2026, 9, 2), offline=True)
    assert isinstance(data, CardData)
    assert len(data.indices) == 3
    assert data.indices[0].name_zh == "标普500"
    assert data.indices[0].status == "ok"
    assert data.indices[0].last == 5634.52
    assert data.indices[1].name_zh == "道琼斯"
    assert data.indices[2].name_zh == "纳斯达克"
    assert data.fx.status == "ok"
    assert data.fx.pair == "USDCNH"
    assert not data.fx.is_dxy_fallback
    assert data.calendar_items
    assert any(i.kind == "macro" for i in data.calendar_items)
    assert len(data.headlines) == 3
    assert all(h.status == "ok" for h in data.headlines)
    assert all(h.url.startswith("http") for h in data.headlines)


def test_calendar_missing_when_ff_fixture_gone(tmp_path, monkeypatch):
    monkeypatch.setenv("PREOPEN_OFFLINE", "1")
    from preopen_card import assemble

    monkeypatch.setattr(assemble, "fixtures_dir", lambda: tmp_path)
    items, notes = load_calendar(date(2026, 9, 2), offline=True)
    assert any(i.kind == "missing" and i.title == "数据暂缺" for i in items)
    assert any("宏观" in n for n in notes)


def test_offline_snapshot_roundtrip(monkeypatch, fixtures_dir: Path):
    monkeypatch.setenv("PREOPEN_OFFLINE", "1")
    monkeypatch.setenv("PREOPEN_NOW", "2026-09-02T07:30:00+08:00")
    data = build_card_data(card_date=date(2026, 9, 2), offline=True)
    snap_path = fixtures_dir / "carddata_offline.json"
    payload = {
        "card_date": data.card_date.isoformat(),
        "indices": [
            {
                "symbol": q.symbol,
                "name_zh": q.name_zh,
                "last": q.last,
                "change_pct": None if q.change_pct is None else round(q.change_pct, 4),
                "source": q.source,
                "status": q.status,
            }
            for q in data.indices
        ],
        "fx": {
            "pair": data.fx.pair,
            "last": data.fx.last,
            "status": data.fx.status,
            "is_dxy_fallback": data.fx.is_dxy_fallback,
        },
        "headline_titles": [h.title for h in data.headlines],
        "calendar_titles": [c.title for c in data.calendar_items],
    }
    if not snap_path.exists():
        snap_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    expected = json.loads(snap_path.read_text())
    assert payload["card_date"] == expected["card_date"]
    assert payload["indices"] == expected["indices"]
    assert payload["fx"] == expected["fx"]
    assert payload["headline_titles"] == expected["headline_titles"]
    assert payload["calendar_titles"] == expected["calendar_titles"]
