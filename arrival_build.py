#!/usr/bin/env python3
"""到着カード（合言葉つき）を作る：建物の見分け方・外観・バス停からの道・今夜の部屋の空き。

使い方:  python3 arrival_build.py          … 中身が変わったときだけ暗号化して m/<m/.token-arrival>/index.html を書く
         python3 arrival_build.py --force  … 変わっていなくても書き直す
- 合言葉は share_lock.py と同じ（ハザードマップと共通。m/.pass か SHARE_PASS）
- 部屋の空きは、予約タスク（miura-yoyaku-calendar）が毎回書く台帳 宿泊者.json から作る。**名前は出さない**
- 外観・道の写真は private_photos/<key>.jpg（.gitignore）に置く。暗号文の中に埋め込むので、公開リポジトリに平文では入らない
- 平文の確認用に arrival.src.html（.gitignore）も書く
"""
import base64, datetime as dt, hashlib, html, json, sys
from pathlib import Path
from share_lock import lock, token_for, ROOT, BASE

LEDGER = Path('/Users/yanudon/claude/mameden-trio/apps/miura-watcher/data/宿泊者.json')
PRIV = ROOT / 'private_photos'
GUEST_ROOMS = ['101', '201', '203']        # 会員さんが泊まる部屋（台帳の題の先頭の番号）
JST = dt.timezone(dt.timedelta(hours=9))
HASH = ROOT / 'm' / '.arrival.hash'
esc = lambda s: html.escape(str(s), quote=True)

def photo(key, cap):
    f = PRIV / f'{key}.jpg'
    if f.exists():
        b = base64.b64encode(f.read_bytes()).decode()
        return f'<figure class="ph"><img src="data:image/jpeg;base64,{b}" alt="{esc(cap)}"><figcaption>{esc(cap)}</figcaption></figure>'
    return (f'<figure class="ph"><div class="shoot"><svg class="cam" viewBox="0 0 48 40" aria-hidden="true"><rect x="3" y="9" width="42" height="28" rx="6"/>'
            f'<circle cx="24" cy="23" r="8"/><path d="M16 9l3-5h10l3 5"/></svg><span class="lbl">撮影予定</span><span class="what">{esc(cap)}</span></div></figure>')

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
def md(d): return f'{d.month}/{d.day}（{WD[d.weekday()]}）'

def build():
    today = dt.datetime.now(JST).date()
    rows, written = rooms(today)
    if rows:
        tr = ''.join(f'<tr><th>{r}</th><td class="st {"ok" if t == "空き" else "in"}">{t}{("（〜" + md(e) + "朝）") if e else ""}</td>'
                     f'<td class="st {"ok" if n == "空き" else "in"}">{n}</td></tr>' for r, t, e, n in rows)
        rooms_html = (f'<table class="rooms"><tr><th>部屋</th><th>今夜 {md(today)}</th><th>明晩</th></tr>{tr}</table>'
                      f'<p class="note">予約の記録から自動で作っています（{esc(written)} 時点）。直前の予約・取り消しは入っていないことがあります。泊まっている人の名前は載せていません。</p>')
    else:
        rooms_html = '<p class="note">いまは部屋の空きを表示できません。</p>'
    body = f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>到着カード｜三浦A邸</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@800&family=Zen+Kaku+Gothic+New:wght@400;700&display=swap">
