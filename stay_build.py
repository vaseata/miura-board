#!/usr/bin/env python3
"""三浦A邸 滞在ガイド（stay/index.html）を作る。単体で動く。build.py の末尾から呼べる。
- 宿泊中・宿泊予定の人向けのトップ。到着前→到着→滞在中→出発の順にカードを並べる
- A邸の座標・番地・暗証番号・Wi-Fiパスは出さない（home.local.json は読まない）
- リンク先がまだ無いカードは href を None にすると「準備中」で出る"""
import html, pathlib, re, shutil, sys, urllib.parse
from stay_pages import PAGES

HERE = pathlib.Path(__file__).parent
OUT = HERE / "stay"
PHOTOS = HERE / "stay-react" / "public" / "photos"   # 位置情報を消した写真（公開前に、使ってよいかヤヌキが確認する）
PROTO = "--proto" in sys.argv            # ラピッドプロトタイプ：記入待ちをダミー文で埋める（公開しない）
if PROTO:
    OUT = HERE / "stay_proto"
DEMO = "--demo" in sys.argv              # 人に見せる試作版（2026-11-14 鍋パーティー用）：stay/ に書く。記入待ちは正直に札で出し、
                                         # 写真の無いカードは文字だけ、写真待ちの枠は隠す。外の読みものには公開済みの場所写真（CC0）を付ける
DEMO_IMG = {"華さんのおすすめマップ": "../img/misaki_harbor.jpg", "三浦のガイドブック": "../img/jogashima_harbor.jpg",
            "最近の三浦": "../img/miura_beach.jpg", "歴史さんぽ": "../img/jogashima_lighthouse.jpg"}

# トップのカードに付けるサムネイル（hrefの先頭部分 → 写真のkey）。写真が無ければダミー画像になる
CARD_IMG = {"chusha.html": "parking", "tochaku.html#ikikata": "bus", "tochaku.html#genkan": "genkan",
            "setsubi.html": "kitchen", "ofuro.html": "bath", "gomi.html": "gomibako", "rules.html": "washitsu",
            "raihou.html": "genkan", "bosai.html": "koudai", "konnatoki.html": "kyuto", "shuppatsu.html": "linenbox",
            "mochimono.html": "season", "faq.html": "kitchen"}
CARD_IMG_BY_NAME = {"防災マップ（3D）": "hazard", "おうちを探検（3D）": "tour", "華さんのおすすめマップ": "map",
                    "三浦のガイドブック": "guide", "最近の三浦": "news", "歴史さんぽ": "history"}

def photo_src(key):
    """写真があれば img/<key>.jpg を返し、無ければ None。"""
    return f"img/{key}.jpg" if (PHOTOS / f"{key}.jpg").exists() else None

def dummy_img(label):
    """ダミー画像（SVG）。写真が無い場所に置く。"""
    label = label if len(label) <= 14 else label[:13] + "…"
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">'
           '<rect width="800" height="600" fill="#DDE5EC"/><rect x="2" y="2" width="796" height="596" fill="none" stroke="#9FB1C1" stroke-width="4" stroke-dasharray="14 10"/>'
           '<g fill="none" stroke="#7E92A4" stroke-width="10" stroke-linejoin="round"><rect x="300" y="230" width="200" height="140" rx="16"/><circle cx="400" cy="300" r="38"/><path d="M340 230l14-24h92l14 24"/></g>'
           f'<text x="400" y="440" font-size="34" text-anchor="middle" fill="#4F6070" font-family="sans-serif" font-weight="700">ダミー画像</text>'
           f'<text x="400" y="490" font-size="30" text-anchor="middle" fill="#4F6070" font-family="sans-serif">{html.escape(label)}</text></svg>')
    return "data:image/svg+xml;charset=utf-8," + urllib.parse.quote(svg)

