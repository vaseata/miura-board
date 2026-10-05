#!/usr/bin/env python3
"""spots.json + items.json + calendar.json + places.json → guide/index.html（ゲスト用）・guide/review.html（候補の確認用）
単体で動く（build.py には依存しない）。build.py の末尾からも呼ばれる。"""
import json, datetime, html, pathlib, math, urllib.parse
from string import Template

HERE = pathlib.Path(__file__).parent
OUT = HERE / "guide"
TODAY = datetime.date.today()
WD = "月火水木金土日"
CATS = ["食べる", "見る・歩く", "体験する", "買う", "移動", "困ったとき"]
CAT_LATIN = {"食べる": "Eat", "見る・歩く": "See & Walk", "体験する": "Do", "買う": "Buy", "移動": "Getting around", "困ったとき": "Help", "季節": "Season"}
CONF = {"🟢": "出典確認", "🟡": "要確認", "🗣": "伝聞"}
BOARD = "../index.html"

def d(s): return datetime.date.fromisoformat(s)
def esc(s): return html.escape(str(s if s is not None else ""), quote=True)
def jdate(dt, approx=False):
    s = f"{dt.month}/{dt.day}({WD[dt.weekday()]})"
    return s + "頃" if approx else s
def conf(c): return CONF.get(c, c)
def short_head(text, n=26):
    for sep in ("。", "（", "、"):
        i = text.find(sep)
        if 0 < i <= n: return text[:i]
    return text[:n] + ("…" if len(text) > n else "")
def sources_html(srcs):
    return "／".join(f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["title"])}</a>' for s in srcs)

def haversine(a, b):
    R = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = math.radians(b[0] - a[0]), math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

