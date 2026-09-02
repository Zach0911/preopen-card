"""CLI: python -m preopen_card [--date YYYY-MM-DD] [--out PATH]."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from preopen_card import __version__
from preopen_card.assemble import build_card_data, resolve_card_date
from preopen_card.render import write_png

SHANGHAI = ZoneInfo("Asia/Shanghai")
DEFAULT_OUT = Path("out/card.png")


def _parse_date(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DD") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="preopen-card",
        description="Generate a 1080×1440 开盘卡 PNG from public market information.",
    )
    parser.add_argument("--date", type=_parse_date, default=None, help="card date YYYY-MM-DD (Asia/Shanghai)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output PNG path (default: out/card.png)")
    parser.add_argument("--version", action="version", version=f"preopen-card {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    now = datetime.now(SHANGHAI)
    if os.environ.get("PREOPEN_NOW"):
        dt = datetime.fromisoformat(os.environ["PREOPEN_NOW"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=SHANGHAI)
        now = dt.astimezone(SHANGHAI)
    card_date = resolve_card_date(now, args.date)
    offline = os.environ.get("PREOPEN_OFFLINE") == "1"
    try:
        data = build_card_data(card_date=card_date, offline=offline)
        write_png(data, Path(args.out))
    except Exception as exc:  # noqa: BLE001
        print(f"failed to write PNG: {exc}", file=sys.stderr)
        return 2
    out_path = Path(args.out)
    if not out_path.is_file():
        print("failed to write PNG: missing file", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
