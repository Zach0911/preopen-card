"""Assemble CardData from live sources or offline fixtures. Never invent macros."""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from preopen_card.calendar_util import (
    next_a_share_trading_day,
    parse_ff_calendar,
    session_items,
)
from preopen_card.fonts import repo_root
from preopen_card.httputil import FetchError
from preopen_card.models import CalendarItem, CardData, FxQuote, Headline, IndexQuote
from preopen_card.sources import (
    FX_CHAIN,
    INDEX_SPECS,
    RSS_FEEDS,
    _degraded_index,
    _fx_from_chart,
    _index_from_stooq,
    _index_from_yahoo,
    _placeholder_headline,
    load_fx,
    load_headlines,
    load_us_indices,
    parse_rss_items,
)

SHANGHAI = ZoneInfo("Asia/Shanghai")

FIXTURE_INDEX = {
    "^GSPC": ("yahoo_chart_gspc.json", "stooq_spx.csv"),
    "^DJI": ("yahoo_chart_dji.json", None),
    "^IXIC": ("yahoo_chart_ixic.json", None),
}
FIXTURE_FX = {
    "USDCNH=X": "yahoo_chart_usdcnh.json",
    "CNH=X": "yahoo_chart_usdcnh.json",
    "USDCNY=X": "yahoo_chart_usdcnh.json",
    "DX-Y.NYB": "yahoo_chart_dxy.json",
}
FIXTURE_RSS = (
    ("rss_google_zh.xml", "Google News"),
    ("rss_bbc_business.xml", "BBC"),
)


def fixtures_dir() -> Path:
    return repo_root() / "tests" / "fixtures"


def _offline_requested(offline: bool) -> bool:
    return offline or os.environ.get("PREOPEN_OFFLINE") == "1"


def resolve_card_date(now_shanghai: datetime, override: date | None) -> date:
    if override is not None:
        return override
    d = now_shanghai.date()
    if not __import__("preopen_card.calendar_util", fromlist=["is_a_share_trading_day"]).is_a_share_trading_day(d):
        return next_a_share_trading_day(d)
    return d


def _read_fixture(name: str) -> str:
    path = fixtures_dir() / name
    if not path.is_file():
        raise FetchError(f"missing fixture {name}")
    return path.read_text(encoding="utf-8")


def _load_indices_offline() -> tuple[IndexQuote, IndexQuote, IndexQuote]:
    quotes: list[IndexQuote] = []
    for yahoo_symbol, stooq_symbol, name_zh in INDEX_SPECS:
        yahoo_file, stooq_file = FIXTURE_INDEX[yahoo_symbol]
        quote: IndexQuote | None = None
        try:
            payload = json.loads(_read_fixture(yahoo_file))
            quote = _index_from_yahoo(payload, yahoo_symbol, name_zh)
        except (FetchError, json.JSONDecodeError, OSError, KeyError, TypeError, ValueError):
            quote = None
        if quote is None and stooq_file:
            try:
                quote = _index_from_stooq(_read_fixture(stooq_file), yahoo_symbol, name_zh)
            except (FetchError, OSError, ValueError):
                quote = None
        quotes.append(quote or _degraded_index(yahoo_symbol, name_zh))
    return quotes[0], quotes[1], quotes[2]


def _load_fx_offline() -> FxQuote:
    for symbol, pair, label, is_dxy in FX_CHAIN:
        fname = FIXTURE_FX.get(symbol)
        if not fname:
            continue
        try:
            payload = json.loads(_read_fixture(fname))
            return _fx_from_chart(payload, pair, label, is_dxy)
        except (FetchError, json.JSONDecodeError, OSError, KeyError, TypeError, ValueError):
            continue
    return FxQuote(
        pair="USDCNH",
        label_zh="美元兑离岸人民币",
        last=None,
        change_pct=None,
        asof_utc=None,
        source="none",
        status="degraded",
        is_dxy_fallback=False,
    )