def build():
    spots_doc = json.load(open(HERE / "spots.json"))
    home = spots_doc["home"]
    spots = spots_doc["spots"]
    items = json.load(open(HERE / "items.json"))["items"]
    cal = json.load(open(HERE / "calendar.json"))["events"]
    places = json.load(open(HERE / "places.json"))["images"]
    OUT.mkdir(exist_ok=True)

    # ---- 徒歩時間（目安）
    for s in spots:
        if s.get("lat") and s.get("lon"):
            m = haversine((home["lat"], home["lon"]), (s["lat"], s["lon"]))
            s["_dist_m"] = int(m)
            s["_walk"] = math.ceil(m * 1.3 / 80)
        else:
            s["_dist_m"] = None; s["_walk"] = None
    published = [s for s in spots if s.get("status") == "◎"]
    candidates = [s for s in spots if s.get("status") == "候補"]
    published.sort(key=lambda s: (CATS.index(s["category"]) if s["category"] in CATS else 99, s["_walk"] if s["_walk"] is not None else 999))

    def thumb(key, label):
        p = places.get(key or "")
        if not p: return f'<div class="thumb noimg" aria-hidden="true"><span>{esc(label)}</span></div>'
        return f'<div class="thumb"><img src="../{esc(p["file"])}" alt="" loading="lazy" width="480" height="300"></div>'
    def figure(key):
        p = places.get(key or "")
        if not p: return ""
        cap = f'<figcaption>{esc(p["caption"])}</figcaption>' if p.get("caption") else ""
        return f'<figure class="photo"><img src="../{esc(p["file"])}" alt="" loading="lazy" width="480" height="300">{cap}</figure>'

    def walk_label(s):
        if s["_walk"] is None: return ""
        w = s["_walk"]
        if w <= 60: return f'<span class="walk">徒歩{w}分</span>'
        return f'<span class="walk far">徒歩{w}分・バス/車</span>'

    def closed_text(s):
        c = s.get("closed")
        if c is None: return "定休日 要確認"
        if not c: return "無休"
        return "定休：" + "・".join(WD[i] for i in sorted(c)) + "曜"

    def map_links(s):
        if not (s.get("lat") and s.get("lon")): return ""
        q = f'{s["lat"]},{s["lon"]}'
        apple = f'https://maps.apple.com/?daddr={q}&dirflg=w'
        goog = "https://www.google.com/maps/dir/?api=1&destination=" + urllib.parse.quote(q) + "&travelmode=walking"
        return f'<p class="maps"><a href="{apple}" target="_blank" rel="noopener">Apple マップで徒歩経路</a><a href="{goog}" target="_blank" rel="noopener">Google マップ</a></p>'

    def spot_card(s):
        tags = s.get("tags", [])
        closed = ",".join(str(i) for i in s["closed"]) if isinstance(s.get("closed"), list) else ""
        months = ",".join(str(m) for m in (s.get("season") or list(range(1, 13))))
        off = s.get("links", {}).get("official") if s.get("links") else None
        rows = []
        if s.get("hours"): rows.append(("営業", s["hours"]))
        rows.append(("休み", closed_text(s) + (f'（{s["closed_note"]}）' if s.get("closed_note") else "")))
        if s.get("closed_until"): rows.append(("臨時休業", f'{jdate(d(s["closed_until"]))} まで'))
        if s.get("price"): rows.append(("料金", s["price"]))
        if s.get("address"): rows.append(("場所", s["address"]))
        if s.get("access"): rows.append(("行き方", s["access"]))
        if s["_walk"] is not None: rows.append(("A邸から", f'徒歩{s["_walk"]}分（直線 {s["_dist_m"]}m・目安）'))
        if s.get("season") and len(s["season"]) < 12: rows.append(("季節", "・".join(f"{m}月" for m in s["season"])))
        dl = "".join(f'<dt>{esc(k)}</dt><dd>{esc(v)}</dd>' for k, v in rows)
        return f'''<article class="art spot" data-cat="{esc(s["category"])}" data-tags="{esc(",".join(tags))}" data-walk="{s["_walk"] if s["_walk"] is not None else ""}" data-closed="{closed}" data-closed-known="{"1" if isinstance(s.get("closed"), list) else ""}" data-until="{esc(s.get("closed_until") or "")}" data-months="{months}">
  {thumb(s.get("image"), s["area"])}
  <div class="ran"><span class="cat">{esc(s["category"])}</span><span class="area">{esc(s["area"])}</span>{walk_label(s)}</div>
  <h3><button type="button" class="open">{esc(s["name"])}</button></h3>
  <p class="dt">{esc(s.get("hours") or "")}{"　" if s.get("hours") else ""}<span class="cl">{esc(closed_text(s))}</span></p>
  <p class="lede">{esc(s.get("note") or "")}</p>
  <div class="detail" hidden>
    {figure(s.get("image"))}
    <p class="d-meta"><span class="cat">{esc(s["category"])}</span>{esc(s["area"])}　{"／".join(esc(t) for t in tags)}</p>
    <h2 class="d-head">{esc(s["name"])}</h2>
    <aside class="talk"><span class="tl">ひとこと</span>{esc(s.get("note") or "")}</aside>
    <dl class="info">{dl}</dl>
    {map_links(s)}
    {f'<p class="off"><a href="{esc(off)}" target="_blank" rel="noopener">公式サイト・案内ページ →</a></p>' if off else ""}
    <p class="src"><span class="cf">{conf(s.get("confidence", "🟡"))}</span>{sources_html(s.get("sources", []))}<span class="chk">確認 {esc(s.get("last_checked") or "—")}</span></p>
  </div>
</article>'''

    # ---- 今の季節
    season_spots = [s for s in published if s["category"] == "季節" and TODAY.month in (s.get("season") or [])]
    nxt_df = None
    for e in cal:
        if "ダイヤモンド富士" in e["fact"]:
            mm, dd = map(int, e["month_day"].split("-"))
            for y in (TODAY.year, TODAY.year + 1):
                dt = datetime.date(y, mm, dd)
                if dt >= TODAY and (nxt_df is None or dt < nxt_df[0]): nxt_df = (dt, e)
    ev = []
    for x in items:
        if x.get("category") != "イベント" or x.get("cancelled"): continue
        start, end = d(x["date"]), d(x.get("end") or x["date"])
        if end < TODAY or start > TODAY + datetime.timedelta(days=30): continue
        ev.append((start, end, x.get("headline") or short_head(x["fact"]), x["area"], x["talk"], x.get("image")))
    ev.sort(key=lambda t: t[0])
    ups = []
    for e in cal:
        mm, dd = map(int, e["month_day"].split("-"))
        for y in (TODAY.year, TODAY.year + 1):
            try: dt = datetime.date(y, mm, dd)
            except ValueError: continue
            if 0 <= (dt - TODAY).days <= 60:
                ups.append((dt, e)); break
    ups.sort(key=lambda t: t[0])

    def ev_card(start, end, head, area, talk, image):
        now = start <= TODAY <= end
        when = jdate(start) + (f"〜{jdate(end)}" if end > start else "")
        st = '<span class="st now">開催中</span>' if now else f'<span class="st soon">{(start-TODAY).days}日後</span>'
        return f'''<a class="art ev" href="{BOARD}">{thumb(image, area)}<div class="ran"><span class="cat">イベント</span><span class="area">{esc(area)}</span>{st}</div><h3>{esc(head)}</h3><p class="dt">{when}</p><p class="lede">{esc(talk)}</p></a>'''
    def up_card(dt, e):
        return f'''<a class="art ev" href="{BOARD}">{thumb(e.get("image"), "定番")}<div class="ran"><span class="cat">定番</span><span class="st soon">{(dt-TODAY).days}日後</span></div><h3>{esc(short_head(e["fact"]))}</h3><p class="dt">{jdate(dt, e.get("approx"))}</p><p class="lede">{esc(e["talk"])}</p></a>'''

    season_html = "".join(spot_card(s) for s in season_spots)
    events_html = "".join(ev_card(*t) for t in ev) + "".join(up_card(dt, e) for dt, e in ups)
    # ダイヤモンド富士は常設しない。30日以内に来るときだけ「今の季節」にカードで出す
    df_card = ""
    if nxt_df and (nxt_df[0] - TODAY).days <= 30:
        dt, e = nxt_df
        df_card = f'''<a class="art ev" href="{BOARD}">{thumb(e.get("image"), "城ヶ島")}<div class="ran"><span class="cat">季節</span><span class="area">城ヶ島大橋</span><span class="st soon">{(dt-TODAY).days}日後</span></div><h3>ダイヤモンド富士 {jdate(dt, e.get("approx"))}</h3><p class="dt">日没・城ヶ島大橋から</p><p class="lede">{esc(e["talk"])}</p></a>'''
    spots_html = "".join(spot_card(s) for s in published)
    tabs = "".join(f'<button type="button" data-cat="{esc(c)}" aria-pressed="false">{esc(c)}</button>' for c in CATS)
    counts = {c: sum(1 for s in published if s["category"] == c) for c in CATS}
    credits = " · ".join(f'{k} {v["license"]}' for k, v in places.items() if v.get("source", "").startswith("https://commons"))

    page = Template(r'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="三浦A邸のゲスト向けガイド。三崎・城ヶ島・三浦海岸の食べる・見る・体験する・買う・移動・困ったときを、A邸からの徒歩時間つきで。">
<meta name="apple-mobile-web-app-title" content="A邸ガイド">
<meta name="theme-color" content="#0A5A8C">
<link rel="apple-touch-icon" href="../img/icon-180.png">
<link rel="manifest" href="manifest.webmanifest">
<title>三浦A邸 ガイドブック</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@500;700;800&family=Zen+Kaku+Gothic+New:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{ color-scheme:light;
  --bg:#FFFFFF; --ink:#14202B; --ink2:#3E4C58; --mute:#4F6070; --rule:#14202B; --hair:#D9E1E8; --tint:#F2F6F9;
  --sea:#0A5A8C; --sea-tint:#E6F0F6; --tuna:#B8243A; --tuna-tint:#FBEAEC; --on:#FFFFFF;
  --shadow:0 18px 50px rgba(10,40,70,.22);
  --mincho:"Shippori Mincho","Hiragino Mincho ProN","Yu Mincho",serif;
  --gothic:"Zen Kaku Gothic New","Hiragino Sans","Hiragino Kaku Gothic ProN","Yu Gothic",sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--gothic);background:var(--bg);color:var(--ink);line-height:1.75;font-size:15.5px;font-feature-settings:"palt";-webkit-font-smoothing:antialiased;overflow-x:hidden}
