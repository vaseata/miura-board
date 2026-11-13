#!/usr/bin/env python3
"""「三崎を知る」の2ページ（2026-11-14 ヤヌキ判断・判断シート https://claude.ai/artifact/RTG7TLxnRQQ6x8sK1qzzCB ）
  hae.json  → guide/hae/index.html・guide/hae/en/index.html（三崎の映えスポット：季節の花と景色・ダイヤモンド富士）
  hito.json → guide/hito/index.html・guide/hito/en/index.html（三崎の人）
              house_faq/hito_review.html（存命の人の候補。公開しない・コミットしない）
歴史さんぽ（history/）は history_build.py。お店・名所のトップの「三崎を知る」の面は guide_build.py の know_html()。

決まり
- 出典は開いたものだけ（items と同じ）。sources に url・title・opened
- 三崎の人：故人は出典で載せる。存命の人は本人の許しを得てから（status を ◎ にできるのはヤヌキだけ。Claude は 候補 で足す）。
  書くのは公開記事にある仕事の話だけ（家族・住まい・年齢は書かない）。写真は本人か店の公式のものだけ
- ダイヤモンド富士：映えページには常設（calendar.json の城ヶ島大橋の2回から次の日を計算）。お店・名所の「今の季節」は30日以内だけのまま
- A邸の位置は出さない（home.local.json は読まない）
"""
import json, datetime, html, pathlib
from ui_parts import UI_CSS, sitenav
from guide_build import LANG_CSS, LANG_JS, langswitch

HERE = pathlib.Path(__file__).parent
TODAY = datetime.date.today()
SITE = "https://vaseata.github.io/miura-board/guide/"
MONTH_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WD, WD_EN = "月火水木金土日", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
NOWC = ' class="now"'
CONF = {"🟢": ("出典確認", "Source checked"), "🟡": ("要確認", "To be confirmed"), "🗣": ("伝聞", "Hearsay")}


def esc(s): return html.escape(str(s if s is not None else ""), quote=True)
def T(o, k, E):
    """英語版なら k_en（無ければ日本語のまま）"""
    return (o.get(k + "_en") or o.get(k)) if E else o.get(k)
def jl(o, k, E):
    """英語版で訳が無い欄には lang="ja" を付ける"""
    return ' lang="ja"' if (E and not o.get(k + "_en") and o.get(k)) else ""
def srcs(lst, E):
    if not lst: return ""
    a = " / ".join(f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["title"])}</a>' for s in lst)
    return f'<p class="src">{"Sources (mostly Japanese): " if E else "出典："}{a}</p>'
def conf(c, E): return CONF.get(c, (c, c))[1 if E else 0]
def months_label(ms, E):
    if not ms: return ""
    ms = sorted(ms)
    if 1 in ms and 12 in ms and len(ms) < 12:   # 11月〜4月のように年をまたぐときは、切れ目から始める
        k = max(i for i in range(len(ms)) if i == 0 or ms[i] != ms[i - 1] + 1)
        ms = ms[k:] + ms[:k]
    runs, start, prev = [], ms[0], ms[0]
    for m in ms[1:] + [None]:
        if m is not None and m == prev % 12 + 1: prev = m; continue
        runs.append((start, prev)); start = prev = m
    f = (lambda m: MONTH_EN[m - 1]) if E else (lambda m: f"{m}月")
    return ("、" if not E else ", ").join(f(a) if a == b else f"{f(a)}–{f(b)}" if E else f"{f(a)}〜{f(b)}" for a, b in runs)
def jdate(dt, E, approx):
    if E: return ("around " if approx else "") + f"{MONTH_EN[dt.month - 1]} {dt.day} ({WD_EN[dt.weekday()]})"
    return f"{dt.month}月{dt.day}日（{WD[dt.weekday()]}）" + ("ごろ" if approx else "")


