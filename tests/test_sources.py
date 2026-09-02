from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from preopen_card.calendar_util import parse_ff_calendar
from preopen_card.sources import parse_rss_items, parse_stooq_csv, parse_yahoo_chart


def test_parse_yahoo_gspc(fixtures_dir: Path):
    payload = json.loads((fixtures_dir / "yahoo_chart_gspc.json").read_text())
    last, prev, asof = parse_yahoo_chart(payload)
    assert last == 5634.52
    assert prev == 5601.10
    assert asof.tzinfo is not None
    assert abs((last / prev - 1) * 100 - 0.5967) < 0.01


def test_parse_stooq(fixtures_dir: Path):
    text = (fixtures_dir / "stooq_spx.csv").read_text()
    last, prev, asof = parse_stooq_csv(text)
    assert last == 5634.52
    assert prev == 5601.10


def test_rss_filters_stock_pitches(fixtures_dir: Path):
    xml = (fixtures_dir / "rss_google_zh.xml").read_text()
    items = parse_rss_items(xml, "Google News")
    titles = [i.title for i in items]
    assert "美联储官员讨论通胀与利率路径" in titles
    assert "农业部发布农产品供需报告综述" in titles
    assert all("目标价" not in t and "强烈推荐" not in t for t in titles)
    assert all("utm_" not in i.url for i in items)


def test_rss_bbc_skips_downgrade(fixtures_dir: Path):
    xml = (fixtures_dir / "rss_bbc_business.xml").read_text()
    items = parse_rss_items(xml, "BBC")
    assert len(items) == 2
    assert all("downgrade" not in i.title.lower() for i in items)


def test_ff_keeps_high_usd_cny_on_card_date(fixtures_dir: Path):
    payload = json.loads((fixtures_dir / "ff_calendar_thisweek.json").read_text())
    items = parse_ff_calendar(payload, date(2026, 9, 2))
    titles = [i.title for i in items]
    assert "ISM Manufacturing PMI" in titles
    assert "Caixin Manufacturing PMI" in titles
    assert "Euro CPI" not in titles
    assert "Nonfarm Payrolls" not in titles
    assert "Low impact fluff" not in titles
    assert len(items) <= 3
