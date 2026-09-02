"""Mixed CJK/Latin wrap, truncate, and number formatting."""

from __future__ import annotations

from PIL import ImageDraw, ImageFont


def _text_width(font: ImageFont.FreeTypeFont, text: str) -> float:
    if not text:
        return 0.0
    bbox = font.getbbox(text)
    return float(bbox[2] - bbox[0])


def is_cjk(ch: str) -> bool:
    code = ord(ch)
    return (
        0x3400 <= code <= 0x9FFF
        or 0xF900 <= code <= 0xFAFF
        or 0x3000 <= code <= 0x303F
        or 0xFF00 <= code <= 0xFFEF
    )


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    if not text:
        return [""]
    lines: list[str] = []
    current = ""
    buf = ""  # latin word buffer

    def flush_buf() -> None:
        nonlocal current, buf
        if not buf:
            return
        trial = current + buf
        if current and _text_width(font, trial) > max_width:
            lines.append(current)
            current = buf
        else:
            current = trial
        buf = ""

    for ch in text.replace("\r", ""):
        if ch == "\n":
            flush_buf()
            lines.append(current)
            current = ""
            continue
        if is_cjk(ch):
            flush_buf()
            trial = current + ch
            if current and _text_width(font, trial) > max_width:
                lines.append(current)
                current = ch
            else:
                current = trial
        else:
            if ch == " ":
                buf += ch
                flush_buf()
            else:
                buf += ch
    flush_buf()
    if current or not lines:
        lines.append(current)
    return lines or [""]


def truncate_text(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    ellipsis: str = "…",
) -> str:
    if _text_width(font, text) <= max_width:
        return text
    ell_w = _text_width(font, ellipsis)
    if ell_w >= max_width:
        return ellipsis
    out = ""
    for ch in text:
        trial = out + ch
        if _text_width(font, trial) + ell_w > max_width:
            break
        out = trial
    return out + ellipsis


def format_pct(pct: float | None) -> str:
    if pct is None:
        return "—"
    if abs(pct) < 0.005:
        return "0.00%"
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.2f}%"


def format_price(value: float | None, *, digits: int = 2) -> str:
    if value is None:
        return "数据暂缺"
    return f"{value:,.{digits}f}"


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    max_width: int,
    line_gap: int = 6,
    max_lines: int = 3,
) -> int:
    x, y = xy
    lines = wrap_text(text, font, max_width)
    if len(lines) > max_lines:
        kept = lines[:max_lines]
        kept[-1] = truncate_text(kept[-1], font, max_width)
        lines = kept
    for i, line in enumerate(lines):
        draw.text((x, y), line, font=font, fill=fill)
        bbox = font.getbbox(line or " ")
        y += (bbox[3] - bbox[1]) + line_gap
        if i + 1 >= max_lines:
            break
    return y