# --proto のときの、空欄のダミー文。実際の内容ではない（見た目と流れを確かめる用）
DUMMY = {
    "ブレーカーの場所": "ブレーカーは、玄関を入ってすぐの壁の上にあります。",
    "食器・鍋・洗剤の場所": "食器と鍋は、キッチンの棚にあります。洗剤は、流しの下です。",
    "頼み先": "頼み先は、家守です。連絡は、オープンチャットかメールでお願いします。",
    "追加の寝具などの置き場と、頼み先": "追加の寝具と延長コードは、和室の押し入れにあります。使いたいときは、家守に連絡してください。",
    "軽・普通車などの制限": "停められるのは、軽自動車と普通車です。大きな車は、事前に相談してください。",
    "給湯器の操作の写真": "（ここに、給湯器のスイッチの写真が入ります）",
    "給湯器とガスの元栓の場所": "給湯器は、家の外の裏手にあります。ガスの元栓は、その横です。",
    "生ごみの置き場": "生ごみは、キッチンの専用バケツに入れてください。",
    "消火器の場所": "消火器は、キッチンの入口の横にあります。",
    "最新の運賃と時刻（京急バスで確認）": "（ここに、京急バスの最新の運賃と時刻が入ります）",
    "懐中電灯の場所": "懐中電灯は、玄関の下駄箱の上にあります。",
    "定食の今の内容・値段・提供条件（お店に確認）": "（ここに、定食の内容・値段・提供条件が入ります）",
    "収集所の場所・時間": "収集所は、家の前の角にあります。朝8時までに出してください。",
    "冬の暖房の種類と、使うときの注意": "冬は、エアコンと電気ストーブを使います。ストーブの近くに、ものを置かないでください。",
    "冬の暖房": "エアコンと電気ストーブを使います。",
    "代わりの駐車場": "満車のときは、三崎港のそばの駐車場を、案内します。",
    "予約のしかた（電話・アプリ・家守を通すか）": "予約は、電話かアプリでお願いします。",
    "予約のしかた・停められる車の大きさ・満車のときの代わりの場所": "予約は、電話かアプリでお願いします。停められるのは、軽自動車と普通車です。満車のときは、三崎港のそばの駐車場を案内します。",
    "リネン回収ボックスの場所": "リネン回収ボックスは、和室の共有スペースにあります。",
    "ドライヤー・風呂桶の場所": "ドライヤーは洗面所の棚に、風呂桶は浴室の隅にあります。",
    "ドネーションボックスの場所": "ドネーションボックスは、キッチンの調味料の棚にあります。",
    "ゴミ箱と袋の置き場": "ゴミ箱は、居間の隅に。ゴミ袋は、その下の引き出しにあります。",
    "ガスの元栓の場所": "ガスの元栓は、給湯器の横にあります。",
    "やらなくてよいこと（掃除機、布団をたたむ、など）": "掃除機をかけたり、布団をたたんだりしなくても、大丈夫です。",
    "漆喰のかまどの使い方（キッチンの黒板の下にある説明書の内容）": "①薪と着火材を入れる。②火をつけて、ふたを少し開けておく。③使い終わったら、火が消えたことを確かめる。（ダミーです）",
    "パーキングから家までの歩く時間と道": "パーキングから家までは、歩いて5分ほどです。港のほうへ、まっすぐ進みます。",
    "この家から近い高台と、歩く道": "近い高台は、家の裏手の坂の上です。歩いて、10分ほどです。",
}

TOUR = "https://miura-a-stay-guide.vaseata.chatgpt.site/"  # 部屋の3Dウォークスルー（外部）
HAZARD = "../m/xjBud6bKpyJnzrbD/"                          # 合言葉つき（宿泊者に合言葉を伝える）

# (見出し, 一言, [(カード名, 説明, href, 新しいタブか)])
# トップに常時出す入口（緊急と、初めての人が迷う3つ）。href が None なら「準備中」
QUICK = [
    ("防災（揺れたら・避難）", "bosai.html", True),
    ("困ったとき", "konnatoki.html", True),
    ("連絡の順番", "konnatoki.html#renraku", False),
    ("鍵", "konnatoki.html#kagi", False),
    ("ゴミ", "gomi.html", False),
    ("お風呂", "ofuro.html", False),
]