<style>
:root{{color-scheme:light;--bg:#fff;--ink:#14202B;--mute:#4F6070;--hair:#D9E1E8;--tint:#F2F6F9;--sea:#0A5A8C;--sea-tint:#E6F0F6;--tuna:#B8243A;--kon:#2E4C9E}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:"Zen Kaku Gothic New","Hiragino Sans",sans-serif;font-size:16px;line-height:1.7}}
main{{max-width:720px;margin:0 auto;padding:16px 16px 56px}}
.hd{{display:block;width:100%;height:auto;border-radius:10px}}
.brand{{display:flex;align-items:center;gap:8px;margin-top:12px;font-size:12px;font-weight:700;letter-spacing:.16em;color:var(--sea)}}.brand img{{width:40px;height:40px}}
h1{{font-family:"Shippori Mincho",serif;font-weight:800;font-size:30px;margin:4px 0 2px;line-height:1.25}}
.lede{{color:var(--mute);margin:0 0 6px}}
.two{{width:120px;height:9px;background:linear-gradient(var(--sea),var(--sea)) 0 0/100% 3px no-repeat,linear-gradient(var(--tuna),var(--tuna)) 0 6px/60% 3px no-repeat;margin:12px 0 4px}}
h2{{font-family:"Shippori Mincho",serif;font-size:20px;border-left:4px solid var(--sea);padding-left:10px;margin:30px 0 8px}}
.rooms{{width:100%;border-collapse:collapse;font-size:15px}}.rooms th,.rooms td{{border:1px solid var(--hair);padding:8px 10px;text-align:left}}.rooms tr:first-child th{{background:var(--tint);font-size:13px}}
.st.ok{{color:var(--mute)}}.st.in{{color:var(--kon);font-weight:700}}
.note{{font-size:13px;color:var(--mute);margin:6px 0}}
.ph{{margin:12px 0}}.ph img{{display:block;width:100%;border-radius:12px}}.ph figcaption{{font-size:12px;color:var(--mute);margin-top:4px}}
.shoot{{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;aspect-ratio:4/3;border:1.5px dashed var(--hair);border-radius:12px;background:var(--sea-tint);color:var(--kon)}}
.cam{{width:44px;fill:none;stroke:var(--kon);stroke-width:2.5;opacity:.75}}.lbl{{font-size:11px;font-weight:700;letter-spacing:.12em}}.what{{font-size:13px;color:var(--mute)}}
.alert{{border:2px solid var(--tuna);border-radius:10px;padding:12px 14px;color:var(--tuna);font-weight:700}}
ol{{padding-left:1.3em}}li{{margin:6px 0}}
.fill{{display:inline-block;font-size:12px;color:var(--tuna);background:#FBEAEC;border:1px dashed var(--tuna);border-radius:4px;padding:0 6px}}
a{{color:var(--sea)}}
</style></head><body><main>
<img class="hd" src="../../img/brand/header-maguro.jpg" alt="" width="1500" height="500">
<div class="brand"><img src="../../img/brand/logo.png" alt="" width="40" height="40">MIURA A-TEI · 宿泊者向け</div>
<h1>到着カード</h1>
<p class="lede">はじめて来る方へ。建物の見分け方と、今夜の部屋の様子です。</p>
<div class="two"></div>

<h2>今夜の部屋</h2>
<p>ご自分の部屋番号は、予約の前日に届くメールの「部屋番号」にあります。</p>
{rooms_html}

<h2>建物の見分け方</h2>
<div class="alert">隣の家と、住所が同じです。三浦A邸は、アイボリー色の外観の建物です。玄関の表札に、ADDress のマークがあります。</div>
{photo('gaikan', '三浦A邸の外観')}
{photo('hyosatsu', '玄関の表札と ADDress のプレート')}

<h2>バス停「日の出」から</h2>
<p><span class="fill">記入待ち：バス停から家までの道順と、歩く時間</span></p>
{photo('michi1', 'バス停「日の出」を降りたところ')}
{photo('michi2', '曲がる角')}
{photo('michi3', '家の前の道')}

<h2>入るとき</h2>
<ol><li>玄関にキーボックスがあります。暗証番号は、前日のメールの「入室情報」のページに書いてあります。</li>
<li>チャイムは鳴らさず、そのままお入りください。</li>
<li>リネン・トイレ・お風呂の場所は、<a href="{BASE}stay/tochaku.html#mazu">滞在ガイドの「着いたら、まず」</a>にあります。</li></ol>
<p class="note">このページの URL と合言葉は、ほかの人に教えないでください。</p>
</main></body></html>'''
    return body.encode()

if __name__ == '__main__':
    plain = build()
    (ROOT / 'arrival.src.html').write_bytes(plain)
    h = hashlib.sha256(plain).hexdigest()
    out = ROOT / 'm' / token_for('.token-arrival') / 'index.html'
    if not ('--force' in sys.argv) and out.exists() and HASH.exists() and HASH.read_text() == h:
        print('変わっていないので、そのまま:', f'{BASE}m/{token_for(".token-arrival")}/')
        sys.exit(0)
    url = lock(plain, '.token-arrival', '到着カード')
    HASH.write_text(h)
    print('書きました:', url)
