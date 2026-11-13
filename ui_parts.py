"""3サイト共通の「操作の部品」（デザインシステム「三浦A邸 大漁旗」の設計図どおり）。

設計図：https://claude.ai/artifact/UCZjqtS3fEUUbG61myCg2P （操作の部品）
- 行動のボタン（.btn）＝角丸12pxの四角。主（.btn-primary）は1画面に1つ・48px
- 選ぶ部品＝丸。絞り込みの札（.fchip）は見た目36px・押せる範囲44px・選ぶと✓と薄い青
- 1つだけ選ぶもの（.seg）＝segmented。4つまで・44px
- 滞在ガイドの下のバー（.bn）＝4つ・アイコンと文字
- 3サイト共通のサイトの切り替え（.sn）＝一番上の細い帯

色は各サイトの :root の変数（--bg --ink --mute --hair --tint --sea --sea-tint --tuna）をそのまま使う。
stay_build.py・guide_build.py・build.py が読み込む。
"""

from html import escape as _esc

UI_CSS = """
/* ── 操作の部品（ui_parts.py・設計図どおり） ── */
:focus-visible{outline:2px solid var(--sea);outline-offset:2px}
/* サイトの切り替え（2026-11-14 討議で直した版） */
.sn{position:relative;z-index:30;background:var(--bg);border-bottom:1px solid var(--hair)}
.sn-in{display:flex;align-items:center;gap:0;max-width:var(--sn-w,1240px);margin:0 auto;padding:0 max(16px,env(safe-area-inset-right)) 0 max(16px,env(safe-area-inset-left));overflow-x:auto;scrollbar-width:none}
.sn-in::-webkit-scrollbar{display:none}
.sn .home{display:flex;align-items:center;gap:6px;min-height:44px;margin-right:auto;padding:0 6px 0 0;color:var(--ink);font:800 14px/1 var(--mincho);text-decoration:none;white-space:nowrap;flex:none}
.sn .home img{width:28px;height:28px;display:block;background:#fff;border-radius:6px}
.sn a.s{display:flex;align-items:center;gap:4px;min-height:44px;padding:0 9px;color:var(--ink);font:400 14px/1 var(--gothic);letter-spacing:0;text-decoration:none;white-space:nowrap;border-bottom:3px solid transparent;flex:none}
.sn a.s[aria-current]{font-weight:700;border-bottom-color:var(--sea)}
.sn a.s small{font-size:11px;color:var(--ink);font-weight:400}
.sn a.sos{min-width:44px;justify-content:center;color:var(--tuna);font-weight:700}
.sn a.sos svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.sn a:focus-visible{outline-offset:-3px}
@media (max-width:400px){.sn .home .t{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)} .sn a.s{padding:0 6px} .sn.has-sos a.s{font-size:13px;padding:0 4px} .sn.has-sos a.sos{padding:0 2px 0 6px;gap:2px}}
@media (max-width:359px){.sn a.s{font-size:13px;padding:0 6px}.sn-in{mask-image:linear-gradient(90deg,#000 calc(100% - 16px),transparent);-webkit-mask-image:linear-gradient(90deg,#000 calc(100% - 16px),transparent)}}
.sn.has-sos .sn-in{flex-wrap:wrap}
@media (max-width:359px){.sn.has-sos .sn-in{mask-image:none;-webkit-mask-image:none}}
@media print{.sn,.bn,.lang{display:none!important}body{padding-bottom:0!important}}
/* ボタン（行動） */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;min-height:44px;padding:0 18px;border-radius:12px;border:1.5px solid transparent;font:700 15px/1.3 var(--gothic);letter-spacing:0;text-align:center;text-decoration:none;cursor:pointer;transition:transform 120ms,background-color 120ms}
.btn:active{transform:scale(.97)}
.btn-primary{min-height:48px;background:var(--sea);color:var(--on,#fff)}
.btn-primary:active{filter:brightness(.88)}
.btn-secondary{background:var(--sea-tint);color:var(--sea)}
.btn-tertiary{min-height:44px;padding:0 4px;background:none;color:var(--sea);justify-content:flex-start}
.btn-emergency{min-height:48px;background:var(--bg);color:var(--tuna);border-color:var(--tuna)}
.btn[hidden],.fchip[hidden]{display:none}
/* 絞り込みの札（複数選べる） */
.fchip{position:relative;display:inline-flex;align-items:center;gap:4px;height:36px;margin:4px 0;padding:0 14px;border-radius:999px;border:1px solid var(--hair);background:var(--bg);color:var(--ink);font:400 14px/1 var(--gothic);letter-spacing:0;white-space:nowrap;cursor:pointer;transition:background-color 180ms,border-color 180ms;flex:none}
.fchip::after{content:"";position:absolute;inset:-4px 0}
.fchip[aria-pressed="true"],.fchip[aria-checked="true"]{background:var(--sea-tint);border-color:var(--sea);color:var(--sea);font-weight:700}
.fchip[aria-pressed="true"]::before,.fchip[aria-checked="true"]::before{content:"✓"}
.fchip .n{font-weight:400;font-size:11px;opacity:.8;margin-left:2px}
/* 切り替え（1つだけ選ぶ・4つまで） */
.seg{display:grid;grid-auto-flow:column;grid-auto-columns:1fr;gap:2px;padding:3px;background:var(--tint);border:1px solid var(--hair);border-radius:999px}
.seg button{position:relative;min-height:38px;border:0;border-radius:999px;background:none;color:var(--mute);font:400 14px/1 var(--gothic);letter-spacing:0;cursor:pointer;transition:background-color 180ms}
.seg button::after{content:"";position:absolute;inset:-4px -1px}
.seg button[aria-checked="true"]{background:var(--bg);color:var(--ink);font-weight:700;box-shadow:0 0 0 1px var(--hair)}
/* 下のバー（滞在ガイド） */
.bn{position:fixed;left:0;right:0;bottom:0;z-index:40;display:grid;grid-template-columns:repeat(4,1fr);background:var(--bg);border-top:1px solid var(--hair);padding:0 env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left)}
.bn a{position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;min-height:56px;color:var(--mute);font:700 11px/1.2 var(--gothic);text-decoration:none}
.bn svg{width:24px;height:24px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.bn a[aria-current="page"]{color:var(--sea)}
.bn a[aria-current="page"]::before{content:"";position:absolute;top:-1px;left:22%;right:22%;height:3px;border-radius:0 0 3px 3px;background:var(--sea)}
.bn a.sos{color:var(--tuna)}
.bn a.sos[aria-current="page"]::before{background:var(--tuna)}
@media (min-width:720px){.bn{left:50%;right:auto;width:560px;transform:translateX(-50%);border:1px solid var(--hair);border-bottom:0;border-radius:12px 12px 0 0}}
@media (prefers-reduced-motion:reduce){.btn,.fchip,.seg button{transition:none}.btn:active{transform:none}}
"""

