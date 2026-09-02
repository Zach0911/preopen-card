# Preopen Card / 开盘卡

<p align="center">
  <img src="docs/latest.png" alt="开盘卡 latest" width="360" />
</p>

One command → a **1080×1440** PNG briefing for the A-share open: overnight US indices, USD/CNH (DXY fallback), session/macro calendar, three headlines with URLs.

一条命令生成开盘前海报：隔夜美股三大指数、美元兑离岸人民币（或美元指数兜底）、当日日历、三条带链接的标题。给小红书转发，给开发者 star。

MIT. Public information only. **Not investment advice. No stock picks. No broker. No LLM. No API keys.**

公开信息整理，**不是投资建议**，不点名个股买卖，不下单。

## Install / 安装

Python 3.11+. Image output uses Pillow only; HTTP uses stdlib `urllib`.

```bash
git clone https://github.com/Zach0911/preopen-card.git
cd preopen-card
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m preopen_card
# → out/card.png
```

```bash
python -m preopen_card --date 2026-09-02 --out docs/latest.png
```

Offline (fixtures, no network):

```bash
PREOPEN_OFFLINE=1 python -m preopen_card --date 2026-09-02 --out docs/latest.png
```

Exit `0` if a PNG was written (even when some fields show 数据暂缺). Exit `2` only if the PNG cannot be written.

## Layout / 版式

- 1080×1440, background `#0B1220`, up `#3DDC97`, down `#E85D4C`, gold `#D4A017`
- 64px side margins
- Header: **开盘卡** + date
- Blocks: 3 US indices, FX, calendar, 3 headlines
- Footer: `本图为公开信息整理，不构成投资建议，不指导个股买卖。`

Chinese on Ubuntu: vendored Noto Sans SC subsets under `fonts/` (OFL). Rebuild with `python scripts/fetch_fonts.py`.

## Disclaimer / 免责声明

This image is a rearrangement of **publicly available** market data and news headlines. It is **not** investment advice, not a recommendation to buy or sell any security, and not a substitute for your own research. Data sources can fail; missing fields render as **数据暂缺** rather than invented numbers.

本图仅为公开信息整理，不构成投资建议，不指导个股买卖。源站失败时显示「数据暂缺」，绝不编造宏观数字或荐股。

## Xiaohongshu / 小红书怎么发

1. Run `python -m preopen_card` on a weekday morning (or use the committed `docs/latest.png`).
2. Upload the PNG; Xiaohongshu prefers 3:4 — this file is already 1080×1440.
3. Caption idea: date + “隔夜美股 / 汇率 / 日历” + **不是投资建议**.
4. Do not add ticker buy/sell calls in the caption. Do not crop away the footer disclaimer.
5. If a block says 数据暂缺, say so — do not type fake CPI/NFP prints on top of the image.

## Daily GitHub Action

`.github/workflows/daily.yml` runs `30 23 * * 0-4` (Sun–Thu 23:30 UTC = **07:30 Asia/Shanghai** on weekdays), writes `docs/latest.png`, commits with `contents: write`.

## Tests

```bash
PREOPEN_OFFLINE=1 pytest
```

## License

MIT. Fonts: SIL Open Font License 1.1 (Noto Sans SC). See `LICENSE` and `fonts/README.md`.
