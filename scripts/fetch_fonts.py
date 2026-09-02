#!/usr/bin/env python3
"""Download Noto Sans SC (OFL), sha256-check, instantiate Regular/Bold, subset."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "fonts"

# Subset variable TTF from notofonts/noto-cjk (OFL-1.1)
SOURCE_URL = (
    "https://github.com/notofonts/noto-cjk/raw/main/"
    "Sans/Variable/TTF/Subset/NotoSansSC-VF.ttf"
)
SOURCE_SHA256 = "d68bafcb48a2707749396aa12bbbd833cb70401f3a9a689fd2902c7e0d295964"
USER_AGENT = "preopen-card/0.1 (+https://github.com/Zach0911/preopen-card; font-fetch; OFL)"


def _gb2312_level1() -> str:
    chars: list[str] = []
    for qu in range(16, 56):
        for wei in range(1, 95):
            try:
                ch = bytes([qu + 0xA0, wei + 0xA0]).decode("gb2312")
            except UnicodeDecodeError:
                continue
            chars.append(ch)
    return "".join(chars)


def subset_text() -> str:
    extra = (
        "开盘卡数据暂缺标普道琼斯纳斯达克美元兑离岸人民币指数今日日历资讯隔夜"
        "美股休市节假日开市全天本图为公开信息整理不构成投资建议不指导个股买卖"
        "生成于上海星期一二三四五六日年月日外汇宏观非农采购经理人就业金价原油"
        "联储降息加息财报政策关税农业部美联储央行汇率通胀增长贸易逆差顺差国债"
        "期货现货收盘上涨下跌持平波动风险市场股票证券基金债券期权商品能源科技"
        "金融银行地产消费医药汽车进出口工业服务业国内生产消费者物价生产者假期"
        "调休周末盘前盘后来源标题公开免费海报小红书转发"
        "—–…·•°%％＋－×÷±≈—–―‐‑“”‘’《》【】（）「」『』、。，．：；？！￥"
    )
    latin = "".join(chr(i) for i in range(0x20, 0x7F))
    latin1 = "".join(chr(i) for i in range(0xA0, 0x100))
    punct = "".join(chr(i) for i in list(range(0x2000, 0x206F)) + list(range(0x3000, 0x303F)) + list(range(0xFF00, 0xFFEF)))
    return latin + latin1 + punct + extra + _gb2312_level1()


def download(url: str, sha256: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != sha256:
        raise SystemExit(f"sha256 mismatch: got {digest} expected {sha256}")
    return data


def instantiate_and_subset(vf_path: Path, weight: int, out_path: Path, text: str) -> None:
    from fontTools.subset import Options, Subsetter
    from fontTools.varLib.instancer import instantiateVariableFont
    from fontTools.ttLib import TTFont

    font = TTFont(vf_path)
    instantiated = instantiateVariableFont(font, {"wght": weight}, inplace=False)
    tmp = out_path.with_suffix(".full.ttf")
    instantiated.save(tmp)
    instantiated.close()

    options = Options()
    options.layout_features = ["*"]
    options.glyph_names = True
    options.legacy_kern = True
    options.notdef_outline = True
    options.recommended_glyphs = True
    options.drop_tables = ["DSIG"]
    subsetter = Subsetter(options=options)
    subsetter.populate(text=text)
    work = TTFont(tmp)
    subsetter.subset(work)
    work.save(out_path)
    work.close()
    tmp.unlink(missing_ok=True)


def main() -> int:
    FONTS.mkdir(parents=True, exist_ok=True)
    cache = Path(tempfile.gettempdir()) / "NotoSansSC-VF.ttf"
    if cache.exists() and hashlib.sha256(cache.read_bytes()).hexdigest() == SOURCE_SHA256:
        print("using cached VF", cache)
        data = cache.read_bytes()
    else:
        print("downloading", SOURCE_URL)
        data = download(SOURCE_URL, SOURCE_SHA256)
        cache.write_bytes(data)
    vf_path = Path(tempfile.gettempdir()) / "preopen-NotoSansSC-VF.ttf"
    vf_path.write_bytes(data)
    text = subset_text()
    regular = FONTS / "NotoSansSC-Regular.subset.ttf"
    bold = FONTS / "NotoSansSC-Bold.subset.ttf"
    print("instantiating Regular 400")
    instantiate_and_subset(vf_path, 400, regular, text)
    print("instantiating Bold 700")
    instantiate_and_subset(vf_path, 700, bold, text)
    for p in (regular, bold):
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        print(f"wrote {p} {p.stat().st_size} bytes sha256={digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
