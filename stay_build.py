#!/usr/bin/env python3
"""三浦A邸 滞在ガイド（stay/index.html）を作る。単体で動く。build.py の末尾から呼べる。
- 宿泊中・宿泊予定の人向けのトップ。到着前→到着→滞在中→出発の順にカードを並べる
- A邸の座標・番地・暗証番号・Wi-Fiパスは出さない（home.local.json は読まない）
- リンク先がまだ無いカードは href を None にすると「準備中」で出る"""
import html, pathlib, re, shutil, sys, urllib.parse
from stay_pages import PAGES
from stay_pages_en import PAGES_EN
from ui_parts import UI_CSS, sitenav, bottomnav

HERE = pathlib.Path(__file__).parent
OUT = HERE / "stay"
SITE = "https://vaseata.github.io/miura-board/stay/"
LANG = "ja"          # build() が "ja" → "en" の順に切り替える。英語版は stay/en/（2026-11-14 2か国語化）
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
    """写真があれば img/<key>.jpg を返し、無ければ None。英語版（stay/en/）からは ../img/。"""
    if not (PHOTOS / f"{key}.jpg").exists():
        return None
    return f"{'../' if LANG == 'en' else ''}img/{key}.jpg"

def fix(href):
    """英語版は1段深いので、../ で始まるリンクを1段上げる。stay の中のページ（bosai.html など）は英語版どうしでつなぐ。"""
    if not href or LANG != "en" or href.startswith(("http", "#", "data:")):
        return href
    return "../" + href if href.startswith("../") else href

# 画面の言葉（日本語・英語）
L = {
    "ja": {"soon": "準備中", "shoot": "撮影予定", "tmp": "仮", "fill": "記入待ち：", "go": "見る →", "more": "くわしく見る →",
           "back": "← 滞在ガイドのトップ", "suffix": "｜三浦A邸 滞在ガイド", "site": "三浦A邸 滞在ガイド",
           "foot": "三浦A邸（ADDress）。住所・鍵の番号・Wi-Fiのパスワードは、予約前日のメールにあります。",
           "credit": "<br>三浦の景色の写真：Wikimedia Commons（Aspere 撮影・CC0）",
           "demo_note": '<div class="slim"><b>試作版</b>：「記入待ち」と「仮」の札がある所は家守に確かめてから直します。「撮影予定」の枠には、写真を順に入れていきます。</div>',
           "demo_top": ('<div class="draft"><b>試作版（2026年11月）</b>です。住人有志が作っている、三浦A邸の非公式の案内です。'
                        '「記入待ち」「仮」の札がある所は、家守に確かめてから入れます。公式のルールは、ADDress のヘルプと家守の案内が優先です。'
                        '<br>気づいたこと・「あったらいいな」は、作った人に一言ください。</div>'),
           "lede": "来る前・着いたとき・滞在中・帰るときに、ここを開いてください。",
           "motif_alt": "跳ねるマグロと波、富士山と朝日の絵", "hero_alt": "三浦A邸の廊下", "steps_label": "章"},
    "en": {"soon": "Coming soon", "shoot": "PHOTO COMING SOON", "tmp": "To be confirmed", "fill": "Pending: ", "go": "Open →", "more": "More →",
           "back": "← Stay guide home", "suffix": " | Miura A-tei Stay Guide", "site": "Miura A-tei Stay Guide",
           "foot": "Miura A-tei (ADDress). The address, key-box code, and Wi-Fi password are in the email you receive the day before your stay.",
           "credit": "<br>Photos of Miura scenery: Wikimedia Commons (by Aspere, CC0)",
           "demo_note": '<div class="slim"><b>Draft</b>: items tagged “Pending” or “To be confirmed” will be fixed after checking with the host. Photos will be added to the “Photo coming soon” frames.</div>',
           "demo_top": ('<div class="draft"><b>Draft version (November 2026).</b> An unofficial guide to Miura A-tei, made by residents. '
                        'Items tagged “Pending” or “To be confirmed” will be filled in after checking with the house host (yamori). '
                        'Official rules in ADDress Help and the host’s instructions come first. This is a translation of the Japanese version; if they differ, the Japanese version is correct.'
                        '<br>Ideas or corrections? Please tell the people who made it.</div>'),
           "lede": "Open this page before you come, when you arrive, during your stay, and when you leave.",
           "motif_alt": "Drawing of a leaping tuna, waves, Mt. Fuji and the rising sun", "hero_alt": "Hallway of Miura A-tei", "steps_label": "Sections"},
}
def t(k): return L[LANG][k]

