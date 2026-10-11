#!/usr/bin/env python3
"""spots.json（hana.v == "rec"）→ 閲覧専用の公開版 おすすめマップ
  guide/map.html          … status が ◎ のお店だけ（ホームページに埋め込む本番用。◎が0件なら作らない）
  guide/map-preview.html  … 候補も含む下書き（noindex・「確認中」の札つき。デザイン確認と埋め込みテスト用）
  guide/map3d.html / map3d-preview.html … 同じお店を地形の3D地図にのせた版（hana_public3d.tpl.html。MapLibre＋地理院の標高タイル。
                                          建物は OpenFreeMap のベクトルタイル、橋・灯台・防波堤は structures.json）
◎にできるのはヤヌキだけ。埋め込み: <iframe src=".../guide/map.html?embed=1"> """
import json, pathlib, sys

HERE = pathlib.Path(__file__).parent
OUT = HERE / "guide"
KEEPER = "家守"  # 名前を出すなら "家守・華さん" に変える
WD = "月火水木金土日"
COLOR = {"食べる": "#0A5A8C", "買う": "#8A5A00", "困ったとき": "#3E7C59"}
FG = {"食べる": "#fff", "買う": "#fff", "困ったとき": "#fff"}
EXAG = 1  # 3D版の高さの強調（倍）。1＝実寸（2026-10-11 ヤヌキ指示）。ページの注記も連動する
EXAGNOTE = "土地と建物の高さは実寸です。" if EXAG == 1 else f"土地と建物の高さは、わかりやすいように{EXAG}倍に強調しています。"
_st = HERE / "structures.json"  # 橋・灯台・防波堤（hana_structures_fetch.py が作る。無ければ構造物なしで作る）
STRUCT = _st.read_text(encoding="utf-8") if _st.exists() else '{"type":"FeatureCollection","features":[]}'
# 3D版だけは宿泊者向けなので A邸の位置を出す（2026-10-11 ヤヌキ指示）。座標は home.local.json から。無ければ出さない。平面版には入れない
_hm = HERE / "home.local.json"
_h = json.load(open(_hm)) if _hm.exists() else None
HOME = json.dumps({"name": "三浦A邸", "lat": round(_h["lat"], 5), "lon": round(_h["lon"], 5)}, ensure_ascii=False) if _h else "null"
HOMENOTE = "赤い家のピンが三浦A邸です。" if _h else ""
HIDE_FLAG = ("今はおすすめしない", "閉店・移転した")

def rows(doc, include_draft):
    out = []
    for s in doc["spots"]:
        h = s.get("hana") or {}
        if h.get("v") != "rec": continue
        if s.get("status") == "休止": continue
        if s.get("status") != "◎" and not include_draft: continue
        if (h.get("flag") or {}).get("type") in HIDE_FLAG: continue
        closed = s.get("closed")
        out.append({
            "id": s["id"], "name": s["name"], "cat": s["category"], "area": s.get("area") or "",
            "lat": s.get("lat"), "lon": s.get("lon"),
            "c": " ／ ".join(x for x in [h.get("comment") or ""] + [m["text"] for m in h.get("more", [])] if x),
            "note": s.get("note") or "", "hours": s.get("hours") or "",
            "closed": ("／".join(WD[i] for i in closed) + "休み") if closed else (s.get("closed_note") or ""),
            "url": (s.get("links") or {}).get("official") or ((s.get("sources") or [{}])[0].get("url") or ""),
            "color": COLOR.get(s["category"], "#555"), "fg": FG.get(s["category"], "#fff"),
            "r": h.get("rating") or 0, "rm": h.get("rating_max") or 5, "w": h.get("when") or [],
            "draft": s.get("status") != "◎",
        })
    return out

def render(tpl, data, draft, flat=""):
    banner = '<p class="draft">下書きです。確認中のお店を含みます。営業時間などは、変わっていることがあります。</p>' if draft else ""
    robots = '<meta name="robots" content="noindex,nofollow">' if draft else ""
    return (tpl.replace("%%DATA%%", json.dumps(data, ensure_ascii=False)).replace("%%KEEPER%%", KEEPER)
               .replace("%%DRAFT%%", banner).replace("%%ROBOTS%%", robots)
               .replace("%%FLAT%%", flat).replace("%%EXAGNOTE%%", EXAGNOTE).replace("%%EXAG%%", str(EXAG)).replace("%%STRUCT%%", STRUCT)
               .replace("%%HOME%%", HOME).replace("%%HOMENOTE%%", HOMENOTE))

def main():
    doc = json.load(open(HERE / "spots.json"))
    tpl = (HERE / "hana_public.tpl.html").read_text(encoding="utf-8")
    tpl3 = (HERE / "hana_public3d.tpl.html").read_text(encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    pre = rows(doc, True)
    (OUT / "map-preview.html").write_text(render(tpl, pre, True), encoding="utf-8")
    (OUT / "map3d-preview.html").write_text(render(tpl3, pre, True, "map-preview.html"), encoding="utf-8")
    print(f"guide/map-preview.html・map3d-preview.html: {len(pre)}件（下書き）")
    fin = rows(doc, False)
    if fin:
        (OUT / "map.html").write_text(render(tpl, fin, False), encoding="utf-8")
        (OUT / "map3d.html").write_text(render(tpl3, fin, False, "map.html"), encoding="utf-8")
        print(f"guide/map.html・map3d.html: {len(fin)}件（◎のみ）")
    else:
        print("guide/map.html: ◎が0件のため作りません（ヤヌキが◎にしたら作られます）")

if __name__ == "__main__":
    main()