# 章立ては house_faq/guide_structure_research.md の第3節（2026-10-21 決定。まず日本語のみ）
SECTIONS = [
    ("到着前", "来る前に見ておくと安心", [
        ("行き方", "バス（日の出が近くて平坦）・電車・車。到着の時間", "tochaku.html#ikikata", False),
        ("駐車場・駐輪場", "この家に駐車場はありません。来る前に予約を", "chusha.html", False),
        ("持ち物と季節", "持ってくるもの・季節の行事・寒さと蚊", "mochimono.html", False),
        ("防災マップ（3D）", "避難先と津波・高潮・土砂災害。合言葉つき（宿泊者のみ）", HAZARD, False),
    ]),
    ("到着したら", "まず家の中を見てみよう", [
        ("玄関から入るまで", "プレート・キーボックス・靴。チャイムは鳴らしません", "tochaku.html#genkan", False),
        ("おうちを探検（3D）", "玄関から各部屋へ。Wi-Fi・ゴミ出し・チェックアウトもここ", TOUR, True),
        ("設備とWi-Fi", "お部屋・キッチン・冷暖房・Wi-Fi", "setsubi.html", False),
        ("お風呂とトイレ・洗濯", "お湯の出し方・洗濯・近くの銭湯", "ofuro.html", False),
        ("ゴミ出し", "分別・出す日と場所", "gomi.html", False),
    ]),
    ("滞在中", "三浦をたのしむ", [
        ("家のルール", "夜・火の元・音。理由も1行ずつ", "rules.html", False),
        ("来客・外泊・郵便", "友人を呼ぶ／外泊／早着・遅くまで／荷物が届く", "raihou.html", False),
        ("華さんのおすすめマップ", "家守のおすすめのお店。平面と3D", "../guide/map-preview.html", False),
        ("三浦のガイドブック", "食べる・見る・体験する。今日やっているお店も", "../guide/", False),
        ("最近の三浦", "イベントや交通の近況", "../index.html", False),
        ("歴史さんぽ", "ゆかりの地を時代ごとに3D地図で", "../history/", False),
    ]),
    ("困ったとき・出発", "", [
        ("地震・津波・体調が悪いとき", "揺れたら・津波・119と#7119", "bosai.html", False),
        ("こんなとき（逆引き）", "連絡の順番／鍵が開かない／お湯が出ない／ブレーカー／壊した／忘れ物", "konnatoki.html", False),
        ("出発のチェックリスト", "時刻・やること・忘れ物", "shuppatsu.html", False),
        ("よくある質問", "鍵・Wi-Fi・ゴミ・洗濯など", "faq.html", False),
    ]),
]

SECTION_ID = {"到着前": "mae", "到着したら": "toochaku", "滞在中": "taizai", "困ったとき・出発": "komatta"}
STEPS = [("mae", "到着前", "来る前に"), ("toochaku", "着いたら", "家の中"), ("taizai", "滞在中", "三浦を楽しむ"), ("komatta", "困った・出発", "いざというとき")]

