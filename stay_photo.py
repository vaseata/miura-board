#!/usr/bin/env python3
"""滞在ガイドの「撮影予定」の枠に、撮った写真を入れる。

使い方:
  python3 stay_photo.py <key> <写真ファイル>     … 1枚入れる（位置情報を消し、長辺1600pxに縮めて保存）
  python3 stay_photo.py --list                  … まだ撮っていない枠の一覧（house_faq/photo_list.md も書き直す）

入れたあとは `python3 stay_build.py --demo` で作り直す。
- 保存先は stay-react/public/photos/<key>.jpg（stay_build.py がここから stay/img/ にコピーする）
- 写してはいけないもの：外観・玄関のキーボックス・表札や番地・郵便受け・Wi-Fiのパスワードの紙・住人の顔や名前
"""
import pathlib, sys
from PIL import Image, ImageOps

HERE = pathlib.Path(__file__).parent
PHOTOS = HERE / "stay-react" / "public" / "photos"
CAUTION = {"genkan": "キーボックスと番号が写っていないか", "kutsu": "玄関の外が写っていないか",
           "takuhai": "宛名・住所が写っていないか", "parkroute": "家の外観・表札が写っていないか"}

def slots():
    from stay_pages import PAGES
    seen = {}
    for slug, sp in PAGES.items():
        for b in sp["blocks"]:
            items = [(b[1], b[3])] if b[0] == "photo" else ([(k, c) for k, _a, c in b[1]] if b[0] == "photos" else [])
            for k, cap in items:
                seen.setdefault(k, (cap, []))[1].append(f"{slug}.html（{sp['title']}）")
    return seen

def list_missing():
    rows = [(k, cap, pages) for k, (cap, pages) in slots().items() if not (PHOTOS / f"{k}.jpg").exists()]
    lines = ["# 撮影リスト（滞在ガイドの「撮影予定」の枠）", "",
             "`python3 stay_photo.py --list` が書き直す。撮ったら `python3 stay_photo.py <key> <写真>` → `python3 stay_build.py --demo`。", "",
             f"残り {len(rows)} 枚。", "", "| key | 撮るもの | 載るページ | 気をつけること |", "|---|---|---|---|"]
    for k, cap, pages in rows:
        lines.append(f"| `{k}` | {cap} | {'、'.join(pages)} | {CAUTION.get(k, '')} |")
    (HERE / "house_faq" / "photo_list.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

def add(key, src):
    known = slots()
    if key not in known:
        sys.exit(f"枠が見つかりません: {key}（`--list` で key を確かめる）")
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")   # 向きを直してから、EXIF（位置情報）を捨てる
    im.thumbnail((1600, 1600))
    PHOTOS.mkdir(parents=True, exist_ok=True)
    out = PHOTOS / f"{key}.jpg"
    im.save(out, quality=82, optimize=True)                       # exif を渡さないので位置情報は残らない
    print(f"{out} に入れました（{im.width}×{im.height}）。枠：{known[key][0]}")
    if key in CAUTION:
        print(f"⚠️ 公開前に目で確かめる：{CAUTION[key]}")

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--list":
        list_missing()
    elif len(sys.argv) == 3:
        add(sys.argv[1], sys.argv[2])
    else:
        print(__doc__)
