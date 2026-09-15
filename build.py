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
    return "／".join(f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["title"])}</a>' for s in srcs)

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
    oq_html = f'<p class="oq"><span class="tl">まだ分からないこと</span>{"／".join(esc(q) for q in oq)}</p>' if oq else ""
    opened = max((s["opened"] for r in rs for s in r.get("sources", [])), default="")
    return f'''<section class="prep"><h4>下調べ<small>{esc(opened)} 時点</small></h4><dl>{rows}</dl>{oq_html}</section>'''

def article(x):
    dt = d(x["date"]); age = (TODAY - dt).days
    end = f'〜{jdate(d(x["end"]))}' if x.get("end") else ""
    head = x.get("headline") or x["fact"][:22]
    going = x.get("going")
    ran_tail = f'<span class="box going-box">参加予定</span><span class="count">{countdown(x)}</span>' if going else f'<span class="ago">{days_ago(dt)}</span>'
    return f'''<article class="art{" going" if going else ""}" data-age="{age}">
  {img_html(x.get("image"))}
  <div class="ran"><span class="box">{esc(x["category"])}</span><span class="dt">{jdate(dt)}{end}　</span>{ran_tail}</div>
  <h3>{esc(head)}</h3>
  <p class="fact"><b class="dl">【{esc(x["area"])}】</b>{esc(x["fact"])}</p>
  <aside class="talk"><span class="tl">話のタネ</span>{esc(x["talk"])}</aside>
  {entry_html(x)}
  {want_html(x)}
  {prep_html(x)}
  <p class="src"><span class="cf">{conf(x["confidence"])}</span>{sources_html(x.get("sources", []))}</p>
</article>'''

def up_article(dt, e):
    return f'''<article class="art small">
  {img_html(e.get("image"))}
  <div class="ran"><span class="box">{esc(e["category"])}</span><span class="dt">{jdate(dt, e.get("approx"))}　<span class="ago">{(dt-TODAY).days}日後</span></span></div>
  <p class="fact">{esc(e["fact"])}</p>
  <aside class="talk"><span class="tl">話のタネ</span>{esc(e["talk"])}</aside>
  <p class="src"><span class="cf">{conf(e["confidence"])}</span><a href="{esc(e["source"]["url"])}" target="_blank" rel="noopener">{esc(e["source"]["title"])}</a></p>
</article>'''

def video_html(v):
    dt = d(v["published"])
    th = f'img/yt/{v["id"]}.jpg'
    img = f'<img src="{th}" alt="" loading="lazy" width="320" height="180">' if (HERE / th).exists() else '<div class="noimg"></div>'
    badge = '<span class="live">生中継</span>' if v.get("live") else ""
    return f'''<a class="vid" href="https://www.youtube.com/watch?v={esc(v["id"])}" target="_blank" rel="noopener">
  <div class="vthumb">{img}{badge}</div>
  <div class="vtitle">{esc(v["title"])}</div>
  <div class="vmeta">{esc(v["channel"])}　{esc("配信中" if v.get("live") else days_ago(dt))}</div>
</a>'''

groups = []
for x in items:
    key = x["date"][:7]
    if not groups or groups[-1][0] != key: groups.append((key, []))
    groups[-1][1].append(x)
groups_html = "\n".join(
    f'<div class="month" data-month="{k}"><h2 class="ym">{int(k[:4])}年{int(k[5:])}月</h2><div class="cols">{"".join(article(x) for x in xs)}</div></div>'
    for k, xs in groups)
up_html = "".join(up_article(dt, e) for dt, e in upcoming) or '<p class="empty">120日以内の定番はありません</p>'
videos_html = "".join(video_html(v) for v in videos) or '<p class="empty">まだ動画がありません</p>'
df_line = f'{jdate(nxt_df[0], nxt_df[1].get("approx"))}（{(nxt_df[0]-TODAY).days}日後）' if nxt_df else "—"
credits_plain = " · ".join(f"{k} {v['license']}" for k, v in places.items() if v["source"].startswith("https://commons"))
credits = "／".join(f'<a href="{esc(v["source"])}" target="_blank" rel="noopener">{esc(k)}</a>（{esc(v["license"])}{"・"+esc(v["credit"]) if v["license"].startswith("CC BY") else ""}）' for k, v in places.items() if v["source"].startswith("https://commons"))
issue_no = (TODAY - FIRST_ISSUE).days + 1


