#!/usr/bin/env python3
"""spots.json（hana.v == "rec"）→ 閲覧専用の公開版 おすすめマップ
  guide/map.html          … status が ◎ のお店だけ（ホームページに埋め込む本番用。◎が0件なら作らない）
  guide/map-preview.html  … 候補も含む下書き（noindex・「確認中」の札つき。デザイン確認と埋め込みテスト用）
  guide/map3d.html / map3d-preview.html … 同じお店を地形の3D地図にのせた版（hana_public3d.tpl.html。MapLibre＋地理院の標高タイル。
                                          建物は OpenFreeMap のベクトルタイル、橋・灯台・防波堤は structures.json）
◎にできるのはヤヌキだけ。埋め込み: <iframe src=".../guide/map.html?embed=1"> """
import json, pathlib, re, sys
import shop_hours

HERE = pathlib.Path(__file__).parent
OUT = HERE / "guide"
KEEPER = "家守"  # 名前を出すなら "家守・華さん" に変える
WD = "月火水木金土日"
COLOR = {"食べる": "#B4501A", "買う": "#0A5A8C", "困ったとき": "#4F6070"}   # 食べる＝柿（暖色・2026-11-14 ヤヌキ判断）／買う＝海の青／暮らし＝墨。マグロの赤は地図に置かない
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
EXAGNOTE_EN = "Land and building heights are true to scale." if EXAG == 1 else f"Heights are exaggerated {EXAG}x."
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
           "T_LEDE3": "三崎・城ヶ島の、ごはんと買い物のお店です。土地の高さと建物が立ち上がる地図で、時刻に合わせて色が変わります。「現在地」を押すと、近い順に並びます。",
           "T_MAPFOOT3": "番号はリストと同じです。白いピンの「2軒」などは、近くのお店をまとめたものです（押すと広がります）。スマホでは指2本で動かし、回せます。左下の矢印でも向きとかたむきを変えられます。「現在地」の位置は、この端末の中だけで使い、どこにも送りません。建物の高さは、記録のないものは一律5mの目安です。",
           "T_FOOT3": "営業時間・定休日は変わることがあります。お出かけの前に、お店の情報もご確認ください。<br>地図・建物・構造物の形は © <a href=\"https://www.openstreetmap.org/copyright\" target=\"_blank\" rel=\"noopener\">OpenStreetMap</a> contributors（タイルは <a href=\"https://openfreemap.org\" target=\"_blank\" rel=\"noopener\">OpenFreeMap</a> © OpenMapTiles）。写真と標高は <a href=\"https://maps.gsi.go.jp/development/ichiran.html\" target=\"_blank\" rel=\"noopener\">国土地理院（地理院タイル）</a>。",
           "cats": [["all", "すべて"], ["食べる", "食べる"], ["買う", "買う"], ["困ったとき", "暮らし"]],
           "js": {"nophoto": "写真準備中", "draft": "確認中", "rating": f"{KEEPER}の評価", "quote": f"{KEEPER}のひとこと", "gmap": "Googleマップで開く",
                  "info": "お店の情報", "empty": "このジャンルのお店は、まだありません。", "count": "軒", **{
                  "sep": " ／ ", "namekey": "name:ja", "stkey": "name", "attrGsi": "写真・標高：国土地理院",
                  "catName": {"食べる": "食べる", "買う": "買う", "困ったとき": "暮らし"},
                  "view": {"3d": "3D", "flat": "平面", "photo": "写真"}, "viewlbl": "地図の見え方", "toolslbl": "地図の操作",
                  "tod": {"morning": "朝", "day": "昼", "evening": "夕", "night": "夜"}, "todBtn": "色：{p}", "todAuto": "（自動）", "todAria": "時刻の色を変える",
                  "locate": "現在地", "locOff": "現在地を止める", "locating": "現在地を探しています…",
                  "locDenied": "位置の利用が許可されていません。端末の設定で、このサイトに位置の利用を許可してください。",
                  "locFail": "現在地が分かりませんでした。外で、もう一度押してください。", "locFar": "今いる所が三崎から離れているので、地図は動かしません。",
                  "privacy": "位置は、この端末の中だけで使います。どこにも送りません。", "meHere": "現在地",
                  "fromHere": "ここから", "walk": "徒歩約{n}分", "nearSort": "近い順",
                  "tour": "ひとめぐり", "tourStop": "止める", "tourStart": "ここから出発します", "home": "最初に戻る", "backHome": "{n}へ戻る",
                  "big": "大きく見る", "close": "とじる", "drag": "ドラッグで回す", "dragTitle": "オンにすると、ふつうのドラッグで向きとかたむきが変わります",
                  "padlbl": "地図の向きとかたむき", "tilt": "かたむける", "up": "起こす（真上から見る）", "left": "左に回す", "right": "右に回す",
                  "sortlbl": "並べ替え", "sort": {"rec": "おすすめ", "heart": "❤️順", "price": "安い順", "near": "近い順"},
                  "emptyOpen": "いま営業中のお店はありません（営業時間が分かるお店の中で）。「今日やっている」で探してみてください。", "fOpen": "今やっている", "fToday": "今日やっている", "price": "予算",
                  "noPrice": "予算が分かっているのは{n}軒だけです。分からないお店は後ろに並びます。",
                  "noHours": "営業時間が分からないお店（{n}軒）は入っていません。",
                  "cl": "軒", "clAria": "{n}軒のお店。押すと広がります", "same": "{n}軒が同じ場所にあります", "homeHere": "ここが宿です",
                  "nogl": "この端末では 3D の地図を表示できませんでした。", "flatlink": "平面の地図で見る",
                  "tourStops": [["海南神社", "三浦の総鎮守"], ["三崎港・うらり", "うらりマルシェ（さかな館・やさい館）"], ["城ヶ島大橋", "長さ575m。海面から16〜23.5mの高さ"],
                                ["城ヶ島灯台", "島の西の端。塔の高さ11.5m"], ["安房埼灯台", "島の東の端、城ヶ島公園の中。高さ16m"]],
                  "gl": {"CooperativeGesturesHandler.WindowsHelpText": "Ctrl を押しながらスクロールで拡大できます", "CooperativeGesturesHandler.MacHelpText": "⌘ を押しながらスクロールで拡大できます",
                         "CooperativeGesturesHandler.MobileHelpText": "指2本で地図を動かせます", "NavigationControl.ZoomIn": "拡大", "NavigationControl.ZoomOut": "縮小", "NavigationControl.ResetBearing": "北を上に戻す"}}},
           "draft": '<p class="draft">下書きです。確認中のお店を含みます。営業時間などは、変わっていることがあります。</p>'},
    "en": {"T_TITLE": "Miura A-tei Recommended Map", "T_EYEBROW": "MIURA A-TEI", "T_H1": "<span>The house manager's</span> <span>recommended map</span>",
           "T_LEDE": "Places to eat and shop in Misaki and Jogashima. Tap a shop to see where it is and the house manager's comment.",
           "T_BYCAT": "Filter by type", "T_BYSCENE": "Filter by occasion", "T_MAPLABEL": "Map of recommended shops", "T_MAP": "Map",
           "T_MAPFOOT": "Numbers match the list. Numbers in white circles show how many shops overlap there (tap to expand).", "T_LIST": "Shops",
           "T_FOOT": "Hours and days off can change; check the shop's information before you go. Comments are translated from Japanese. Map",
           "T_LEDE3": "Places to eat and shop in Misaki and Jogashima, on a 3D map whose colors follow the time of day. Tap “My location” to sort the shops by distance.",
           "T_MAPFOOT3": "Numbers match the list. White pins with a number group nearby shops (tap to expand). On a phone, use two fingers to move and rotate the map; the arrows at the bottom left also turn and tilt it. Your location is used only on this device and never sent anywhere. Buildings without height data are drawn 5 m tall.",
           "T_FOOT3": "Hours and days off can change; check the shop's information before you go. Comments are translated from Japanese.<br>Map, buildings and structures © <a href=\"https://www.openstreetmap.org/copyright\" target=\"_blank\" rel=\"noopener\">OpenStreetMap</a> contributors (tiles: <a href=\"https://openfreemap.org\" target=\"_blank\" rel=\"noopener\">OpenFreeMap</a> © OpenMapTiles). Aerial photos and elevation: <a href=\"https://maps.gsi.go.jp/development/ichiran.html\" target=\"_blank\" rel=\"noopener\">GSI Japan</a>.",
           "cats": [["all", "All"], ["食べる", "Eat"], ["買う", "Shop"], ["困ったとき", "Daily needs"]],
           "js": {"nophoto": "Photo coming soon", "draft": "Unconfirmed", "rating": "House manager's rating", "quote": "From the house manager", "gmap": "Open in Google Maps",
                  "info": "Shop info", "empty": "No shops of this type yet.", "count": " shops", **{
                  "sep": " / ", "namekey": "name:en", "stkey": "name_en", "attrGsi": "Photo & elevation: GSI Japan",
                  "catName": {"食べる": "Eat", "買う": "Shop", "困ったとき": "Daily needs"},
                  "view": {"3d": "3D", "flat": "Flat", "photo": "Photo"}, "viewlbl": "Map view", "toolslbl": "Map controls",
                  "tod": {"morning": "Morning", "day": "Day", "evening": "Evening", "night": "Night"}, "todBtn": "Colors: {p}", "todAuto": " (auto)", "todAria": "Change the time-of-day colors",
                  "locate": "My location", "locOff": "Stop location", "locating": "Finding your location…",
                  "locDenied": "Location access is off. Allow this site to use your location in your phone's settings.",
                  "locFail": "Couldn't find your location. Try again outdoors.", "locFar": "You're far from Misaki, so the map stays where it is.",
                  "privacy": "Your location is used only on this device. It is never sent anywhere.", "meHere": "Your location",
                  "fromHere": "From here", "walk": "about {n} min walk", "nearSort": "nearest first",
                  "tour": "Fly-through", "tourStop": "Stop", "tourStart": "Starting here", "home": "Reset view", "backHome": "Back to {n}",
                  "big": "Full screen", "close": "Close", "drag": "Drag to rotate", "dragTitle": "When on, dragging changes the direction and tilt",
                  "padlbl": "Map direction and tilt", "tilt": "Tilt", "up": "Look straight down", "left": "Rotate left", "right": "Rotate right",
                  "sortlbl": "Sort", "sort": {"rec": "Picks", "heart": "❤️ most", "price": "Cheapest", "near": "Nearest"},
                  "emptyOpen": "No shops are open right now (among those with known hours). Try “Open today”.", "fOpen": "Open now", "fToday": "Open today", "price": "Budget",
                  "noPrice": "Only {n} shops have a known budget. The rest are listed after them.",
                  "noHours": "Shops with unknown hours ({n}) are not included.",
                  "cl": "", "clAria": "{n} shops here. Tap to expand", "same": "{n} shops at the same spot", "homeHere": "This is the house",
                  "nogl": "This device can't show the 3D map.", "flatlink": "Open the flat map",
                  "tourStops": [["Kainan Shrine", "Miura's main guardian shrine"], ["Misaki Port / Urari", "Urari market (fish & vegetables)"], ["Jogashima Bridge", "575 m long, 16–23.5 m above the sea"],
                                ["Jogashima Lighthouse", "West tip of the island. Tower 11.5 m"], ["Awasaki Lighthouse", "East tip, in Jogashima Park. 16 m tall"]],
                  "gl": {"CooperativeGesturesHandler.WindowsHelpText": "Use Ctrl + scroll to zoom the map", "CooperativeGesturesHandler.MacHelpText": "Use ⌘ + scroll to zoom the map",
                         "CooperativeGesturesHandler.MobileHelpText": "Use two fingers to move the map", "NavigationControl.ZoomIn": "Zoom in", "NavigationControl.ZoomOut": "Zoom out", "NavigationControl.ResetBearing": "Reset north"}}},
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

def price_value(p):
    """予算の文から、並べ替えに使う一番安い金額（円）を取る。「1,000〜1,999円」→1000。読めなければ None"""
    m = re.search(r"(\d[\d,]*)\s*(?:〜|~|円)", p or "")
    return int(m.group(1).replace(",", "")) if m else None

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
            "price": tr.get("price") or s.get("price") or "", "pv": price_value(s.get("price")),
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
               .replace("%%FLAT%%", flat).replace("%%EXAGNOTE%%", EXAGNOTE if lang == "ja" else EXAGNOTE_EN).replace("%%EXAG%%", str(EXAG)).replace("%%STRUCT%%", STRUCT)
               .replace("%%HOME%%", home).replace("%%HOMENOTE%%", note)
               .replace("%%OPENJS%%", shop_hours.OPEN_JS).replace("%%STATUSCSS%%", shop_hours.STATUS_CSS)
               .replace("%%LANG%%", lang).replace("%%R%%", "../../" if lang == "en" else "../")
               .replace("%%T_CATS%%", json.dumps(X["cats"], ensure_ascii=False)).replace("%%T_JS%%", json.dumps(X["js"], ensure_ascii=False))
               .replace("%%LANGCSS%%", LANG_CSS).replace("%%LANGJS%%", LANG_JS).replace("%%LANGSWITCH%%", langswitch(lang, page))
               .replace("%%ALT%%", f'<link rel="alternate" hreflang="ja" href="{SITE}{page}"><link rel="alternate" hreflang="en" href="{SITE}en/{page}">')
               .replace("%%T_LEDE3%%", X["T_LEDE3"]).replace("%%T_MAPFOOT3%%", X["T_MAPFOOT3"]).replace("%%T_FOOT3%%", X["T_FOOT3"])
               .replace("%%T_TITLE%%", X["T_TITLE"]).replace("%%T_EYEBROW%%", X["T_EYEBROW"]).replace("%%T_H1%%", X["T_H1"]).replace("%%T_LEDE%%", X["T_LEDE"])
               .replace("%%T_BYCAT%%", X["T_BYCAT"]).replace("%%T_BYSCENE%%", X["T_BYSCENE"]).replace("%%T_MAPLABEL%%", X["T_MAPLABEL"])
               .replace("%%T_MAPFOOT%%", X["T_MAPFOOT"]).replace("%%T_LIST%%", X["T_LIST"]).replace("%%T_FOOT%%", X["T_FOOT"]).replace("%%T_MAP%%", X["T_MAP"]))

