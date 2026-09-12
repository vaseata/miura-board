#!/usr/bin/env python3
"""items.json + calendar.json + places.json + videos.json → index.html（最近の三浦・紙面）"""
import json, datetime, html, pathlib, re
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
    return f'<img class="{cls}" src="{esc(p["file"])}" alt="" loading="lazy" width="480" height="300">'

def sources_html(srcs):
    return "／".join(f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["title"])}</a>' for s in srcs)

def article(x):
    dt = d(x["date"]); age = (TODAY - dt).days
    end = f'〜{jdate(d(x["end"]))}' if x.get("end") else ""
    head = x.get("headline") or x["fact"][:22]
    return f'''<article class="art" data-age="{age}">
  {img_html(x.get("image"))}
  <div class="dateline"><span class="cat">{esc(x["category"])}</span><span class="where">{esc(x["area"])}　{jdate(dt)}{end}</span><span class="ago">{days_ago(dt)}</span></div>
  <h3>{esc(head)}</h3>
  <p class="fact">{esc(x["fact"])}</p>
  <p class="talk"><span class="tl">話のタネ</span>{esc(x["talk"])}</p>
  <p class="src"><span class="cf">{conf(x["confidence"])}</span>{sources_html(x.get("sources", []))}</p>
</article>'''

def up_article(dt, e):
    return f'''<article class="art small">
  {img_html(e.get("image"))}
  <div class="dateline"><span class="cat">{esc(e["category"])}</span><span class="where">{jdate(dt, e.get("approx"))}</span><span class="ago">{(dt-TODAY).days}日後</span></div>
  <p class="fact">{esc(e["fact"])}</p>
  <p class="talk"><span class="tl">話のタネ</span>{esc(e["talk"])}</p>
  <p class="src"><span class="cf">{conf(e["confidence"])}</span><a href="{esc(e["source"]["url"])}" target="_blank" rel="noopener">{esc(e["source"]["title"])}</a></p>
</article>'''

def video_html(v):
    dt = d(v["published"])
    th = f'img/yt/{v["id"]}.jpg'
    style = f' style="background-image:url({th})"' if (HERE / th).exists() else ""
    badge = '<span class="live">LIVE</span>' if v.get("live") else ""
    return f'''<a class="vid" href="https://www.youtube.com/watch?v={esc(v["id"])}" target="_blank" rel="noopener">
  <div class="vimg"{style}></div>{badge}
  <div class="vtext"><div class="vtitle">{esc(v["title"])}</div><div class="vmeta">{esc(v["channel"])}　{esc("配信中" if v.get("live") else days_ago(dt))}</div></div>
</a>'''

groups = []
for x in items:
    key = x["date"][:7]
    if not groups or groups[-1][0] != key: groups.append((key, []))
    groups[-1][1].append(x)
