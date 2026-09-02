# Fonts (Noto Sans SC, SIL Open Font License 1.1)

This folder ships **subset** TrueType files so GitHub Actions Ubuntu can paint Simplified Chinese without `apt` font packages.

| File | Role | Source |
| --- | --- | --- |
| `NotoSansSC-Regular.subset.ttf` | UI / body | Noto Sans SC VF `wght=400` |
| `NotoSansSC-Bold.subset.ttf` | Title / numbers | Noto Sans SC VF `wght=700` |

Upstream variable font (not vendored, ~17 MB):

```
https://github.com/notofonts/noto-cjk/raw/main/Sans/Variable/TTF/Subset/NotoSansSC-VF.ttf
sha256: d68bafcb48a2707749396aa12bbbd833cb70401f3a9a689fd2902c7e0d295964
```

License: [OFL-1.1](https://github.com/notofonts/noto-cjk/blob/main/LICENSE). Reserved names follow Noto.

## Subset coverage

Glyphs kept: Basic Latin, Latin-1, general + CJK punctuation, fullwidth forms, GB2312 level-1 Han, plus product strings (开盘卡 / 数据暂缺 / disclaimer). Live RSS may still hit missing glyphs (tofu) for rare characters; that is acceptable. Numbers and the poster chrome must never tofu.

## Rebuild

```bash
python scripts/fetch_fonts.py
```

The script downloads the VF, verifies `sha256`, instantiates Regular/Bold, then subsets. Requires `fonttools`.

If the download fails (GitHub rate limit, offline CI clone without LFS, etc.):

1. Manually place any OFL Noto Sans SC TTF named `NotoSansSC-Regular.subset.ttf` / `NotoSansSC-Bold.subset.ttf` in this directory, **or**
2. Install `fonts-noto-cjk` on Ubuntu and copy a SC TTF here.

`preopen_card.fonts` refuses to render if no file >1 KB is found, so tests fail loudly instead of emitting boxes for 开盘卡.