CSS = """
:root{--bg:#fff;--ink:#14202B;--mute:#4F6070;--hair:#D9E1E8;--tint:#F2F6F9;--sea:#0A5A8C;--sea-tint:#E6F0F6;--tuna:#B8243A;
--mincho:"Shippori Mincho","Hiragino Mincho ProN","Yu Mincho",serif;--gothic:"Zen Kaku Gothic New","Hiragino Sans","Yu Gothic",sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0E1820;--ink:#E8EEF3;--mute:#9DB0C0;--hair:#25384A;--tint:#16252F;--sea:#6BB6E3;--sea-tint:#12303F;--tuna:#F08A9A}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--gothic);line-height:1.7}
.wrap{max-width:720px;margin:0 auto;padding:0 16px 56px}
header{padding:40px 0 20px;border-bottom:3px solid var(--sea)}
.eyebrow{font-size:12px;letter-spacing:.18em;color:var(--sea);font-weight:700}
h1{font-family:var(--mincho);font-weight:800;font-size:34px;margin:6px 0 4px;line-height:1.25}
.lede{color:var(--mute);margin:0;font-size:15px}
h2{font-family:var(--mincho);font-size:22px;margin:36px 0 2px}
.sub{color:var(--mute);font-size:13px;margin:0 0 12px}
.grid{display:grid;gap:10px}
@media(min-width:600px){.grid{grid-template-columns:1fr 1fr}}
.card{display:block;padding:14px 16px;border:1px solid var(--hair);border-radius:10px;background:var(--tint);color:inherit;text-decoration:none}
a.card:hover,a.card:focus-visible{border-color:var(--sea);background:var(--sea-tint)}
.card b{display:block;font-size:16px}
.card span{display:block;font-size:13px;color:var(--mute)}
.card.soon{opacity:.6}
.card.soon b::after{content:"準備中";margin-left:8px;font-size:11px;color:var(--tuna);border:1px solid var(--tuna);border-radius:99px;padding:1px 7px;vertical-align:2px}
.quick{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 0}
.chip{display:inline-block;padding:8px 14px;border-radius:99px;border:1px solid var(--hair);background:var(--tint);font-size:14px;color:inherit;text-decoration:none}
.chip.alert{border-color:var(--tuna);color:var(--tuna);font-weight:700}
.chip.soon{opacity:.55}
footer{margin-top:40px;font-size:12px;color:var(--mute)}
.back{display:inline-block;margin:16px 0 0;font-size:13px;color:var(--sea);text-decoration:none}
.page h2{border-left:4px solid var(--sea);padding-left:10px;font-size:20px;margin:32px 0 8px}
.page p{margin:8px 0}.page ul,.page ol{margin:8px 0;padding-left:1.4em}.page li{margin:6px 0}
.alert-box{margin:20px 0 0;padding:14px 16px;border:2px solid var(--tuna);border-radius:10px;color:var(--tuna);font-weight:700}
.note{font-size:12px;color:var(--mute);margin:6px 0}
table{width:100%;border-collapse:collapse;margin:10px 0;font-size:14px}
th,td{border:1px solid var(--hair);padding:8px 10px;text-align:left;vertical-align:top}
th{background:var(--tint)}
.links{display:flex;flex-direction:column;gap:6px;margin:8px 0}
.links a{color:var(--sea)}
.tmp{display:inline-block;font-size:11px;font-weight:700;color:#7a5b00;background:#FFF2C2;border:1px solid #E0C050;border-radius:4px;padding:0 6px;margin-left:4px}
.phrow{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 0 14px}
.phrow figure{margin:0}
.phrow img{display:block;width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:10px}
.phrow figcaption{font-size:11px;color:var(--mute);margin-top:4px;line-height:1.4}
.phrow .wait div{aspect-ratio:1/1;display:flex;align-items:center;justify-content:center;border:1px dashed var(--tuna);border-radius:10px;color:var(--tuna);font-size:12px}
.toc{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 4px}
.toc a{padding:7px 12px;border:1px solid var(--hair);border-radius:99px;background:var(--sea-tint);color:var(--sea);font-weight:700;font-size:13px;text-decoration:none}
.ph{margin:12px 0 18px}
.ph img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:12px;background:var(--tint)}
.ph figcaption{font-size:12px;color:var(--mute);margin-top:6px}
.ph.wait div{padding:36px 16px;text-align:center;border:1px dashed var(--tuna);border-radius:12px;color:var(--tuna);font-size:13px}
.card.im{padding:0;overflow:hidden;display:grid;grid-template-columns:104px 1fr;align-items:stretch}
.card.im img{display:block;width:100%;height:100%;min-height:92px;object-fit:cover}
.card.im .tx{padding:10px 14px;align-self:center}
.card.im.big{display:block}
.card.im.big img{aspect-ratio:16/9;height:auto}
.card.im.big .tx{padding:12px 16px 14px}
.steps{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:14px 0 0}
.steps a{display:block;text-align:center;padding:9px 2px;border:1px solid var(--hair);border-radius:10px;background:var(--sea-tint);color:var(--sea);font-weight:700;font-size:13px;text-decoration:none}
.steps small{display:block;font-weight:400;font-size:10px;color:var(--mute)}
.slim{margin:12px 0 0;padding:6px 10px;font-size:12px;color:#6b5314;background:#FFF8E1;border:1px dashed #C9A227;border-radius:8px}
.hero{margin:18px 0 0}
.hero img{display:block;width:100%;aspect-ratio:16/10;object-fit:cover;border-radius:14px}
.dummy{display:inline-block;font-size:11px;font-weight:700;color:#fff;background:#8A6D1F;border-radius:4px;padding:0 6px;margin-right:4px}
.fill{display:inline-block;font-size:12px;color:var(--tuna);background:var(--tuna-tint,#FBEAEC);border:1px dashed var(--tuna);border-radius:4px;padding:0 6px}
.qa{border:1px solid var(--hair);border-radius:10px;margin:8px 0;background:var(--tint)}
.qa summary{cursor:pointer;padding:12px 14px;font-weight:700;list-style:none}
.qa summary::-webkit-details-marker{display:none}
.qa summary::before{content:"Q　";color:var(--sea)}
.qa[open] summary{border-bottom:1px solid var(--hair)}
.qa p{margin:0;padding:10px 14px}.qa .more{padding-top:0;font-size:13px}.qa a{color:var(--sea)}
.bar{position:fixed;left:0;right:0;bottom:0;display:flex;gap:6px;padding:8px 12px calc(8px + env(safe-area-inset-bottom));background:var(--bg);border-top:1px solid var(--hair);z-index:10;justify-content:center}
.bar a{flex:1;max-width:220px;text-align:center;padding:9px 6px;border-radius:99px;border:1px solid var(--hair);background:var(--tint);font-size:13px;color:inherit;text-decoration:none}
.bar a.alert{border-color:var(--tuna);color:var(--tuna);font-weight:700}
body{padding-bottom:64px}
.draft{margin:16px 0 0;padding:10px 14px;border:1px dashed #E0C050;background:#FFF9E0;color:#5a4400;border-radius:8px;font-size:13px}
"""

