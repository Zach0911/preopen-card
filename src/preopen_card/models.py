"""Frozen dataclasses for the preopen card. No I/O."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

QuoteStatus = Literal["ok", "degraded"]


@dataclass(frozen=True)
class IndexQuote:
    symbol: str
    name_zh: str
    last: float | None
    prev_close: float | None
    change_pct: float | None
    asof_utc: datetime | None
    source: str
    status: QuoteStatus


@dataclass(frozen=True)
class FxQuote:
    pair: str
    label_zh: str
    last: float | None
    change_pct: float | None
    asof_utc: datetime | None
    source: str
    status: QuoteStatus
    is_dxy_fallback: bool


@dataclass(frozen=True)
class CalendarItem:
    kind: Literal["session", "macro", "missing"]
    title: str
    time_label: str
    region: str
    impact: Literal["high", "medium", "none"]


@dataclass(frozen=True)
class Headline:
    title: str
    url: str
    source_name: str
    status: QuoteStatus


@dataclass(frozen=True)
class CardData:
    card_date: date
    generated_at_shanghai: datetime
    indices: tuple[IndexQuote, IndexQuote, IndexQuote]
    fx: FxQuote
    calendar_items: tuple[CalendarItem, ...]
    headlines: tuple[Headline, Headline, Headline]
    degrade_notes: tuple[str, ...]
