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
/* サイトの切り替え */
.sn{position:relative;z-index:30;background:var(--bg);border-bottom:1px solid var(--hair)}
.sn-in{display:flex;align-items:center;gap:2px;max-width:1240px;margin:0 auto;padding:0 12px;overflow-x:auto;scrollbar-width:none}
.sn-in::-webkit-scrollbar{display:none}
.sn .home{display:flex;align-items:center;gap:6px;min-height:44px;margin-right:auto;padding:0 6px 0 0;color:var(--ink);font:800 14px/1 var(--mincho);text-decoration:none;white-space:nowrap;flex:none}
.sn .home img{width:28px;height:28px;display:block;background:#fff;border-radius:6px}
.sn a.s{display:flex;align-items:center;min-height:44px;padding:0 9px;color:var(--mute);font:700 13px/1 var(--gothic);letter-spacing:0;text-decoration:none;white-space:nowrap;border-bottom:3px solid transparent;flex:none}
.sn a.s[aria-current="true"]{color:var(--ink);border-bottom-color:var(--sea)}
@media (max-width:400px){.sn .home .t{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)} .sn a.s{padding:0 8px}}
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
.bn{position:fixed;left:0;right:0;bottom:0;z-index:40;display:grid;grid-template-columns:repeat(4,1fr);background:var(--bg);border-top:1px solid var(--hair);padding-bottom:env(safe-area-inset-bottom)}
.bn a{position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;min-height:56px;color:var(--mute);font:700 11px/1.2 var(--gothic);text-decoration:none}
.bn svg{width:24px;height:24px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.bn a[aria-current="page"]{color:var(--sea)}
.bn a[aria-current="page"]::before{content:"";position:absolute;top:-1px;left:22%;right:22%;height:3px;border-radius:0 0 3px 3px;background:var(--sea)}
.bn a.sos{color:var(--tuna)}
.bn a.sos[aria-current="page"]::before{background:var(--tuna)}
@media (min-width:720px){.bn{left:50%;right:auto;width:560px;transform:translateX(-50%);border:1px solid var(--hair);border-bottom:0;border-radius:12px 12px 0 0}}
@media (prefers-reduced-motion:reduce){.btn,.fchip,.seg button{transition:none}.btn:active{transform:none}}
"""

SITES = [
    ("stay", "stay/", "滞在ガイド", "Stay guide"),
    ("guide", "guide/", "ガイドブック", "Guidebook"),
    ("board", "", "最近の三浦", "Miura news"),
]


def sitenav(current, root, lang="ja"):
    """3サイト共通の切り替えの帯。root はページからリポジトリの一番上への道（"../" など）。"""
    en = lang == "en"
    home = root + ("stay/en/" if en else "stay/")
    cur = ' aria-current="true"'
    items = "".join(
        f'<a class="s" href="{_esc(root + path)}"{cur if key == current else ""}>{_esc(en_l if en else ja)}</a>'
        for key, path, ja, en_l in SITES)
    label = "Miura A-tei sites" if en else "三浦A邸のサイト"
    return (f'<nav class="sn" aria-label="{label}"><div class="sn-in">'
            f'<a class="home" href="{_esc(home)}"><img src="{_esc(root)}img/brand/logo.png" alt="" width="28" height="28">'
            f'<span class="t">{"Miura A-tei" if en else "三浦A邸"}</span></a>{items}</div></nav>')


_ICONS = {
    "index": '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/>',
    "tochaku": '<path d="M5 21V4h10l4 4v13"/><path d="M9 12h6M9 16h4"/>',
    "konnatoki": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.5V14"/><path d="M12 17.5v.01"/>',
    "bosai": '<path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17v.01"/>',
}
_BN = [("index", "トップ", "Top"), ("tochaku", "到着", "Arrival"),
       ("konnatoki", "困ったとき", "Trouble"), ("bosai", "防災", "Emergency")]


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
