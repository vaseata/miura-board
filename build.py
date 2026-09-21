#!/usr/bin/env python3
"""items.json + calendar.json + places.json + videos.json → index.html（最近の三浦・紙面）"""
import json, datetime, html, pathlib, re, urllib.parse
from string import Template

HERE = pathlib.Path(__file__).parent
TODAY = datetime.date.today()
FIRST_ISSUE = datetime.date(2026, 9, 12)
items = json.load(open(HERE / "items.json"))["items"]
cal = json.load(open(HERE / "calendar.json"))["events"]
places = json.load(open(HERE / "places.json"))["images"]
videos = json.load(open(HERE / "videos.json"))["videos"] if (HERE / "videos.json").exists() else []

def d(s): return datetime.date.fromisoformat(s)
def esc(s): return html.escape(str(s), quote=True)
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

# ---- 日付つき項目（新しい順）。1年より古いものは出さない
items = [x for x in items if (TODAY - d(x["date"])).days <= 366]
items.sort(key=lambda x: (0, (d(x["date"]) - TODAY).days) if d(x["date"]) >= TODAY else (1, (TODAY - d(x["date"])).days))

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
nxt_df = None
for e in cal:
    if "ダイヤモンド富士" in e["fact"]:
        mm, dd = map(int, e["month_day"].split("-"))
        for y in (TODAY.year, TODAY.year + 1):
            dt = datetime.date(y, mm, dd)
            if dt >= TODAY and (nxt_df is None or dt < nxt_df[0]): nxt_df = (dt, e)

CONF = {"🟢": "出典確認", "🟡": "要確認", "🗣": "伝聞"}
def conf(c): return CONF.get(c, c)

def img_html(key, cls="photo"):
    p = places.get(key or "")
    if not p: return ""
    cr = "" if p["source"].startswith("https://commons") else ""
    return f'<figure class="{cls}"><img src="{esc(p["file"])}" alt="" loading="lazy" width="480" height="300"><figcaption>{esc(p.get("caption", ""))}</figcaption></figure>'

def sources_html(srcs):
    return "／".join(f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["title"])}</a>' if s.get("url") else f'<span>{esc(s["title"])}</span>' for s in srcs)

# ---- 「行ってみたい」→ カレンダー登録（イベントのみ・終わっていないもの）
PAGE_URL = "https://vaseata.github.io/miura-board/"
JST = datetime.timezone(datetime.timedelta(hours=9))
ICS_DIR = HERE / "ics"

def cal_event(x):
    if x.get("category") != "イベント": return None
    start, end = d(x["date"]), d(x.get("end") or x["date"])
    if end < TODAY: return None
    c = x.get("cal", {})
    title = c.get("title") or x.get("headline") or x["fact"][:22]
    place = c.get("place") or x["area"]
    ndays = (end - start).days + 1
    details = x["fact"]
    if c.get("note"): details += f"\n※{c['note']}"
    if x.get("sources"): details += "\n出典: " + x["sources"][0]["url"]
    details += "\n最近の三浦: " + PAGE_URL
    ev = {"id": x["id"], "title": title, "place": place, "details": details, "start": start, "end": end, "ndays": ndays}
    if c.get("start") and c.get("end"):
        hm = lambda t: datetime.time(*map(int, t.split(":")))
        ev["t0"], ev["t1"] = hm(c["start"]), hm(c["end"])
    return ev

def ics_text(s):
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

def ics_fold(line):
    out, cur = [], b""
    for ch in line:
        bch = ch.encode("utf-8")
        if len(cur) + len(bch) > (75 if not out else 74):
            out.append(cur); cur = b""
        cur += bch
    out.append(cur)
    return "\r\n ".join(b.decode("utf-8") for b in out)

def utc(dt, t):
    return datetime.datetime.combine(dt, t, JST).astimezone(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def write_ics(ev):
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//miura-board//JA", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
         "BEGIN:VEVENT", f"UID:miura-board-{ev['id']}@vaseata.github.io", f"DTSTAMP:{stamp}"]
    if "t0" in ev:
        L += [f"DTSTART:{utc(ev['start'], ev['t0'])}", f"DTEND:{utc(ev['start'], ev['t1'])}"]
        if ev["ndays"] > 1: L.append(f"RRULE:FREQ=DAILY;COUNT={ev['ndays']}")
    else:
        L += [f"DTSTART;VALUE=DATE:{ev['start']:%Y%m%d}", f"DTEND;VALUE=DATE:{ev['end'] + datetime.timedelta(days=1):%Y%m%d}"]
    L += [f"SUMMARY:{ics_text(ev['title'])}", f"LOCATION:{ics_text(ev['place'])}",
          f"DESCRIPTION:{ics_text(ev['details'])}", f"URL:{PAGE_URL}", "END:VEVENT", "END:VCALENDAR"]
    (ICS_DIR / f"{ev['id']}.ics").write_text("\r\n".join(ics_fold(l) for l in L) + "\r\n", encoding="utf-8", newline="")