CSS = r""":root{ color-scheme:light;
  --bg:#FFFFFF; --ink:#14202B; --ink2:#3E4C58; --mute:#4F6070; --rule:#14202B; --hair:#D9E1E8; --tint:#F2F6F9;
  --sea:#0A5A8C; --sea-tint:#E6F0F6; --tuna:#B8243A; --kon:#2E4C9E; --on:#FFFFFF;
  --mincho:"Shippori Mincho","Hiragino Mincho ProN","Yu Mincho",serif;
  --gothic:"Zen Kaku Gothic New","Hiragino Sans","Hiragino Kaku Gothic ProN","Yu Gothic",sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--gothic);background:var(--bg);color:var(--ink);line-height:1.75;font-size:15.5px;font-feature-settings:"palt";-webkit-font-smoothing:antialiased;overflow-x:hidden}
main{max-width:1040px;margin:0 auto;padding:12px max(16px,env(safe-area-inset-right)) 56px max(16px,env(safe-area-inset-left))}
@media (min-width:720px){ main{padding-inline:28px} .sn-in{padding-inline:28px} }
a{color:var(--sea)} button{font:inherit;color:inherit}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 10px}
.topbar .back{display:inline-flex;align-items:center;min-height:44px;font-weight:700;text-decoration:none}
.masthead{padding:4px 0 12px;border-bottom:4px solid var(--sea);position:relative}
.masthead::after{content:"";position:absolute;left:0;right:0;bottom:-8px;border-bottom:1px solid var(--sea)}
.daiji{font-family:var(--mincho);font-weight:800;font-size:clamp(28px,7vw,48px);line-height:1.2;letter-spacing:.1em}
.daiji small{display:block;font-family:var(--gothic);font-weight:700;font-size:11px;letter-spacing:.3em;color:var(--kon);margin-bottom:6px}
.mh-lead{font-size:14px;color:var(--ink2);margin-top:10px;line-height:1.85;max-width:40em}
.men{display:flex;align-items:baseline;flex-wrap:wrap;gap:4px 12px;font-family:var(--mincho);font-weight:800;font-size:19px;letter-spacing:.16em;margin:34px 0 12px;padding-bottom:6px;border-bottom:2px solid var(--rule)}
.men .latin{font-family:var(--gothic);font-weight:500;font-size:10px;letter-spacing:.3em;text-transform:uppercase;color:var(--mute)}
.sub{font-size:13px;color:var(--ink2);margin:-4px 0 12px}
/* ダイヤモンド富士 */
.df{display:grid;gap:10px;border:1.5px solid var(--sea);border-radius:14px;padding:14px 16px;background:var(--sea-tint)}
.df .k{font-size:11px;font-weight:700;letter-spacing:.2em;color:var(--sea)}
.df h3{font-family:var(--mincho);font-weight:800;font-size:22px;line-height:1.35}
.df .dates{display:flex;flex-wrap:wrap;gap:8px}
.df .d{display:flex;flex-direction:column;min-width:140px;padding:8px 12px;border-radius:12px;background:var(--bg);border:1px solid var(--hair)}
.df .d b{font-size:16px;font-variant-numeric:tabular-nums}
.df .d span{font-size:12px;color:var(--mute)}
.df .d.next{border-color:var(--sea);box-shadow:0 0 0 1px var(--sea)}
.df .d.next span{color:var(--sea);font-weight:700}
.df p{font-size:14px;line-height:1.8}
/* 月の表 */
.cal{overflow-x:auto;-webkit-overflow-scrolling:touch;border:1px solid var(--hair);border-radius:12px}
.cal table{border-collapse:separate;border-spacing:0;width:100%;min-width:340px;font-size:12.5px;table-layout:fixed}
.cal col.c0{width:120px}
.cal th,.cal td{padding:6px 0;text-align:center;border-bottom:1px solid var(--hair)}
.cal tr:last-child td,.cal tr:last-child th{border-bottom:0}
.cal thead th{font-weight:700;color:var(--mute);font-size:11px;font-variant-numeric:tabular-nums}
.cal th.nm{position:sticky;left:0;z-index:1;background:var(--bg);text-align:left;padding:6px 6px 6px 8px;font-weight:700;font-size:12px;line-height:1.35}
.cal th.nm a{color:var(--ink);text-decoration:none}
.cal td i{display:block;height:14px;margin:0 1px;border-radius:3px}
.cal td.on i{background:var(--sea)}
.cal .now{background:var(--sea-tint)}
.cal thead th.now{color:var(--sea)}
.legend{font-size:12px;color:var(--mute);margin-top:6px}
/* カード */
.grid{display:grid;grid-template-columns:1fr;gap:22px}
@media (min-width:640px){ .grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:26px 22px} }
@media (min-width:960px){ .grid.three{grid-template-columns:repeat(3,minmax(0,1fr))} }
.card{display:flex;flex-direction:column;gap:6px;min-width:0;padding-top:10px;border-top:1px solid var(--rule);scroll-margin-top:12px}
.thumb{aspect-ratio:16/10;overflow:hidden;background:var(--tint);border-radius:4px}
.thumb img{display:block;width:100%;height:100%;object-fit:cover}
.ran{display:flex;align-items:center;flex-wrap:wrap;gap:4px 8px;font-size:11.5px;line-height:1.5}
.cat{display:inline-block;font-weight:700;letter-spacing:.1em;padding:1px 7px;background:var(--sea);color:var(--on)}
.area{color:var(--mute);letter-spacing:.06em}
.st{margin-left:auto;font-weight:700;color:var(--sea);white-space:nowrap}
.card h3{font-family:var(--mincho);font-weight:800;font-size:19px;line-height:1.45;text-wrap:balance}
.card h3 small{display:block;font-family:var(--gothic);font-weight:500;font-size:12px;color:var(--mute);letter-spacing:.04em}
.card p{font-size:14.5px;line-height:1.85;color:var(--ink)}
.card .when{font-size:13px;color:var(--ink2)}
.card .when b{color:var(--sea);margin-right:6px}
.card .trace{border-left:4px solid var(--sea);background:var(--sea-tint);padding:8px 12px;font-size:14px}
.card .trace b{display:block;font-size:10.5px;letter-spacing:.2em;color:var(--sea)}
.links{display:flex;flex-wrap:wrap;gap:4px 14px}
.src{font-size:11.5px !important;color:var(--mute) !important;line-height:1.8 !important}
.src a{color:var(--mute);margin-right:4px}
.src .cf{font-weight:700;margin-right:6px}
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.note{font-size:13px;color:var(--ink2);border:1px dashed var(--hair);border-radius:12px;padding:10px 14px;margin-top:14px}
.okuzuke{margin-top:44px;border-top:3px double var(--rule);padding-top:12px;font-size:11.5px;line-height:1.9;color:var(--mute)}
.okuzuke a{color:var(--sea)}
"""


