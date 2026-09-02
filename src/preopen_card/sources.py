"""Free public sources: Yahoo chart, Stooq CSV, ForexFactory, RSS."""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

from preopen_card.httputil import FetchError, fetch_json, fetch_text
from preopen_card.models import FxQuote, Headline, IndexQuote, QuoteStatus

YAHOO_CHART = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"
)
STOOQ_CSV = "https://stooq.com/q/l/?s={symbol}&f=sd2t2ohlcv&h&e=csv"
FF_CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

RSS_FEEDS: tuple[tuple[str, str], ...] = (
    (
        "https://news.google.com/rss/search?q=%E7%BE%8E%E8%82%A1%20OR%20%E7%BE%8E%E8%81%94%E5%82%A8%20OR%20%E5%86%9C%E4%B8%9A%E9%83%A8&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
        "Google News",
    ),
    ("https://feeds.bbci.co.uk/news/business/rss.xml", "BBC"),
    ("https://finance.yahoo.com/news/rssindex", "Yahoo"),
)

INDEX_SPECS: tuple[tuple[str, str, str], ...] = (
    ("^GSPC", "^spx", "标普500"),
    ("^DJI", "^dji", "道琼斯"),
    ("^IXIC", "^ixic", "纳斯达克"),
)

FX_CHAIN: tuple[tuple[str, str, str, bool], ...] = (
    ("USDCNH=X", "USDCNH", "美元兑离岸人民币", False),
    ("CNH=X", "USDCNH", "美元兑离岸人民币", False),
    ("USDCNY=X", "USDCNY", "美元兑离岸人民币", False),
    ("DX-Y.NYB", "DXY", "美元指数（离岸人民币暂缺）", True),
)

STOCK_PITCH_WORDS = (
    "买入",
    "卖出",
    "加仓",
    "减仓",
    "目标价",
    "price target",
    "upgrade",
    "downgrade",
    "强烈推荐",
    "必看黑马",
    "涨停",
)

_PITCH_RE = re.compile(
    "|".join(re.escape(w) for w in STOCK_PITCH_WORDS),
    re.IGNORECASE,
)


def parse_yahoo_chart(payload: dict[str, Any]) -> tuple[float, float, datetime]:
    try:
        result = payload["chart"]["result"][0]
    except (KeyError, IndexError, TypeError) as exc:
        raise FetchError("yahoo chart missing result") from exc
    meta = result.get("meta") or {}
    timestamps = result.get("timestamp") or []
    closes: list[Any] = []
    try:
        closes = (result.get("indicators") or {}).get("quote", [{}])[0].get("close") or []
    except (IndexError, TypeError, AttributeError):
        closes = []

    def _last_close(values: list[Any]) -> float | None:
        for item in reversed(values):
            if item is not None:
                try:
                    return float(item)
                except (TypeError, ValueError):
                    continue
        return None

    last: float | None = None
    rmp = meta.get("regularMarketPrice")
    if rmp is not None:
        try:
            last = float(rmp)
        except (TypeError, ValueError):
            last = None
    if last is None:
        last = _last_close(closes)

    prev: float | None = None
    cpc = meta.get("chartPreviousClose")
    if cpc is not None:
        try:
            prev = float(cpc)
        except (TypeError, ValueError):
            prev = None
    if prev is None:
        numeric = [float(x) for x in closes if x is not None]
        if len(numeric) >= 2:
            prev = numeric[-2]
        elif meta.get("previousClose") is not None:
            try:
                prev = float(meta["previousClose"])
            except (TypeError, ValueError):
                prev = None

    if last is None or prev is None or prev <= 0:
        raise FetchError("yahoo chart missing close")

    ts = None
    if timestamps:
        ts = timestamps[-1]
    elif meta.get("regularMarketTime") is not None:
        ts = meta["regularMarketTime"]
    if ts is None:
        asof = datetime.now(timezone.utc)
    else:
        asof = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    return last, prev, asof


