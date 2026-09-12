#!/usr/bin/env python3
"""items.json + calendar.json → index.html（最近の三浦）"""
import json, datetime, html, pathlib

HERE = pathlib.Path(__file__).parent
TODAY = datetime.date.today()
items = json.load(open(HERE / "items.json"))["items"]
cal = json.load(open(HERE / "calendar.json"))["events"]
places = json.load(open(HERE / "places.json"))["images"]
videos = json.load(open(HERE / "videos.json"))["videos"] if (HERE / "videos.json").exists() else []

def d(s): return datetime.date.fromisoformat(s)
def esc(s): return html.escape(s, quote=True)

# ---- 日付つき項目（新しい順）。1年より古いものは出さない
items = [x for x in items if (TODAY - d(x["date"])).days <= 366]
items.sort(key=lambda x: x["date"], reverse=True)

# ---- 定番：今日から120日以内の次回
upcoming = []
for e in cal:
    mm, dd = map(int, e["month_day"].split("-"))
    for y in (TODAY.year, TODAY.year + 1):
        try: dt = datetime.date(y, mm, dd)
        except ValueError: continue
        if 0 <= (dt - TODAY).days <= 120:
            upcoming.append((dt, e)); break
upcoming.sort(key=lambda t: t[0])

# ---- 次のダイヤモンド富士（120日を超えても出す）
nxt_df = None
for e in cal:
    if "ダイヤモンド富士" in e["fact"]:
        mm, dd = map(int, e["month_day"].split("-"))
        for y in (TODAY.year, TODAY.year + 1):
            dt = datetime.date(y, mm, dd)
            if dt >= TODAY and (nxt_df is None or dt < nxt_df[0]): nxt_df = (dt, e)

WD = "月火水木金土日"
def jdate(dt, approx=False):
    s = f"{dt.month}/{dt.day}({WD[dt.weekday()]})"
    return s + "頃" if approx else s

def days_ago(dt):
    n = (TODAY - dt).days
    if n < 0: return f"{-n}日後"
    if n == 0: return "今日"
    if n < 30: return f"{n}日前"
    if n < 365: return f"{n//30}ヶ月前"
    return "1年前"

def img_html(key):
    p = places.get(key or "")
    if not p: return ""
    return f'<img class="thumb" src="{esc(p["file"])}" alt="" loading="lazy" width="480" height="300">'

def item_html(x):
    dt = d(x["date"]); age = (TODAY - dt).days
    src = " ".join(f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["title"])}</a>' for s in x.get("sources", []))
    period = esc(x["date"][:7])
    end = f'〜{jdate(d(x["end"]))}' if x.get("end") else ""
    return f'''<li class="item cat-{esc(x["category"])}" data-age="{age}">
  <div class="when"><span class="date">{jdate(dt)}{end}</span><span class="ago">{days_ago(dt)}</span></div>
  <div class="body">{img_html(x.get("image"))}
    <div class="tags"><span class="chip">{esc(x["category"])}</span><span class="area">{esc(x["area"])}</span><span class="conf" title="確信度">{x["confidence"]}</span></div>
    <p class="fact">{esc(x["fact"])}</p>
    <p class="talk">{esc(x["talk"])}</p>
    <p class="src">{src}</p>
  </div>
</li>'''

def up_html(dt, e):
    return f'''<li class="item cat-{esc(e["category"])}">
  <div class="when"><span class="date">{jdate(dt, e.get("approx"))}</span><span class="ago">{(dt-TODAY).days}日後</span></div>
  <div class="body">{img_html(e.get("image"))}
    <div class="tags"><span class="chip">{esc(e["category"])}</span><span class="conf">{e["confidence"]}</span></div>
    <p class="fact">{esc(e["fact"])}</p>
    <p class="talk">{esc(e["talk"])}</p>
    <p class="src"><a href="{esc(e["source"]["url"])}" target="_blank" rel="noopener">{esc(e["source"]["title"])}</a></p>
  </div>
</li>'''

def video_html(v):
    dt = d(v["published"]); ago = days_ago(dt)
    th = f'img/yt/{v["id"]}.jpg'
    img = f'<img src="{th}" alt="" loading="lazy" width="320" height="180">' if (HERE / th).exists() else '<div class="noimg"></div>'
    badge = '<span class="live">LIVE</span>' if v.get("live") else ""
    return f'''<a class="vid" href="https://www.youtube.com/watch?v={esc(v["id"])}" target="_blank" rel="noopener">
  <div class="vthumb">{img}{badge}</div>
  <div class="vtitle">{esc(v["title"])}</div>
  <div class="vmeta">{esc(v["channel"])}・{esc(ago if not v.get("live") else "配信中")}</div>
</a>'''
videos_html = "".join(video_html(v) for v in videos) or '<p class="empty">まだ動画がありません</p>'