def page(E, R, title, desc, small, h1, lead, body, foot, alt_path):
    return f'''<!DOCTYPE html>
<html lang="{"en" if E else "ja"}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="{esc(desc)}">
<link rel="alternate" hreflang="ja" href="{SITE}{alt_path}"><link rel="alternate" hreflang="en" href="{SITE}{alt_path}en/">
<meta name="theme-color" content="#0A5A8C">
<title>{esc(title)}</title>
<link rel="icon" href="{R}img/brand/logo.png">
<link rel="apple-touch-icon" href="{R}img/icon-180.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@500;700;800&family=Zen+Kaku+Gothic+New:wght@400;500;700&display=swap" rel="stylesheet">
<style>{CSS}{UI_CSS}{LANG_CSS}
.topbar{{justify-content:space-between}}</style>
</head>
<body>
{sitenav("guide", R, lang="en" if E else "ja", is_top=False, sos=True)}
<main>
<div class="topbar"><a class="back" href="{"../../../guide/en/" if E else "../"}">← {"Eat &amp; See" if E else "お店・名所"}</a>{langswitch("en" if E else "ja")}</div>
<header class="masthead">
  <h1 class="daiji"><small>{small}</small>{h1}</h1>
  <p class="mh-lead">{lead}</p>
</header>
{body}
<footer class="okuzuke">{foot}</footer>
</main>
{LANG_JS}
</body>
</html>
'''


