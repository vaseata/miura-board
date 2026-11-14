#!/usr/bin/env python3
"""到着カード（合言葉つき）を作る：建物の見分け方・外観・バス停からの道・今夜の部屋の空き。

使い方:  python3 arrival_build.py          … 中身が変わったときだけ暗号化して m/<m/.token-arrival>/index.html を書く
         python3 arrival_build.py --force  … 変わっていなくても書き直す
- 合言葉は share_lock.py と同じ（ハザードマップと共通。m/.pass か SHARE_PASS）
- 部屋の空きは、予約タスク（miura-yoyaku-calendar）が毎回書く台帳 宿泊者.json から作る。**名前は出さない**
- 外観・道の写真は private_photos/<key>.jpg（.gitignore）に置く（gaikan・hyosatsu・michi1〜3・higashioka1〜2・misakiko1〜2）。暗号文の中に埋め込むので、公開リポジトリに平文では入らない
- 平文の確認用に arrival.src.html（.gitignore）も書く
"""
import base64, datetime as dt, hashlib, html, json, sys
from pathlib import Path
from share_lock import lock, token_for, ROOT, BASE

LEDGER = Path('/Users/yanudon/claude/mameden-trio/apps/miura-watcher/data/宿泊者.json')
PRIV = ROOT / 'private_photos'
GUEST_ROOMS = ['101', '201', '203']        # 会員さんが泊まる部屋（台帳の題の先頭の番号）
RESIDENT = ('202', '2026年4月から')        # 固定の住人の部屋（2026-11-14 ヤヌキ指示。名前は出さない）
JST = dt.timezone(dt.timedelta(hours=9))
HASH = ROOT / 'm' / '.arrival.hash'
esc = lambda s: html.escape(str(s), quote=True)

def photo(key, cap, lang='ja'):
    f = PRIV / f'{key}.jpg'
    if f.exists():
        if lang == 'en':   # 英語側は日本語側の画像を JS で写す（暗号文に同じ写真を2回入れない）
            return f'<figure class="ph"><img data-copy="{key}" alt="{esc(cap)}"><figcaption>{esc(cap)}</figcaption></figure>'
        b = base64.b64encode(f.read_bytes()).decode()
        return f'<figure class="ph"><img data-key="{key}" src="data:image/jpeg;base64,{b}" alt="{esc(cap)}"><figcaption>{esc(cap)}</figcaption></figure>'
    return (f'<figure class="ph"><div class="shoot"><svg class="cam" viewBox="0 0 48 40" aria-hidden="true"><rect x="3" y="9" width="42" height="28" rx="6"/>'
            f'<circle cx="24" cy="23" r="8"/><path d="M16 9l3-5h10l3 5"/></svg><span class="lbl">{"PHOTO COMING SOON" if lang == "en" else "撮影予定"}</span><span class="what">{esc(cap)}</span></div></figure>')

def d_of(x):
    s = x.get('dateTime') or x.get('date')
    return dt.date.fromisoformat(s[:10])

def rooms(today):
    """部屋ごとの今夜・明晩の状態。台帳が無い・古いときは None。"""
    if not LEDGER.exists():
        return None, None
    data = json.loads(LEDGER.read_text())
    stay = {r: [] for r in GUEST_ROOMS}
    for e in data.get('events', []):
        summ = e.get('summary', '')
        if summ.startswith('【取消】'):
            continue
        room = summ.split('　')[0].strip()
        if room in stay:
            stay[room].append((d_of(e['start']), d_of(e['end'])))
    def night(room, day):
        for a, b in stay[room]:
            if a <= day < b:
                return ('今日から' if a == day else '使用中', b)
        return ('空き', None)
    rows = []
    for r in GUEST_ROOMS:
        t, tend = night(r, today)
        n, _ = night(r, today + dt.timedelta(days=1))
        rows.append((r, t, tend, n))
    return rows, data.get('書いた', '')

WD = '月火水木金土日'
WD_EN = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
def md(d, lang='ja'):
    return f'{d.month}/{d.day} ({WD_EN[d.weekday()]})' if lang == 'en' else f'{d.month}/{d.day}（{WD[d.weekday()]}）'

