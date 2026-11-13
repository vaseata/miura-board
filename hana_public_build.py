#!/usr/bin/env python3
"""spots.json（hana.v == "rec"）→ 閲覧専用の公開版 おすすめマップ
  guide/map.html          … status が ◎ のお店だけ（ホームページに埋め込む本番用。◎が0件なら作らない）
  guide/map-preview.html  … 候補も含む下書き（noindex・「確認中」の札つき。デザイン確認と埋め込みテスト用）
  guide/map3d.html / map3d-preview.html … 同じお店を地形の3D地図にのせた版（hana_public3d.tpl.html。MapLibre＋地理院の標高タイル。
                                          建物は OpenFreeMap のベクトルタイル、橋・灯台・防波堤は structures.json）
◎にできるのはヤヌキだけ。埋め込み: <iframe src=".../guide/map.html?embed=1"> """
import json, pathlib, sys
import shop_hours

HERE = pathlib.Path(__file__).parent
OUT = HERE / "guide"
KEEPER = "家守"  # 名前を出すなら "家守・華さん" に変える
WD = "月火水木金土日"
COLOR = {"食べる": "#0A5A8C", "買う": "#4F6070", "困ったとき": "#B8243A"}   # デザインシステム：海の青／墨／マグロの赤（困ったときだけ赤）
FG = {"食べる": "#fff", "買う": "#fff", "困ったとき": "#fff"}
EXAG = 1  # 3D版の高さの強調（倍）。1＝実寸（2026-10-11 ヤヌキ指示）。ページの注記も連動する
EXAGNOTE = "土地と建物の高さは実寸です。" if EXAG == 1 else f"土地と建物の高さは、わかりやすいように{EXAG}倍に強調しています。"
_st = HERE / "structures.json"  # 橋・灯台・防波堤（hana_structures_fetch.py が作る。無ければ構造物なしで作る）
STRUCT = _st.read_text(encoding="utf-8") if _st.exists() else '{"type":"FeatureCollection","features":[]}'
# A邸の位置（2026-11-13 ヤヌキ判断で変更）：guide/ の公開版には、平面・3Dとも位置を入れない。
# 位置つきの3D版は、公開しない map3d-guest.src.html（.gitignore）にだけ書く。宿泊者には share_lock.py で合言葉をかけて出す。
# 座標は home.local.json から。無ければ位置つき版は作らない
_hm = HERE / "home.local.json"
_h = json.load(open(_hm)) if _hm.exists() else None
HOME_GUEST = json.dumps({"name": "三浦A邸", "lat": round(_h["lat"], 5), "lon": round(_h["lon"], 5)}, ensure_ascii=False) if _h else None
HOMENOTE_GUEST = "赤い家のピンが三浦A邸です。"
IMAGES = json.load(open(HERE / "places.json", encoding="utf-8"))["images"]
HIDE_FLAG = ("今はおすすめしない", "閉店・移転した")

