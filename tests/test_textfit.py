from __future__ import annotations

from preopen_card.fonts import load_font_set
from preopen_card.textfit import format_pct, format_price, truncate_text, wrap_text


def test_format_pct():
    assert format_pct(None) == "—"
    assert format_pct(0.42).startswith("+0.42")
    assert format_pct(-0.42).startswith("-0.42")
    assert format_pct(0.0) == "0.00%"


def test_format_price_missing():
    assert format_price(None) == "数据暂缺"


def test_long_chinese_truncate():
    fonts = load_font_set()
    font = fonts.regular(24)
    long = "这是一条非常非常长的中文标题需要被截断以免画出画布" * 3
    out = truncate_text(long, font, 400)
    assert out.endswith("…")
    assert font.getbbox(out)[2] <= 400 + 2


def test_wrap_mixed():
    fonts = load_font_set()
    font = fonts.regular(24)
    lines = wrap_text("标普500 gained overnight after ISM data 发布", font, 280)
    assert len(lines) >= 2