# 月ごとにまとめる
groups = []
for x in items:
    key = x["date"][:7]
    if not groups or groups[-1][0] != key: groups.append((key, []))
    groups[-1][1].append(x)

groups_html = "\n".join(
    f'<section class="month" data-month="{k}"><h2>{int(k[:4])}年{int(k[5:])}月</h2><ul class="list">{"".join(item_html(x) for x in xs)}</ul></section>'
    for k, xs in groups)
up_html_all = "".join(up_html(dt, e) for dt, e in upcoming) or '<li class="empty">120日以内の定番はありません</li>'
df_line = f'{jdate(nxt_df[0], nxt_df[1].get("approx"))}（{(nxt_df[0]-TODAY).days}日後）' if nxt_df else "—"

credits = "　".join(f'<a href="{esc(v["source"])}" target="_blank" rel="noopener">{esc(k)}</a>（{esc(v["license"])}{"・"+esc(v["credit"]) if v["license"].startswith("CC BY") else ""}）' for k, v in places.items() if v["source"].startswith("https://commons"))
page = f'''<title>最近の三浦</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Zen+Old+Mincho:wght@500;700&family=BIZ+UDPGothic:wght@400;700&display=swap">
<style>
:root{{
  --bg:#F1F4F5; --surface:#FFFFFF; --ink:#16222B; --muted:#5C6C77; --line:#D3DCE1;
  --accent:#1E6E8C; --shop:#8A5A2B; --season:#3F7A5C; --grave:#3A4652;
  --chip-ink:#FFFFFF;
}}
@media (prefers-color-scheme: dark){{ :root:not([data-theme="light"]){{
  --bg:#0F171D; --surface:#172129; --ink:#E7ECEF; --muted:#94A4AE; --line:#2A3740;
  --accent:#5FB3D1; --shop:#D9A468; --season:#7FBF9C; --grave:#AEBAC3; --chip-ink:#0F171D;
}}}}
:root[data-theme="dark"]{{
  --bg:#0F171D; --surface:#172129; --ink:#E7ECEF; --muted:#94A4AE; --line:#2A3740;
  --accent:#5FB3D1; --shop:#D9A468; --season:#7FBF9C; --grave:#AEBAC3; --chip-ink:#0F171D;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:"BIZ UDPGothic","Hiragino Sans","Yu Gothic",sans-serif;font-size:16px;line-height:1.6;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:640px;margin:0 auto;padding:20px 16px 48px}}
header{{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}}
.eyebrow{{font-size:12px;letter-spacing:.12em;color:var(--muted);text-transform:uppercase}}
h1{{font-family:"Zen Old Mincho","Hiragino Mincho ProN",serif;font-weight:700;font-size:30px;line-height:1.2;margin:0;text-wrap:balance}}
.updated{{font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums}}
.toggle{{position:sticky;top:0;z-index:2;background:var(--bg);padding:10px 0 12px;display:flex;gap:8px;border-bottom:1px solid var(--line);margin-bottom:8px}}
.toggle .q{{font-size:13px;color:var(--muted);align-self:center;margin-right:2px;white-space:nowrap}}
.toggle button{{flex:1;font:inherit;font-size:14px;padding:8px 0;border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:999px;cursor:pointer}}
.toggle button[aria-pressed="true"]{{background:var(--accent);border-color:var(--accent);color:var(--chip-ink);font-weight:700}}
.toggle button:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
h2{{font-family:"Zen Old Mincho",serif;font-weight:500;font-size:18px;margin:22px 0 8px;color:var(--muted)}}
.list{{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:10px}}
.item{{display:grid;grid-template-columns:76px 1fr;gap:12px;background:var(--surface);border-left:4px solid var(--cat,var(--accent));padding:12px 14px 12px 12px}}
.item[hidden]{{display:none}}
.cat-出来事{{--cat:var(--grave)}} .cat-店{{--cat:var(--shop)}} .cat-イベント{{--cat:var(--accent)}} .cat-季節{{--cat:var(--season)}} .cat-交通{{--cat:var(--muted)}} .cat-A邸{{--cat:var(--accent)}}
.when{{display:flex;flex-direction:column;font-variant-numeric:tabular-nums}}
.when .date{{font-weight:700;font-size:14px;line-height:1.3}}
.when .ago{{font-size:12px;color:var(--muted)}}
.body{{min-width:0}}
.thumb{{display:block;width:100%;height:auto;max-height:160px;object-fit:cover;object-position:50% 45%;margin:0 0 8px;background:var(--line)}}
.tags{{display:flex;gap:6px;align-items:center;margin-bottom:4px;font-size:12px}}
.chip{{background:var(--cat,var(--accent));color:var(--chip-ink);padding:1px 8px;border-radius:999px;font-weight:700}}
.area{{color:var(--muted)}}
.conf{{margin-left:auto}}
.fact{{margin:0 0 4px;font-size:15px;line-height:1.55}}
.talk{{margin:0 0 6px;color:var(--muted);font-size:14px;padding-left:1.1em;text-indent:-1.1em}}
.talk::before{{content:"→ ";}}
.src{{margin:0;font-size:12px}}
.src a{{color:var(--accent);text-decoration:none;border-bottom:1px solid var(--line)}}
.src a+a{{margin-left:8px}}
.empty{{color:var(--muted);font-size:14px;padding:12px 0}}
.df{{margin:18px 0 0;padding:12px 14px;background:var(--surface);border:1px solid var(--line);display:flex;gap:12px;align-items:baseline}}
.df .k{{font-size:12px;color:var(--season);font-weight:700;white-space:nowrap}}
.df .v{{font-variant-numeric:tabular-nums}}
.vgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px 10px}}
.vid{{display:block;color:inherit;text-decoration:none;min-width:0}}
.vid:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
.vthumb{{position:relative;aspect-ratio:16/9;background:var(--line);overflow:hidden}}
.vthumb img{{display:block;width:100%;height:100%;object-fit:cover}}
.vthumb .live{{position:absolute;left:6px;top:6px;background:#C8322B;color:#fff;font-size:10px;font-weight:700;padding:1px 6px;border-radius:3px;letter-spacing:.06em}}
.vtitle{{font-size:13px;line-height:1.4;margin-top:6px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.vmeta{{font-size:11px;color:var(--muted);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.legend{{margin-top:28px;font-size:12px;color:var(--muted);border-top:1px solid var(--line);padding-top:10px}}
</style>
<div class="wrap">
<header>
  <div class="eyebrow">三浦A邸 近況ボード</div>
  <h1>最近の三浦</h1>
  <div class="updated">{TODAY.year}年{TODAY.month}月{TODAY.day}日 更新</div>
</header>
<div class="toggle" role="group" aria-label="前回来てから">
  <span class="q">前回は</span>
  <button data-days="31">1ヶ月</button><button data-days="93">3ヶ月</button><button data-days="184">半年</button><button data-days="366">1年</button>
</div>
<div id="dated">
{groups_html}
<p class="empty" id="none" hidden>この期間に新しい項目はありません。「これから」を話題にどうぞ。</p>
</div>
<div class="df"><span class="k">次のダイヤモンド富士（城ヶ島大橋）</span><span class="v">{df_line}</span></div>
<h2>これから（120日以内の定番）</h2>
<ul class="list">{up_html_all}</ul>
<h2>動画（YouTube・城ヶ島／三崎／三浦海岸／油壺／小網代）</h2>
<div class="vgrid">{videos_html}</div>
<p class="legend">🟢 出典を開いて確認　🟡 一次でない／「頃」　🗣 伝聞。各項目の下は開いた出典。<br>場所の写真は Wikimedia Commons：{credits}。出典記事の写真はその記事の og:image。</p>
</div>
<script>
(function(){{
  var btns=[].slice.call(document.querySelectorAll('.toggle button'));
  var items=[].slice.call(document.querySelectorAll('#dated .item'));
  var months=[].slice.call(document.querySelectorAll('#dated .month'));
  var none=document.getElementById('none');
  function apply(days){{
    btns.forEach(function(b){{b.setAttribute('aria-pressed',String(+b.dataset.days===days));}});
    var shown=0;
    items.forEach(function(el){{var ok=+el.dataset.age<=days;el.hidden=!ok;if(ok)shown++;}});
    months.forEach(function(m){{m.hidden=![].some.call(m.querySelectorAll('.item'),function(el){{return !el.hidden;}});}});
    none.hidden=shown>0;
    try{{localStorage.setItem('miura-days',days);}}catch(e){{}}
  }}
  btns.forEach(function(b){{b.addEventListener('click',function(){{apply(+b.dataset.days);}});}});
  var init=93; try{{init=+localStorage.getItem('miura-days')||93;}}catch(e){{}}
  apply(init);
}})();
</script>
'''
(HERE / "index.html").write_text(page, encoding="utf-8")
print(f"index.html: {len(items)} items, {len(upcoming)} upcoming, {len(videos)} videos, next DF {df_line}")