# 部屋の状態の言葉（台帳から作る値 → 英語）
ST_EN = {'空き': 'Free', '使用中': 'In use', '今日から': 'From today'}

def rooms_block(rows, written, today, lang):
    en = lang == 'en'
    if not rows:
        return '<p class="note">Room status is not available right now.</p>' if en else '<p class="note">いまは部屋の空きを表示できません。</p>'
    def st(x): return ST_EN[x] if en else x
    def until(e):
        if not e: return ''
        return f' (until {md(e, lang)} morning)' if en else f'（〜{md(e)}朝）'
    trs = [(r, f'<tr><th>{r}</th><td class="st {"ok" if t == "空き" else "in"}">{st(t)}{until(e)}</td>'
                f'<td class="st {"ok" if n == "空き" else "in"}">{st(n)}</td></tr>') for r, t, e, n in rows]
    res_cell = (f'Resident’s room (lived in since April 2026)' if en else f'住人の部屋（{RESIDENT[1]}住んでいます）')
    trs.append((RESIDENT[0], f'<tr><th>{RESIDENT[0]}</th><td class="st res" colspan="2">{res_cell}</td></tr>'))
    tr = ''.join(h for _r, h in sorted(trs))
    if en:
        return (f'<table class="rooms"><tr><th>Room</th><th>Tonight {md(today, lang)}</th><th>Tomorrow night</th></tr>{tr}</table>'
                f'<p class="res-note">A resident has lived in Room {RESIDENT[0]} since April 2026. If you have questions, feel free to ask them.</p>'
                f'<p class="note">Made automatically from the booking records (as of {esc(written)}). Last-minute bookings or cancellations may not be shown. Guests’ names are not shown. If two rooms say “from today”, one is yours and the other is another member arriving the same day.</p>')
    return (f'<table class="rooms"><tr><th>部屋</th><th>今夜 {md(today)}</th><th>明晩</th></tr>{tr}</table>'
            f'<p class="res-note">{RESIDENT[0]}号室には、{RESIDENT[1]}住人が住んでいます。分からないことがあったら、声をかけてください。</p>'
            f'<p class="note">予約の記録から自動で作っています（{esc(written)} 時点）。直前の予約・取り消しは入っていないことがあります。泊まっている人の名前は載せていません。「今日から」が2つあるときは、ひとつがご自分、もうひとつは同じ日に来るほかの会員さんです。</p>')

def landmark():
    """建物の目印の文（家の場所が分かるので、公開リポジトリに置かない。home.local.json の landmark_ja / landmark_en）。"""
    h = ROOT / 'home.local.json'
    d = json.loads(h.read_text()) if h.exists() else {}
    return d.get('landmark_ja', ''), (' ' + d['landmark_en']) if d.get('landmark_en') else ''