# 英語版（guide/en/map-preview.html・2026-11-14）。お店の文は spots_en.json、画面の言葉はここ。3D版はまだ日本語だけ
EN_DATA = json.load(open(HERE / "spots_en.json", encoding="utf-8")) if (HERE / "spots_en.json").exists() else {"spots": {}, "areas": {}}
WD_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
SITE = "https://vaseata.github.io/miura-board/guide/"
TXT = {
    "ja": {"T_TITLE": "三浦A邸 おすすめマップ", "T_EYEBROW": "MIURA A-TEI · 三浦A邸", "T_H1": f"<span>{KEEPER}の</span> <span>おすすめマップ</span>",
           "T_LEDE": "三崎・城ヶ島の、ごはんと買い物のお店です。気になるお店を押すと、地図の場所と、ひとことが見られます。",
           "T_BYCAT": "ジャンルで絞り込む", "T_BYSCENE": "シーンで絞り込む", "T_MAPLABEL": "おすすめのお店の地図", "T_MAP": "地図",
           "T_MAPFOOT": "番号はリストと同じです。白い丸の数字は、重なっているお店の数です（押すと広がります）。", "T_LIST": "お店リスト",
           "T_FOOT": "営業時間・定休日は変わることがあります。お出かけの前に、お店の情報もご確認ください。地図は",
           "cats": [["all", "すべて"], ["食べる", "食べる"], ["買う", "買う"], ["困ったとき", "暮らし"]],
           "js": {"nophoto": "写真準備中", "draft": "確認中", "rating": f"{KEEPER}の評価", "quote": f"{KEEPER}のひとこと", "gmap": "Googleマップで開く",
                  "info": "お店の情報", "empty": "このジャンルのお店は、まだありません。", "count": "軒"},
           "draft": '<p class="draft">下書きです。確認中のお店を含みます。営業時間などは、変わっていることがあります。</p>'},
    "en": {"T_TITLE": "Miura A-tei Recommended Map", "T_EYEBROW": "MIURA A-TEI", "T_H1": "<span>The house manager's</span> <span>recommended map</span>",
           "T_LEDE": "Places to eat and shop in Misaki and Jogashima. Tap a shop to see where it is and the house manager's comment.",
           "T_BYCAT": "Filter by type", "T_BYSCENE": "Filter by occasion", "T_MAPLABEL": "Map of recommended shops", "T_MAP": "Map",
           "T_MAPFOOT": "Numbers match the list. Numbers in white circles show how many shops overlap there (tap to expand).", "T_LIST": "Shops",
           "T_FOOT": "Hours and days off can change; check the shop's information before you go. Comments are translated from Japanese. Map",
           "cats": [["all", "All"], ["食べる", "Eat"], ["買う", "Shop"], ["困ったとき", "Daily needs"]],
           "js": {"nophoto": "Photo coming soon", "draft": "Unconfirmed", "rating": "House manager's rating", "quote": "From the house manager", "gmap": "Open in Google Maps",
                  "info": "Shop info", "empty": "No shops of this type yet.", "count": " shops"},
           "draft": '<p class="draft">Draft. Includes shops not yet confirmed. Hours and other details may have changed.</p>'},
}
LANG_CSS = """.lang{float:right;display:inline-grid;grid-template-columns:1fr 1fr;gap:2px;padding:3px;margin:0 0 10px 8px;background:var(--tint);border:1px solid var(--hair);border-radius:999px}
.lang a{display:flex;align-items:center;justify-content:center;min-width:52px;min-height:38px;border-radius:999px;color:var(--mute);font:400 14px/1 var(--font);letter-spacing:.04em;text-decoration:none}
.lang a[aria-current="page"]{background:#fff;color:var(--ink);font-weight:700;box-shadow:0 0 0 1px var(--hair)}
.hero .hd{clear:both}
body.embed .lang{display:none}"""
LANG_JS = """<script>(function(){try{var L=document.documentElement.lang;
document.querySelectorAll('.lang a').forEach(function(a){a.addEventListener('click',function(){a.href=a.href.split('#')[0]+location.search+location.hash;try{localStorage.setItem('lang',a.hreflang)}catch(e){}})});
var p=null;try{p=localStorage.getItem('lang')}catch(e){}
var r=document.referrer,same=false;try{same=!!r&&new URL(r).origin===location.origin}catch(e){}
if(p&&p!==L&&!same&&!/[?&]embed=1/.test(location.search)){var a=document.querySelector('.lang a[hreflang="'+p+'"]');if(a)location.replace(a.href.split('#')[0]+location.search+location.hash)}}catch(e){}})();</script>"""

def rows(doc, include_draft, lang="ja"):
    out = []
    for s in doc["spots"]:
        h = s.get("hana") or {}
        if h.get("v") != "rec": continue
        if s.get("status") == "休止": continue
        if s.get("status") != "◎" and not include_draft: continue
        if (h.get("flag") or {}).get("type") in HIDE_FLAG: continue
        closed = s.get("closed")
        E = lang == "en"
        tr = EN_DATA["spots"].get(s["id"], {}) if E else {}
        hc = [x for x in [h.get("comment") or ""] + [m["text"] for m in h.get("more", [])] if x]
        if E and tr.get("hana") and len(tr["hana"]) == len(hc):
            hc = tr["hana"]
        out.append({
            "id": s["id"], "name": tr.get("name") or s["name"], "cat": s["category"],
            "area": (EN_DATA["areas"].get(s.get("area"), s.get("area")) if E else s.get("area")) or "",
            "lat": s.get("lat"), "lon": s.get("lon"),
            "c": (" / " if E else " ／ ").join(hc),
            "note": tr.get("note") or s.get("note") or "", "hours": tr.get("hours") or s.get("hours") or "",
            "closed": ((("Closed " + ", ".join(WD_EN[i] for i in closed)) if E else ("／".join(WD[i] for i in closed) + "休み")) if closed
                       else (tr.get("closed_note") or s.get("closed_note") or "")),
            "url": (s.get("links") or {}).get("official") or ((s.get("sources") or [{}])[0].get("url") or ""),
            "color": COLOR.get(s["category"], "#555"), "fg": FG.get(s["category"], "#fff"),
            "r": h.get("rating") or 0, "rm": h.get("rating_max") or 5, "w": h.get("when") or [],
            "draft": s.get("status") != "◎",
            "sc": shop_hours.parse(s.get("hours"), closed), "cl": closed if isinstance(closed, list) else None,
            "img": (("../../" if E else "../") + IMAGES[s["image"]]["file"]) if s.get("image") in IMAGES else "",
        })
    return out