SITES = [  # (key, 日本語版の道, 英語版の道 or None, 日本語の名前, 英語の名前)
    ("stay", "stay/", "stay/en/", "滞在ガイド", "Stay guide"),
    ("guide", "guide/", None, "ガイドブック", "Guidebook"),
    ("board", "", None, "最近の三浦", "Miura news"),
]
_SOS_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17v.01"/></svg>'


def sitenav(current, root, lang="ja", is_top=False, sos=False):
    """3サイト共通の切り替えの帯。root はページからリポジトリの一番上への道（"../" など）。
    is_top：そのサイトのトップページなら True（aria-current="page"）。
    sos：滞在ガイドの外（ガイドブック・最近の三浦）では True。右端に赤い▲「防災」を出す（2026-11-14 討議）。"""
    en = lang == "en"
    home = root + ("stay/en/" if en else "stay/")
    items = []
    for key, path, en_path, ja, en_l in SITES:
        jp_only = en and en_path is None
        href = (root + (en_path if en and en_path else path)) or "./"
        cur = (' aria-current="page"' if is_top else ' aria-current="true"') if key == current else ""
        hl = ' hreflang="ja"' if jp_only else ""
        label = _esc(en_l if en else ja) + (" <small>(JP)</small>" if jp_only else "")
        items.append(f'<a class="s" href="{_esc(href)}"{hl}{cur}>{label}</a>')
    if sos:
        bosai = root + ("stay/en/bosai.html" if en else "stay/bosai.html")
        word = "Emergency" if en else "防災"
        items.append(f'<a class="s sos" href="{_esc(bosai)}">{_SOS_ICON}{word}</a>')
    label = "Miura A-tei sites" if en else "三浦A邸のサイト"
    home_label = "Miura A-tei: stay guide top" if en else "三浦A邸 滞在ガイドのトップ"
    return (f'<nav class="sn{" has-sos" if sos else ""}" aria-label="{label}"><div class="sn-in">'
            f'<a class="home" href="{_esc(home)}" aria-label="{home_label}"><img src="{_esc(root)}img/brand/logo.png" alt="" width="28" height="28">'
            f'<span class="t">{"Miura A-tei" if en else "三浦A邸"}</span></a>{"".join(items)}</div></nav>')


_ICONS = {
    "index": '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/>',
    "tochaku": '<path d="M5 21V4h10l4 4v13"/><path d="M9 12h6M9 16h4"/>',
    "konnatoki": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.5V14"/><path d="M12 17.5v.01"/>',
    "bosai": '<path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17v.01"/>',
}
_BN = [("index", "トップ", "Top"), ("tochaku", "到着", "Arrival"),
       ("konnatoki", "困ったとき", "Help"), ("bosai", "防災", "Emergency")]


def bottomnav(current, lang="ja"):
    """滞在ガイドの下のバー。current はページの slug（index・tochaku・konnatoki・bosai ほか）。"""
    en = lang == "en"
    out = []
    for slug, ja, en_l in _BN:
        cls = ' class="sos"' if slug == "bosai" else ""
        cur = ' aria-current="page"' if slug == current else ""
        out.append(f'<a href="{slug}.html"{cls}{cur}><svg viewBox="0 0 24 24" aria-hidden="true">{_ICONS[slug]}</svg>{en_l if en else ja}</a>')
    label = "Stay guide menu" if en else "滞在ガイドのメニュー"
    return f'<nav class="bn" aria-label="{label}">' + "".join(out) + "</nav>"