def langswitch(lang, page):
    ja, en = (f"../{page}", page) if lang == "en" else (page, f"en/{page}")
    a = ' aria-current="page"'
    return (f'<nav class="lang" aria-label="Language / 言語"><a href="{ja}" hreflang="ja" lang="ja"{a if lang == "ja" else ""}>JP</a>'
            f'<a href="{en}" hreflang="en" lang="en"{a if lang == "en" else ""}>EN</a></nav>')

REDIRECT = """<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url={to}"><link rel="canonical" href="{to}"><title>おすすめマップ</title>
<script>location.replace("{to}"+location.search+location.hash)</script></head>
<body><p>おすすめマップは <a href="{to}">こちら</a> に移りました（3D と平面が1つのページになりました）。</p></body></html>
"""

def main():
    # 2026-11-14 ヤヌキ判断：入口は 3D の地図1つ（map-preview.html）。平面・写真はページの中のボタンで切り替える。
    # 平面（Leaflet）の map-flat.html は、3D を出せない端末のための予備。map3d-preview.html は map-preview.html へ移す
    doc = json.load(open(HERE / "spots.json"))
    tpl = (HERE / "hana_public.tpl.html").read_text(encoding="utf-8")
    tpl3 = (HERE / "hana_public3d.tpl.html").read_text(encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    (OUT / "en").mkdir(exist_ok=True)
    for lang, d in (("ja", OUT), ("en", OUT / "en")):
        pre = rows(doc, True, lang)
        (d / "map-preview.html").write_text(render(tpl3, pre, True, "map-flat.html", lang=lang, page="map-preview.html"), encoding="utf-8")
        (d / "map-flat.html").write_text(render(tpl, pre, True, lang=lang, page="map-flat.html"), encoding="utf-8")
        print(f"guide/{'en/' if lang == 'en' else ''}map-preview.html（3D）・map-flat.html（予備の平面）: {len(pre)}件（下書き・A邸の位置なし）")
    (OUT / "map3d-preview.html").write_text(REDIRECT.format(to="map-preview.html"), encoding="utf-8")
    if HOME_GUEST:
        (HERE / "map3d-guest.src.html").write_text(render(tpl3, rows(doc, True), True, "guide/map-flat.html", guest=True), encoding="utf-8")
        print("map3d-guest.src.html: A邸の位置つき（公開しない。合言葉をかけて出す元）")
    fin = rows(doc, False)
    if fin:
        for lang, d in (("ja", OUT), ("en", OUT / "en")):
            f = rows(doc, False, lang)
            (d / "map.html").write_text(render(tpl3, f, False, "map-flat-final.html", lang=lang, page="map.html"), encoding="utf-8")
            (d / "map-flat-final.html").write_text(render(tpl, f, False, lang=lang, page="map-flat-final.html"), encoding="utf-8")
        (OUT / "map3d.html").write_text(REDIRECT.format(to="map.html"), encoding="utf-8")
        print(f"guide/map.html: {len(fin)}件（◎のみ）")
    else:
        print("guide/map.html: ◎が0件のため作りません（ヤヌキが◎にしたら作られます）")

if __name__ == "__main__":
    main()
