"""A-share / NYSE session calendar and FF macro filtering."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from preopen_card.fonts import DATA_DIR, repo_root
from preopen_card.models import CalendarItem

SHANGHAI = ZoneInfo("Asia/Shanghai")
NY = ZoneInfo("America/New_York")

_HIGH_COUNTRIES = {"USD", "CNY", "CHN", "CHINA"}


def _data_dir() -> Path:
    return repo_root() / "data"


@lru_cache(maxsize=4)
def _load_holiday_dates(filename: str) -> set[date]:
    path = _data_dir() / filename
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: set[date] = set()
    for key, value in raw.items():
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, str) and len(item) >= 10 and item[4] == "-":
                out.add(date.fromisoformat(item[:10]))
    return out


def sse_holidays() -> set[date]:
    return _load_holiday_dates("cn_sse_holidays.json")


def nyse_holidays() -> set[date]:
    return _load_holiday_dates("us_nyse_holidays.json")


def is_weekend(d: date) -> bool:
    return d.weekday() >= 5


def is_a_share_trading_day(d: date) -> bool:
    if is_weekend(d):
        return False
    return d not in sse_holidays()


def is_nyse_full_holiday(d: date) -> bool:
    return d in nyse_holidays()


def is_nyse_trading_day(d: date) -> bool:
    if is_weekend(d):
        return False
    return not is_nyse_full_holiday(d)


def next_a_share_trading_day(d: date) -> date:
    cur = d
    for _ in range(40):
        if is_a_share_trading_day(cur):
            return cur
        cur += timedelta(days=1)
    return cur


def session_items(card_date: date) -> list[CalendarItem]:
    items: list[CalendarItem] = []
    if is_a_share_trading_day(card_date):
        items.append(
            CalendarItem(
                kind="session",
                title="A股今日开市",
                time_label="全天",
                region="CN",
                impact="none",
            )
        )
    else:
        reason = "周末" if is_weekend(card_date) else "节假日休市"
        items.append(
            CalendarItem(
                kind="session",
                title=f"A股休市（{reason}）",
                time_label="全天",
                region="CN",
                impact="none",
            )
        )
    overnight = card_date - timedelta(days=1)
    if not is_nyse_trading_day(overnight):
        items.append(
            CalendarItem(
                kind="session",
                title="美股隔夜休市",
                time_label="全天",
                region="US",
                impact="none",
            )
        )
    return items


def _parse_ff_when(item: dict[str, Any]) -> datetime | None:
    for key in ("date", "datetime", "time", "timestamp"):
        val = item.get(key)
        if not val:
            continue
        if isinstance(val, (int, float)):
            ts = float(val)
            if ts > 1e12:
                ts /= 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        if isinstance(val, str):
            text = val.strip()
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            try:
                dt = datetime.fromisoformat(text)
            except ValueError:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
    return None


def parse_ff_calendar(payload: Any, card_date: date) -> list[CalendarItem]:
    rows: list[Any]
    if isinstance(payload, dict):
        rows = payload.get("events") or payload.get("calendar") or payload.get("data") or []
    elif isinstance(payload, list):
        rows = payload
    else:
        return []

    out: list[CalendarItem] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        country = str(raw.get("country") or raw.get("currency") or "").strip().upper()
        if country not in _HIGH_COUNTRIES:
            continue
        impact = str(raw.get("impact") or raw.get("volatility") or "").strip().lower()
        if impact != "high":
            continue
        when = _parse_ff_when(raw)
        if when is None:
            continue
        local_day = when.astimezone(SHANGHAI).date()
        if local_day != card_date:
            continue
        title = str(raw.get("title") or raw.get("event") or "").strip()
        if not title:
            continue
        clock = when.astimezone(SHANGHAI).strftime("%H:%M")
        region = "US" if country == "USD" else "CN"
        out.append(
            CalendarItem(
                kind="macro",
                title=title,
                time_label=clock,
                region=region,
                impact="high",
            )
        )
    out.sort(key=lambda it: it.time_label)
    return out[:3]
