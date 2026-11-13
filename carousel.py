"""滞在ガイドのトップの、横幅いっぱいのカルーセル（季節の写真・イベントの画像）。

台帳は stay_carousel.json の "slides"（上から順に並ぶ）。1枚の書き方は2通り：
  {"item": 49}                       … items.json の番号。見出し・日付・写真・リンクを自動で取り、終わった日の翌日に自動で外れる
  {"src": "写真の場所", "kind": "季節", "title": "見出し", "sub": "1行", "href": "リンク先", "until": "2026-12-31", "credit": "写真：…"}
    src はリポジトリからの道（img/raw/xxx.jpg、stay-react/public/photos/hero.jpg など）。until を過ぎると出ない
  どちらにも "title_en" "sub_en" "kind_en" を足すと英語版で使う（無ければ日本語のまま）
写真は build のたびに 1200×750 に切り出して stay/img/c-<名前>.jpg に書く（位置情報などは残らない）。
"""

import datetime, html, json, pathlib

HERE = pathlib.Path(__file__).parent
W, H = 1200, 750
esc = lambda s: html.escape(str(s or ""), quote=True)

CSS = """
/* ── カルーセル（carousel.py） ── */
.car{margin:18px -16px 0}
.car-track{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:none;-webkit-overflow-scrolling:touch;overscroll-behavior-x:contain}
.car-track::-webkit-scrollbar{display:none}
.car-s{flex:0 0 100%;margin:0;scroll-snap-align:start;scroll-snap-stop:always}
.car-s a{display:block;color:inherit;text-decoration:none}
.car-s img{display:block;width:100%;height:auto;aspect-ratio:16/10;object-fit:cover;background:var(--tint)}
.car-s figcaption{padding:10px 16px 0;line-height:1.5}
.car-k{display:inline-block;margin-right:8px;padding:0 7px;border:1px solid var(--sea);border-radius:4px;color:var(--sea);font-size:11px;font-weight:700;letter-spacing:.08em;vertical-align:2px}
.car-s b{font-size:16px}
.car-s .car-sub{display:block;font-size:13px;color:var(--mute)}
.car-s .car-cr{display:block;font-size:10.5px;color:var(--mute)}
.car-ctl{display:flex;align-items:center;justify-content:center;gap:4px;padding:2px 16px 0}
.car-ctl button{position:relative;display:inline-flex;align-items:center;justify-content:center;min-width:44px;min-height:44px;border:0;background:none;color:var(--sea);cursor:pointer;font:inherit}
.car-ctl .car-pn svg{width:22px;height:22px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.car-ctl .car-pn:disabled{color:var(--hair);cursor:default}
.car-dots{display:flex}
.car-dots button{min-width:28px}
.car-dots button::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--hair);transition:background-color 180ms,width 180ms}
.car-dots button[aria-current="true"]::before{width:20px;border-radius:4px;background:var(--sea)}
.car-dots button::after{content:"";position:absolute;inset:0 -2px}
@media (min-width:720px){.car{margin:18px 0 0}.car-s img{border-radius:14px}.car-s figcaption{padding:10px 2px 0}}
@media (prefers-reduced-motion:reduce){.car-track{scroll-behavior:auto}.car-dots button::before{transition:none}}
"""

JS = """<script>
(function(){document.querySelectorAll('.car').forEach(function(c){
  var t=c.querySelector('.car-track'),s=[].slice.call(t.children),d=[].slice.call(c.querySelectorAll('.car-dots button')),
      p=c.querySelector('.car-prev'),n=c.querySelector('.car-next'),i=0,
      sm=matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth';
  function go(k){k=Math.max(0,Math.min(s.length-1,k));t.scrollTo({left:s[k].offsetLeft-t.offsetLeft,behavior:sm});}
  function mark(){i=Math.round(t.scrollLeft/t.clientWidth);d.forEach(function(b,k){b.setAttribute('aria-current',String(k===i));});
    if(p)p.disabled=i===0; if(n)n.disabled=i===s.length-1;}
  d.forEach(function(b,k){b.addEventListener('click',function(){go(k);});});
  if(p)p.addEventListener('click',function(){go(i-1);}); if(n)n.addEventListener('click',function(){go(i+1);});
  t.addEventListener('keydown',function(e){if(e.key==='ArrowRight'){go(i+1);e.preventDefault();}if(e.key==='ArrowLeft'){go(i-1);e.preventDefault();}});
  var r;t.addEventListener('scroll',function(){cancelAnimationFrame(r);r=requestAnimationFrame(mark);},{passive:true});mark();
});})();
</script>"""