def gcal_url(ev):
    if "t0" in ev:
        dates = f"{ev['start']:%Y%m%d}T{ev['t0']:%H%M%S}/{ev['start']:%Y%m%d}T{ev['t1']:%H%M%S}"
    else:
        dates = f"{ev['start']:%Y%m%d}/{ev['end'] + datetime.timedelta(days=1):%Y%m%d}"
    q = {"action": "TEMPLATE", "text": ev["title"], "dates": dates, "ctz": "Asia/Tokyo", "location": ev["place"], "details": ev["details"]}
    if "t0" in ev and ev["ndays"] > 1: q["recur"] = f"RRULE:FREQ=DAILY;COUNT={ev['ndays']}"
    return "https://calendar.google.com/calendar/render?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote, safe="/:")

def when_text(ev):
    days = jdate(ev["start"]) + (f"〜{jdate(ev['end'])}" if ev["ndays"] > 1 else "")
    return days + (f" {ev['t0']:%H:%M}〜{ev['t1']:%H:%M}" if "t0" in ev else "（終日）")

def entry_event(x, ev):
    e = x.get("entry")
    if not e or d(e["open"]) < TODAY: return None
    o = d(e["open"])
    return {"id": f"{x['id']}-entry", "title": f"エントリー開始：{ev['title']}", "place": e.get("how", ""),
            "details": f"受付 {jdate(o)}〜{jdate(d(e['close']))}。" + (e.get("note") or "") + "\n" + PAGE_URL,
            "start": o, "end": o, "ndays": 1}

def want_html(x):
    ev = cal_event(x)
    if not ev: return ""
    write_ics(ev)
    en = entry_event(x, ev)
    en_html = ""
    if en:
        write_ics(en)
        en_html = f'<p class="want-what">エントリー開始日 {jdate(en["start"])}</p><a class="want-link" href="ics/{en["id"]}.ics">iPhone のカレンダーに追加</a><a class="want-link" href="{esc(gcal_url(en))}" target="_blank" rel="noopener">Google カレンダーに追加</a>'
    return f'''<div class="want" data-id="{ev['id']}">
    <button type="button" class="want-btn" aria-expanded="false">行ってみたい</button>
    <div class="want-to" hidden>
      <p class="want-what">{esc(ev["title"])}<br>{esc(when_text(ev))}<br>{esc(ev["place"])}</p>
      <a class="want-link" href="ics/{ev['id']}.ics">iPhone のカレンダーに追加</a><a class="want-link" href="{esc(gcal_url(ev))}" target="_blank" rel="noopener">Google カレンダーに追加</a>
      {en_html}
      <button type="button" class="want-off" hidden>行ってみたいを外す</button>
    </div>
  </div>'''

ICS_DIR.mkdir(exist_ok=True)
for f in ICS_DIR.glob("*.ics"): f.unlink()

def countdown(x):
    n = (d(x["date"]) - TODAY).days
    if n > 0: return f"あと{n}日"
    if n == 0: return "今日"
    return "終了"

def entry_html(x):
    e = x.get("entry")
    if not e: return ""
    o, c = d(e["open"]), d(e["close"])
    if TODAY < o: line = f'<b>エントリー開始まで あと{(o-TODAY).days}日</b>（{jdate(o)}〜{jdate(c)}）'
    elif TODAY <= c: line = f'<b>エントリー受付中 締切まで あと{(c-TODAY).days}日</b>（〜{jdate(c)}）'
    else: line = f'エントリー締切済（{jdate(c)}）'
    extra = "".join(f'<span>{esc(v)}</span>' for v in (e.get("how"), e.get("note")) if v)
    return f'<p class="entry">{line}{extra}</p>'

def prep_html(x):
    rs = x.get("research") or []
    if not rs and not x.get("open_questions"): return ""
    rows = "".join(f'<dt>{esc(r["h"])}</dt><dd>{esc(r["t"])}<span class="src"><span class="cf">{conf(r.get("confidence","🟡"))}</span>{sources_html(r.get("sources", []))}</span></dd>' for r in rs)
    oq = x.get("open_questions") or []
    oq_html = f'<div class="oq"><span class="tl">まだ分からないこと</span><ul>{"".join(f"<li>{esc(q)}</li>" for q in oq)}</ul></div>' if oq else ""
    opened = max((s["opened"] for r in rs for s in r.get("sources", [])), default="")
    return f'''<section class="prep"><h4>下調べ<small>{esc(opened)} 時点</small></h4><dl>{rows}</dl>{oq_html}</section>'''

def short_head(text, n=26):
    t = text
    for sep in ("。", "（", "、"):
        i = t.find(sep)
        if 0 < i <= n: return t[:i]
    return t[:n] + ("…" if len(t) > n else "")