def parse_stooq_csv(text: str) -> tuple[float, float | None, datetime]:
    lines = [ln.strip() for ln in text.replace("\r", "").split("\n") if ln.strip()]
    if len(lines) < 2:
        raise FetchError("stooq empty")
    rows = lines[1:]
    parsed: list[tuple[float, datetime]] = []
    for row in rows:
        parts = [p.strip() for p in row.split(",")]
        if len(parts) < 7:
            continue
        close_s = parts[6]
        if close_s.upper() in {"N/A", "N/D", ""}:
            continue
        try:
            close = float(close_s)
        except ValueError:
            continue
        date_s = parts[1] if len(parts) > 1 else ""
        time_s = parts[2] if len(parts) > 2 else "00:00:00"
        asof = datetime.now(timezone.utc)
        try:
            asof = datetime.fromisoformat(f"{date_s}T{time_s}").replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                asof = datetime.strptime(date_s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        parsed.append((close, asof))
    if not parsed:
        raise FetchError("stooq no close")
    last, asof = parsed[-1]
    prev = parsed[-2][0] if len(parsed) >= 2 else None
    return last, prev, asof


def _index_from_yahoo(payload: dict[str, Any], yahoo_symbol: str, name_zh: str) -> IndexQuote:
    last, prev, asof = parse_yahoo_chart(payload)
    change = (last / prev - 1.0) * 100.0
    return IndexQuote(
        symbol=yahoo_symbol,
        name_zh=name_zh,
        last=last,
        prev_close=prev,
        change_pct=change,
        asof_utc=asof,
        source="yahoo",
        status="ok",
    )


def _index_from_stooq(text: str, yahoo_symbol: str, name_zh: str) -> IndexQuote:
    last, prev, asof = parse_stooq_csv(text)
    if prev is None or prev <= 0:
        change = None
        status: QuoteStatus = "degraded"
    else:
        change = (last / prev - 1.0) * 100.0
        status = "ok"
    return IndexQuote(
        symbol=yahoo_symbol,
        name_zh=name_zh,
        last=last,
        prev_close=prev,
        change_pct=change,
        asof_utc=asof,
        source="stooq",
        status=status,
    )


def _degraded_index(yahoo_symbol: str, name_zh: str) -> IndexQuote:
    return IndexQuote(
        symbol=yahoo_symbol,
        name_zh=name_zh,
        last=None,
        prev_close=None,
        change_pct=None,
        asof_utc=None,
        source="none",
        status="degraded",
    )


def load_one_index(yahoo_symbol: str, stooq_symbol: str, name_zh: str) -> IndexQuote:
    try:
        url = YAHOO_CHART.format(symbol=quote(yahoo_symbol, safe=""))
        payload = fetch_json(url)
        return _index_from_yahoo(payload, yahoo_symbol, name_zh)
    except FetchError:
        pass
    try:
        url = STOOQ_CSV.format(symbol=quote(stooq_symbol, safe=""))
        text = fetch_text(url)
        return _index_from_stooq(text, yahoo_symbol, name_zh)
    except FetchError:
        return _degraded_index(yahoo_symbol, name_zh)


def load_us_indices() -> tuple[IndexQuote, IndexQuote, IndexQuote]:
    a = load_one_index(*INDEX_SPECS[0])
    b = load_one_index(*INDEX_SPECS[1])
    c = load_one_index(*INDEX_SPECS[2])
    return a, b, c


def _fx_from_chart(payload: dict[str, Any], pair: str, label_zh: str, is_dxy: bool) -> FxQuote:
    last, prev, asof = parse_yahoo_chart(payload)
    change = (last / prev - 1.0) * 100.0
    return FxQuote(
        pair=pair,
        label_zh=label_zh,
        last=last,
        change_pct=change,
        asof_utc=asof,
        source="yahoo",
        status="ok",
        is_dxy_fallback=is_dxy,
    )


def load_fx() -> FxQuote:
    for symbol, pair, label, is_dxy in FX_CHAIN:
        try:
            url = YAHOO_CHART.format(symbol=quote(symbol, safe=""))
            payload = fetch_json(url)
            return _fx_from_chart(payload, pair, label, is_dxy)
        except FetchError:
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


def _strip_source_suffix(title: str) -> str:
    title = re.sub(r"\s+-\s+Yahoo Finance\s*$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+-\s+BBC News\s*$", "", title, flags=re.IGNORECASE)
    return title.strip()


def _clean_title(raw: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", "", raw or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return _strip_source_suffix(text)


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    q = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if not k.lower().startswith("utm_")
    ]
    clean = parsed._replace(query=urlencode(q), fragment="")
    return urlunparse(clean)


def _is_http_url(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")


def parse_rss_items(xml_text: str, source_name: str) -> list[Headline]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items: list[Headline] = []
    nodes = list(root.findall(".//item"))
    if not nodes:
        nodes = list(root.findall(".//atom:entry", ns))
    for node in nodes:
        title_el = node.find("title")
        if title_el is None:
            title_el = node.find("atom:title", ns)
        title = _clean_title("".join(title_el.itertext()) if title_el is not None else "")
        link = ""
        link_el = node.find("link")
        if link_el is not None:
            link = (link_el.get("href") or (link_el.text or "")).strip()
        if not link:
            atom_link = node.find("atom:link", ns)
            if atom_link is not None:
                link = (atom_link.get("href") or "").strip()
        guid = node.find("guid")
        if not link and guid is not None and (guid.text or "").startswith("http"):
            link = guid.text.strip()
        if not title or not _is_http_url(link):
            continue
        if _PITCH_RE.search(title):
            continue
        items.append(
            Headline(
                title=title,
                url=normalize_url(link),
                source_name=source_name,
                status="ok",
            )
        )
    return items


def _placeholder_headline() -> Headline:
    return Headline(title="数据暂缺", url="", source_name="—", status="degraded")


def load_headlines() -> tuple[Headline, Headline, Headline]:
    picked: list[Headline] = []
    seen: set[str] = set()
    for url, name in RSS_FEEDS:
        if len(picked) >= 3:
            break
        try:
            xml_text = fetch_text(url)
        except FetchError:
            continue
        for item in parse_rss_items(xml_text, name):
            key = item.url
            if key in seen:
                continue
            seen.add(key)
            picked.append(item)
            if len(picked) >= 3:
                break
    while len(picked) < 3:
        picked.append(_placeholder_headline())
    return picked[0], picked[1], picked[2]
