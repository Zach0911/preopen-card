from __future__ import annotations

from datetime import date

from preopen_card.calendar_util import (
    is_a_share_trading_day,
    is_nyse_full_holiday,
    is_nyse_trading_day,
    next_a_share_trading_day,
    session_items,
)


def test_sse_new_year_2025():
    assert not is_a_share_trading_day(date(2025, 1, 1))
    assert is_a_share_trading_day(date(2025, 1, 2))


def test_sse_spring_festival_2025():
    assert not is_a_share_trading_day(date(2025, 1, 28))
    assert not is_a_share_trading_day(date(2025, 2, 4))
    assert is_a_share_trading_day(date(2025, 2, 5))


def test_weekend_closed_even_makeup_note():
    assert not is_a_share_trading_day(date(2025, 1, 26))
    assert not is_a_share_trading_day(date(2025, 2, 8))


def test_sse_2026_cny():
    assert not is_a_share_trading_day(date(2026, 2, 17))
    assert is_a_share_trading_day(date(2026, 2, 24))


def test_next_from_weekend():
    assert next_a_share_trading_day(date(2026, 9, 5)) == date(2026, 9, 7)


def test_nyse_independence_observed_2026():
    assert is_nyse_full_holiday(date(2026, 7, 3))
    assert not is_nyse_trading_day(date(2026, 7, 3))
    assert is_nyse_trading_day(date(2026, 7, 2))


def test_session_items_weekday():
    items = session_items(date(2026, 9, 2))
    assert items[0].title == "A股今日开市"
    # 2026-09-01 is Tuesday, NYSE open unless holiday
    assert all("美股隔夜休市" != i.title for i in items)


def test_session_items_us_weekend_overnight():
    # Monday card date -> Sunday overnight US closed
    items = session_items(date(2026, 9, 7))
    titles = [i.title for i in items]
    assert "美股隔夜休市" in titles