def _load_headlines_offline() -> tuple[Headline, Headline, Headline]:
    picked: list[Headline] = []
    seen: set[str] = set()
    for fname, name in FIXTURE_RSS:
        try:
            xml_text = _read_fixture(fname)
        except FetchError:
            continue
        for item in parse_rss_items(xml_text, name):
            if item.url in seen:
                continue
            seen.add(item.url)
            picked.append(item)
            if len(picked) >= 3:
                break
        if len(picked) >= 3:
            break
    while len(picked) < 3:
        picked.append(_placeholder_headline())
    return picked[0], picked[1], picked[2]


def load_calendar(card_date: date, *, offline: bool = False) -> tuple[tuple[CalendarItem, ...], list[str]]:
    notes: list[str] = []
    items = list(session_items(card_date))
    ff_failed = False
    macros: list[CalendarItem] = []
    try:
        if _offline_requested(offline):
            payload = json.loads(_read_fixture("ff_calendar_thisweek.json"))
        else:
            from preopen_card.httputil import fetch_json
            from preopen_card.sources import FF_CALENDAR_URL

            payload = fetch_json(FF_CALENDAR_URL)
        macros = parse_ff_calendar(payload, card_date)
    except Exception:
        ff_failed = True
        notes.append("宏观日历暂缺")
        macros = []
    items.extend(macros[:3])
    if ff_failed and not any(it.kind == "macro" for it in items):
        items.append(
            CalendarItem(
                kind="missing",
                title="数据暂缺",
                time_label="—",
                region="—",
                impact="none",
            )
        )
    if not items:
        items.append(
            CalendarItem(
                kind="missing",
                title="数据暂缺",
                time_label="—",
                region="—",
                impact="none",
            )
        )
    return tuple(items), notes


def _now_shanghai() -> datetime:
    override = os.environ.get("PREOPEN_NOW")
    if override:
        dt = datetime.fromisoformat(override)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=SHANGHAI)
        return dt.astimezone(SHANGHAI)
    return datetime.now(SHANGHAI)


def build_card_data(*, card_date: date, offline: bool = False) -> CardData:
    notes: list[str] = []
    use_off = _offline_requested(offline)
    try:
        indices = _load_indices_offline() if use_off else load_us_indices()
    except Exception:
        indices = (
            _degraded_index(INDEX_SPECS[0][0], INDEX_SPECS[0][2]),
            _degraded_index(INDEX_SPECS[1][0], INDEX_SPECS[1][2]),
            _degraded_index(INDEX_SPECS[2][0], INDEX_SPECS[2][2]),
        )
        notes.append("指数暂缺")
    if any(q.status == "degraded" for q in indices):
        notes.append("部分指数降级")

    try:
        fx = _load_fx_offline() if use_off else load_fx()
    except Exception:
        fx = FxQuote(
            pair="USDCNH",
            label_zh="美元兑离岸人民币",
            last=None,
            change_pct=None,
            asof_utc=None,
            source="none",
            status="degraded",
            is_dxy_fallback=False,
        )
        notes.append("外汇暂缺")
    if fx.status == "degraded":
        notes.append("外汇降级")

    try:
        calendar_items, cal_notes = load_calendar(card_date, offline=use_off)
        notes.extend(cal_notes)
    except Exception:
        calendar_items = (
            CalendarItem(
                kind="missing",
                title="数据暂缺",
                time_label="—",
                region="—",
                impact="none",
            ),
        )
        notes.append("日历暂缺")

    try:
        headlines = _load_headlines_offline() if use_off else load_headlines()
    except Exception:
        headlines = (
            _placeholder_headline(),
            _placeholder_headline(),
            _placeholder_headline(),
        )
        notes.append("标题暂缺")
    if any(h.status == "degraded" for h in headlines):
        notes.append("部分标题降级")

    generated = _now_shanghai()
    return CardData(
        card_date=card_date,
        generated_at_shanghai=generated,
        indices=indices,
        fx=fx,
        calendar_items=calendar_items,
        headlines=headlines,
        degrade_notes=tuple(notes),
    )