CREDIT = ("<br>三浦の景色の写真：Wikimedia Commons（Aspere 撮影・CC0）" if DEMO else "")

def esc(s): return html.escape(str(s), quote=True)

def card(name, desc, href, ext, first=False):
    key = CARD_IMG.get(href or "") or CARD_IMG_BY_NAME.get(name)
    if DEMO and name in DEMO_IMG:
        key, src = None, DEMO_IMG[name]
        tgt = ' target="_blank" rel="noopener"' if ext else ""
        cls = "card im big" if first else "card im"
        return (f'<a class="{cls}" href="{esc(href)}"{tgt}><img src="{src}" alt="" loading="lazy">'
                f'<div class="tx"><b>{esc(name)}</b><span>{esc(desc)}</span></div></a>')
    if href and key:
        src = photo_src(key)
        if src or PROTO:
            im = src or dummy_img(name)
            tgt = ' target="_blank" rel="noopener"' if ext else ""
            cls = "card im big" if first else "card im"
            return (f'<a class="{cls}" href="{esc(href)}"{tgt}><img src="{im}" alt="" loading="lazy">'
                    f'<div class="tx"><b>{esc(name)}</b><span>{esc(desc)}</span></div></a>')
    if not href:
        return f'<div class="card soon"><b>{esc(name)}</b><span>{esc(desc)}</span></div>'
    tgt = ' target="_blank" rel="noopener"' if ext else ""
    return f'<a class="card" href="{esc(href)}"{tgt}><b>{esc(name)}</b><span>{esc(desc)}</span></a>'

def chip(name, href, alert):
    cls = "chip" + (" alert" if alert else "") + ("" if href else " soon")
    label = esc(name) + ("" if href else "（準備中）")
    return f'<a class="{cls}" href="{esc(href)}">{label}</a>' if href else f'<span class="{cls}">{label}</span>'