def thumb_html(key, area):
    p = places.get(key or "")
    if not p: return f'<div class="thumb noimg" aria-hidden="true"><span>{esc(area)}</span></div>'
    return f'<div class="thumb"><img src="{esc(p["file"])}" alt="" loading="lazy" width="480" height="300"></div>'

def figure_html(key):
    p = places.get(key or "")
    if not p: return ""
    cap = f'<figcaption>{esc(p["caption"])}</figcaption>' if p.get("caption") else ""
    return f'<figure class="photo"><img src="{esc(p["file"])}" alt="" loading="lazy" width="480" height="300">{cap}</figure>'

def status(x):
    """カード右上の状態：開催中／あとN日／N日前"""
    start, end = d(x["date"]), d(x.get("end") or x["date"])
    if start <= TODAY <= end and end > start: return '<span class="st now">開催中</span>'
    if x.get("going"): return f'<span class="st going">参加予定 {countdown(x)}</span>'
    if start > TODAY: return f'<span class="st soon">{(start-TODAY).days}日後</span>'
    return f'<span class="st ago">{days_ago(start)}</span>'

def card(x, lead_ok=True):
    dt = d(x["date"]); age = (TODAY - dt).days
    end = f'〜{jdate(d(x["end"]))}' if x.get("end") else ""
    head = x.get("headline") or short_head(x["fact"])
    going = x.get("going")
    has_prep = bool(x.get("research") or x.get("open_questions"))
    more = '<span class="more">下調べあり</span>' if has_prep else ""
    return f'''<article class="art{" going" if going else ""}" data-age="{age}" data-cat="{esc(x["category"])}" data-tags="{esc(",".join(x.get("tags", [])))}">
  {thumb_html(x.get("image"), x["area"])}
  <div class="ran"><span class="cat">{esc(x["category"])}</span><span class="area">{esc(x["area"])}</span>{status(x)}</div>
  <h3><button type="button" class="open">{esc(head)}</button></h3>
  <p class="dt">{jdate(dt)}{end}{more}</p>
  <p class="lede">{esc(x["talk"])}</p>
  <div class="detail" hidden>
    {figure_html(x.get("image"))}
    <p class="d-meta"><span class="cat">{esc(x["category"])}</span>{esc(x["area"])}　{jdate(dt)}{end}</p>
    <h2 class="d-head">{esc(head)}</h2>
    <p class="fact">{esc(x["fact"])}</p>
    <aside class="talk"><span class="tl">話のタネ</span>{esc(x["talk"])}</aside>
    {entry_html(x)}
    {want_html(x)}
    {prep_html(x)}
    <p class="src"><span class="cf">{conf(x["confidence"])}</span>{sources_html(x.get("sources", []))}</p>
  </div>
</article>'''

def up_card(dt, e):
    head = short_head(e["fact"])
    return f'''<article class="art up" data-cat="{esc(e["category"])}" data-tags="{esc(",".join(e.get("tags", [])))}">
  {thumb_html(e.get("image"), "三浦")}
  <div class="ran"><span class="cat">{esc(e["category"])}</span><span class="area">定番</span><span class="st soon">{(dt-TODAY).days}日後</span></div>
  <h3><button type="button" class="open">{esc(head)}</button></h3>
  <p class="dt">{jdate(dt, e.get("approx"))}</p>
  <p class="lede">{esc(e["talk"])}</p>
  <div class="detail" hidden>
    {figure_html(e.get("image"))}
    <p class="d-meta"><span class="cat">{esc(e["category"])}</span>毎年の定番　{jdate(dt, e.get("approx"))}</p>
    <h2 class="d-head">{esc(head)}</h2>
    <p class="fact">{esc(e["fact"])}</p>
    <aside class="talk"><span class="tl">話のタネ</span>{esc(e["talk"])}</aside>
    <p class="src"><span class="cf">{conf(e["confidence"])}</span><a href="{esc(e["source"]["url"])}" target="_blank" rel="noopener">{esc(e["source"]["title"])}</a></p>
  </div>
</article>'''

def video_html(v):
    dt = d(v["published"])
    th = f'img/yt/{v["id"]}.jpg'
    img = f'<img src="{th}" alt="" loading="lazy" width="320" height="180">' if (HERE / th).exists() else ''
    badge = '<span class="live">生中継</span>' if v.get("live") else ""
    return f'''<a class="vid" href="https://www.youtube.com/watch?v={esc(v["id"])}" target="_blank" rel="noopener">
  <div class="vthumb">{img}{badge}</div>
  <div class="vtitle">{esc(v["title"])}</div>
  <div class="vmeta">{esc(v["channel"])}　{esc("配信中" if v.get("live") else days_ago(dt))}</div>
</a>'''