def _items():
    data = json.loads((HERE / "items.json").read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("items", [])
    return {str(x.get("id")): x for x in items}


def _image_src(key):
    """places.json の image キーから、なるべく大きい元の写真を探す。"""
    for p in (HERE / "img" / "raw" / f"{key}.jpg", HERE / "img" / "raw" / f"{key}.png", HERE / "img" / f"{key}.jpg"):
        if p.exists():
            return p
    return None


def _credit(key):
    try:
        im = json.loads((HERE / "places.json").read_text(encoding="utf-8"))["images"].get(key) or {}
    except Exception:
        return ""
    lic = im.get("license") or ""
    if lic.startswith("CC"):
        return f"写真：Wikimedia Commons（{lic}）"
    return "写真：" + html.unescape(im.get("credit") or "").split("（")[0] if im.get("credit") else ""


def _jdate(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.month}/{d.day}"


def _crop(src, out):
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    im = ImageOps.fit(im, (W, H), method=Image.LANCZOS, centering=(0.5, 0.45))
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "JPEG", quality=80, optimize=True, progressive=True)


def slides(today=None):
    """台帳を読み、出す分だけを {img_src(パス), kind, title, sub, href, credit, name} で返す。"""
    today = today or datetime.date.today()
    conf = json.loads((HERE / "stay_carousel.json").read_text(encoding="utf-8"))
    items, out = None, []
    for s in conf.get("slides", []):
        s = dict(s)
        if "item" in s:
            items = items or _items()
            x = items.get(str(s["item"]))
            if not x:
                continue
            end = x.get("end") or x.get("date")
            s.setdefault("until", end)
            s.setdefault("kind", x.get("category") or "お知らせ")
            s.setdefault("title", x.get("headline") or x.get("fact", "")[:25])
            when = _jdate(x["date"]) + (f"〜{_jdate(x['end'])}" if x.get("end") else "")
            head_has_date = any(c.isdigit() for c in s["title"][:6])
            s.setdefault("sub", (x.get("area") or "") if head_has_date else f"{when}　{x.get('area') or ''}".strip())
            s.setdefault("href", "../index.html")
            s.setdefault("credit", _credit(x.get("image")))
            src = _image_src(x.get("image")) if x.get("image") else None
            s["name"] = f"i{s['item']}"
        else:
            src = HERE / s["src"] if s.get("src") else None
            s["name"] = s.get("name") or pathlib.Path(s.get("src", "x")).stem
        if s.get("until") and datetime.date.fromisoformat(s["until"]) < today:
            continue
        if not src or not src.exists():
            continue
        s["img_src"] = src
        out.append(s)
    return out


def render(out_dir, img_prefix="img/", lang="ja", today=None):
    """カルーセルの HTML を返す。写真は out_dir/img/c-<name>.jpg に書く。1枚も無ければ空文字。"""
    en = lang == "en"
    ss = slides(today)
    if not ss:
        return ""
    figs, dots = [], []
    for k, s in enumerate(ss):
        fn = f"c-{s['name']}.jpg"
        dst = pathlib.Path(out_dir) / "img" / fn
        if not dst.exists() or dst.stat().st_mtime < s["img_src"].stat().st_mtime:
            _crop(s["img_src"], dst)
        g = (lambda key: s.get(key + "_en") or s.get(key)) if en else s.get
        alt = g("alt") or g("title") or ""
        kind = f'<span class="car-k">{esc(g("kind"))}</span>' if g("kind") else ""
        lazy = "" if k == 0 else ' loading="lazy"'
        img = f'<img src="{esc(img_prefix + fn)}" alt="{esc(alt)}" width="{W}" height="{H}"{lazy}>'
        cap = (f'<figcaption>{kind}<b>{esc(g("title"))}</b>'
               + (f'<span class="car-sub">{esc(g("sub"))}</span>' if g("sub") else "")
               + (f'<span class="car-cr">{esc(s["credit"])}</span>' if s.get("credit") else "")
               + "</figcaption>")
        inner = f'<a href="{esc(s["href"])}">{img}{cap}</a>' if s.get("href") else img + cap
        label = f"{k + 1} / {len(ss)}"
        figs.append(f'<figure class="car-s" role="group" aria-roledescription="{"slide" if en else "スライド"}" aria-label="{label}">{inner}</figure>')
        dots.append(f'<button type="button" aria-label="{label}" aria-current="{"true" if k == 0 else "false"}"></button>')
    chev = lambda d: f'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="{d}"/></svg>'
    ctl = ""
    if len(ss) > 1:
        ctl = (f'<div class="car-ctl"><button type="button" class="car-pn car-prev" aria-label="{"Previous" if en else "前へ"}">{chev("M15 5l-7 7 7 7")}</button>'
               f'<div class="car-dots">{"".join(dots)}</div>'
               f'<button type="button" class="car-pn car-next" aria-label="{"Next" if en else "次へ"}">{chev("M9 5l7 7-7 7")}</button></div>')
    label = "Season and events" if en else "季節とイベント"
    return (f'<section class="car" aria-roledescription="carousel" aria-label="{label}">'
            f'<div class="car-track" tabindex="0">{"".join(figs)}</div>{ctl}</section>{JS}')