def credit_list(keys, places, E):
    """Wikimedia Commons の写真の作者とライセンス（CC BY などは作者名の表示が要る）"""
    out = []
    for k in dict.fromkeys(k for k in keys if k):
        p = places.get(k)
        if not p or not p.get("source", "").startswith("https://commons"): continue
        who = p.get("credit") or ""
        who = "" if "<" in who else who
        out.append(f'<a href="{esc(p["source"])}" target="_blank" rel="noopener">{esc(p.get("caption") or k)}</a>' + (f" {esc(who)}" if who else "") + f' ({esc(p["license"])})')
    return out


# ───────── 映えスポット ─────────
def df_next(cal):
    """calendar.json の城ヶ島大橋のダイヤモンド富士（年2回）から、今年と来年の日を並べ、次の日を返す"""
    evs = [e for e in cal if "ダイヤモンド富士" in e.get("fact", "")]
    dates = []
    for e in evs:
        mm, dd = map(int, e["month_day"].split("-"))
        for y in (TODAY.year, TODAY.year + 1):
            dates.append((datetime.date(y, mm, dd), e))
    dates.sort(key=lambda t: t[0])
    return evs, [t for t in dates if t[0] >= TODAY]


def build_hae(E, doc, places, cal):
    R = "../../../" if E else "../../"
    spots = doc["spots"]
    m = TODAY.month
    in_now = lambda s: m in (s.get("months") or [])
    order = sorted(spots, key=lambda s: (not in_now(s), min(((x - m) % 12 for x in s.get("months") or [m]))))

    # ダイヤモンド富士（常設）
    evs, ups = df_next(cal)
    df = doc.get("diamond_fuji", {})
    chips = []
    for i, (dt, e) in enumerate(ups[:2]):
        n = (dt - TODAY).days
        left = ("today" if n == 0 else f"in {n} days") if E else ("今日" if n == 0 else f"あと{n}日")
        chips.append(f'<div class="d{" next" if i == 0 else ""}"><b>{jdate(dt, E, e.get("approx"))}</b><span>{left}</span></div>')
    df_src = df.get("sources") or ([evs[0]["source"]] if evs and evs[0].get("source") else [])
    df_html = f'''<section aria-labelledby="df-h">
<h2 class="men" id="df-h">{"Diamond Fuji" if E else "ダイヤモンド富士"}<span class="latin">{"Twice a year" if E else "Diamond Fuji · twice a year"}</span></h2>
<div class="df">
  <span class="k">{"FROM JOGASHIMA BRIDGE · AT SUNSET" if E else "城ヶ島大橋から・日没"}</span>
  <h3{jl(df, "head", E)}>{esc(T(df, "head", E))}</h3>
  <div class="dates">{"".join(chips)}</div>
  <p{jl(df, "text", E)}>{esc(T(df, "text", E))}</p>
  {srcs(df_src, E)}
</div>
</section>'''

    # 月の表
    head = "".join(f'<th scope="col"{NOWC if i == m else ""}>{MONTH_EN[i - 1][:1] if E else i}</th>' for i in range(1, 13))
    rows = "".join(
        f'<tr><th class="nm" scope="row"><a href="#{esc(s["id"])}"{jl(s, "short", E)}>{esc(T(s, "short", E) or T(s, "name", E))}</a></th>'
        + "".join(f'<td class="{"on" if i in s.get("months", []) else ""}{" now" if i == m else ""}"><i></i></td>' for i in range(1, 13)) + "</tr>"
        for s in sorted(spots, key=lambda s: (min(s.get("months") or [13]), s["id"])) if s.get("months"))
    dfm = sorted({int(e["month_day"][:2]) for e in evs})
    rows += (f'<tr><th class="nm" scope="row"><a href="#df-h">{"Diamond Fuji" if E else "ダイヤモンド富士"}</a></th>'
             + "".join(f'<td class="{"on" if i in dfm else ""}{" now" if i == m else ""}"><i></i></td>' for i in range(1, 13)) + "</tr>")
    cal_html = f'''<section aria-labelledby="cal-h">
<h2 class="men" id="cal-h">{"When to go" if E else "見ごろの月"}<span class="latin">{"Flowers &amp; views by month" if E else "Season calendar"}</span></h2>
<p class="sub">{"Blue = usually at its best. The shaded column is this month. Timing shifts a little each year." if E else "青い所が例年の見ごろ。色のついた列が今月です。年によって前後します。"}</p>
<div class="cal"><table><colgroup><col class="c0"><col span="12"></colgroup><thead><tr><th class="nm" scope="col"><span class="vh">{"Spot" if E else "場所"}</span></th>{head}</tr></thead><tbody>{rows}</tbody></table></div>
</section>'''

    def when_line(s, when, E):
        note = T(s, "when_note", E)
        if not when and not note: return ""
        body = esc(when) + (("　" if not E else " · ") if when and note else "") + esc(note or "")
        return f'<p class="when"{jl(s, "when_note", E) if not when else ""}><b>{("Best" if when else "Season") if E else ("見ごろ" if when else "季節")}</b>{body}</p>'

    def card(s):
        p = places.get(s.get("image") or "")
        img = f'<div class="thumb"><img src="{R}{esc(p["file"])}" alt="" loading="lazy" width="480" height="300"></div>' if p else ""
        st = f'<span class="st">{"In season now" if E else "今が見ごろ"}</span>' if in_now(s) else ""
        when = months_label(s.get("months"), E)
        tod = T(s, "time_of_day", E)
        maps = (f'<a href="https://www.google.com/maps/search/?api=1&query={s["lat"]},{s["lon"]}" target="_blank" rel="noopener">{"Open in Google Maps" if E else "Googleマップで開く"}</a>'
                if s.get("lat") and s.get("lon") else "")
        return f'''<article class="card" id="{esc(s["id"])}">{img}
<div class="ran"><span class="cat"{jl(s, "kind", E)}>{esc(T(s, "kind", E))}</span><span class="area"{jl(s, "area", E)}>{esc(T(s, "area", E))}</span>{st}</div>
<h3{jl(s, "name", E)}>{esc(T(s, "name", E))}</h3>
{when_line(s, when, E)}
<p{jl(s, "what", E)}>{esc(T(s, "what", E))}</p>
{f'<p class="when"{jl(s, "time_of_day", E)}><b>{"Tip" if E else "ひとこと"}</b>{esc(tod)}</p>' if tod else ""}
<div class="links">{maps}</div>
{srcs(s.get("sources"), E).replace('<p class="src">', f'<p class="src"><span class="cf">{conf(s.get("confidence"), E)}</span>').replace("出典：", "").replace("Sources (mostly Japanese): ", "")}
</article>'''
    cards = f'''<section aria-labelledby="sp-h">
<h2 class="men" id="sp-h">{"Spots" if E else "場所"}<span class="latin">{"In season first" if E else "Photo spots"}</span></h2>
<div class="grid three">{"".join(card(s) for s in order)}</div>
</section>'''

    credits = credit_list([s.get("image") for s in spots], places, E)
    foot = (("Source checked = confirmed on an official or tourism-association page; To be confirmed = secondary source. Flowers bloom earlier or later depending on the year. Photos: Wikimedia Commons (" + ", ".join(credits) + "). Translated from the Japanese; if they differ, the Japanese version is correct.<br>"
             '<a href="../../../history/en/">Miura History Walk</a> · <a href="../../hito/en/">People of Misaki</a> · By Yanuki')
            if E else
            ("出典確認＝公式や観光協会のページで確かめたもの／要確認＝一次でない出典。花の時期は年によって前後します。写真：Wikimedia Commons（" + "、".join(credits) + "）。<br>"
             '<a href="../../history/">歴史さんぽ</a> · <a href="../hito/">三崎の人</a> · By Yanuki'))
    lead = ("Where the flowers bloom and the views open up around Misaki, Jogashima and Miura Kaigan, month by month. Diamond Fuji from Jogashima Bridge is listed all year."
            if E else "三崎・城ヶ島・三浦海岸で、季節の花と、写真に残したい景色。いつ・どこへ行けばいいかを月ごとに。城ヶ島大橋のダイヤモンド富士も、いつでも見られるようにしています。")
    out = HERE / "guide" / "hae" / ("en" if E else "")
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page(E, R, "Misaki Photo Spots | Miura A-tei" if E else "三崎の映えスポット｜三浦A邸",
        "Seasonal flowers and photo spots around Misaki and Jogashima, and when to see Diamond Fuji from Jogashima Bridge." if E else "三崎・城ヶ島・三浦海岸の季節の花と映えスポット。城ヶ島大橋のダイヤモンド富士の時期も。",
        "MIURA A-TEI · PHOTO SPOTS", "Misaki<br>Photo Spots" if E else "三崎の<br>映えスポット", lead,
        df_html + cal_html + cards, foot, "hae/"), encoding="utf-8")
    return len(spots)


