"""Pillow canvas: 1080×1440 pre-open card."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw

from preopen_card.fonts import load_font_set
from preopen_card.models import CalendarItem, CardData, FxQuote, Headline, IndexQuote
from preopen_card.textfit import format_pct, format_price, truncate_text, wrap_text

WIDTH = 1080
HEIGHT = 1440
MARGIN = 64
BG = (0x0B, 0x12, 0x20)
UP = (0x3D, 0xDC, 0x97)
DOWN = (0xE8, 0x5D, 0x4C)
GOLD = (0xD4, 0xA0, 0x17)
TEXT = (0xE8, 0xEE, 0xF7)
MUTED = (0x8B, 0x98, 0xAB)
PANEL = (0x12, 0x1C, 0x30)
DISCLAIMER = "本图为公开信息整理，不构成投资建议，不指导个股买卖。"

WEEKDAYS = "星期一 星期二 星期三 星期四 星期五 星期六 星期日".split()


def _pct_color(pct: float | None) -> tuple[int, int, int]:
    if pct is None:
        return MUTED
    if pct > 0:
        return UP
    if pct < 0:
        return DOWN
    return MUTED


def _round_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int],
) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def _header_date(d: date) -> str:
    return f"{d.year}年{d.month}月{d.day}日 {WEEKDAYS[d.weekday()]}"


def _draw_section_title(
    draw: ImageDraw.ImageDraw,
    y: int,
    title: str,
    font,
) -> int:
    x = MARGIN
    draw.rectangle((x, y + 8, x + 8, y + 32), fill=GOLD)
    draw.text((x + 20, y), title, font=font, fill=GOLD)
    bbox = font.getbbox(title)
    return y + (bbox[3] - bbox[1]) + 18


def render_card(data: CardData) -> Image.Image:
    fonts = load_font_set()
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    title_font = fonts.bold(56)
    date_font = fonts.regular(26)
    section_font = fonts.bold(28)
    name_font = fonts.regular(28)
    num_font = fonts.bold(30)
    pct_font = fonts.bold(28)
    small_font = fonts.regular(22)
    body_font = fonts.regular(24)
    foot_font = fonts.regular(18)

    y = 44
    draw.text((MARGIN, y), "开盘卡", font=title_font, fill=GOLD)
    y += 70
    draw.text((MARGIN, y), _header_date(data.card_date), font=date_font, fill=TEXT)
    gen = data.generated_at_shanghai.strftime("%H:%M")
    gen_label = f"生成 {gen} 上海"
    gw = date_font.getbbox(gen_label)[2]
    draw.text((WIDTH - MARGIN - gw, y), gen_label, font=date_font, fill=MUTED)
    y += 48
    draw.rectangle((MARGIN, y, WIDTH - MARGIN, y + 2), fill=GOLD)
    y += 28

    y = _draw_section_title(draw, y, "隔夜美股", section_font)
    panel_top = y - 6
    row_h = 72
    panel_h = row_h * 3 + 16
    _round_rect(draw, (MARGIN - 8, panel_top, WIDTH - MARGIN + 8, panel_top + panel_h), 16, PANEL)
    y = panel_top + 12
    for quote in data.indices:
        _draw_index_row(draw, y, quote, name_font, num_font, pct_font)
        y += row_h
    y = panel_top + panel_h + 28

    y = _draw_section_title(draw, y, "外汇", section_font)
    panel_top = y - 6
    panel_h = 80
    _round_rect(draw, (MARGIN - 8, panel_top, WIDTH - MARGIN + 8, panel_top + panel_h), 16, PANEL)
    _draw_fx_row(draw, panel_top + 18, data.fx, name_font, num_font, pct_font)
    y = panel_top + panel_h + 28

    y = _draw_section_title(draw, y, "今日日历", section_font)
    cal_h = 36 + 40 * max(len(data.calendar_items), 1)
    panel_top = y - 6
    _round_rect(draw, (MARGIN - 8, panel_top, WIDTH - MARGIN + 8, panel_top + cal_h), 16, PANEL)
    cy = panel_top + 14
    inner_w = WIDTH - 2 * MARGIN - 24
    for item in data.calendar_items:
        _draw_cal_row(draw, cy, item, small_font, body_font, inner_w)
        cy += 40
    y = panel_top + cal_h + 28

    y = _draw_section_title(draw, y, "资讯", section_font)
    inner_w = WIDTH - 2 * MARGIN
    for i, hl in enumerate(data.headlines, start=1):
        y = _draw_headline(draw, y, i, hl, body_font, small_font, inner_w)
        y += 10

    # footer pinned near bottom
    footer_y = HEIGHT - 92
    draw.rectangle((MARGIN, footer_y - 18, WIDTH - MARGIN, footer_y - 16), fill=(0x1E, 0x2A, 0x40))
    lines = wrap_text(DISCLAIMER, foot_font, WIDTH - 2 * MARGIN)
    fy = footer_y
    for line in lines:
        draw.text((MARGIN, fy), line, font=foot_font, fill=MUTED)
        fy += 26
    return img


def _draw_index_row(
    draw: ImageDraw.ImageDraw,
    y: int,
    quote: IndexQuote,
    name_font,
    num_font,
    pct_font,
) -> None:
    x = MARGIN + 16
    draw.text((x, y + 16), quote.name_zh, font=name_font, fill=TEXT)
    if quote.status == "degraded" or quote.last is None:
        val = "数据暂缺"
        color = MUTED
        pct = ""
    else:
        val = format_price(quote.last, digits=2)
        color = _pct_color(quote.change_pct)
        pct = format_pct(quote.change_pct)
    vw = num_font.getbbox(val)[2]
    right = WIDTH - MARGIN - 20
    if pct:
        pw = pct_font.getbbox(pct)[2]
        draw.text((right - pw, y + 16), pct, font=pct_font, fill=color)
        draw.text((right - pw - 16 - vw, y + 14), val, font=num_font, fill=TEXT)
    else:
        draw.text((right - vw, y + 14), val, font=num_font, fill=color)


def _draw_fx_row(
    draw: ImageDraw.ImageDraw,
    y: int,
    fx: FxQuote,
    name_font,
    num_font,
    pct_font,
) -> None:
    x = MARGIN + 16
    label = truncate_text(fx.label_zh, name_font, 520)
    draw.text((x, y + 8), label, font=name_font, fill=TEXT)
    if fx.status == "degraded" or fx.last is None:
        val = "数据暂缺"
        color = MUTED
        pct = ""
        digits = 2
    else:
        digits = 2 if fx.pair == "DXY" else 4
        val = format_price(fx.last, digits=digits)
        color = _pct_color(fx.change_pct)
        pct = format_pct(fx.change_pct)
    right = WIDTH - MARGIN - 20
    vw = num_font.getbbox(val)[2]
    if pct:
        pw = pct_font.getbbox(pct)[2]
        draw.text((right - pw, y + 10), pct, font=pct_font, fill=color)
        draw.text((right - pw - 16 - vw, y + 8), val, font=num_font, fill=TEXT)
    else:
        draw.text((right - vw, y + 8), val, font=num_font, fill=color)


def _draw_cal_row(
    draw: ImageDraw.ImageDraw,
    y: int,
    item: CalendarItem,
    small_font,
    body_font,
    inner_w: int,
) -> None:
    time_s = item.time_label or "—"
    draw.text((MARGIN + 16, y + 6), time_s, font=small_font, fill=GOLD)
    title = truncate_text(item.title, body_font, inner_w - 140)
    fill = MUTED if item.kind == "missing" else TEXT
    draw.text((MARGIN + 130, y + 4), title, font=body_font, fill=fill)


def _draw_headline(
    draw: ImageDraw.ImageDraw,
    y: int,
    idx: int,
    hl: Headline,
    body_font,
    small_font,
    inner_w: int,
) -> int:
    prefix = f"{idx}. "
    title = hl.title if hl.title else "数据暂缺"
    fill = MUTED if hl.status == "degraded" else TEXT
    wrapped = wrap_text(prefix + title, body_font, inner_w)
    if len(wrapped) > 2:
        wrapped = wrapped[:2]
        wrapped[-1] = truncate_text(wrapped[-1], body_font, inner_w)
    for line in wrapped:
        draw.text((MARGIN, y), line, font=body_font, fill=fill)
        y += 32
    src = hl.source_name if hl.source_name and hl.source_name != "—" else ""
    if src and hl.url:
        draw.text((MARGIN + 28, y), src, font=small_font, fill=MUTED)
        y += 26
    elif src:
        draw.text((MARGIN + 28, y), src, font=small_font, fill=MUTED)
        y += 26
    return y


def write_png(data: CardData, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img = render_card(data)
    img.save(path, format="PNG", optimize=True)
    return path