def langswitch(slug):
    """JP / EN の切り替え（設計図の segmented の形。中身はリンク）。選んだ言語は localStorage 'lang' に覚える。"""
    page = "" if slug == "index" else f"{slug}.html"
    ja_href, en_href = (f"../{page}", "") if LANG == "en" else ("", f"en/{page}")
    ja_href = ja_href or (page or "./")
    en_href = en_href or (page or "./")
    cur = ' aria-current="page"'
    return (f'<nav class="lang" aria-label="Language / 言語">'
            f'<a href="{esc(ja_href)}" hreflang="ja" lang="ja"{cur if LANG == "ja" else ""}>JP</a>'
            f'<a href="{esc(en_href)}" hreflang="en" lang="en"{cur if LANG == "en" else ""}>EN</a></nav>')

LANG_JS = """<script>(function(){try{var L=document.documentElement.lang;
document.querySelectorAll('.lang a').forEach(function(a){a.addEventListener('click',function(){a.href=a.href.split('#')[0]+location.hash;try{localStorage.setItem('lang',a.hreflang)}catch(e){}})});
var p=null;try{p=localStorage.getItem('lang')}catch(e){}
var r=document.referrer,same=false;try{same=!!r&&new URL(r).origin===location.origin}catch(e){}
if(p&&p!==L&&!same){var a=document.querySelector('.lang a[hreflang="'+p+'"]');if(a)location.replace(a.href.split('#')[0]+location.hash)}}catch(e){}})();</script>"""

def alternates(slug):
    page = "" if slug == "index" else f"{slug}.html"
    return (f'<link rel="alternate" hreflang="ja" href="{SITE}{page}">'
            f'<link rel="alternate" hreflang="en" href="{SITE}en/{page}">'
            f'<link rel="alternate" hreflang="x-default" href="{SITE}{page}">')

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
HAZARD = "../m/xjBud6bKpyJnzrbD/"
_tok = HERE / "m" / ".token-arrival"
ARRIVAL = (f"../m/{_tok.read_text().strip()}/" if _tok.exists() and (HERE / "m" / _tok.read_text().strip() / "index.html").exists() else None)   # 到着カード（合言葉つき・arrival_build.py）                          # 合言葉つき（宿泊者に合言葉を伝える）