groups_html = "\n".join(
    f'<div class="month" data-month="{k}"><h2 class="ym">{int(k[:4])}年{int(k[5:])}月</h2><div class="cards">{"".join(article(x) for x in xs)}</div></div>'
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
<link href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{ --h:42; --s:18%; --l:84%; --th:28; --ts:20%; --tl:26%;
  --bg:hsl(var(--h),var(--s),var(--l)); --ink:hsl(var(--th),var(--ts),var(--tl));
  --card:rgba(255,250,240,.42); --hair:rgba(100,80,60,.14); --cream:#F5EEE0; --latin:-apple-system,"Helvetica Neue",sans-serif; }
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:"Shippori Mincho","Hiragino Mincho ProN","Yu Mincho",serif;background:var(--bg);color:var(--ink);line-height:1.9;letter-spacing:.06em;font-feature-settings:"palt";font-size:15px;overflow-x:hidden;transition:background 1.2s cubic-bezier(.4,0,.2,1),color 1.2s cubic-bezier(.4,0,.2,1);-webkit-font-smoothing:antialiased}
/* 漆喰の繊維目 */
body::before{content:"";position:fixed;inset:0;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='2.8' numOctaves='2' seed='3'/><feColorMatrix values='0 0 0 0 0.4 0 0 0 0 0.35 0 0 0 0 0.3 0 0 0 0.3 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");mix-blend-mode:multiply;opacity:.28;pointer-events:none;z-index:1}
body::after{content:"";position:fixed;inset:-5%;background-image:radial-gradient(ellipse 40% 30% at 25% 30%,rgba(150,130,100,.05),transparent 70%),radial-gradient(ellipse 35% 30% at 75% 70%,rgba(160,140,110,.04),transparent 70%);mix-blend-mode:multiply;pointer-events:none;z-index:1}
main{position:relative;z-index:2}
a{color:inherit}
.wrap{max-width:640px;margin:0 auto;padding:0 6vw}
/* 見出し帯 */
.hd{position:fixed;top:0;left:0;right:0;z-index:50;display:flex;justify-content:space-between;align-items:center;padding:16px 6vw;backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);background:rgba(216,207,188,.28)}
.hd .logo{font-size:15px;font-weight:500;letter-spacing:.3em;text-decoration:none}
.hd .logo small{font-family:var(--latin);font-size:9px;letter-spacing:.3em;opacity:.6;margin-left:8px}
.hd .issue{font-family:var(--latin);font-size:10px;letter-spacing:.25em;opacity:.65}
section{position:relative;padding:12vh 0 10vh}
.label{font-family:var(--latin);font-size:10px;letter-spacing:.5em;text-transform:uppercase;opacity:.55;margin-bottom:28px}
.label::before{content:"";display:inline-block;width:28px;height:1px;background:currentColor;vertical-align:middle;margin-right:14px;opacity:.6}
.label .jp{font-family:"Shippori Mincho",serif;letter-spacing:.3em;margin-left:14px}
/* 冒頭 */
.hero{padding:22vh 0 12vh}
.hero h1{font-size:clamp(40px,11vw,68px);font-weight:500;letter-spacing:.15em;line-height:1.25;margin-bottom:28px}
.hero .tag{font-size:clamp(15px,2.2vw,18px);line-height:2;opacity:.9;max-width:34em}
.hero .meta{font-family:var(--latin);font-size:11px;letter-spacing:.3em;opacity:.55;margin-top:40px;line-height:2}
/* 前回は */
.toggle{position:sticky;top:56px;z-index:40;display:flex;align-items:baseline;gap:0 18px;flex-wrap:wrap;padding:12px 0;margin:-4px 0 32px;background:rgba(216,207,188,.55);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);border-top:1px solid var(--hair);border-bottom:1px solid var(--hair)}
.toggle .q{font-size:12px;letter-spacing:.3em;opacity:.6}
.toggle button{font:inherit;font-size:14px;letter-spacing:.2em;background:none;border:0;color:inherit;cursor:pointer;padding:2px 0;opacity:.55;border-bottom:1px solid transparent;transition:opacity .3s,border-color .3s}
.toggle button[aria-pressed="true"]{opacity:1;border-bottom-color:currentColor}
.toggle button:focus-visible{outline:1px solid currentColor;outline-offset:4px}
/* 記事 */
.ym{font-family:var(--latin);font-size:11px;letter-spacing:.3em;opacity:.55;margin:40px 0 14px}
.month:first-child .ym{margin-top:0}
.cards{display:flex;flex-direction:column;gap:16px}
.art{background:var(--card);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);border:1px solid var(--hair);padding:26px 24px 22px;position:relative;overflow:hidden}
.art[hidden]{display:none}
.photo{display:block;width:calc(100% + 48px);margin:-26px -24px 20px;height:auto;max-height:170px;object-fit:cover;object-position:50% 45%;filter:saturate(.85) contrast(.95)}
.dateline{font-family:var(--latin);font-size:10px;letter-spacing:.25em;opacity:.6;display:flex;gap:14px;flex-wrap:wrap;margin-bottom:12px}
.dateline .cat{font-family:"Shippori Mincho",serif;letter-spacing:.3em}
.dateline .ago{margin-left:auto}
h3{font-size:20px;font-weight:500;letter-spacing:.08em;line-height:1.6;margin-bottom:12px;text-wrap:balance}
.fact{font-size:14px;line-height:2;opacity:.88;margin-bottom:14px}
.talk{font-size:14px;line-height:2;opacity:.9;padding-left:1em;border-left:1px solid var(--hair);margin-bottom:14px}
.tl{display:block;font-size:10px;letter-spacing:.4em;opacity:.55;line-height:1.6}
.src{font-family:var(--latin);font-size:10px;letter-spacing:.12em;opacity:.55;line-height:2}
.src .cf{font-family:"Shippori Mincho",serif;letter-spacing:.3em;margin-right:14px}
.src a{text-decoration:none;border-bottom:1px solid currentColor;margin-right:12px}
/* 一面 */
.art.lead{padding:0 0 26px}
.art.lead .photo{width:100%;margin:0 0 22px;max-height:260px}
.art.lead .dateline,.art.lead h3,.art.lead .fact,.art.lead .talk,.art.lead .src{margin-left:24px;margin-right:24px}
.art.lead h3{font-size:clamp(24px,6vw,30px);font-weight:500;letter-spacing:.1em;line-height:1.55}
.art.lead .fact{font-size:15px}
.art.small .fact{font-size:13.5px}
.empty{font-size:13px;opacity:.6;padding:8px 0}
/* 灯台 */
.df{margin:64px 0 0;text-align:center}
.df .k{font-size:14px;letter-spacing:1em;opacity:.55;margin-bottom:14px}
.df .v{font-size:clamp(24px,6vw,32px);font-weight:400;letter-spacing:.15em;line-height:1.5}
.df .n{font-family:var(--latin);font-size:10px;letter-spacing:.25em;opacity:.55;margin-top:12px}
/* 動画 */
.vgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:4px}
.vid{position:relative;aspect-ratio:4/5;overflow:hidden;text-decoration:none;color:var(--cream);display:block}
.vimg{position:absolute;inset:0;background:rgba(80,70,60,.35) center/cover no-repeat;filter:saturate(.85) contrast(.95);transition:transform .8s cubic-bezier(.4,0,.2,1),filter .5s}
.vid::after{content:"";position:absolute;inset:0;background:linear-gradient(to bottom,rgba(0,0,0,0) 35%,rgba(40,30,20,.78) 100%)}
.vid:hover .vimg{transform:scale(1.05);filter:saturate(1) contrast(1)}
.vid:focus-visible{outline:1px solid var(--cream);outline-offset:-4px}
.vtext{position:absolute;left:0;right:0;bottom:0;padding:18px 16px;z-index:2}
.vtitle{font-size:13px;font-weight:500;letter-spacing:.06em;line-height:1.6;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.vmeta{font-family:var(--latin);font-size:9px;letter-spacing:.2em;opacity:.8;margin-top:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.live{position:absolute;top:12px;left:12px;z-index:2;font-family:var(--latin);font-size:9px;letter-spacing:.3em;color:var(--cream);border:1px solid rgba(245,238,224,.7);padding:2px 8px}
/* 奥付 */
footer{text-align:center;padding:14vh 6vw 10vh;font-size:11px;letter-spacing:.3em;line-height:2.2;opacity:.75;position:relative;z-index:2}
footer small{display:block;font-family:var(--latin);font-size:9px;letter-spacing:.3em;opacity:.7;margin-top:14px;line-height:2}
footer a{text-decoration:none;border-bottom:1px solid currentColor}
@media (prefers-reduced-motion:reduce){ html{scroll-behavior:auto} body,.toggle button,.vimg{transition:none} }
</style>
<header class="hd"><a class="logo" href="#top">最近の三浦<small>MIURA A-TEI</small></a><span class="issue">NO.$issue · $ymd_latin</span></header>
<main id="top">
<section class="hero" data-time="morning"><div class="wrap">
  <div class="label">Kinkyo board<span class="jp">近況</span></div>
  <h1>最近<br>の三浦</h1>
  <p class="tag">城ヶ島、三崎、三浦海岸——<br>この町で起きたこと、はじまったこと、季節のこと。</p>
  <p class="meta">城ヶ島 · 三崎 · 三浦海岸 · 油壺 · 小網代<br>第$issue号　$ymd（$wd）発行</p>
</div></section>
<section class="kiji" data-time="noon"><div class="wrap">
  <div class="label">Since your last visit<span class="jp">前回から</span></div>
  <nav class="toggle" role="group" aria-label="前回来てから"><span class="q">前回は</span><button data-days="31">一ヶ月</button><button data-days="93">三ヶ月</button><button data-days="184">半年</button><button data-days="366">一年</button></nav>
  <div id="dated">
$groups
  <p class="empty" id="none" hidden>この期間に新しい記事はありません。下の「これから」を話題にどうぞ。</p>
  </div>
  <div class="df"><div class="k">次の灯台</div><div class="v">ダイヤモンド富士　$df</div><div class="n">城ヶ島大橋から · 西北西 85 km · 年により前後</div></div>
</div></section>
<section class="korekara" data-time="evening"><div class="wrap">
  <div class="label">Coming up<span class="jp">これから</span></div>
  <div class="cards">$upcoming</div>
</div></section>
<section class="douga" data-time="dusk"><div class="wrap">
  <div class="label">On video<span class="jp">動画</span></div>
  <div class="vgrid">$videos</div>
</div></section>
<footer data-time="night">
  出典確認 ＝ 記事を開いて確かめたもの　／　要確認 ＝ 一次でない・「頃」　／　伝聞 ＝ 聞いた話
  <small>PHOTOS · WIKIMEDIA COMMONS ($credits_plain) · SOURCE OG:IMAGE · YOUTUBE THUMBNAILS<br>SINCE 2026.09.12 · UPDATED EVERY MORNING · BY YANUKI</small>
</footer>
</main>
<script>
(function(){
  var btns=[].slice.call(document.querySelectorAll('.toggle button'));
  var arts=[].slice.call(document.querySelectorAll('#dated .art'));
  var months=[].slice.call(document.querySelectorAll('#dated .month'));
  var none=document.getElementById('none');
  function apply(days){
    btns.forEach(function(b){b.setAttribute('aria-pressed',String(+b.dataset.days===days));});
    var shown=0, first=null;
    arts.forEach(function(el){var ok=+el.dataset.age<=days;el.hidden=!ok;el.classList.remove('lead');if(ok){shown++;if(!first)first=el;}});
    if(first)first.classList.add('lead');
    months.forEach(function(m){m.hidden=![].some.call(m.querySelectorAll('.art'),function(el){return !el.hidden;});});
    none.hidden=shown>0;
    try{localStorage.setItem('miura-days',days);}catch(e){}
    updateLight();
  }
  /* 光環境：朝→昼→夕→宵→夜（左菊デモと同じ仕掛け） */
  var L={morning:{h:42,s:18,l:84,th:28,ts:20,tl:26},noon:{h:40,s:20,l:87,th:30,ts:18,tl:22},evening:{h:32,s:28,l:78,th:25,ts:25,tl:20},dusk:{h:28,s:22,l:68,th:22,ts:20,tl:18},night:{h:35,s:12,l:58,th:40,ts:15,tl:90}};
  var secs=[].slice.call(document.querySelectorAll('[data-time]'));
  function lerp(a,b,t){return a+(b-a)*t}
  function mix(a,b,t){var o={};for(var k in a)o[k]=lerp(a[k],b[k],t);return o}
  function updateLight(){
    var y=window.scrollY, c=y+window.innerHeight/2;
    var pts=secs.map(function(s){var r=s.getBoundingClientRect();return {c:r.top+y+r.height/2,st:L[s.dataset.time]}});
    var cur=pts[0].st;
    if(c>pts[pts.length-1].c)cur=pts[pts.length-1].st;
    else for(var i=0;i<pts.length-1;i++){var a=pts[i],b=pts[i+1];if(c>=a.c&&c<=b.c){var t=(c-a.c)/(b.c-a.c);var e=-(Math.cos(Math.PI*t)-1)/2;cur=mix(a.st,b.st,e);break;}}
    var r=document.documentElement.style;
    r.setProperty('--h',cur.h);r.setProperty('--s',cur.s+'%');r.setProperty('--l',cur.l+'%');
    r.setProperty('--th',cur.th);r.setProperty('--ts',cur.ts+'%');r.setProperty('--tl',cur.tl+'%');
  }
  var tick=false;
  window.addEventListener('scroll',function(){if(!tick){requestAnimationFrame(function(){updateLight();tick=false});tick=true}});
  window.addEventListener('resize',updateLight);
  btns.forEach(function(b){b.addEventListener('click',function(){apply(+b.dataset.days);});});
  var init=93; try{init=+localStorage.getItem('miura-days')||93;}catch(e){}
  apply(init);
})();
</script>
''').substitute(issue=issue_no, ymd=f"{TODAY.year}年{TODAY.month}月{TODAY.day}日", ymd_latin=TODAY.strftime('%Y.%m.%d'), wd=WD[TODAY.weekday()],
                 groups=groups_html, df=df_line, upcoming=up_html, videos=videos_html, credits_plain=credits_plain)
(HERE / "index.html").write_text(page, encoding="utf-8")
print(f"index.html 第{issue_no}号: {len(items)} items, {len(upcoming)} upcoming, {len(videos)} videos, next DF {df_line}")