def render(tpl, data, draft, flat="", guest=False, lang="ja", page="map-preview.html"):
    X = TXT[lang]
    banner = X["draft"] if draft else ""
    robots = '<meta name="robots" content="noindex,nofollow">' if draft or guest else ""
    home = HOME_GUEST if guest and HOME_GUEST else "null"
    note = HOMENOTE_GUEST if guest and HOME_GUEST else ""
    return (tpl.replace("%%DATA%%", json.dumps(data, ensure_ascii=False)).replace("%%KEEPER%%", KEEPER)
               .replace("%%DRAFT%%", banner).replace("%%ROBOTS%%", robots)
               .replace("%%FLAT%%", flat).replace("%%EXAGNOTE%%", EXAGNOTE).replace("%%EXAG%%", str(EXAG)).replace("%%STRUCT%%", STRUCT)
               .replace("%%HOME%%", home).replace("%%HOMENOTE%%", note)
               .replace("%%OPENJS%%", shop_hours.OPEN_JS).replace("%%STATUSCSS%%", shop_hours.STATUS_CSS)
               .replace("%%LANG%%", lang).replace("%%R%%", "../../" if lang == "en" else "../")
               .replace("%%T_CATS%%", json.dumps(X["cats"], ensure_ascii=False)).replace("%%T_JS%%", json.dumps(X["js"], ensure_ascii=False))
               .replace("%%LANGCSS%%", LANG_CSS).replace("%%LANGJS%%", LANG_JS).replace("%%LANGSWITCH%%", langswitch(lang, page))
               .replace("%%ALT%%", f'<link rel="alternate" hreflang="ja" href="{SITE}{page}"><link rel="alternate" hreflang="en" href="{SITE}en/{page}">')
               .replace("%%T_TITLE%%", X["T_TITLE"]).replace("%%T_EYEBROW%%", X["T_EYEBROW"]).replace("%%T_H1%%", X["T_H1"]).replace("%%T_LEDE%%", X["T_LEDE"])
               .replace("%%T_BYCAT%%", X["T_BYCAT"]).replace("%%T_BYSCENE%%", X["T_BYSCENE"]).replace("%%T_MAPLABEL%%", X["T_MAPLABEL"])
               .replace("%%T_MAPFOOT%%", X["T_MAPFOOT"]).replace("%%T_LIST%%", X["T_LIST"]).replace("%%T_FOOT%%", X["T_FOOT"]).replace("%%T_MAP%%", X["T_MAP"]))

def langswitch(lang, page):
    ja, en = (f"../{page}", page) if lang == "en" else (page, f"en/{page}")
    a = ' aria-current="page"'
    return (f'<nav class="lang" aria-label="Language / 言語"><a href="{ja}" hreflang="ja" lang="ja"{a if lang == "ja" else ""}>JP</a>'
            f'<a href="{en}" hreflang="en" lang="en"{a if lang == "en" else ""}>EN</a></nav>')

def main():
    doc = json.load(open(HERE / "spots.json"))
    tpl = (HERE / "hana_public.tpl.html").read_text(encoding="utf-8")
    tpl3 = (HERE / "hana_public3d.tpl.html").read_text(encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    pre = rows(doc, True)
    (OUT / "map-preview.html").write_text(render(tpl, pre, True), encoding="utf-8")   # 日本語版
    (OUT / "map3d-preview.html").write_text(render(tpl3, pre, True, "map-preview.html"), encoding="utf-8")
    print(f"guide/map-preview.html・map3d-preview.html: {len(pre)}件（下書き・A邸の位置なし）")
    (OUT / "en").mkdir(exist_ok=True)
    pre_en = rows(doc, True, "en")
    (OUT / "en" / "map-preview.html").write_text(render(tpl, pre_en, True, lang="en"), encoding="utf-8")
    print(f"guide/en/map-preview.html: {len(pre_en)}件（英語・下書き）")
    if HOME_GUEST:
        (HERE / "map3d-guest.src.html").write_text(render(tpl3, pre, True, "guide/map-preview.html", guest=True), encoding="utf-8")
        print("map3d-guest.src.html: A邸の位置つき（公開しない。合言葉をかけて出す元）")
    fin = rows(doc, False)
    if fin:
        (OUT / "map.html").write_text(render(tpl, fin, False), encoding="utf-8")
        (OUT / "map3d.html").write_text(render(tpl3, fin, False, "map.html"), encoding="utf-8")
        (OUT / "en" / "map.html").write_text(render(tpl, rows(doc, False, "en"), False, lang="en", page="map.html"), encoding="utf-8")
        print(f"guide/map.html・map3d.html: {len(fin)}件（◎のみ）")
    else:
        print("guide/map.html: ◎が0件のため作りません（ヤヌキが◎にしたら作られます）")

if __name__ == "__main__":
    main()