page = Template('''<title>最近の三浦</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{ --bg:#D8CFBC; --ink:#4A4238; --ink2:rgba(74,66,56,.72); --mute:rgba(74,66,56,.55); --rule:rgba(74,66,56,.85); --hair:rgba(100,80,60,.22); --box:rgba(255,250,240,.38); --cream:#F5EEE0; --latin:-apple-system,"Helvetica Neue",sans-serif; }
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Shippori Mincho","Hiragino Mincho ProN","Yu Mincho",serif;background:var(--bg);color:var(--ink);line-height:1.85;letter-spacing:.04em;font-feature-settings:"palt";font-size:15px;overflow-x:hidden;-webkit-font-smoothing:antialiased}
/* 漆喰／紙の繊維目 */
body::before{content:"";position:fixed;inset:0;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='2.8' numOctaves='2' seed='3'/><feColorMatrix values='0 0 0 0 0.4 0 0 0 0 0.35 0 0 0 0 0.3 0 0 0 0.3 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");mix-blend-mode:multiply;opacity:.28;pointer-events:none;z-index:1}
body::after{content:"";position:fixed;inset:-5%;background-image:radial-gradient(ellipse 40% 30% at 25% 30%,rgba(150,130,100,.05),transparent 70%),radial-gradient(ellipse 35% 30% at 75% 70%,rgba(160,140,110,.04),transparent 70%);mix-blend-mode:multiply;pointer-events:none;z-index:1}
main{position:relative;z-index:2;max-width:760px;margin:0 auto;padding:18px 5vw 40px}
a{color:inherit}
.latin{font-family:var(--latin);letter-spacing:.3em;text-transform:uppercase;font-size:9px}
/* ── 題字 ── */
.masthead{border-top:4px double var(--rule);border-bottom:1px solid var(--rule);padding:12px 0 18px}
.issue{font-size:11px;letter-spacing:.2em;color:var(--ink2);display:flex;flex-wrap:wrap;gap:0 16px;border-bottom:1px solid var(--hair);padding-bottom:8px;margin-bottom:12px}
.issue .latin{align-self:center;opacity:.7}
.mh-lead{font-size:clamp(14px,2.4vw,16px);line-height:2;letter-spacing:.06em;max-width:30em}
.areas{font-size:11px;letter-spacing:.3em;color:var(--ink2);margin-top:12px}
.daiji{font-size:clamp(36px,9vw,64px);font-weight:600;letter-spacing:.2em;line-height:1.2;margin:6px 0 16px;text-wrap:balance}
/* ── 前回は ── */
.toggle{position:sticky;top:0;z-index:20;display:flex;align-items:baseline;gap:0 16px;flex-wrap:wrap;padding:10px 0;margin:0 0 22px;background:var(--bg);border-bottom:1px solid var(--rule);box-shadow:0 8px 12px -10px rgba(74,66,56,.35)}
.toggle .q{font-size:12px;letter-spacing:.25em;color:var(--ink2)}
.toggle button{font:inherit;font-size:14px;letter-spacing:.15em;background:none;border:0;color:inherit;cursor:pointer;padding:2px 0;opacity:.5;border-bottom:1.5px solid transparent}
.toggle button[aria-pressed="true"]{opacity:1;font-weight:600;border-bottom-color:currentColor}
.toggle button:focus-visible{outline:1px solid currentColor;outline-offset:3px}
/* ── 面 ── */
.men{display:flex;align-items:baseline;justify-content:space-between;border-top:1px solid var(--rule);border-bottom:3px double var(--rule);padding:6px 2px;margin:40px 0 18px;font-size:15px;font-weight:600;letter-spacing:.35em}
.men .latin{color:var(--ink2)}
.ym{font-size:11px;letter-spacing:.25em;color:var(--ink2);margin:26px 0 10px;display:flex;align-items:center;gap:10px}
.ym::after{content:"";flex:1;height:1px;background:var(--hair)}
.month:first-child .ym{margin-top:0}
/* ── 記事：段組 ── */
.cols{columns:1;column-gap:28px;column-rule:1px solid var(--hair)}
@media (min-width:600px){ .cols{columns:2} }
.art{break-inside:avoid;padding:0 0 18px;margin:0 0 18px;border-bottom:1px solid var(--hair)}
.art[hidden]{display:none}
.photo{margin:0 0 10px}
.photo img{display:block;width:100%;height:auto;max-height:180px;object-fit:cover;object-position:50% 45%;filter:saturate(.85) contrast(.95) sepia(.08)}
.photo figcaption{font-size:10px;letter-spacing:.12em;color:var(--mute);margin-top:4px;text-align:right}
.ran{display:flex;align-items:center;gap:10px;font-size:11px;letter-spacing:.15em;color:var(--ink2);margin-bottom:8px}
.box{border:1px solid var(--rule);color:var(--ink);padding:0 6px;line-height:1.6;letter-spacing:.25em;font-size:10.5px;font-weight:600}
.ago{color:var(--mute)}
h3{font-size:19px;font-weight:600;letter-spacing:.06em;line-height:1.55;margin-bottom:10px;text-wrap:balance}
.fact{font-size:14px;line-height:1.95;text-align:justify;margin-bottom:10px}
.dl{font-weight:600}
.talk{background:var(--box);border:1px solid var(--hair);padding:8px 12px;font-size:13.5px;line-height:1.9;margin-bottom:10px}
.tl{display:inline-block;font-size:10px;letter-spacing:.3em;color:var(--ink2);border-bottom:1px solid var(--hair);margin-right:10px}
.src{font-size:10px;letter-spacing:.1em;color:var(--mute);line-height:1.9}
.src .cf{letter-spacing:.25em;margin-right:10px;color:var(--ink2)}
.src a{text-decoration:none;border-bottom:1px solid var(--hair);margin-right:10px}
/* 行ってみたい */
.toggle .tag-want{margin-left:auto;border:1px solid var(--rule);padding:3px 10px;opacity:1;letter-spacing:.15em}
.toggle .tag-want .n{font-weight:700;margin-left:2px}
.toggle .tag-want[aria-pressed="true"]{background:var(--ink);color:var(--cream)}
.box.want-tag{background:var(--ink);color:var(--cream);border-color:var(--ink)}
.want-off{font-size:11px;letter-spacing:.15em;color:var(--mute);background:none;border:0;cursor:pointer;padding:4px 0;margin-left:6px;text-decoration:underline;text-underline-offset:3px}
.want{margin:0 0 10px}
.want-btn{font:inherit;font-size:13px;letter-spacing:.2em;color:var(--ink);background:none;border:1px solid var(--rule);padding:5px 14px;cursor:pointer;min-height:36px}
.want-btn:focus-visible,.want-link:focus-visible{outline:1px solid currentColor;outline-offset:3px}
.want-btn[aria-expanded="true"],.want.done .want-btn{background:var(--ink);color:var(--cream)}
.want.done .want-btn::before{content:"✓ "}
.want-to{margin-top:8px;border-left:2px solid var(--rule);padding:2px 0 2px 12px}
.want-what{font-size:12.5px;line-height:1.8;color:var(--ink2);margin-bottom:6px}
.want-link{display:inline-block;font-size:13px;letter-spacing:.1em;text-decoration:none;border-bottom:1px solid var(--rule);margin:2px 18px 4px 0;padding:4px 0}
/* 参加予定・下調べ */
.going-box{background:var(--ink);color:var(--cream);border-color:var(--ink)}
.entry{font-size:13px;line-height:1.9;border:1px solid var(--rule);padding:6px 12px;margin:0 0 10px;display:flex;flex-direction:column}
.entry b{font-size:14.5px;letter-spacing:.08em}
.entry span{font-size:11.5px;color:var(--ink2)}
.count{font-size:16px;font-weight:700;letter-spacing:.1em;color:var(--ink);margin-left:auto}
.art.going{border-left:3px solid var(--rule);padding-left:14px}
.art.going.lead{border-left:0;padding-left:0}
.prep{border-top:3px double var(--rule);border-bottom:1px solid var(--rule);padding:10px 0 8px;margin:4px 0 12px}
.prep h4{font-size:13px;font-weight:600;letter-spacing:.35em;margin-bottom:8px;display:flex;align-items:baseline;gap:12px}
.prep h4 small{font-size:10px;font-weight:400;letter-spacing:.15em;color:var(--mute)}
.prep dl{display:grid;grid-template-columns:auto 1fr;gap:6px 14px;font-size:13px;line-height:1.8}
.prep dt{font-weight:600;letter-spacing:.08em;white-space:nowrap;color:var(--ink2)}
.prep dd{margin:0}
.prep dd .src{display:block}
.oq{font-size:12.5px;line-height:1.9;color:var(--ink2);margin-top:8px;border-top:1px solid var(--hair);padding-top:6px}
@media (max-width:480px){ .prep dl{grid-template-columns:1fr;gap:2px 0} .prep dt{margin-top:6px} }
/* 一面 */
.art.lead{column-span:all;border-bottom:3px double var(--rule);padding-bottom:22px;margin-bottom:26px}
.art.lead .photo img{max-height:280px}
.art.lead h3{font-size:clamp(24px,6vw,32px);font-weight:700;letter-spacing:.08em;line-height:1.5}
.art.lead .fact{font-size:15.5px}
.empty{font-size:13px;color:var(--ink2);padding:8px 0}
/* ── 灯台（囲み） ── */
.df{margin:8px 0 0;border:1px solid var(--rule);padding:14px 16px;display:flex;gap:16px;align-items:stretch;background:var(--box)}
.df .k{flex:none;font-size:12px;letter-spacing:.3em;font-weight:600;writing-mode:vertical-rl;text-orientation:upright;white-space:nowrap;border-right:1px solid var(--hair);padding-right:10px;display:flex;align-items:center}
.df .b{display:flex;flex-direction:column;justify-content:center;gap:4px;min-width:0}
.df .v{font-size:clamp(18px,4.6vw,24px);letter-spacing:.1em;line-height:1.5}
.df .n{font-size:11px;letter-spacing:.15em;color:var(--ink2)}
/* ── 映像欄 ── */
.vgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:18px 14px}
.vid{display:block;text-decoration:none;min-width:0}
.vid:focus-visible{outline:1px solid currentColor;outline-offset:3px}
.vthumb{position:relative;aspect-ratio:16/9;background:var(--hair);overflow:hidden;border:1px solid var(--hair)}
.vthumb img{display:block;width:100%;height:100%;object-fit:cover;filter:saturate(.85) contrast(.95) sepia(.08)}
.live{position:absolute;left:0;top:0;background:var(--ink);color:var(--cream);font-size:9px;letter-spacing:.3em;padding:1px 6px 1px 8px}
.vtitle{font-size:12.5px;line-height:1.6;margin-top:6px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.vmeta{font-size:10px;letter-spacing:.1em;color:var(--mute);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
/* ── 奥付 ── */
.okuzuke{margin-top:44px;border-top:3px double var(--rule);padding-top:12px;font-size:11px;letter-spacing:.15em;line-height:2;color:var(--ink2)}
.okuzuke .latin{display:block;margin-top:8px;opacity:.7}
</style>
<main>
<header class="masthead">
  <div class="issue"><span>第$issue号</span><span>$ymd（$wd）</span><span class="latin">Miura A-tei · Kinkyo</span></div>
  <h1 class="daiji">最近の三浦</h1>
  <p class="mh-lead">城ヶ島、三崎、三浦海岸——<br>この町で起きたこと、はじまったこと、季節のこと。</p>
  <div class="areas">城ヶ島 · 三崎 · 三浦海岸 · 油壺 · 小網代</div>
</header>
<nav class="toggle" role="group" aria-label="前回来てから"><span class="q">前回のご来訪は</span><button data-days="31">一ヶ月前</button><button data-days="93">三ヶ月前</button><button data-days="184">半年前</button><button data-days="366">一年前</button><button class="tag-want" data-tag="want" aria-pressed="false" hidden>行ってみたい <b class="n">0</b></button></nav>
<div id="dated">
$groups
<p class="empty" id="none" hidden>この期間に新しい記事はありません。下の「これから」を話題にどうぞ。</p>
</div>
<div class="df"><span class="k">次の灯台</span><div class="b"><span class="v">ダイヤモンド富士　$df</span><span class="n">城ヶ島大橋から。西北西85km先の富士に日が沈む。年により前後（要確認）</span></div></div>
<h2 class="men">これから<span class="latin">Coming up · 120 days</span></h2>
<div class="cols">$upcoming</div>
<h2 class="men">映像欄<span class="latin">YouTube</span></h2>
<div class="vgrid">$videos</div>
<footer class="okuzuke">
出典確認＝記事を開いて確かめたもの／要確認＝一次でない・「頃」／伝聞＝聞いた話<br>
写真：Wikimedia Commons（$credits_plain）、出典記事の og:image、YouTube のサムネイル
<span class="latin">Since 2026.09.12 · Updated every morning · By Yanuki</span>
</footer>
</main>
<script>
(function(){
  var btns=[].slice.call(document.querySelectorAll('.toggle button[data-days]'));
  var tagBtn=document.querySelector('.tag-want');
  var arts=[].slice.call(document.querySelectorAll('#dated .art'));
  var months=[].slice.call(document.querySelectorAll('#dated .month'));
  var none=document.getElementById('none');
  var days=93, tag=false;
  function get(k){try{return localStorage.getItem(k);}catch(e){return null;}}
  function set(k,v){try{if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,v);}catch(e){}}
  function isWant(el){var w=el.querySelector('.want');return !!(w&&w.classList.contains('done'));}
  function render(){
    btns.forEach(function(b){b.setAttribute('aria-pressed',String(!tag&&+b.dataset.days===days));});
    var shown=0, first=null, n=0;
    arts.forEach(function(el){
      var w=isWant(el); if(w)n++;
      var ok=tag?w:(+el.dataset.age<=days);
      el.hidden=!ok; el.classList.remove('lead'); if(ok){shown++;if(!first)first=el;}
      var ran=el.querySelector('.ran'), t=ran&&ran.querySelector('.want-tag');
      if(ran){ if(w&&!t){t=document.createElement('span');t.className='box want-tag';t.textContent='行ってみたい';ran.insertBefore(t,ran.children[1]||null);} else if(!w&&t){t.remove();} }
    });
    if(first)first.classList.add('lead');
    months.forEach(function(m){m.hidden=![].some.call(m.querySelectorAll('.art'),function(el){return !el.hidden;});});
    none.hidden=shown>0;
    if(tagBtn){tagBtn.hidden=(n===0&&!tag);tagBtn.querySelector('.n').textContent=n;tagBtn.setAttribute('aria-pressed',String(tag));}
    if(tag&&n===0){tag=false;set('miura-tag',null);return render();}
    none.textContent=tag?'「行ってみたい」を押した記事はまだありません。':'この期間に新しい記事はありません。下の「これから」を話題にどうぞ。';
  }
  btns.forEach(function(b){b.addEventListener('click',function(){days=+b.dataset.days;tag=false;set('miura-days',days);set('miura-tag',null);render();});});
  if(tagBtn)tagBtn.addEventListener('click',function(){tag=!tag;set('miura-tag',tag?'1':null);render();});
  days=+get('miura-days')||93; tag=get('miura-tag')==='1';
  [].forEach.call(document.querySelectorAll('.want'),function(w){
    var key='miura-want-'+w.dataset.id, b=w.querySelector('.want-btn'), to=w.querySelector('.want-to'), off=w.querySelector('.want-off');
    function mark(on){w.classList.toggle('done',on);set(key,on?'1':null);if(off)off.hidden=!on;render();}
    if(get(key))mark(true);
    b.addEventListener('click',function(){var open=to.hidden;to.hidden=!open;b.setAttribute('aria-expanded',String(open));});
    [].forEach.call(w.querySelectorAll('.want-link'),function(a){a.addEventListener('click',function(){mark(true);});});
    if(off)off.addEventListener('click',function(){mark(false);});
  });
  render();
})();
</script>
''').substitute(issue=issue_no, ymd=f"{TODAY.year}年{TODAY.month}月{TODAY.day}日", ymd_latin=TODAY.strftime('%Y.%m.%d'), wd=WD[TODAY.weekday()],
                 groups=groups_html, df=df_line, upcoming=up_html, videos=videos_html, credits_plain=credits_plain)
# Artifact 用（断片）と GitHub Pages 用（完全なHTML）の2本を書く
(HERE / "artifact.html").write_text(page, encoding="utf-8")
i = page.index("<main>")
full = ('<!DOCTYPE html>\n<html lang="ja">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="description" content="城ヶ島・三崎・三浦海岸——この町で起きたこと、はじまったこと、季節のこと。">\n'
        + page[:i] + '</head>\n<body>\n' + page[i:] + '</body>\n</html>\n')
(HERE / "index.html").write_text(full, encoding="utf-8")
print(f"index.html 第{issue_no}号: {len(items)} items, {len(upcoming)} upcoming, {len(videos)} videos, next DF {df_line}")