def body_ja(rooms_html):
    return f'''<div class="L" lang="ja" data-l="ja">
<h1>到着カード</h1>
<p class="lede">はじめて来る方へ。建物の見分け方と、今夜の部屋の様子です。</p>
<div class="two"></div>

<h2>今夜の部屋</h2>
<p>ご自分の部屋番号は、予約の前日に届くメールの「部屋番号」にあります。</p>
{rooms_html}

<h2>建物の見分け方</h2>
<div class="alert">隣の家と、住所が同じです。三浦A邸は、アイボリー色の外観の建物です。玄関の表札に、ADDress のマークがあります。@LANDMARK_JA@</div>
{photo('gaikan', '三浦A邸の外観')}
{photo('hyosatsu', '玄関の表札と ADDress のプレート')}

<h2>バス停から家まで</h2>
<p>三崎口駅からのバスは、降りるバス停が3つあります。いちばん近くて楽なのは「日の出」です。</p>
<nav class="stops"><a href="#hinode">日の出</a><a href="#higashioka">三崎東岡</a><a href="#misakiko">三崎港</a></nav>

<h3 id="hinode">「日の出」から<small>おすすめ・道はほぼ平坦</small></h3>
<p><span class="fill">記入待ち：バス停から家までの道順と、歩く時間</span></p>
<p>家までの道は、前日のメールのGoogleマップで家のピンを開いて歩くのが確実です。迷ったら、家守に連絡してください。</p>
{photo('michi1', 'バス停「日の出」を降りたところ')}
{photo('michi2', '曲がる角')}
{photo('michi3', '家の前の道')}

<h3 id="higashioka">「三崎東岡」から<small>徒歩7分ほど・下り坂</small></h3>
<p>家までは、ゆるい下り坂です。帰りにこのバス停から乗るときは、坂を登ることになります。荷物が多いと、少し大変です。</p>
<p><span class="fill">記入待ち：バス停から家までの道順</span></p>
{photo('higashioka1', 'バス停「三崎東岡」を降りたところ')}
{photo('higashioka2', '坂の入口')}

<h3 id="misakiko">「三崎港」から<small>家からは遠い</small></h3>
<p>三崎港（終点）まで乗ってしまったときの道です。港の店に寄ってから歩くときにも。</p>
<p><span class="fill">記入待ち：バス停から家までの道順と、歩く時間</span></p>
{photo('misakiko1', 'バス停「三崎港」を降りたところ')}
{photo('misakiko2', '曲がる角')}

<h2>入るとき</h2>
<ol><li>玄関にキーボックスがあります。暗証番号は、前日のメールの「入室情報」のページに書いてあります。</li>
<li>チャイムは鳴らさず、そのままお入りください。</li>
<li>リネン・トイレ・お風呂の場所は、<a href="{BASE}stay/tochaku.html#mazu">家の案内の「着いたら、まず」</a>にあります。</li></ol>
<p class="note">このページの URL と合言葉は、ほかの人に教えないでください。</p>
</div>'''

def body_en(rooms_html):
    return f'''<div class="L" lang="en" data-l="en">
<h1>Arrival card</h1>
<p class="lede">For first-time guests: how to find the building, and the rooms tonight.</p>
<div class="two"></div>

<h2>Rooms tonight</h2>
<p>Your room number is in the “Room number” section of the email you receive the day before your stay.</p>
{rooms_html}

<h2>How to find the building</h2>
<div class="alert">The house next door has the same address. Miura A-tei is the ivory-colored building. The nameplate at the entrance has the ADDress mark.@LANDMARK_EN@</div>
{photo('gaikan', 'Outside of Miura A-tei', 'en')}
{photo('hyosatsu', 'Nameplate and ADDress plate at the entrance', 'en')}

<h2>From the bus stop to the house</h2>
<p>Buses from Misakiguchi Station have three stops you can use. The closest and easiest is “Hinode” (日の出).</p>
<nav class="stops"><a href="#hinode-en">Hinode 日の出</a><a href="#higashioka-en">Misaki Higashioka 三崎東岡</a><a href="#misakiko-en">Misaki-ko 三崎港</a></nav>

<h3 id="hinode-en">From “Hinode” 日の出<small>Recommended · almost flat</small></h3>
<p><span class="fill">Pending: route and walking time from the bus stop to the house</span></p>
<p>To find the house, open the house pin in the Google Maps link in the day-before email and follow it. If you get lost, contact the house manager.</p>
{photo('michi1', 'Getting off at the “Hinode” bus stop', 'en')}
{photo('michi2', 'The corner where you turn', 'en')}
{photo('michi3', 'The street in front of the house', 'en')}

<h3 id="higashioka-en">From “Misaki Higashioka” 三崎東岡<small>About 7 min walk · downhill</small></h3>
<p>The road to the house is a gentle downhill slope. When you take the bus back from this stop, you walk uphill, which is a bit hard with a lot of luggage.</p>
<p><span class="fill">Pending: route from the bus stop to the house</span></p>
{photo('higashioka1', 'Getting off at the “Misaki Higashioka” bus stop', 'en')}
{photo('higashioka2', 'Start of the slope', 'en')}

<h3 id="misakiko-en">From “Misaki-ko” 三崎港<small>Far from the house</small></h3>
<p>The route if you stayed on to Misaki-ko (the last stop). Also useful if you visit the harbor shops first.</p>
<p><span class="fill">Pending: route and walking time from the bus stop to the house</span></p>
{photo('misakiko1', 'Getting off at the “Misaki-ko” bus stop', 'en')}
{photo('misakiko2', 'The corner where you turn', 'en')}

<h2>Going in</h2>
<ol><li>There is a key box at the entrance. The code is on the “Entry information” page in the email from the day before.</li>
<li>Don’t ring the bell; just come in.</li>
<li>Where the linens, toilet, and bath are: <a href="{BASE}stay/en/tochaku.html#mazu">“First things on arrival” in the Stay Guide</a>.</li></ol>
<p class="note">Please do not share this page’s URL or the passphrase with anyone else.</p>
</div>'''