# ───────── 三崎の人 ─────────
def build_hito(E, doc, places):
    R = "../../../" if E else "../../"
    pub = [p for p in doc["people"] if p.get("status") == "◎"]
    past = [p for p in pub if p.get("kind") == "past"]
    living = [p for p in pub if p.get("kind") == "living"]
    hist = R + ("history/en/" if E else "history/")

    def card(p):
        img = places.get(p.get("image") or "")
        im = f'<div class="thumb"><img src="{R}{esc(img["file"])}" alt="" loading="lazy" width="480" height="300"></div>' if img else ""
        sub = " · ".join(x for x in [T(p, "reading", E) if not E else "", p.get("years"), T(p, "role", E)] if x)
        trace = T(p, "traces", E)
        links = []
        if p.get("history"): links.append(f'<a href="{hist}">{"See it on the History Walk map" if E else "歴史さんぽの地図で見る"}</a>')
        for l in p.get("links", []): links.append(f'<a href="{esc(l["url"])}" target="_blank" rel="noopener">{esc(T(l, "title", E))}</a>')
        return f'''<article class="card" id="{esc(p["id"])}">{im}
<div class="ran"><span class="cat"{jl(p, "tag", E)}>{esc(T(p, "tag", E))}</span><span class="area"{jl(p, "area", E)}>{esc(T(p, "area", E))}</span></div>
<h3{jl(p, "name", E)}>{esc(T(p, "name", E))}<small>{esc(sub)}</small></h3>
<p{jl(p, "facts", E)}>{esc(T(p, "facts", E))}</p>
{f'<div class="trace"{jl(p, "traces", E)}><b>{"SEE IT TODAY" if E else "いま見られる所"}</b>{esc(trace)}</div>' if trace else ""}
<div class="links">{"".join(links)}</div>
{srcs(p.get("sources"), E).replace('<p class="src">', f'<p class="src"><span class="cf">{conf(p.get("confidence"), E)}</span>').replace("出典：", "").replace("Sources (mostly Japanese): ", "")}
</article>'''

    body = f'''<section aria-labelledby="past-h">
<h2 class="men" id="past-h">{"People of the past" if E else "三崎ゆかりの人"}<span class="latin">{"Writers, lords and others" if E else "History"}</span></h2>
<div class="grid">{"".join(card(p) for p in past)}</div>
</section>'''
    if living:
        body += f'''<section aria-labelledby="now-h">
<h2 class="men" id="now-h">{"Misaki people today" if E else "いまの三崎の人"}<span class="latin">{"With their permission" if E else "Today"}</span></h2>
<div class="grid">{"".join(card(p) for p in living)}</div>
</section>'''
    body += f'<p class="note">{"People working in Misaki today are introduced only with their permission. We write only about their work, as published in articles." if E else "いま三崎で働いている人は、ご本人の了解をいただいてから紹介します。書くのは、記事などで公になっている仕事の話だけです。"}</p>'
    cr = credit_list([p.get("image") for p in pub], places, E)
    foot = (("Source checked = confirmed on an official or tourism-association page; To be confirmed = secondary source such as Wikipedia. " + ("Photos: Wikimedia Commons (" + ", ".join(cr) + "). " if cr else "") + "Translated from the Japanese; if they differ, the Japanese version is correct.<br>"
             f'<a href="{hist}">Miura History Walk</a> · <a href="../../hae/en/">Photo spots</a> · By Yanuki') if E else
            ("出典確認＝三浦市・観光協会などのページで確かめたもの／要確認＝Wikipedia など一次でない出典。" + ("写真：Wikimedia Commons（" + "、".join(cr) + "）。" if cr else "") + "<br>"
             f'<a href="{hist}">歴史さんぽ</a> · <a href="../hae/">映えスポット</a> · By Yanuki'))
    lead = ("The people whose stories are woven into Misaki — the poet who sang of rain on Jogashima, and more. Their traces are still here to visit."
            if E else "「城ヶ島の雨」の白秋をはじめ、三崎に足あとを残した人たち。いまも歩いて会いに行ける場所があります。")
    out = HERE / "guide" / "hito" / ("en" if E else "")
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page(E, R, "People of Misaki | Miura A-tei" if E else "三崎の人｜三浦A邸",
        "People linked to Misaki, Miura, and the places where you can still find their traces." if E else "三崎ゆかりの人と、いまも訪ねられるゆかりの場所。",
        "MIURA A-TEI · PEOPLE", "People of<br>Misaki" if E else "三崎の人", lead, body, foot, "hito/"), encoding="utf-8")
    return len(past), len(living)