# (見出し, 一言, [(カード名, 説明, href, 新しいタブか)])
# トップに常時出す入口（緊急と、初めての人が迷う3つ）。href が None なら「準備中」
QUICK = [
    ("防災・避難", "bosai.html", True),
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

# 英語版のトップ。並び・リンクは上の日本語と1対1（写真の選び方は日本語のカード名で引く）
QUICK_EN = ["Emergency & evacuation", "Help", "Who to contact", "Key", "Garbage", "Bath"]
SECTIONS_EN = [
    ("Before you come", "Good to read before you arrive", [
        ("Getting here", "Bus (Hinode stop is close and flat), train, car. Arrival time"),
        ("Parking (cars & bikes)", "This house has no parking. Book before you come"),
        ("What to bring & seasons", "What to bring, seasonal events, cold and mosquitoes"),
        ("Hazard map (3D)", "Evacuation sites; tsunami, storm surge, landslides. Passphrase (guests only). In Japanese"),
    ]),
    ("When you arrive", "First, look around the house", [
        ("From the entrance to inside", "Plate, key box, shoes. No need to ring the bell"),
        ("Explore the house (3D)", "From the entrance to each room. In Japanese"),
        ("Facilities & Wi-Fi", "Rooms, kitchen, heating and cooling, Wi-Fi"),
        ("Bath, toilet & laundry", "Hot water, laundry, nearby public bath"),
        ("Garbage", "Sorting, collection days and place"),
    ]),
    ("During your stay", "Enjoy Miura", [
        ("House rules", "Night, fire, noise — with the reasons"),
        ("Visitors, nights away & mail", "Inviting friends / nights away / early or late / parcels"),
        ("Hana's recommended map", "The host's favorite places. 2D and 3D. In Japanese"),
        ("Miura Guidebook", "Eat, see, do. Shops open today. In Japanese"),
        ("Miura News", "Events and traffic news. In Japanese"),
        ("History walk", "Historic places by era on a 3D map. In Japanese"),
    ]),
    ("Help & leaving", "", [
        ("Earthquake, tsunami & feeling sick", "When it shakes, tsunami, 119 and #7119"),
        ("If something happens", "Who to contact / key / hot water / breaker / broken items / things left behind"),
        ("Check-out checklist", "Time, what to do, things left behind"),
        ("FAQ", "Key, Wi-Fi, garbage, laundry, and more"),
    ]),
]
STEPS_EN = [("Before", "you come"), ("Arrival", "in the house"), ("Stay", "enjoy Miura"), ("Help", "leaving")]

def check_en():
    """英訳が日本語の正本と同じ形か確かめる（ブロックの種類・id・写真・リンク・札の数）。ずれていたら止める。"""
    def shape(b):
        k = b[0]
        if k == "h2": return (k, b[2] if len(b) > 2 else None)
        if k == "photo": return (k, b[1])
        if k == "photos": return (k, tuple(x[0] for x in b[1]))
        if k == "links": return (k, tuple(u for _l, u in b[1]))
        if k == "faq": return (k, tuple(x[2] for x in b[1]))
        if k == "eight": return (k, tuple(x[2] for x in b[1]))
        if k == "toc": return (k, tuple(i for i, _l in b[1]))
        if k in ("ul", "ol"): return (k, len(b[1]))
        if k == "table": return (k, len(b[1]), len(b[2]))
        return (k,)
    errs = []
    if PAGES.keys() != PAGES_EN.keys():
        errs.append(f"ページの並びが違う: {set(PAGES) ^ set(PAGES_EN)}")
    for slug in PAGES:
        ja, en = PAGES[slug]["blocks"], PAGES_EN.get(slug, {}).get("blocks", [])
        if [shape(b) for b in ja] != [shape(b) for b in en]:
            errs.append(f"{slug}: ブロックの形が違う")
        for mark in ("{仮}", "{記入:"):
            if repr(ja).count(mark) != repr(en).count(mark):
                errs.append(f"{slug}: {mark} の数が違う（日 {repr(ja).count(mark)}・英 {repr(en).count(mark)}）")
    if [len(c) for _t, _s, c in SECTIONS] != [len(c) for _t, _s, c in SECTIONS_EN] or len(QUICK) != len(QUICK_EN):
        errs.append("トップのカードの数が違う")
    if errs:
        sys.exit("英訳（stay_pages_en.py）が日本語とずれています:\n  " + "\n  ".join(errs))

CSS = """
:root{color-scheme:light;--bg:#fff;--ink:#14202B;--mute:#4F6070;--hair:#D9E1E8;--tint:#F2F6F9;--sea:#0A5A8C;--sea-tint:#E6F0F6;--tuna:#B8243A;--kon:#2E4C9E;
--mincho:"Shippori Mincho","Hiragino Mincho ProN","Yu Mincho",serif;--gothic:"Zen Kaku Gothic New","Hiragino Sans","Yu Gothic",sans-serif}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--gothic);line-height:1.7}
.wrap{max-width:720px;margin:0 auto;padding:0 16px 56px}
header{padding:40px 0 22px;position:relative}
header::after{content:"";position:absolute;left:0;bottom:0;width:120px;height:9px;background:linear-gradient(var(--sea),var(--sea)) 0 0/100% 3px no-repeat,linear-gradient(var(--tuna),var(--tuna)) 0 6px/60% 3px no-repeat}
.brand{display:flex;align-items:center;gap:10px}.brand img{width:44px;height:44px;flex:none}
.motif{display:block;width:100%;max-width:100%;height:auto;margin:0 0 12px;border-radius:10px}
header.top{padding-top:8px}
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
.quick{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 0}
.chip{display:inline-flex;align-items:center;min-height:44px;padding:0 16px;border-radius:999px;border:1px solid var(--hair);background:var(--tint);font-size:14px;color:inherit;text-decoration:none}
.sos2{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:18px 0 0}
.sos2 .btn{font-size:14px;padding:0 10px}
.chip.soon{opacity:.55}
footer{margin-top:40px;font-size:12px;color:var(--mute)}
.back{margin:4px 0 0;font-size:14px}
.page h2{border-left:4px solid var(--sea);padding-left:10px;font-size:20px;margin:32px 0 8px}
.page p{margin:8px 0}.page ul,.page ol{margin:8px 0;padding-left:1.4em}.page li{margin:6px 0}
.alert-box{margin:20px 0 0;padding:14px 16px;border:2px solid var(--tuna);border-radius:10px;color:var(--tuna);font-weight:700}
.note{font-size:12px;color:var(--mute);margin:6px 0}
table{width:100%;border-collapse:collapse;margin:10px 0;font-size:14px}
th,td{border:1px solid var(--hair);padding:8px 10px;text-align:left;vertical-align:top}
th{background:var(--tint)}
.links{display:flex;flex-direction:column;gap:6px;margin:8px 0}
.links a{display:flex;align-items:center;min-height:44px;color:var(--sea)}
.page header{padding-top:12px}
.tmp{display:inline-block;font-size:11px;font-weight:700;color:#7a5b00;background:#FFF2C2;border:1px solid #E0C050;border-radius:4px;padding:0 6px;margin-left:4px}
.phrow{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 0 14px}
.phrow figure{margin:0}
.phrow img{display:block;width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:10px}
.phrow figcaption{font-size:11px;color:var(--mute);margin-top:4px;line-height:1.4}
.phrow .wait div{aspect-ratio:1/1;display:flex;align-items:center;justify-content:center;border:1px dashed var(--tuna);border-radius:10px;color:var(--tuna);font-size:12px}
.toc{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 4px}
.toc a{display:inline-flex;align-items:center;min-height:44px;padding:0 14px;border:1px solid var(--hair);border-radius:999px;background:var(--tint);color:var(--ink);font-size:14px;text-decoration:none}
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
.steps{display:grid;grid-template-columns:repeat(4,1fr);margin:22px 0 0;border-top:1px solid var(--hair);border-bottom:1px solid var(--hair)}
.steps a{display:flex;flex-direction:column;justify-content:center;min-height:56px;text-align:center;padding:6px 2px;color:var(--sea);font-weight:700;font-size:13px;line-height:1.3;text-decoration:none}
.steps a+a{border-left:1px solid var(--hair)}
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
body{padding-bottom:calc(72px + env(safe-area-inset-bottom))}
.shoot{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;aspect-ratio:4/3;width:100%;max-width:100%;border:1.5px dashed var(--hair);border-radius:12px;background:var(--sea-tint);color:var(--kon);text-align:center;padding:10px}
.shoot .cam{width:44px;height:auto;fill:none;stroke:var(--kon);stroke-width:2.5;stroke-linejoin:round;opacity:.75}
.shoot .lbl{font-size:11px;font-weight:700;letter-spacing:.12em;color:var(--kon)}
.shoot .what{font-size:13px;color:var(--mute);line-height:1.4}
.phrow .shoot{aspect-ratio:1/1;border-radius:10px;padding:6px}.phrow .shoot .what{display:none}.phrow .shoot .cam{width:32px}
.card.im .shoot{aspect-ratio:auto;height:100%;min-height:92px;border:0;border-right:1.5px dashed var(--hair);border-radius:0}
.card.im .shoot.sm .cam{width:32px}
.card.im.big .shoot{aspect-ratio:16/9;height:auto;border-right:0;border-bottom:1.5px dashed var(--hair)}
.eight,.page ol.eight{list-style:none;counter-reset:n;padding:0;margin:10px 0;display:grid;gap:8px}
.eight li{counter-increment:n;display:grid;grid-template-columns:28px 1fr;column-gap:10px;padding:10px 12px;border:1px solid var(--hair);border-radius:10px;background:var(--tint)}
.eight li::before{content:counter(n);grid-row:1/4;width:28px;height:28px;border-radius:50%;background:var(--sea);color:#fff;font-weight:700;font-size:14px;display:flex;align-items:center;justify-content:center}
.eight b{font-size:15px}.eight span{font-size:13px;color:var(--mute)}.eight a{font-size:13px;font-weight:700;color:var(--sea);text-decoration:none;justify-self:start}
.eight .soon{font-size:12px;color:var(--mute)}
.draft{margin:16px 0 0;padding:10px 14px;border:1px dashed #E0C050;background:#FFF9E0;color:#5a4400;border-radius:8px;font-size:13px}
.topbar{display:flex;align-items:center;gap:8px;padding-top:8px}
.lang{display:inline-grid;grid-template-columns:1fr 1fr;gap:2px;padding:3px;margin-left:auto;background:var(--tint);border:1px solid var(--hair);border-radius:999px;flex:none}
.lang a{display:flex;align-items:center;justify-content:center;min-width:52px;min-height:38px;border-radius:999px;color:var(--mute);font:400 14px/1 var(--gothic);letter-spacing:.04em;text-decoration:none}
.lang a[aria-current="page"]{background:var(--bg);color:var(--ink);font-weight:700;box-shadow:0 0 0 1px var(--hair)}
.topbar .back{margin:0}
html[lang="en"] .card.soon b::after{content:"Coming soon"}
html[lang="en"] h1{font-size:30px}
""" + UI_CSS

CAM = ('<svg class="cam" viewBox="0 0 48 40" aria-hidden="true"><rect x="3" y="9" width="42" height="28" rx="6"/>'
       '<circle cx="24" cy="23" r="8"/><path d="M16 9l3-5h10l3 5"/></svg>')

def shoot(cap, small=False):
    """撮影予定の枠（写真が届くまでの置き場）。"""
    if small:
        return f'<div class="shoot sm">{CAM}</div>'
    return f'<div class="shoot">{CAM}<span class="lbl">{t("shoot")}</span><span class="what">{esc(cap)}</span></div>'

def esc(s): return html.escape(str(s), quote=True)

def card(name, desc, href, ext, first=False, jname=None):
    jname = jname or name
    key = CARD_IMG.get(href or "") or CARD_IMG_BY_NAME.get(jname)
    href = fix(href)
    if DEMO and jname in DEMO_IMG:
        key, src = None, fix(DEMO_IMG[jname])
        tgt = ' target="_blank" rel="noopener"' if ext else ""
        cls = "card im big" if first else "card im"
        return (f'<a class="{cls}" href="{esc(href)}"{tgt}><img src="{src}" alt="" loading="lazy">'
                f'<div class="tx"><b>{esc(name)}</b><span>{esc(desc)}</span></div></a>')
    if href and key:
        src = photo_src(key)
        if not src and not PROTO:
            tgt = ' target="_blank" rel="noopener"' if ext else ""
            cls = "card im big" if first else "card im"
            return (f'<a class="{cls}" href="{esc(href)}"{tgt}>{shoot(name, small=not first)}'
                    f'<div class="tx"><b>{esc(name)}</b><span>{esc(desc)}</span></div></a>')
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
    if alert and href:
        return f'<a class="btn btn-emergency" href="{esc(href)}">{esc(name)}</a>'
    cls = "chip" + ("" if href else " soon")
    label = esc(name) + ("" if href else f"（{t('soon')}）")
    return f'<a class="{cls}" href="{esc(href)}">{label}</a>' if href else f'<span class="{cls}">{label}</span>'

def inline(text):
    t = esc(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = t.replace("\n", "<br><small>")+("</small>" if "\n" in t else "")
    t = t.replace("{仮}", f'<span class="tmp">{L[LANG]["tmp"]}</span>')
    if PROTO:
        t = re.sub(r"\{記入:(.+?)\}", lambda m: '<span class="dummy">ダミー</span>' + DUMMY.get(m.group(1), m.group(1) + "が、ここに入ります。"), t)
    t = re.sub(r"\{記入:(.+?)\}", lambda m: f'<span class="fill">{L[LANG]["fill"]}{m.group(1)}</span>', t)
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
    if kind == "eight":
        lis = []
        for title, ans, href in b[1]:
            href = (ARRIVAL + ("#en" if LANG == "en" else "")) if href == "ARRIVAL" and ARRIVAL else (None if href == "ARRIVAL" else href)
            href = fix(href)
            ext = href and href.startswith("http")
            tgt = ' target="_blank" rel="noopener"' if ext else ""
            go = f'<a href="{esc(href)}"{tgt}>{t("go")}</a>' if href else f'<span class="soon">{t("soon")}</span>'
            lis.append(f'<li><b>{esc(title)}</b><span>{inline(ans)}</span>{go}</li>')
        return '<ol class="eight">' + "".join(lis) + "</ol>"
    if kind == "photo":
        key, alt, cap = b[1], b[2], b[3]
        src = photo_src(key)
        if src:
            return f'<figure class="ph"><img src="{src}" alt="{esc(alt)}" loading="lazy"><figcaption>{esc(cap)}</figcaption></figure>'
        if PROTO:
            return f'<figure class="ph dm"><img src="{dummy_img(alt)}" alt="ダミー画像：{esc(alt)}" loading="lazy"><figcaption><span class="dummy">ダミー</span>{esc(cap)}</figcaption></figure>'
        return f'<figure class="ph">{shoot(cap)}<figcaption>{esc(cap)}</figcaption></figure>'
    if kind == "photos":
        cells = []
        for key, alt, cap in b[1]:
            src = photo_src(key)
            if src: cells.append(f'<figure><img src="{src}" alt="{esc(alt)}" loading="lazy"><figcaption>{esc(cap)}</figcaption></figure>')
            elif PROTO: cells.append(f'<figure class="dm"><img src="{dummy_img(cap)}" alt="ダミー画像：{esc(alt)}" loading="lazy"><figcaption><span class="dummy">ダミー</span>{esc(cap)}</figcaption></figure>')
            else: cells.append(f'<figure>{shoot(cap)}<figcaption>{esc(cap)}</figcaption></figure>')
        return '<div class="phrow">' + "".join(cells) + "</div>"
    if kind == "toc":
        return '<nav class="toc">' + "".join(f'<a href="#{esc(i)}">{esc(l)}</a>' for i, l in b[1]) + "</nav>"
    if kind == "faq":
        out = []
        for item in b[1]:
            q, ans, link = item
            more = f'<p class="more"><a href="{esc(fix(link))}">{t("more")}</a></p>' if link else ""
            out.append(f'<details class="qa"><summary>{inline(q)}</summary><p>{inline(ans)}</p>{more}</details>')
        return "".join(out)
    if kind == "links":
        return '<div class="links">' + "".join(f'<a href="{esc(u)}" target="_blank" rel="noopener">{esc(l)} ↗</a>' if u.startswith("http") else f'<a href="{esc(fix(u))}">{esc(l)} →</a>' for l, u in b[1]) + "</div>"
    raise ValueError(kind)

def head_html(title, slug):
    root = "../../" if LANG == "en" else "../"
    return f"""<!doctype html>
<html lang="{LANG}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>{esc(title)}</title>
{alternates(slug)}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@500;800&family=Zen+Kaku+Gothic+New:wght@400;700&display=swap" rel="stylesheet">
<link rel="icon" href="{root}img/brand/logo.png"><link rel="apple-touch-icon" href="{root}img/brand/logo.png">
<style>{CSS}</style></head>"""

def root(): return "../../" if LANG == "en" else "../"

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
            notice = t("demo_note")
        elif PROTO:
            notice = '<div class="draft"><b>ラピッドプロトタイプ。</b>「ダミー」の札の文は、作り話です。実際の内容ではありません。</div>'
        else:
          notice = f'<div class="draft">確認中のページです。仮の文が{tmp}か所、記入待ちが{fill}か所あります。公開する前に、家守に確かめて直します。</div>'
    body = "".join(render_block(b) for b in spec["blocks"])
    page = f"""{head_html(spec["title"] + t("suffix"), slug)}<body>{sitenav("stay", root(), lang=LANG)}<div class="wrap page">
<div class="topbar"><a class="btn btn-tertiary back" href="index.html">{t("back")}</a>{langswitch(slug)}</div>
<header><div class="brand"><img src="{root()}img/brand/logo.png" alt="" width="44" height="44"><div class="eyebrow">MIURA · STAY GUIDE</div></div><h1>{esc(spec["title"])}</h1>
<p class="lede">{esc(spec["lede"])}</p></header>
{notice}
{body}
<footer>{t("foot")}</footer>
</div>{bottomnav(slug, lang=LANG)}{LANG_JS}</body></html>"""
    (OUTL / f"{slug}.html").write_text(page, encoding="utf-8")
    return tmp, fill

def build_lang(public=False):
    if PROTO:
        dummy = '<div class="slim"><b>プロトタイプ</b>：「ダミー」の札は作り話です。防災や場所の情報を、信じないでください。</div>'
    else:
        dummy = ""
    if DEMO:
        dummy = t("demo_top")
    dummy = dummy if (PROTO or public or DEMO) else '<div class="draft">これは、構造を確認するための<b>ダミーのサイト</b>です。「仮」の札のある文は仮の内容、「記入待ち」は、あとで入れる情報です。正確な情報は、これから追加します。</div>'
    hs = photo_src("hero")
    hero = (f'<div class="hero"><img src="{hs}" alt="{t("hero_alt")}"></div>' if hs else
            (f'<div class="hero"><img src="{dummy_img("トップの写真")}" alt="ダミー画像"></div>' if PROTO else ""))
    en = LANG == "en"
    steps_t = [(i, *STEPS_EN[k]) for k, (i, _n, _s) in enumerate(STEPS)] if en else STEPS
    steps = f'<nav class="steps" aria-label="{t("steps_label")}">' + "".join(f'<a href="#{i}">{esc(n)}<small>{esc(s)}</small></a>' for i, n, s in steps_t) + "</nav>"
    quick_t = [(QUICK_EN[k] if en else q[0], q[1], q[2]) for k, q in enumerate(QUICK)]
    quick = ('<div class="sos2">' + "".join(chip(*q) for q in quick_t if q[2]) + "</div>"
             + '<div class="quick">' + "".join(chip(*q) for q in quick_t if not q[2]) + "</div>")
    parts = []
    for k, (title, sub, cards) in enumerate(SECTIONS):
        sid = SECTION_ID.get(title, "")
        if en:
            title, sub, names = SECTIONS_EN[k]
            cs = [(names[j][0], names[j][1], c[2], c[3], c[0]) for j, c in enumerate(cards)]
        else:
            cs = [(c[0], c[1], c[2], c[3], c[0]) for c in cards]
        parts.append(f'<section id="{sid}"><h2>{esc(title)}</h2>' + (f'<p class="sub">{esc(sub)}</p>' if sub else "")
                     + '<div class="grid">' + "".join(card(n, d, h, x, first=(i == 0), jname=j) for i, (n, d, h, x, j) in enumerate(cs)) + "</div></section>")
    credit = t("credit") if DEMO else ""
    page = f"""{head_html(t("site"), "index")}<body>{sitenav("stay", root(), lang=LANG)}<div class="wrap">
<div class="topbar">{langswitch("index")}</div>
<header class="top"><img class="motif" src="{root()}img/brand/header-maguro.jpg" alt="{t("motif_alt")}" width="1500" height="500">
<div class="brand"><img src="{root()}img/brand/logo.png" alt="" width="44" height="44"><div class="eyebrow">MIURA · STAY GUIDE</div></div><h1>{t("site")}</h1>
<p class="lede">{t("lede")}</p>
{hero}{quick}{steps}</header>
{dummy}
{"".join(parts)}
<footer>{t("foot")}{credit}</footer>
</div>{bottomnav("index", lang=LANG)}{LANG_JS}</body></html>"""
    OUTL.mkdir(exist_ok=True)
    (OUTL / "index.html").write_text(page, encoding="utf-8")
    pre = "stay/en/" if en else "stay/"
    print(f"{pre}index.html を書きました")
    left = 0
    for slug, spec in (PAGES_EN if en else PAGES).items():
        tmp, fill = build_page(slug, spec, public)
        left += tmp + fill
        print(f"{pre}{slug}.html を書きました（仮 {tmp}・記入待ち {fill}）")
    return left

def build(public=False):
    global LANG, OUTL
    check_en()
    OUT.mkdir(exist_ok=True)
    (OUT / "img").mkdir(exist_ok=True)
    if PHOTOS.exists():
        for f in PHOTOS.glob("*.jpg"):
            shutil.copy(f, OUT / "img" / f.name)
    left = 0
    for LANG, OUTL in (("ja", OUT), ("en", OUT / "en")):
        left += build_lang(public)
    LANG = "ja"
    if public and left:
        sys.exit(f"公開できません：仮・記入待ちが{left}か所残っています")


if __name__ == "__main__":
    build(public="--public" in sys.argv)
