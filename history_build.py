#!/usr/bin/env python3
"""history.json → history/index.html（三浦 歴史さんぽ：歴史のゆかりの地を時代ごとに 3D 地図にのせた1ページ）
英語版は history/en/index.html（訳は history_en.json。id で対応。2026-11-14）。
テンプレートは history.tpl.html。地図の仕組みは おすすめマップ 3D版（hana_public3d.tpl.html）と同じで、
橋・灯台・防波堤は structures.json を使う。だれでも見られるページなので、A邸の位置（home.local.json）は読まない。
番号は「時代の順 → 年の順」で build がふる（history.json の並び順は問わない）。"""
import json, pathlib

HERE = pathlib.Path(__file__).parent
OUT = HERE / "history"
SITE = "https://vaseata.github.io/miura-board/history/"
EXAG = 1  # 高さの強調（倍）。おすすめマップ 3D版と同じく実寸
_st = HERE / "structures.json"
STRUCT = _st.read_text(encoding="utf-8") if _st.exists() else '{"type":"FeatureCollection","features":[]}'
KEEP = ("id", "name", "era", "when", "area", "lat", "lon", "headline", "story", "see", "legend", "confidence", "tour", "cam", "sources")
TR_KEYS = ("name", "when", "area", "headline", "story", "see")