def build_hito_review(doc):
    """存命の人の候補（公開しない）。house_faq/ はコミットしない"""
    cand = [p for p in doc["people"] if p.get("status") != "◎"]
    def row(p):
        s = "<br>".join(f'<a href="{esc(x["url"])}">{esc(x["title"])}</a> {esc(x.get("date", ""))}' for x in p.get("sources", []))
        return f'<tr><td><code>{esc(p["id"])}</code><br>{esc(p.get("status"))}</td><td><b>{esc(p["name"])}</b><br><small>{esc(p.get("role", ""))}</small></td><td>{esc(p.get("facts", ""))}</td><td><small>{s}</small></td></tr>'
    (HERE / "house_faq").mkdir(exist_ok=True)
    (HERE / "house_faq" / "hito_review.html").write_text(f'''<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>三崎の人 候補の確認</title>
<style>body{{font-family:-apple-system,"Hiragino Sans",sans-serif;font-size:14px;line-height:1.6;color:#14202B;margin:0;padding:16px}}table{{border-collapse:collapse;width:100%}}th,td{{border-top:1px solid #D9E1E8;padding:8px 6px;vertical-align:top;text-align:left}}th{{font-size:12px;color:#5A6A77;background:#F2F6F9}}@media(max-width:700px){{tr:first-child{{display:none}}tr{{display:block;border-top:2px solid #0A5A8C;padding:8px 0}}td{{display:block;border:0;padding:2px 0}}}}small{{color:#5A6A77}}</style></head><body>
<h1 style="font-size:18px">三崎の人 候補の確認（{TODAY.isoformat()}・公開していません）</h1>
<p>本人の了解が取れた人の id を「◎: id」で伝えてください。了解の範囲（名前・店名・写真）も一言あると助かります。</p>
<table><tr><th>id</th><th>名前・役割</th><th>載せる予定の文（記事にある仕事の話だけ）</th><th>出典</th></tr>{"".join(row(p) for p in cand) or "<tr><td colspan=4>候補はありません</td></tr>"}</table></body></html>''', encoding="utf-8")
    return len(cand)


def main():
    places = json.load(open(HERE / "places.json"))["images"]
    cal = json.load(open(HERE / "calendar.json"))["events"]
    hae = json.load(open(HERE / "hae.json"))
    hito = json.load(open(HERE / "hito.json"))
    kp = HERE / "hito_kouho.local.json"   # 存命の人の候補（公開しない）
    if kp.exists(): hito["people"] += json.load(open(kp))["people"]
    for E in (False, True):
        n = build_hae(E, hae, places, cal)
        a, b = build_hito(E, hito, places)
    c = build_hito_review(hito)
    print(f"guide/hae/: {n}か所（日・英） / guide/hito/: ゆかりの人 {a}・いまの人 {b}（日・英） / 候補 {c}（house_faq/hito_review.html・非公開）")


if __name__ == "__main__":
    main()