# 「これから・開催中」と「最近のできごと」に分ける
soon = sorted([x for x in items if d(x.get("end") or x["date"]) >= TODAY], key=lambda x: x["date"])
recent = sorted([x for x in items if d(x.get("end") or x["date"]) < TODAY], key=lambda x: x["date"], reverse=True)
soon_html = "".join(card(x) for x in soon)
recent_html = "".join(card(x) for x in recent)
up_html = "".join(up_card(dt, e) for dt, e in upcoming)
videos_html = "".join(video_html(v) for v in videos) or '<p class="empty">まだ動画がありません</p>'
df_line = f'{jdate(nxt_df[0], nxt_df[1].get("approx"))}（{(nxt_df[0]-TODAY).days}日後）' if nxt_df else "—"
credits_plain = " · ".join(f"{k} {v['license']}" for k, v in places.items() if v["source"].startswith("https://commons"))
issue_no = (TODAY - FIRST_ISSUE).days + 1


page = Template('''<title>最近の三浦</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@500;700;800&family=Zen+Kaku+Gothic+New:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#FFFFFF; --ink:#14202B; --ink2:#3E4C58; --mute:#5A6A77; --rule:#14202B; --hair:#D9E1E8; --tint:#F2F6F9;
  --sea:#0A5A8C; --sea-tint:#E6F0F6; --tuna:#B8243A; --tuna-tint:#FBEAEC; --on:#FFFFFF;
  --shadow:0 18px 50px rgba(10,40,70,.22);
  --mincho:"Shippori Mincho","Hiragino Mincho ProN","Yu Mincho",serif;
  --gothic:"Zen Kaku Gothic New","Hiragino Sans","Hiragino Kaku Gothic ProN","Yu Gothic",sans-serif;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --bg:#0E151B; --ink:#E7EDF2; --ink2:#C3CED7; --mute:#8FA0AD; --rule:#E7EDF2; --hair:#26333E; --tint:#15202A;
  --sea:#5DB0E4; --sea-tint:#10283A; --tuna:#F0697C; --tuna-tint:#3A1820; --on:#0E151B; --shadow:0 18px 50px rgba(0,0,0,.6);
}}
:root[data-theme="dark"]{
  --bg:#0E151B; --ink:#E7EDF2; --ink2:#C3CED7; --mute:#8FA0AD; --rule:#E7EDF2; --hair:#26333E; --tint:#15202A;
  --sea:#5DB0E4; --sea-tint:#10283A; --tuna:#F0697C; --tuna-tint:#3A1820; --on:#0E151B; --shadow:0 18px 50px rgba(0,0,0,.6);
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--gothic);background:var(--bg);color:var(--ink);line-height:1.75;font-size:15px;font-feature-settings:"palt";-webkit-font-smoothing:antialiased;overflow-x:hidden}
main{max-width:1240px;margin:0 auto;padding:14px 16px 48px}
@media (min-width:720px){ main{padding-inline:28px} }
a{color:inherit}
button{font:inherit;color:inherit}
:focus-visible{outline:2px solid var(--sea);outline-offset:2px}

/* ── 題字 ── */
.masthead{display:grid;grid-template-columns:1fr auto;align-items:end;gap:6px 16px;padding:6px 0 10px;border-bottom:4px solid var(--sea);position:relative}
.masthead::after{content:"";position:absolute;left:0;right:0;bottom:-8px;border-bottom:1px solid var(--sea)}
.daiji{font-family:var(--mincho);font-weight:800;font-size:clamp(34px,8vw,68px);line-height:1.1;letter-spacing:.14em}
.daiji small{display:block;font-family:var(--gothic);font-weight:500;font-size:11px;letter-spacing:.28em;color:var(--mute);margin-bottom:6px}
.issue{text-align:right;font-size:12px;line-height:1.6;color:var(--ink2)}
.issue .no{display:inline-block;font-family:var(--mincho);font-weight:800;font-size:15px;color:var(--tuna);border:2px solid var(--tuna);padding:0 8px;margin-bottom:4px;letter-spacing:.08em}
.mh-lead{grid-column:1/-1;font-size:12.5px;color:var(--mute);letter-spacing:.06em}

/* ── 前回は（絞り込み） ── */
.toggle{position:sticky;top:env(safe-area-inset-top,0px);z-index:20;display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:18px 0 16px;padding:8px 0;background:var(--bg);border-bottom:1px solid var(--hair)}
.toggle .q{font-size:12px;color:var(--mute);margin-right:4px;letter-spacing:.08em}
.toggle button{font-size:13px;background:var(--bg);border:1px solid var(--hair);border-radius:999px;padding:4px 12px;cursor:pointer;min-height:32px}
.toggle button[aria-pressed="true"]{background:var(--sea);border-color:var(--sea);color:var(--on);font-weight:700}
.toggle .tag-want{margin-left:auto;border-color:var(--tuna);color:var(--tuna)}
.toggle .tag-want[aria-pressed="true"]{background:var(--tuna);border-color:var(--tuna);color:var(--on)}
.toggle .tag-reco{border-style:dashed;border-color:var(--tuna);color:var(--tuna)}
.toggle .tag-reco[aria-pressed="true"]{background:var(--tuna);color:var(--on);border-style:solid}
.toggle .n{font-weight:700;margin-left:2px}

/* ── 面見出し ── */
.men{display:flex;align-items:baseline;gap:12px;font-family:var(--mincho);font-weight:800;font-size:19px;letter-spacing:.2em;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid var(--rule)}
.men .latin{font-family:var(--gothic);font-weight:500;font-size:10px;letter-spacing:.3em;text-transform:uppercase;color:var(--mute)}
.men .count-n{margin-left:auto;font-family:var(--gothic);font-size:12px;font-weight:500;letter-spacing:.05em;color:var(--mute)}
.sec:first-of-type .men{margin-top:4px}

/* ── 記事グリッド ── */
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px 12px;grid-auto-flow:dense}
@media (min-width:640px){ .grid{grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:24px 20px} }
.art{position:relative;display:flex;flex-direction:column;gap:6px;min-width:0;padding-top:10px;border-top:1px solid var(--rule)}
.art[hidden]{display:none}
.thumb{position:relative;aspect-ratio:16/10;overflow:hidden;background:var(--tint);max-width:100%}
.thumb img{display:block;width:100%;height:100%;object-fit:cover;transition:transform .35s ease}
.art:hover .thumb img{transform:scale(1.03)}
.noimg{display:flex;align-items:center;justify-content:center;background:var(--sea-tint)}
.noimg span{font-family:var(--mincho);font-weight:800;font-size:clamp(20px,5vw,30px);letter-spacing:.3em;color:var(--sea);opacity:.8}
.ran{display:flex;align-items:center;flex-wrap:wrap;gap:4px 8px;font-size:11px;line-height:1.5}
.cat{display:inline-block;font-weight:700;letter-spacing:.12em;padding:1px 7px;border:1px solid var(--ink);color:var(--ink)}
.art[data-cat="イベント"] .cat,.d-meta .cat.ev{background:var(--tuna);border-color:var(--tuna);color:var(--on)}
.art[data-cat="季節"] .cat,.art[data-cat="店"] .cat{background:var(--sea);border-color:var(--sea);color:var(--on)}
.art[data-cat="交通"] .cat{border-color:var(--sea);color:var(--sea)}
.area{color:var(--mute);letter-spacing:.08em}
.st{margin-left:auto;color:var(--mute);font-variant-numeric:tabular-nums;white-space:nowrap}
.st.soon{color:var(--sea);font-weight:700}
.st.now{color:var(--on);background:var(--sea);padding:0 6px;font-weight:700}
.st.going{color:var(--tuna);font-weight:700}
.box{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.08em;padding:0 6px;line-height:1.7}
.box.want-tag{background:var(--tuna);color:var(--on)}
.box.reco-tag{border:1px dashed var(--tuna);color:var(--tuna)}
.art h3{font-family:var(--mincho);font-weight:700;font-size:15.5px;line-height:1.5;letter-spacing:.02em;text-wrap:balance}
.art h3 .open{all:unset;cursor:pointer;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.art h3 .open::after{content:"";position:absolute;inset:0;z-index:1}
.art h3 .open:focus-visible{outline:none}
.art:has(.open:focus-visible){outline:2px solid var(--sea);outline-offset:4px}
.art:hover h3 .open{color:var(--sea)}
.dt{font-size:11.5px;color:var(--mute);font-variant-numeric:tabular-nums;display:flex;gap:8px;flex-wrap:wrap}
.more{color:var(--tuna);font-weight:700}
.more::before{content:"▸ "}
.lede{font-size:12.5px;line-height:1.7;color:var(--ink2);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
@media (max-width:639px){ .grid .art:not(.lead) .lede{display:none} .art h3{font-size:14.5px} }
/* 一面（各面の先頭） */
.art.lead{grid-column:1/-1;padding-top:0;border-top:0}
.art.lead h3{font-size:clamp(20px,4.6vw,30px);line-height:1.4}
.art.lead h3 .open{-webkit-line-clamp:4}
.art.lead .lede{font-size:14px;-webkit-line-clamp:3}
@media (min-width:640px){
  .art.lead{grid-column:span 2;grid-row:span 2}
  .art.lead .thumb{aspect-ratio:16/9}
}

/* ── 詳細シート ── */
#sheet{border:0;padding:0;margin:auto;width:min(720px,100%);max-width:100%;max-height:min(92vh,100%);background:var(--bg);color:var(--ink);box-shadow:var(--shadow)}
#sheet::backdrop{background:rgba(8,25,40,.55)}
@media (max-width:639px){ #sheet{margin:auto 0 0;width:100%;max-height:92vh;border-radius:14px 14px 0 0} }
.sheet-in{max-height:inherit;overflow-y:auto;overscroll-behavior:contain;padding:0 20px calc(24px + env(safe-area-inset-bottom,0px))}
.sheet-bar{position:sticky;top:0;z-index:2;display:flex;justify-content:flex-end;padding:10px 0 6px;background:var(--bg)}
.sheet-close{border:1px solid var(--hair);background:var(--bg);border-radius:999px;padding:4px 14px;font-size:13px;cursor:pointer;min-height:34px}
.detail .photo{margin:0 -20px 12px}
.detail .photo img{display:block;width:100%;max-height:340px;object-fit:cover}
.detail .photo figcaption{font-size:10.5px;color:var(--mute);text-align:right;padding:4px 20px 0}
.d-meta{display:flex;align-items:center;gap:10px;font-size:12px;color:var(--mute);margin-bottom:6px}
.d-head{font-family:var(--mincho);font-weight:800;font-size:clamp(21px,5vw,28px);line-height:1.45;letter-spacing:.03em;margin-bottom:12px;text-wrap:balance}
.fact{font-size:15px;line-height:1.95;margin-bottom:14px;max-width:40em}
.talk{border-left:4px solid var(--sea);background:var(--sea-tint);padding:10px 14px;font-size:14.5px;line-height:1.85;margin-bottom:14px}
.tl{display:block;font-size:10.5px;font-weight:700;letter-spacing:.25em;color:var(--sea);margin-bottom:2px}
.src{font-size:11px;color:var(--mute);line-height:1.9;margin-top:10px}
.src .cf{font-weight:700;letter-spacing:.12em;margin-right:8px;color:var(--ink2)}
.src a{margin-right:8px;text-underline-offset:2px}
.entry{display:flex;flex-direction:column;border:1px solid var(--tuna);padding:8px 12px;margin-bottom:14px;font-size:13px}
.entry b{color:var(--tuna);font-size:15px}
.entry span{color:var(--ink2);font-size:12px}
/* 行ってみたい */
.want{margin:0 0 14px}
.want-btn{font-size:14px;font-weight:700;letter-spacing:.12em;background:var(--bg);color:var(--tuna);border:2px solid var(--tuna);padding:6px 18px;cursor:pointer;min-height:40px}
.want-btn[aria-expanded="true"],.want.done .want-btn{background:var(--tuna);color:var(--on)}
.want.done .want-btn::before{content:"✓ "}
.want-to{margin-top:10px;padding:8px 0 4px 12px;border-left:2px solid var(--tuna)}
.want-what{font-size:13px;line-height:1.8;color:var(--ink2);margin-bottom:6px}
.want-link{display:inline-block;font-size:14px;font-weight:700;color:var(--sea);margin:2px 18px 6px 0;padding:4px 0;text-underline-offset:3px}
.want-off{font-size:12px;color:var(--mute);background:none;border:0;cursor:pointer;padding:4px 0;text-decoration:underline}
/* 下調べ */
.prep{border-top:2px solid var(--rule);padding-top:10px;margin:6px 0 10px}
.prep h4{font-family:var(--mincho);font-weight:800;font-size:17px;letter-spacing:.2em;display:flex;align-items:baseline;gap:12px;margin-bottom:6px}
.prep h4 small{font-family:var(--gothic);font-size:11px;font-weight:400;letter-spacing:.05em;color:var(--mute)}
.prep dl{font-size:13.5px;line-height:1.85}
.prep dt{font-weight:700;color:var(--sea);margin-top:12px}
.prep dd .src{display:block;margin-top:2px}
.oq{margin-top:14px;background:var(--tuna-tint);padding:10px 14px;font-size:13px;line-height:1.8}
.oq .tl{color:var(--tuna)}
.oq ul{padding-left:1.2em}

/* ── 灯台（囲み） ── */
.df{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 14px;margin:30px 0 0;padding:12px 16px;border:1px solid var(--sea);background:var(--sea-tint)}
.df .k{font-weight:700;font-size:12px;letter-spacing:.2em;color:var(--sea)}
.df .v{font-family:var(--mincho);font-weight:700;font-size:18px}
.df .n{flex-basis:100%;font-size:12px;color:var(--ink2)}
.empty{font-size:13px;color:var(--mute);padding:8px 0}

/* ── 映像欄 ── */
.vgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px 12px}
@media (min-width:640px){ .vgrid{grid-template-columns:repeat(auto-fill,minmax(180px,1fr))} }
.vid{display:block;text-decoration:none;min-width:0}
.vthumb{position:relative;aspect-ratio:16/9;background:var(--tint);overflow:hidden;max-width:100%}
.vthumb img{display:block;width:100%;height:100%;object-fit:cover}
.live{position:absolute;left:0;top:0;background:var(--tuna);color:#fff;font-size:10px;font-weight:700;letter-spacing:.2em;padding:1px 8px}
.vtitle{font-size:12.5px;line-height:1.55;margin-top:6px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.vid:hover .vtitle{color:var(--sea)}
.vmeta{font-size:10.5px;color:var(--mute);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

/* ── 奥付 ── */
.okuzuke{margin-top:40px;border-top:4px solid var(--sea);padding-top:10px;font-size:11px;line-height:2;color:var(--mute)}
.okuzuke .latin{display:block;margin-top:6px;letter-spacing:.25em;text-transform:uppercase;font-size:9.5px}
@media (prefers-reduced-motion: reduce){ .thumb img{transition:none} }
</style>
<main>
<header class="masthead">
  <h1 class="daiji"><small>三浦A邸 近況ボード</small>最近の三浦</h1>
  <div class="issue"><span class="no">第$issue号</span><br>$ymd（$wd）</div>
  <p class="mh-lead">城ヶ島・三崎・三浦海岸・油壺・小網代 ── この町で起きたこと、はじまったこと、季節のこと。記事をタップすると詳しく読めます。</p>
</header>
<nav class="toggle" role="group" aria-label="前回来てから"><span class="q">前回のご来訪</span><button data-days="31">1ヶ月前</button><button data-days="93">3ヶ月前</button><button data-days="184">半年前</button><button data-days="366">1年前</button><button class="tag-want" data-tag="want" aria-pressed="false" hidden>行ってみたい <b class="n">0</b></button><button class="tag-reco" data-tag="reco" aria-pressed="false" hidden>おすすめ <b class="n">0</b></button></nav>
<section class="sec dated" id="soon"><h2 class="men">これから・開催中<span class="latin">Coming up</span></h2><div class="grid">$soon</div></section>
<section class="sec dated" id="recent"><h2 class="men">最近のできごと<span class="latin">Recent</span></h2><div class="grid">$recent</div></section>
<p class="empty" id="none" hidden>この期間に新しい記事はありません。下の「毎年の定番」を話題にどうぞ。</p>
<div class="df"><span class="k">次のダイヤモンド富士</span><span class="v">$df</span><span class="n">城ヶ島大橋から。西北西85km先の富士に日が沈む。年により前後（要確認）</span></div>
<section class="sec" id="ups"><h2 class="men">毎年の定番<span class="latin">Seasonal · 120 days</span></h2><div class="grid">$upcoming</div></section>
<section class="sec" id="videos"><h2 class="men">映像欄<span class="latin">YouTube</span></h2><div class="vgrid">$videos</div></section>
<footer class="okuzuke">
出典確認＝記事を開いて確かめたもの／要確認＝一次でない・「頃」／伝聞＝聞いた話<br>
写真：Wikimedia Commons（$credits_plain）、出典記事の og:image、YouTube のサムネイル
<span class="latin">Since 2026.09.12 · Updated every morning · By Yanuki</span>
</footer>
</main>
<dialog id="sheet" aria-label="記事の詳細"><div class="sheet-in"><div class="sheet-bar"><button type="button" class="sheet-close">閉じる</button></div><div class="sheet-body"></div></div></dialog>
<script>
(function(){
  var btns=[].slice.call(document.querySelectorAll('.toggle button[data-days]'));
  var tagBtn=document.querySelector('.tag-want'), recoBtn=document.querySelector('.tag-reco');
  var arts=[].slice.call(document.querySelectorAll('.dated .art'));
  var ups=[].slice.call(document.querySelectorAll('#ups .art'));
  var secs=[].slice.call(document.querySelectorAll('.sec.dated, #ups'));
  var none=document.getElementById('none');
  var days=93, mode='days';
  function get(k){try{return localStorage.getItem(k);}catch(e){return null;}}
  function set(k,v){try{if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,v);}catch(e){}}
  function isWant(el){return el.classList.contains('is-want');}
  function tagsOf(el){return (el.dataset.tags||'').split(',').filter(Boolean);}
  function badge(el,cls,text,on){var ran=el.querySelector('.ran');if(!ran)return;var t=ran.querySelector('.'+cls);
    if(on&&!t){t=document.createElement('span');t.className='box '+cls;t.textContent=text;ran.insertBefore(t,ran.children[2]||null);}else if(!on&&t){t.remove();}}
  function render(){
    var wantTags={}, n=0;
    arts.forEach(function(el){if(isWant(el)){n++;tagsOf(el).forEach(function(t){wantTags[t]=1;});}});
    function isReco(el){
      if(isWant(el))return false;
      var cat=el.dataset.cat; if(cat!=='イベント'&&cat!=='季節')return false;
      if(el.dataset.age!==undefined&&+el.dataset.age>0)return false;
      return tagsOf(el).some(function(t){return wantTags[t];});
    }
    if(n===0&&mode!=='days'){mode='days';set('miura-mode',null);}
    btns.forEach(function(b){b.setAttribute('aria-pressed',String(mode==='days'&&+b.dataset.days===days));});
    var shown=0, r=0;
    arts.forEach(function(el){
      var w=isWant(el), rc=isReco(el); if(rc)r++;
      var ok=mode==='want'?w:mode==='reco'?rc:(+el.dataset.age<=days);
      el.hidden=!ok; el.classList.remove('lead'); if(ok)shown++;
      badge(el,'want-tag','行ってみたい',w); badge(el,'reco-tag','おすすめ',n>0&&rc);
    });
    ups.forEach(function(el){var rc=isReco(el); if(rc)r++; el.hidden=(mode==='reco')?!rc:(mode==='want'); badge(el,'reco-tag','おすすめ',n>0&&rc);});
    secs.forEach(function(s){
      var vis=[].filter.call(s.querySelectorAll('.art'),function(el){return !el.hidden;});
      s.hidden=vis.length===0;
      if(vis[0]&&s.classList.contains('dated'))vis[0].classList.add('lead');
    });
    none.hidden=shown>0;
    none.textContent=mode==='want'?'「行ってみたい」を押した記事はまだありません。':mode==='reco'?'似た行事はまだ見つかっていません。':'この期間に新しい記事はありません。下の「毎年の定番」を話題にどうぞ。';
    if(tagBtn){tagBtn.hidden=(n===0);tagBtn.querySelector('.n').textContent=n;tagBtn.setAttribute('aria-pressed',String(mode==='want'));}
    if(recoBtn){recoBtn.hidden=(n===0||r===0);recoBtn.querySelector('.n').textContent=r;recoBtn.setAttribute('aria-pressed',String(mode==='reco'));}
  }
  function setMode(m){mode=m;set('miura-mode',m==='days'?null:m);render();}
  btns.forEach(function(b){b.addEventListener('click',function(){days=+b.dataset.days;set('miura-days',days);setMode('days');});});
  if(tagBtn)tagBtn.addEventListener('click',function(){setMode(mode==='want'?'days':'want');});
  if(recoBtn)recoBtn.addEventListener('click',function(){setMode(mode==='reco'?'days':'reco');});
  days=+get('miura-days')||93; mode=get('miura-mode')||'days';
  [].forEach.call(document.querySelectorAll('.want'),function(w){
    var card=w.closest('.art'), key='miura-want-'+w.dataset.id, b=w.querySelector('.want-btn'), to=w.querySelector('.want-to'), off=w.querySelector('.want-off');
    function mark(on){w.classList.toggle('done',on);if(card)card.classList.toggle('is-want',on);set(key,on?'1':null);if(off)off.hidden=!on;render();}
    if(get(key))mark(true);
    b.addEventListener('click',function(){var open=to.hidden;to.hidden=!open;b.setAttribute('aria-expanded',String(open));});
    [].forEach.call(w.querySelectorAll('.want-link'),function(a){a.addEventListener('click',function(){mark(true);});});
    if(off)off.addEventListener('click',function(){mark(false);});
  });
  /* 詳細シート：記事の中身をシートへ移し、閉じたら戻す（ボタンの動きを保つため） */
  var sheet=document.getElementById('sheet'), sbody=sheet.querySelector('.sheet-body'), sin=sheet.querySelector('.sheet-in'), home=null, cur=null, opener=null;
  function putBack(){ if(cur&&home){cur.hidden=true;home.appendChild(cur);} cur=home=null; if(opener){opener.focus();opener=null;} }
  function openCard(card, btn){
    var det=card.querySelector('.detail'); if(!det)return;
    home=card; cur=det; opener=btn; sbody.appendChild(det); det.hidden=false; sin.scrollTop=0;
    if(sheet.showModal){sheet.showModal();}else{sheet.setAttribute('open','');}
  }
  function closeSheet(){ if(sheet.close&&sheet.open){sheet.close();}else{sheet.removeAttribute('open');putBack();} }
  sheet.addEventListener('close',putBack);
  sheet.addEventListener('click',function(e){if(e.target===sheet)closeSheet();});
  sheet.querySelector('.sheet-close').addEventListener('click',closeSheet);
  [].forEach.call(document.querySelectorAll('.art .open'),function(b){b.addEventListener('click',function(){openCard(b.closest('.art'),b);});});
  render();
})();
</script>
''').substitute(issue=issue_no, ymd=f"{TODAY.year}年{TODAY.month}月{TODAY.day}日", wd=WD[TODAY.weekday()],
                 soon=soon_html, recent=recent_html, df=df_line, upcoming=up_html, videos=videos_html, credits_plain=credits_plain)
# Artifact 用（断片）と GitHub Pages 用（完全なHTML）の2本を書く
(HERE / "artifact.html").write_text(page, encoding="utf-8")
i = page.index("<main>")
full = ('<!DOCTYPE html>\n<html lang="ja">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="description" content="城ヶ島・三崎・三浦海岸——この町で起きたこと、はじまったこと、季節のこと。">\n'
        + page[:i] + '</head>\n<body>\n' + page[i:] + '</body>\n</html>\n')
(HERE / "index.html").write_text(full, encoding="utf-8")
print(f"index.html 第{issue_no}号: {len(soon)} soon, {len(recent)} recent, {len(upcoming)} upcoming, {len(videos)} videos, next DF {df_line}")