# 英語版：テンプレートの日本語を順に置き換える（左が history.tpl.html の文のまま）
EN_REPL = [
    ('content="三浦の歴史のゆかりの地を、時代ごとに3Dの地図でたどります。弥生のムラ、頼朝の御所、三浦一族の最期、灯台、城ヶ島の雨、マグロの港まで。"',
     'content="Explore historic sites of Miura on a 3D map, era by era: a Yayoi village, Yoritomo\'s villas, the fall of the Miura clan, lighthouses, “Rain on Jogashima” and the tuna port."'),
    ("<title>三浦 歴史さんぽ（3Dマップ）</title>", "<title>Miura History Walk (3D map)</title>"),
    ('<p class="eyebrow">三浦A邸</p>', '<p class="eyebrow">MIURA A-TEI</p>'),
    ("<h1><span>三浦 歴史さんぽ</span></h1>", "<h1><span>Miura History Walk</span></h1>"),
    ("弥生のムラ、頼朝の3つの別荘、三浦一族の最期、のろし台と灯台、「城ヶ島の雨」、マグロの港。三浦の歴史のゆかりの地 %%COUNT%%か所を、古い順に番号をふって、土地の高さが立ち上がる地図にのせました。ピンの色は時代です。",
     "A Yayoi village, Yoritomo's three villas, the last stand of the Miura clan, beacons and lighthouses, “Rain on Jogashima” and the tuna port. %%COUNT%% historic places in Miura, numbered from oldest to newest, on a map where the land rises in 3D. Pin colours show the era. Place names on the map are partly in Japanese."),
    ('aria-label="時代で絞り込む"', 'aria-label="Filter by era"'),
    ('aria-label="歴史のゆかりの地の地図"', 'aria-label="Map of historic places"'),
    ('aria-label="地図"', 'aria-label="Map"'),
    ('aria-label="地図の向きとかたむき"', 'aria-label="Map direction and tilt"'),
    ('aria-label="かたむける" title="かたむける"', 'aria-label="Tilt" title="Tilt"'),
    ('aria-label="左に回す" title="左に回す"', 'aria-label="Rotate left" title="Rotate left"'),
    ('aria-label="右に回す" title="右に回す"', 'aria-label="Rotate right" title="Rotate right"'),
    ('aria-label="起こす（真上から見る）" title="起こす（真上から見る）"', 'aria-label="Look straight down" title="Look straight down"'),
    ('aria-label="地図の操作"', 'aria-label="Map controls"'),
    ('aria-pressed="false">時代をたどる</button>', 'aria-pressed="false">Tour the eras</button>'),
    ('aria-pressed="false">写真</button>', 'aria-pressed="false">Photo</button>'),
    ('title="オンにすると、ふつうのドラッグで向きとかたむきが変わります">ドラッグで回す</button>', 'title="When on, dragging rotates and tilts the map">Drag to rotate</button>'),
    ('id="thm">全体に戻る</button>', 'id="thm">Reset view</button>'),
    ('aria-pressed="false">大きく見る</button>', 'aria-pressed="false">Full screen</button>'),
    ("「時代をたどる」を押すと、弥生から昭和まで、古い順に空から見てまわります（地図にさわると止まります）。番号は下の読みものと同じで、古い順です。白いピンの「2か所」「3か所」は、近くの場所をまとめたものです（押すと広がります）。向きとかたむきは、左下の矢印ボタンで変えられます。%%EXAGNOTE%%建物の高さは、地図データに記録のあるもの以外は一律5mの目安です。",
     "“Tour the eras” flies over the places from the Yayoi period to Showa, oldest first (touch the map to stop). Numbers match the stories below. White pins with a number group nearby places (tap to spread them). Use the arrow buttons at the lower left to rotate and tilt. %%EXAGNOTE%%Buildings without recorded heights are shown at 5 m."),
    ("書いてあることは、出典を開いて確かめたものだけです。各項目の下に出典があります。🟢 は三浦市・三浦市観光協会のページで確かめたもの、🟡 は Wikipedia など一次でない出典によるもの。「伝承」の札は、言い伝えをふくむ話です。ピンの位置は OpenStreetMap と Wikipedia の座標によるもので、数十mずれていることがあります。社寺や研究施設は、公開の時間や立ち入れる範囲がそれぞれ決まっています。",
     "Everything here was checked against the sources listed under each item (mostly in Japanese). 🟢 = checked on a Miura City or Miura Tourism Association page; 🟡 = from a secondary source such as Wikipedia. “Legend” marks stories that include tradition. Pin positions come from OpenStreetMap and Wikipedia and may be off by tens of metres. Temples, shrines and research facilities have their own opening hours and access rules. Translated from the Japanese; if they differ, the Japanese version is correct."),
    ("地図・建物・構造物の形は ©", "Map, buildings and structures ©"),
    ("contributors（タイルは ", "contributors (tiles: "),
    ("© OpenMapTiles）。写真と標高は ", "© OpenMapTiles). Photos and elevation: "),
    ("国土地理院（地理院タイル）</a>。", "GSI Japan (GSI tiles)</a>."),
    ('<br><a href="../">最近の三浦</a> ・ <a href="../guide/">お店・名所</a> ・ <a href="../guide/hito/">三崎の人</a> ・ <a href="../guide/hae/">映えスポット</a></p>',
     '<br><a href="../../en/">Miura news</a> · <a href="../../guide/en/">Eat &amp; See</a> · <a href="../../guide/hito/en/">People of Misaki</a> · <a href="../../guide/hae/en/">Photo spots</a></p>'),
    ('attribution:"写真・標高：国土地理院"', 'attribution:"Photo & elevation: GSI Japan"'),
    ('attribution:"地図：OpenFreeMap', 'attribution:"Map: OpenFreeMap'),
    ('"Ctrl を押しながらスクロールで拡大できます"', '"Hold Ctrl and scroll to zoom"'),
    ('"⌘ を押しながらスクロールで拡大できます"', '"Hold ⌘ and scroll to zoom"'),
    ('"指2本で地図を動かせます"', '"Use two fingers to move the map"'),
    ('"NavigationControl.ZoomIn":"拡大","NavigationControl.ZoomOut":"縮小","NavigationControl.ResetBearing":"北を上に戻す"',
     '"NavigationControl.ZoomIn":"Zoom in","NavigationControl.ZoomOut":"Zoom out","NavigationControl.ResetBearing":"Reset north"'),
    ("<p>この端末では 3D の地図を表示できませんでした。<br>下の読みものは、そのまま読めます。</p>", "<p>This device could not show the 3D map.<br>The stories below can still be read.</p>"),
    ('b.textContent="くわしく読む"', 'b.textContent="Read more"'),
    ('"<small>か所</small>"', '"<small> places</small>"'),
    ('g.m.length+"か所。押すと広がります"', 'g.m.length+" places. Tap to spread"'),
    ('g.m.length+"か所がすぐ近くにあります</b>"', 'g.m.length+" places are close together</b>"'),
    ("'<span class=\"tag lg\">伝承</span>'", "'<span class=\"tag lg\">Legend</span>'"),
    ("'<p class=\"see\"><b>現地で</b>'", "'<p class=\"see\"><b>On site </b>'"),
    ("d.confidence+' 出典：'", "d.confidence+' Sources (Japanese): '"),
    ('.join("、")', '.join(", ")'),
    ("'<div class=\"empty\">この時代の場所は、まだありません。</div>'", "'<div class=\"empty\">No places for this era yet.</div>'"),
    ('{key:"all",name:"すべて"}', '{key:"all",name:"All"}'),
    ('this.textContent=on?"とじる":"大きく見る"', 'this.textContent=on?"Close":"Full screen"'),
    ('$("#ttr").textContent="時代をたどる"', '$("#ttr").textContent="Tour the eras"'),
    ('this.textContent="止める"', 'this.textContent="Stop"'),
]


