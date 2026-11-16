#!/usr/bin/env python3
"""城ヶ島の潮（満潮・干潮・潮の名前）を tide736.net から取り、tide.json に置く（2026-11-16 ヤヌキ依頼）。

使い方:  python3 tide.py   … 今月と来月の分を取り直す（中身が変わったときだけ tide.json を書き換える）
- 毎朝の近況ボードタスクが回す。ページ（家の案内・お店・名所）は tide.json を読んで、閲覧者の端末の「今日」を出す
  （訪れた人のスマホから tide736 を直接呼ばない＝相手のサーバーに負担をかけない。1日に2回だけ）
- 港は tide736 の 神奈川県（pc=14）の「城ヶ島」（hc=13）
- 利用条件（2026-11-16 に tide736.net のトップを開いて確認）：「データに関して ご自由にご利用ください（グラフやリンクもご自由に）」。
  免責あり。航海用の公式の推算は海上保安庁の「潮汐表」。一日のアクセス数を制限する場合がある
- ⚠️ この Mac の python3 は SSL 証明書が無いので、取得は curl
"""
import datetime as dt, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "tide.json"
PC, HC = 14, 13
JST = dt.timezone(dt.timedelta(hours=9))
SOURCE = "https://tide736.net/"

def fetch_month(y, m):
    url = f"https://tide736.net/api/get_tide.php?pc={PC}&hc={HC}&yr={y}&mn={m}&dy=1&rg=month"
    r = subprocess.run(["curl", "-s", "-m", "30", "-A", "miura-board (tide display)", url], capture_output=True, text=True)
    d = json.loads(r.stdout)
    if d.get("status") != 1:
        raise RuntimeError(d.get("message"))
    days = {}
    for k, c in d["tide"]["chart"].items():
        days[k] = {"n": c["moon"].get("title", ""),
                   "hi": [[x["time"], round(x["cm"])] for x in c.get("flood", [])],
                   "lo": [[x["time"], round(x["cm"])] for x in c.get("edd", [])]}
    return d["tide"]["port"].get("harbor_namej", ""), days

def update():
    today = dt.datetime.now(JST).date()
    nxt = (today.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
    port, days = fetch_month(today.year, today.month)
    _p, d2 = fetch_month(nxt.year, nxt.month)
    days.update(d2)
    old = json.loads(OUT.read_text()) if OUT.exists() else {}
    if old.get("days") == days:
        print("tide.json：変わっていないので、そのまま")
        return False
    OUT.write_text(json.dumps({"port": port, "source": SOURCE, "fetched": today.isoformat(), "days": days},
                              ensure_ascii=False, separators=(",", ":")))
    print(f"tide.json を書きました（{port}・{min(days)}〜{max(days)}）")
    return True

NAME_EN = {"大潮": "Spring tide", "中潮": "Mid tide", "小潮": "Neap tide", "長潮": "Long tide", "若潮": "Young tide"}

def tide_html(root, lang="ja"):
    """今日の城ヶ島の潮のカード。tide.json を読んで、閲覧者の端末の日付の分を出す（無ければ何も出さない）。"""
    en = lang == "en"
    L = ({"h": "Tide at Jogashima today", "hi": "High", "lo": "Low",
          "note": "A guide only. Rock pools are easiest around low tide. Stay away from the shore on days with high waves or storm surge.",
          "src": "Tide: tide736.net (calculated, not for navigation)"} if en else
         {"h": "今日の城ヶ島の潮", "hi": "満潮", "lo": "干潮",
          "note": "目安です。磯遊びは干潮の前後が歩きやすいです。高波・高潮の日は、海に近づかないでください。",
          "src": "潮汐：tide736.net（推算値。航海用ではありません）"})
    names = json.dumps(NAME_EN if en else {}, ensure_ascii=False)
    return f'''<div class="tide" id="tide" hidden><div class="tide-h">{L["h"]}<span class="tide-n" id="tide-n"></span></div>
<div class="tide-r"><span><b>{L["hi"]}</b> <span id="tide-hi"></span></span><span><b>{L["lo"]}</b> <span id="tide-lo"></span></span></div>
<p class="tide-note">{L["note"]}</p><p class="tide-src"><a href="{SOURCE}" target="_blank" rel="noopener">{L["src"]}</a></p></div>
<script>(function(){{var N={names};var d=new Date(),k=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
fetch('{root}tide.json',{{cache:'no-cache'}}).then(function(r){{return r.json()}}).then(function(j){{var t=j.days&&j.days[k];if(!t)return;
var f=function(a){{return a.map(function(x){{return x[0].replace(/^0/,'')}}).join(' / ')||'—'}};
document.getElementById('tide-n').textContent=N[t.n]||t.n;document.getElementById('tide-hi').textContent=f(t.hi);document.getElementById('tide-lo').textContent=f(t.lo);
document.getElementById('tide').hidden=false;}}).catch(function(){{}});}})();</script>'''

TIDE_CSS = """.tide{margin:14px 0;padding:12px 16px;border:1.5px solid var(--sea);border-radius:12px;background:var(--sea-tint,#E6F0F6)}
.tide-h{font-weight:700;font-size:15px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.tide-n{font-size:12px;font-weight:700;color:var(--sea);border:1px solid var(--sea);border-radius:999px;padding:0 8px;background:var(--bg,#fff)}
.tide-r{display:flex;flex-wrap:wrap;gap:4px 18px;margin:6px 0 2px;font-size:16px;font-variant-numeric:tabular-nums}
.tide-r b{color:var(--sea);font-size:13px;margin-right:2px}
.tide-note{font-size:12.5px;color:var(--mute,#4F6070);margin:4px 0 0}.tide-src{font-size:11px;margin:2px 0 0}.tide-src a{color:var(--mute,#4F6070)}"""

if __name__ == "__main__":
    try:
        update()
    except Exception as e:
        sys.exit(f"潮の情報を取れませんでした：{e}")