def inline(text):
    t = esc(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = t.replace("\n", "<br><small>")+("</small>" if "\n" in t else "")
    t = t.replace("{仮}", '<span class="tmp">仮</span>')
    if PROTO:
        t = re.sub(r"\{記入:(.+?)\}", lambda m: '<span class="dummy">ダミー</span>' + DUMMY.get(m.group(1), m.group(1) + "が、ここに入ります。"), t)
    t = re.sub(r"\{記入:(.+?)\}", r'<span class="fill">記入待ち：\1</span>', t)
    return t

def count_marks(blocks):
    raw = repr(blocks)
    nophoto = sum(1 for b in blocks if b[0] == "photo" and not photo_src(b[1]))
    nophoto += sum(1 for b in blocks if b[0] == "photos" for k, _a, _c in b[1] if not photo_src(k))
    return raw.count("{仮}"), len(re.findall(r"\{記入:", raw)) + nophoto

def render_block(b):
    kind = b[0]
    if kind == "h2":
        i = f' id="{esc(b[2])}"' if len(b) > 2 else ""
        return f"<h2{i}>{inline(b[1])}</h2>"
    if kind == "p": return f"<p>{inline(b[1])}</p>"
    if kind == "note": return f'<p class="note">{inline(b[1])}</p>'
    if kind == "alert": return f'<div class="alert-box">{inline(b[1])}</div>'
    if kind in ("ul", "ol"): return f"<{kind}>" + "".join(f"<li>{inline(x)}</li>" for x in b[1]) + f"</{kind}>"
    if kind == "table":
        head = "<tr>" + "".join(f"<th>{inline(h)}</th>" for h in b[1]) + "</tr>"
        rows = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in b[2])
        return f"<table>{head}{rows}</table>"
    if kind == "photo":
        key, alt, cap = b[1], b[2], b[3]
        src = photo_src(key)
        if src:
            return f'<figure class="ph"><img src="{src}" alt="{esc(alt)}" loading="lazy"><figcaption>{esc(cap)}</figcaption></figure>'
        if PROTO:
            return f'<figure class="ph dm"><img src="{dummy_img(alt)}" alt="ダミー画像：{esc(alt)}" loading="lazy"><figcaption><span class="dummy">ダミー</span>{esc(cap)}</figcaption></figure>'
        if DEMO: return ""
        return f'<figure class="ph wait"><div>写真待ち：{esc(cap)}</div></figure>'
    if kind == "photos":
        cells = []
        for key, alt, cap in b[1]:
            src = photo_src(key)
            if src: cells.append(f'<figure><img src="{src}" alt="{esc(alt)}" loading="lazy"><figcaption>{esc(cap)}</figcaption></figure>')
            elif PROTO: cells.append(f'<figure class="dm"><img src="{dummy_img(cap)}" alt="ダミー画像：{esc(alt)}" loading="lazy"><figcaption><span class="dummy">ダミー</span>{esc(cap)}</figcaption></figure>')
            elif DEMO: continue
            else: cells.append(f'<figure class="wait"><div>写真待ち</div><figcaption>{esc(cap)}</figcaption></figure>')
        if DEMO and not cells: return ""
        return '<div class="phrow">' + "".join(cells) + "</div>"
    if kind == "toc":
        return '<nav class="toc">' + "".join(f'<a href="#{esc(i)}">{esc(l)}</a>' for i, l in b[1]) + "</nav>"
    if kind == "faq":
        out = []
        for item in b[1]:
            q, ans, link = item
            more = f'<p class="more"><a href="{esc(link)}">くわしく見る →</a></p>' if link else ""
            out.append(f'<details class="qa"><summary>{inline(q)}</summary><p>{inline(ans)}</p>{more}</details>')
        return "".join(out)
    if kind == "links":
        return '<div class="links">' + "".join(f'<a href="{esc(u)}" target="_blank" rel="noopener">{esc(l)} ↗</a>' if u.startswith("http") else f'<a href="{esc(u)}">{esc(l)} →</a>' for l, u in b[1]) + "</div>"
    raise ValueError(kind)