def nav(lang):
    ja, en = ("../", "./") if lang == "en" else ("./", "en/")
    a = ' aria-current="page"'
    back = ('<a class="back" href="../../guide/en/">← Eat &amp; See</a>' if lang == "en"
            else '<a class="back" href="../guide/">← お店・名所</a>')
    return (f'<nav class="hnav" aria-label="{"Navigation" if lang == "en" else "移動"}">{back}'
            f'<span class="lang"><a href="{ja}" hreflang="ja" lang="ja"{a if lang == "ja" else ""}>JP</a>'
            f'<a href="{en}" hreflang="en" lang="en"{a if lang == "en" else ""}>EN</a></span></nav>')


def build(lang, doc, tr):
    E = lang == "en"
    eras = [dict(e, **tr["eras"].get(e["key"], {})) if E else e for e in doc["eras"]]
    order = {e["key"]: i for i, e in enumerate(eras)}
    spots = sorted(doc["spots"], key=lambda s: (order[s["era"]], s["year"]))
    rows, missing = [], []
    for i, s in enumerate(spots, 1):
        assert s.get("sources"), f'{s["id"]}: 出典がありません'
        assert s.get("lat") and s.get("lon"), f'{s["id"]}: 座標がありません'
        r = {k: s[k] for k in KEEP if s.get(k) not in (None, "", False)}
        if E:
            t = tr["spots"].get(s["id"])
            if not t: missing.append(s["id"])
            else: r.update({k: t[k] for k in TR_KEYS if t.get(k)})
        r["sources"] = [{"url": x["url"], "title": x["title"]} for x in s["sources"]]
        r["no"] = i
        rows.append(r)
    tpl = (HERE / "history.tpl.html").read_text(encoding="utf-8")
    if E:
        for a, b in EN_REPL:
            assert a in tpl, f"英語版の置き換え元がテンプレートに見つかりません: {a[:40]}"
            tpl = tpl.replace(a, b)
        tpl = tpl.replace('<link rel="preconnect" href="https://fonts.googleapis.com">',
                          f'<link rel="alternate" hreflang="ja" href="{SITE}"><link rel="alternate" hreflang="en" href="{SITE}en/">\n<link rel="preconnect" href="https://fonts.googleapis.com">', 1)
        exag = "Land and building heights are true to scale. " if EXAG == 1 else f"Heights are exaggerated {EXAG}× for clarity. "
    else:
        tpl = tpl.replace('<link rel="preconnect" href="https://fonts.googleapis.com">',
                          f'<link rel="alternate" hreflang="ja" href="{SITE}"><link rel="alternate" hreflang="en" href="{SITE}en/">\n<link rel="preconnect" href="https://fonts.googleapis.com">', 1)
        exag = "土地と建物の高さは実寸です。" if EXAG == 1 else f"土地と建物の高さは、わかりやすいように{EXAG}倍に強調しています。"
    html = (tpl.replace("%%DATA%%", json.dumps(rows, ensure_ascii=False))
               .replace("%%ERAS%%", json.dumps(eras, ensure_ascii=False))
               .replace("%%STRUCT%%", STRUCT).replace("%%EXAGNOTE%%", exag)
               .replace("%%EXAG%%", str(EXAG)).replace("%%COUNT%%", str(len(rows)))
               .replace("%%LANG%%", lang).replace("%%NAV%%", nav(lang))
               .replace("%%NAMEKEY%%", "name:en" if E else "name:ja"))
    assert "%%" not in html.replace("%%%", ""), "置き換え忘れがあります"
    out = OUT / "en" if E else OUT
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html, encoding="utf-8")
    label = "history/en/index.html" if E else "history/index.html"
    print(f"{label}: {len(rows)}か所（" + "・".join(f'{e["name"]}{sum(1 for r in rows if r["era"] == e["key"])}' for e in eras) + "）"
          + (f"　英訳なし {len(missing)}: {', '.join(missing)}" if missing else ""))


def main():
    doc = json.load(open(HERE / "history.json", encoding="utf-8"))
    p = HERE / "history_en.json"
    tr = json.load(open(p, encoding="utf-8")) if p.exists() else {"eras": {}, "spots": {}}
    for lang in ("ja", "en"):
        build(lang, doc, tr)


if __name__ == "__main__":
    main()