def build():
    today = dt.datetime.now(JST).date()
    rows, written = rooms(today)
    ja = body_ja(rooms_block(rows, written, today, 'ja'))
    en = body_en(rooms_block(rows, written, today, 'en'))
    body = f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>到着カード / Arrival card｜三浦A邸</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@800&family=Zen+Kaku+Gothic+New:wght@400;700&display=swap">
<style>
:root{{color-scheme:light;--bg:#fff;--ink:#14202B;--mute:#4F6070;--hair:#D9E1E8;--tint:#F2F6F9;--sea:#0A5A8C;--sea-tint:#E6F0F6;--tuna:#B8243A;--kon:#2E4C9E}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:"Zen Kaku Gothic New","Hiragino Sans",sans-serif;font-size:16px;line-height:1.7}}
main{{max-width:720px;margin:0 auto;padding:16px 16px 56px}}
.hd{{display:block;width:100%;height:auto;border-radius:10px}}
.top{{display:flex;align-items:center;gap:8px;margin-top:12px}}
.brand{{display:flex;align-items:center;gap:8px;font-size:12px;font-weight:700;letter-spacing:.16em;color:var(--sea)}}.brand img{{width:40px;height:40px}}
.seg{{display:inline-grid;grid-template-columns:1fr 1fr;gap:2px;padding:3px;margin-left:auto;background:var(--tint);border:1px solid var(--hair);border-radius:999px;flex:none}}
.seg button{{min-width:52px;min-height:38px;border:0;border-radius:999px;background:none;color:var(--mute);font:400 14px/1 "Zen Kaku Gothic New",sans-serif;letter-spacing:.04em;cursor:pointer}}
.seg button[aria-checked="true"]{{background:var(--bg);color:var(--ink);font-weight:700;box-shadow:0 0 0 1px var(--hair)}}
:focus-visible{{outline:2px solid var(--sea);outline-offset:2px}}
.L[hidden]{{display:none}}
h1{{font-family:"Shippori Mincho",serif;font-weight:800;font-size:30px;margin:4px 0 2px;line-height:1.25}}
.lede{{color:var(--mute);margin:0 0 6px}}
.two{{width:120px;height:9px;background:linear-gradient(var(--sea),var(--sea)) 0 0/100% 3px no-repeat,linear-gradient(var(--tuna),var(--tuna)) 0 6px/60% 3px no-repeat;margin:12px 0 4px}}
h2{{font-family:"Shippori Mincho",serif;font-size:20px;border-left:4px solid var(--sea);padding-left:10px;margin:30px 0 8px}}
.rooms{{width:100%;border-collapse:collapse;font-size:15px}}.rooms th,.rooms td{{border:1px solid var(--hair);padding:8px 10px;text-align:left}}.rooms tr:first-child th{{background:var(--tint);font-size:13px}}
.st.ok{{color:var(--mute)}}.st.in{{color:var(--kon);font-weight:700}}.st.res{{color:var(--sea);font-weight:700}}
.res-note{{margin:10px 0 0;padding:10px 14px;border-radius:10px;background:var(--sea-tint);color:var(--ink);font-size:15px}}
.note{{font-size:13px;color:var(--mute);margin:6px 0}}
.ph{{margin:12px 0}}.ph img{{display:block;width:100%;border-radius:12px}}.ph figcaption{{font-size:12px;color:var(--mute);margin-top:4px}}
.shoot{{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;aspect-ratio:4/3;border:1.5px dashed var(--hair);border-radius:12px;background:var(--sea-tint);color:var(--kon)}}
.cam{{width:44px;fill:none;stroke:var(--kon);stroke-width:2.5;opacity:.75}}.lbl{{font-size:11px;font-weight:700;letter-spacing:.12em}}.what{{font-size:13px;color:var(--mute)}}
.alert{{border:2px solid var(--tuna);border-radius:10px;padding:12px 14px;color:var(--tuna);font-weight:700}}
h3{{font-family:"Shippori Mincho",serif;font-size:18px;margin:22px 0 6px;padding-top:12px;border-top:1px dashed var(--hair)}}h3 small{{display:block;font-family:"Zen Kaku Gothic New",sans-serif;font-size:12px;font-weight:700;color:var(--sea);letter-spacing:.06em}}
.stops{{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0}}.stops a{{display:inline-flex;align-items:center;min-height:44px;padding:0 14px;border-radius:999px;background:var(--sea-tint);color:var(--sea);font-weight:700;font-size:14px;text-decoration:none}}
ol{{padding-left:1.3em}}li{{margin:6px 0}}
.fill{{display:inline-block;font-size:12px;color:var(--tuna);background:#FBEAEC;border:1px dashed var(--tuna);border-radius:4px;padding:0 6px}}
a{{color:var(--sea)}}
</style></head><body><main>
<img class="hd" src="../../img/brand/header-maguro.jpg" alt="" width="1500" height="500">
<div class="top"><div class="brand"><img src="../../img/brand/logo.png" alt="" width="40" height="40">MIURA A-TEI</div>
<div class="seg" role="radiogroup" aria-label="Language / 言語"><button type="button" role="radio" aria-checked="true" data-l="ja" lang="ja">JP</button><button type="button" role="radio" aria-checked="false" data-l="en" lang="en">EN</button></div></div>
{ja}
{en}
</main>
<script>(function(){{
var bs=[].slice.call(document.querySelectorAll('.seg button')),ls=[].slice.call(document.querySelectorAll('.L'));
function set(l,save){{ls.forEach(function(d){{d.hidden=d.getAttribute('data-l')!==l}});bs.forEach(function(b){{b.setAttribute('aria-checked',b.getAttribute('data-l')===l)}});
document.documentElement.lang=l;if(save){{try{{localStorage.setItem('lang',l)}}catch(e){{}}}}}}
[].forEach.call(document.querySelectorAll('img[data-copy]'),function(i){{var o=document.querySelector('img[data-key="'+i.getAttribute('data-copy')+'"]');if(o)i.src=o.src}});
bs.forEach(function(b){{b.onclick=function(){{set(b.getAttribute('data-l'),true)}}}});
var p=null;try{{p=localStorage.getItem('lang')}}catch(e){{}}
set(location.hash==='#en'?'en':(location.hash==='#ja'?'ja':(p==='en'?'en':'ja')),false);
}})();</script></body></html>'''
    lj, le = landmark()
    body = body.replace('@LANDMARK_JA@', html.escape(lj)).replace('@LANDMARK_EN@', html.escape(le))
    return body.encode()

if __name__ == '__main__':
    plain = build()
    (ROOT / 'arrival.src.html').write_bytes(plain)
    h = hashlib.sha256(plain).hexdigest()
    out = ROOT / 'm' / token_for('.token-arrival') / 'index.html'
    if not ('--force' in sys.argv) and out.exists() and HASH.exists() and HASH.read_text() == h:
        print('変わっていないので、そのまま:', f'{BASE}m/{token_for(".token-arrival")}/')
        sys.exit(0)
    url = lock(plain, '.token-arrival', '到着カード / Arrival card')
    HASH.write_text(h)
    print('書きました:', url)