main{max-width:1240px;margin:0 auto;padding:12px 16px 56px}
@media (min-width:720px){ main{padding-inline:28px} }
a{color:inherit} button{font:inherit;color:inherit}
:focus-visible{outline:2px solid var(--sea);outline-offset:2px}
/* 題字 */
.masthead{padding:8px 0 12px;border-bottom:4px solid var(--sea);position:relative}
.masthead::after{content:"";position:absolute;left:0;right:0;bottom:-8px;border-bottom:1px solid var(--sea)}
.daiji{font-family:var(--mincho);font-weight:800;font-size:clamp(30px,7.5vw,60px);line-height:1.15;letter-spacing:.12em}
.daiji small{display:block;font-family:var(--gothic);font-weight:700;font-size:11px;letter-spacing:.3em;color:var(--tuna);margin-bottom:6px}
.mh-lead{font-size:13px;color:var(--ink2);margin-top:8px;line-height:1.8}
.mh-links{display:flex;flex-wrap:wrap;gap:8px 16px;font-size:12.5px;margin-top:8px}
.mh-links a{color:var(--sea);font-weight:700;text-underline-offset:3px}
/* 面見出し */
.men{display:flex;align-items:baseline;gap:12px;font-family:var(--mincho);font-weight:800;font-size:19px;letter-spacing:.2em;margin:30px 0 12px;padding-bottom:6px;border-bottom:2px solid var(--rule)}
.men .latin{font-family:var(--gothic);font-weight:500;font-size:10px;letter-spacing:.3em;text-transform:uppercase;color:var(--mute)}
.men .count-n{margin-left:auto;font-family:var(--gothic);font-size:12px;font-weight:500;color:var(--mute)}
/* 季節 */
.df{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 14px;border:1.5px solid var(--sea);padding:10px 14px;margin:0 0 14px;background:var(--sea-tint)}
.df .k{font-size:11px;font-weight:700;letter-spacing:.25em;color:var(--sea)}
.df .v{font-family:var(--mincho);font-weight:800;font-size:18px}
.df .n{flex-basis:100%;font-size:12px;color:var(--ink2)}
/* 絞り込み */
.filter{position:sticky;top:env(safe-area-inset-top,0px);z-index:20;background:var(--bg);padding:8px 0 10px;margin:22px 0 14px;border-bottom:1px solid var(--hair)}
.tabs{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;padding-bottom:4px;-webkit-overflow-scrolling:touch}
.tabs::-webkit-scrollbar{display:none}
.tabs button{flex:none;font-size:14px;font-weight:700;letter-spacing:.06em;background:var(--bg);border:1.5px solid var(--hair);border-radius:999px;padding:8px 14px;min-height:44px;cursor:pointer;white-space:nowrap}
.tabs button[aria-pressed="true"]{background:var(--sea);border-color:var(--sea);color:var(--on)}
.tabs button .n{font-weight:500;font-size:11px;margin-left:4px;opacity:.75}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;align-items:center}
.chips button{font-size:12.5px;background:var(--tint);border:1px solid var(--hair);border-radius:999px;padding:5px 11px;min-height:34px;cursor:pointer}
.chips button[aria-pressed="true"]{background:var(--tuna);border-color:var(--tuna);color:var(--on);font-weight:700}
.chips .tg{border-color:var(--sea);color:var(--sea);font-weight:700;background:var(--bg)}
.chips .tg[aria-pressed="true"]{background:var(--sea);color:var(--on)}
.chips .sep{width:1px;height:22px;background:var(--hair);margin:0 2px}
.empty{font-size:14px;color:var(--ink2);padding:18px 0}
.empty button{margin-left:8px;color:var(--sea);background:none;border:0;text-decoration:underline;cursor:pointer}
/* グリッド */
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px 12px}
@media (min-width:640px){ .grid{grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:24px 20px} }
.art{position:relative;display:flex;flex-direction:column;gap:6px;min-width:0;padding-top:10px;border-top:1px solid var(--rule);text-decoration:none}
.art[hidden]{display:none}
.thumb{position:relative;aspect-ratio:16/10;overflow:hidden;background:var(--tint)}
.thumb img{display:block;width:100%;height:100%;object-fit:cover;transition:transform .35s ease}
.art:hover .thumb img{transform:scale(1.03)}
.noimg{display:flex;align-items:center;justify-content:center;background:var(--sea-tint)}
.noimg span{font-family:var(--mincho);font-weight:800;font-size:clamp(18px,5vw,28px);letter-spacing:.3em;color:var(--sea);opacity:.8}
.ran{display:flex;align-items:center;flex-wrap:wrap;gap:4px 8px;font-size:11px;line-height:1.5}
.cat{display:inline-block;font-weight:700;letter-spacing:.12em;padding:1px 7px;border:1px solid var(--ink);color:var(--ink)}
.art[data-cat="食べる"] .cat,.d-meta .cat{background:var(--tuna);border-color:var(--tuna);color:var(--on)}
.art[data-cat="見る・歩く"] .cat,.art[data-cat="体験する"] .cat,.art[data-cat="季節"] .cat{background:var(--sea);border-color:var(--sea);color:var(--on)}
.art[data-cat="移動"] .cat,.art[data-cat="困ったとき"] .cat{border-color:var(--sea);color:var(--sea)}
.art.ev .cat{background:var(--tuna);border-color:var(--tuna);color:var(--on)}
.area{color:var(--mute);letter-spacing:.08em}
.walk{margin-left:auto;font-weight:700;color:var(--sea);white-space:nowrap;font-variant-numeric:tabular-nums}
.walk.far{color:var(--mute);font-weight:500}
.st{margin-left:auto;color:var(--mute);white-space:nowrap} .st.soon{color:var(--sea);font-weight:700} .st.now{color:var(--on);background:var(--sea);padding:0 6px;font-weight:700}
.art h3{font-family:var(--mincho);font-weight:700;font-size:16px;line-height:1.5;letter-spacing:.02em;text-wrap:balance}
.art h3 .open{all:unset;cursor:pointer;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.art h3 .open::after{content:"";position:absolute;inset:0;z-index:1}
.art:has(.open:focus-visible){outline:2px solid var(--sea);outline-offset:4px}
.art:hover h3 .open{color:var(--sea)}
.dt{font-size:11.5px;color:var(--mute);font-variant-numeric:tabular-nums}
.dt .cl{color:var(--tuna);font-weight:700}
.lede{font-size:13px;line-height:1.7;color:var(--ink2);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
@media (max-width:639px){ .art h3{font-size:15px} }
/* 詳細シート */
#sheet{border:0;padding:0;margin:auto;width:min(720px,100%);max-width:100%;max-height:min(92vh,100%);background:var(--bg);color:var(--ink);box-shadow:var(--shadow)}
#sheet::backdrop{background:rgba(8,25,40,.55)}
@media (max-width:639px){ #sheet{margin:auto 0 0;width:100%;max-height:92vh;border-radius:14px 14px 0 0} }
.sheet-in{max-height:inherit;overflow-y:auto;overscroll-behavior:contain;padding:0 20px calc(24px + env(safe-area-inset-bottom,0px))}
.sheet-bar{position:sticky;top:0;z-index:2;display:flex;justify-content:flex-end;padding:10px 0 6px;background:var(--bg)}
.sheet-close{border:1px solid var(--hair);background:var(--bg);border-radius:999px;padding:6px 16px;font-size:14px;cursor:pointer;min-height:40px}
.detail .photo{margin:0 -20px 12px}
.detail .photo img{display:block;width:100%;max-height:340px;object-fit:cover}
.detail .photo figcaption{font-size:10.5px;color:var(--mute);text-align:right;padding:4px 20px 0}
.d-meta{display:flex;align-items:center;flex-wrap:wrap;gap:6px 10px;font-size:12px;color:var(--mute);margin-bottom:6px}
.d-head{font-family:var(--mincho);font-weight:800;font-size:clamp(22px,5vw,28px);line-height:1.45;letter-spacing:.03em;margin-bottom:12px;text-wrap:balance}
.talk{border-left:4px solid var(--sea);background:var(--sea-tint);padding:10px 14px;font-size:15px;line-height:1.85;margin-bottom:14px}
.tl{display:block;font-size:10.5px;font-weight:700;letter-spacing:.25em;color:var(--sea);margin-bottom:2px}
.info{display:grid;grid-template-columns:auto 1fr;gap:6px 14px;font-size:14.5px;line-height:1.8;margin-bottom:14px}
.info dt{font-weight:700;color:var(--sea);white-space:nowrap;letter-spacing:.06em}
.maps{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px}
.maps a{display:inline-block;font-weight:700;font-size:14px;color:var(--on);background:var(--sea);padding:10px 16px;border-radius:999px;text-decoration:none;min-height:44px}
.maps a+a{background:var(--bg);color:var(--sea);border:1.5px solid var(--sea)}
.off a{font-weight:700;color:var(--sea);text-underline-offset:3px}
.src{font-size:11px;color:var(--mute);line-height:1.9;margin-top:10px}
.src .cf{font-weight:700;letter-spacing:.12em;margin-right:8px;color:var(--ink2)}
.src .chk{margin-left:8px}
.src a{margin-right:8px;text-underline-offset:2px}
/* 奥付 */
.okuzuke{margin-top:44px;border-top:3px double var(--rule);padding-top:12px;font-size:11.5px;line-height:1.9;color:var(--mute)}
.okuzuke a{color:var(--sea)}
</style>
</head>
<body>
<main>
<header class="masthead">
  <h1 class="daiji"><small>MIURA A-TEI · GUIDE</small>三浦A邸<br>ガイドブック</h1>
  <p class="mh-lead">三崎・城ヶ島・三浦海岸で、食べる・見る・体験する・買う。A邸からの徒歩時間つき。<br>$ymd 現在。毎朝自動で更新しています。</p>
  <p class="mh-links"><a href="$board">最近の三浦（近況・イベント）→</a></p>
</header>

<section class="sec" id="season">
  <h2 class="men">今の季節<span class="latin">$month</span></h2>
  <div class="grid">$df$season$events</div>
  $season_empty
</section>

<section class="sec" id="spots">
  <h2 class="men">おすすめの場所<span class="latin">Places</span><span class="count-n" id="count"></span></h2>
  <div class="filter">
    <div class="tabs"><button type="button" data-cat="all" aria-pressed="true">すべて<span class="n">$total</span></button>$tabs</div>
    <div class="chips" id="chips"></div>
  </div>
  <div class="grid" id="grid">$spots</div>
  <p class="empty" id="empty" hidden>この条件では見つかりません。<button type="button" id="reset">条件を外す</button></p>
</section>

<footer class="okuzuke">
出典確認＝公式や観光協会の案内を開いて確かめたもの／要確認＝一次でない・未確認。営業時間・定休は変わることがあります（各項目の「確認」日を参照）。<br>
徒歩時間は A邸からの直線距離×1.3÷80m/分 の目安。写真：Wikimedia Commons（$credits）、公式サイト、出典記事の og:image。<br>
<a href="$board">最近の三浦</a> · Since 2026.10 · By Yanuki
</footer>
</main>
<dialog id="sheet" aria-label="詳細"><div class="sheet-in"><div class="sheet-bar"><button type="button" class="sheet-close">閉じる</button></div><div class="sheet-body"></div></div></dialog>
<script>
(function(){
  var CATS=$cats_json;
  var cards=[].slice.call(document.querySelectorAll('#grid .spot'));
  var tabs=[].slice.call(document.querySelectorAll('.tabs button'));
  var chips=document.getElementById('chips'), empty=document.getElementById('empty'), count=document.getElementById('count');
  var state={cat:'all',tag:'',open:false,near:false};
  function readHash(){
    var h=location.hash.replace(/^#/,''); if(!h)return;
    h.split('&').forEach(function(kv){var p=kv.split('='),k=decodeURIComponent(p[0]),v=decodeURIComponent(p[1]||'');
      if(k==='cat'&&(v==='all'||CATS.indexOf(v)>=0))state.cat=v; if(k==='tag')state.tag=v; if(k==='open')state.open=v==='1'; if(k==='near')state.near=v==='1';});
  }
  function writeHash(){
    var q=[]; if(state.cat!=='all')q.push('cat='+encodeURIComponent(state.cat)); if(state.tag)q.push('tag='+encodeURIComponent(state.tag));
    if(state.open)q.push('open=1'); if(state.near)q.push('near=1');
    var nh=q.length?'#'+q.join('&'):''; if(nh!==location.hash){history.replaceState(null,'',location.pathname+location.search+nh);}
  }
  var now=new Date(), dow=(now.getDay()+6)%7, month=now.getMonth()+1, today=now.toISOString().slice(0,10);
  function openToday(el){
    var months=(el.dataset.months||'').split(',').filter(Boolean).map(Number); if(months.length&&months.indexOf(month)<0)return false;
    if(el.dataset.until&&el.dataset.until>=today)return false;
    if(el.dataset.closedKnown){var c=(el.dataset.closed||'').split(',').filter(Boolean).map(Number); if(c.indexOf(dow)>=0)return false;}
    return true;
  }
  function tagsOf(el){return (el.dataset.tags||'').split(',').filter(Boolean);}
  function render(){
    tabs.forEach(function(b){b.setAttribute('aria-pressed',String(b.dataset.cat===state.cat));});
    var inCat=cards.filter(function(el){return state.cat==='all'||el.dataset.cat===state.cat;});
    var tagCount={}; inCat.forEach(function(el){tagsOf(el).forEach(function(t){tagCount[t]=(tagCount[t]||0)+1;});});
    var tags=Object.keys(tagCount).sort(function(a,b){return tagCount[b]-tagCount[a]||a.localeCompare(b,'ja');}).slice(0,14);
    if(state.tag&&tags.indexOf(state.tag)<0)state.tag='';
    chips.innerHTML='';
    function chip(label,pressed,cls,fn){var b=document.createElement('button');b.type='button';b.textContent=label;b.className=cls||'';b.setAttribute('aria-pressed',String(pressed));b.addEventListener('click',fn);chips.appendChild(b);}
    chip('今日やっている',state.open,'tg',function(){state.open=!state.open;render();});
    chip('徒歩15分以内',state.near,'tg',function(){state.near=!state.near;render();});
    if(tags.length){var s=document.createElement('span');s.className='sep';chips.appendChild(s);}
    tags.forEach(function(t){chip(t,state.tag===t,'',function(){state.tag=state.tag===t?'':t;render();});});
    var shown=0;
    cards.forEach(function(el){
      var ok=(state.cat==='all'||el.dataset.cat===state.cat)&&(!state.tag||tagsOf(el).indexOf(state.tag)>=0)&&(!state.open||openToday(el))&&(!state.near||(el.dataset.walk!==''&&+el.dataset.walk<=15));
      el.hidden=!ok; if(ok)shown++;
    });
    empty.hidden=shown>0; count.textContent=shown+'件';
    writeHash();
  }
  tabs.forEach(function(b){b.addEventListener('click',function(){state.cat=b.dataset.cat;render();document.getElementById('spots').scrollIntoView({block:'start'});});});
  document.getElementById('reset').addEventListener('click',function(){state={cat:'all',tag:'',open:false,near:false};render();});
  window.addEventListener('hashchange',function(){state={cat:'all',tag:'',open:false,near:false};readHash();render();});
  /* 詳細シート（記事の中身をシートへ移し、閉じたら戻す） */
  var sheet=document.getElementById('sheet'), sbody=sheet.querySelector('.sheet-body'), sin=sheet.querySelector('.sheet-in'), home=null, cur=null, opener=null;
  function putBack(){ if(cur&&home){cur.hidden=true;home.appendChild(cur);} cur=home=null; if(opener){opener.focus();opener=null;} }
  function openCard(card,btn){ var det=card.querySelector('.detail'); if(!det)return; home=card;cur=det;opener=btn; sbody.appendChild(det); det.hidden=false; sin.scrollTop=0; if(sheet.showModal){sheet.showModal();}else{sheet.setAttribute('open','');} }
  function closeSheet(){ if(sheet.close&&sheet.open){sheet.close();}else{sheet.removeAttribute('open');putBack();} }
  sheet.addEventListener('close',putBack);
  sheet.addEventListener('click',function(e){if(e.target===sheet)closeSheet();});
  sheet.querySelector('.sheet-close').addEventListener('click',closeSheet);
  [].forEach.call(document.querySelectorAll('.art .open'),function(b){b.addEventListener('click',function(){openCard(b.closest('.art'),b);});});
  readHash(); render();
})();
</script>
</body>
</html>
''').substitute(ymd=f"{TODAY.year}年{TODAY.month}月{TODAY.day}日", board=BOARD, month=f"{TODAY.month}月 · {TODAY.strftime('%B')}",
                 df=df_card, season=season_html, events=events_html,
                 season_empty='' if (season_html or events_html) else '<p class="empty">いまは季節の項目がありません。</p>',
                 total=len(published), tabs="".join(f'<button type="button" data-cat="{esc(c)}" aria-pressed="false">{esc(c)}<span class="n">{counts[c]}</span></button>' for c in CATS),
                 spots=spots_html or '<p class="empty">掲載中の場所はまだありません。</p>', credits=credits, cats_json=json.dumps(CATS, ensure_ascii=False))
    (OUT / "index.html").write_text(page, encoding="utf-8")

    # ---- review.html（候補の確認用・noindex）
    def row(s):
        src = sources_html(s.get("sources", []))
        return f'''<tr><td><code>{esc(s["id"])}</code></td><td>{esc(s["category"])}</td><td><b>{esc(s["name"])}</b><br><small>{esc(s.get("note") or "")}</small></td><td>{esc(s["area"])}<br><small>{f"徒歩{s['_walk']}分" if s["_walk"] is not None else "座標なし"}</small></td><td><small>{esc(s.get("hours") or "—")}<br>{esc(closed_text(s))}<br>{esc(s.get("price") or "")}</small></td><td><small>{conf(s.get("confidence","🟡"))} {esc(s.get("last_checked") or "")}<br>{src}</small></td></tr>'''
    review = f'''<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>ガイドブック 候補の確認</title>
<style>body{{font-family:-apple-system,"Hiragino Sans",sans-serif;font-size:14px;line-height:1.6;color:#14202B;margin:0;padding:16px}}h1{{font-size:18px;margin:0 0 6px}}p{{margin:0 0 12px;color:#3E4C58}}table{{border-collapse:collapse;width:100%}}th,td{{border-top:1px solid #D9E1E8;padding:8px 6px;vertical-align:top;text-align:left}}th{{font-size:12px;color:#5A6A77;background:#F2F6F9}}@media(max-width:700px){{thead,tr:first-child{{display:none}}tr{{display:block;border-top:2px solid #0A5A8C;padding:8px 0}}td{{display:block;border:0;padding:2px 0}}td:first-child{{font-weight:700}}}}code{{background:#F2F6F9;padding:1px 5px}}small{{color:#5A6A77}}.pub{{color:#0A5A8C}}</style></head><body>
<h1>ガイドブック 候補の確認（{TODAY.isoformat()}）</h1>
<p>載せてよいものは id を伝えてください（例「◎: misaki_asaichi, urari」）。掲載中は {len(published)} 件、候補は {len(candidates)} 件。</p>
<h2>候補（未掲載）</h2>
<table><tr><th>id</th><th>分類</th><th>名前／ひとこと</th><th>場所／徒歩</th><th>営業・休み・料金</th><th>確認・出典</th></tr>{"".join(row(s) for s in candidates) or "<tr><td colspan=6>候補はありません</td></tr>"}</table>
<h2 class="pub">掲載中（◎）</h2>
<table><tr><th>id</th><th>分類</th><th>名前／ひとこと</th><th>場所／徒歩</th><th>営業・休み・料金</th><th>確認・出典</th></tr>{"".join(row(s) for s in published) or "<tr><td colspan=6>まだありません</td></tr>"}</table>
</body></html>'''
    (OUT / "review.html").write_text(review, encoding="utf-8")
    (OUT / "manifest.webmanifest").write_text(json.dumps({"name": "三浦A邸 ガイドブック", "short_name": "A邸ガイド", "start_url": "./", "display": "browser", "background_color": "#FFFFFF", "theme_color": "#0A5A8C",
        "icons": [{"src": "../img/icon-180.png", "sizes": "180x180", "type": "image/png"}, {"src": "../img/icon-512.png", "sizes": "512x512", "type": "image/png"}]}, ensure_ascii=False, indent=1), encoding="utf-8")
    # ---- アイコン（無ければ作る）
    for size in (180, 512):
        p = HERE / "img" / f"icon-{size}.png"
        if p.exists(): continue
        try:
            from PIL import Image, ImageDraw, ImageFont
            im = Image.new("RGB", (size, size), "#0A5A8C"); dr = ImageDraw.Draw(im)
            dr.rectangle([0, int(size * .78), size, size], fill="#B8243A")
            try: f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", int(size * .62))
            except Exception: f = ImageFont.load_default()
            bb = dr.textbbox((0, 0), "A", font=f); w, h = bb[2] - bb[0], bb[3] - bb[1]
            dr.text(((size - w) / 2 - bb[0], (size * .78 - h) / 2 - bb[1]), "A", fill="white", font=f)
            im.save(p)
        except Exception as e:
            print("icon skipped:", e)
    print(f"guide/: {len(published)} 掲載, {len(candidates)} 候補, 季節 {len(season_spots)}, イベント {len(ev)}+{len(ups)}")

if __name__ == "__main__":
    build()