def head_html(title):
    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>{esc(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@500;800&family=Zen+Kaku+Gothic+New:wght@400;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head>"""

BAR = ('<nav class="bar"><a href="index.html">トップ・ページ一覧</a>'
       '<a class="alert" href="bosai.html">防災</a><a class="alert" href="konnatoki.html">困ったとき</a></nav>')

def with_auto_toc(blocks):
    """h2が4つ以上あり、目次ブロックが無いページには、自動で目次を付ける（h2にidも振る）。"""
    if any(b[0] == "toc" for b in blocks):
        return blocks
    h2s = [b for b in blocks if b[0] == "h2"]
    if len(h2s) < 4:
        return blocks
    out, toc, n = [], [], 0
    for b in blocks:
        if b[0] == "h2":
            n += 1
            sid = b[2] if len(b) > 2 else f"s{n}"
            toc.append((sid, re.sub(r"[（(].*?[）)]", "", b[1]).strip()))
            out.append(("h2", b[1], sid))
        else:
            out.append(b)
    # 最初のh2の直前に目次を入れる
    i = next(k for k, b in enumerate(out) if b[0] == "h2")
    return out[:i] + [("toc", toc)] + out[i:]

def build_page(slug, spec, public):
    spec = dict(spec, blocks=with_auto_toc(spec["blocks"]))
    tmp, fill = count_marks(spec["blocks"])
    notice = ""
    if (tmp or fill) and not public:
        if DEMO:
            notice = '<div class="slim"><b>試作版</b>：「記入待ち」と「仮」の札がある所は、家守に確かめてから直します。</div>'
        elif PROTO:
            notice = '<div class="draft"><b>ラピッドプロトタイプ。</b>「ダミー」の札の文は、作り話です。実際の内容ではありません。</div>'
        else:
          notice = f'<div class="draft">確認中のページです。仮の文が{tmp}か所、記入待ちが{fill}か所あります。公開する前に、家守に確かめて直します。</div>'
    body = "".join(render_block(b) for b in spec["blocks"])
    page = f"""{head_html(spec["title"] + "｜三浦A邸 滞在ガイド")}<body><div class="wrap page">
<a class="back" href="index.html">← 滞在ガイドのトップ</a>
<header><div class="eyebrow">MIURA · STAY GUIDE</div><h1>{esc(spec["title"])}</h1>
<p class="lede">{esc(spec["lede"])}</p></header>
{notice}
{body}
<footer>三浦A邸（ADDress）。住所・鍵の番号・Wi-Fiのパスワードは、予約前日のメールにあります。</footer>
</div>{BAR}</body></html>"""
    (OUT / f"{slug}.html").write_text(page, encoding="utf-8")
    return tmp, fill

def build(public=False):
    if PROTO:
        dummy = '<div class="slim"><b>プロトタイプ</b>：「ダミー」の札は作り話です。防災や場所の情報を、信じないでください。</div>'
    else:
        dummy = ""
    if DEMO:
        dummy = ('<div class="draft"><b>試作版（2026年11月）</b>です。住人有志が作っている、三浦A邸の非公式の案内です。'
                 '「記入待ち」「仮」の札がある所は、家守に確かめてから入れます。公式のルールは、ADDress のヘルプと家守の案内が優先です。'
                 '<br>気づいたこと・「あったらいいな」は、作った人に一言ください。</div>')
    dummy = dummy if (PROTO or public or DEMO) else '<div class="draft">これは、構造を確認するための<b>ダミーのサイト</b>です。「仮」の札のある文は仮の内容、「記入待ち」は、あとで入れる情報です。正確な情報は、これから追加します。</div>'
    hs = photo_src("hero")
    hero = (f'<div class="hero"><img src="{hs}" alt="三浦A邸の廊下"></div>' if hs else
            (f'<div class="hero"><img src="{dummy_img("トップの写真")}" alt="ダミー画像"></div>' if PROTO else ""))
    steps = '<nav class="steps">' + "".join(f'<a href="#{i}">{esc(n)}<small>{esc(s)}</small></a>' for i, n, s in STEPS) + "</nav>"
    quick = '<div class="quick">' + "".join(chip(*q) for q in QUICK) + "</div>"
    parts = []
    for title, sub, cards in SECTIONS:
        sid = SECTION_ID.get(title, "")
        parts.append(f'<section id="{sid}"><h2>{esc(title)}</h2>' + (f'<p class="sub">{esc(sub)}</p>' if sub else "")
                     + '<div class="grid">' + "".join(card(*c, first=(i == 0)) for i, c in enumerate(cards)) + "</div></section>")
    page = f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>三浦A邸 滞在ガイド</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@500;800&family=Zen+Kaku+Gothic+New:wght@400;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><div class="wrap">
<header><div class="eyebrow">MIURA · STAY GUIDE</div><h1>三浦A邸 滞在ガイド</h1>
<p class="lede">来る前・着いたとき・滞在中・帰るときに、ここを開いてください。</p>
{hero}{quick}{steps}</header>
{dummy}
{"".join(parts)}
<footer>三浦A邸（ADDress）。住所・鍵の番号・Wi-Fiのパスワードは、予約前日のメールにあります。{CREDIT}</footer>
</div>{BAR}</body></html>"""
    OUT.mkdir(exist_ok=True)
    (OUT / "img").mkdir(exist_ok=True)
    if PHOTOS.exists():
        for f in PHOTOS.glob("*.jpg"):
            shutil.copy(f, OUT / "img" / f.name)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print("stay/index.html を書きました")
    left = 0
    for slug, spec in PAGES.items():
        tmp, fill = build_page(slug, spec, public)
        left += tmp + fill
        print(f"stay/{slug}.html を書きました（仮 {tmp}・記入待ち {fill}）")
    if public and left:
        sys.exit(f"公開できません：仮・記入待ちが{left}か所残っています")

if __name__ == "__main__":
    build(public="--public" in sys.argv)
