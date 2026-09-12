#!/usr/bin/env python3
"""YouTube を三浦の地名で検索 → 地域に関係する動画だけ videos.json に貯め、サムネイルを img/yt/ に落とす。
使い方: python3 yt_fetch.py            （検索して追記）
        python3 yt_fetch.py <videoId>  （指定IDを1本追加。ヤヌキから渡されたURL用）
取得は curl（この Mac の python3 は SSL 証明書が無い）。"""
import subprocess, json, re, sys, datetime, pathlib, urllib.parse, os

HERE = pathlib.Path(__file__).parent
VJ = HERE / "videos.json"
THUMB_DIR = HERE / "img" / "yt"; THUMB_DIR.mkdir(parents=True, exist_ok=True)
NOW = datetime.datetime.now()
KEEP_DAYS = 60

QUERIES = ["城ヶ島", "三崎港", "三崎 マグロ", "三浦海岸", "油壺", "小網代", "三浦半島 三崎", "三浦市"]
PLACE = ["城ヶ島", "三崎", "三浦海岸", "三浦半島", "三浦市", "油壺", "小網代", "剱崎", "剣崎", "毘沙門", "津久井浜", "松輪", "諸磯", "宮川", "二町谷", "うらり", "みうら"]
NG = ["三浦瑠麗", "三浦春馬", "三浦大知", "三浦翔平", "三浦知良", "三浦友和", "三浦建太郎", "三浦龍", "三浦カズ", "三崎優太", "三浦綾子", "短劇", "短剧", "ShortTV", "有聲書", "愛媛", "ELDEN", "焼鳥", "焼き鳥", "油壺を作る", "油壺の取り方", "#sho"]

def curl(url):
    return subprocess.run(["curl", "-sL", "-m", "40", "-A", "Mozilla/5.0 (Macintosh)", "-H", "Accept-Language: ja",
                           "-b", "CONSENT=YES+1", url], capture_output=True, text=True).stdout

def rel_to_date(txt):
    m = re.search(r"(\d+)\s*(分|時間|日|週間|か月|ヶ月|年)", txt or "")
    if not m: return NOW.date().isoformat()
    n, u = int(m.group(1)), m.group(2)
    days = {"分": 0, "時間": 0, "日": n, "週間": n*7, "か月": n*30, "ヶ月": n*30, "年": n*365}[u]
    return (NOW - datetime.timedelta(days=days)).date().isoformat()

def walk(o, out):
    if isinstance(o, dict):
        if "videoRenderer" in o:
            v = o["videoRenderer"]
            out.append(dict(
                id=v["videoId"],
                title="".join(r["text"] for r in v.get("title", {}).get("runs", [])),
                channel="".join(r["text"] for r in v.get("ownerText", {}).get("runs", [])),
                published_text=v.get("publishedTimeText", {}).get("simpleText", ""),
                views=v.get("viewCountText", {}).get("simpleText", ""),
                length=v.get("lengthText", {}).get("simpleText", ""),
            ))
        for x in o.values(): walk(x, out)
    elif isinstance(o, list):
        for x in o: walk(x, out)

def search(q):
    url = "https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": q, "sp": "CAI%3D"})  # 並び: アップロード日
    html = curl(url)
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", html, re.S)
    out = []
    if m: walk(json.loads(m.group(1)), out)
    return out

def oembed(vid):
    j = curl(f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json")
    try: d = json.loads(j)
    except Exception: return None
    return dict(id=vid, title=d["title"], channel=d["author_name"], published_text="", views="", length="")

def relevant(v):
    t = v["title"] + " " + v["channel"]
    if any(n in t for n in NG): return False
    if not any(p in t for p in PLACE): return False
    # 長時間ライブ配信のアーカイブは除外（ライブカメラは channel 単位で1本だけ残す）
    h = re.match(r"(\d+):(\d+):(\d+)", v.get("length", ""))
    if h and int(h.group(1)) >= 3 and "ライブカメラ" not in v["title"]: return False
    return True

def thumb(vid):
    dst = THUMB_DIR / f"{vid}.jpg"
    if dst.exists(): return
    subprocess.run(["curl", "-sL", "-m", "30", "-o", str(dst), f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg"])  # 320x180
    if dst.stat().st_size < 1000: dst.unlink(missing_ok=True)

data = json.load(open(VJ)) if VJ.exists() else {"_note": "YouTube 検索の結果。yt_fetch.py が管理。手で足すなら python3 yt_fetch.py <videoId>", "videos": []}
have = {v["id"]: v for v in data["videos"]}
added = []

if len(sys.argv) > 1:
    for vid in sys.argv[1:]:
        v = oembed(vid)
        if v and vid not in have:
            v["published"] = NOW.date().isoformat(); v["fetched"] = NOW.date().isoformat(); v["manual"] = True
            have[vid] = v; added.append(v)
else:
    livecam_channels = set()
    for q in QUERIES:
        for v in search(q):
            if v["id"] in have or not relevant(v): continue
            if "ライブカメラ" in v["title"] or "LIVE" in v["title"].upper() and "ライブ" in v["title"]:
                if v["channel"] in livecam_channels: continue
                livecam_channels.add(v["channel"]); v["live"] = True
            v["published"] = rel_to_date(v["published_text"]); v["fetched"] = NOW.date().isoformat(); v["q"] = q
            have[v["id"]] = v; added.append(v)

# 古いものを落とす（manual は残す）。同じチャンネルの同じ日は1本、ライブカメラは全体で1本、合計20本まで
cand = [v for v in have.values() if v.get("manual") or (NOW.date() - datetime.date.fromisoformat(v["published"])).days <= KEEP_DAYS]
cand = [v for v in cand if not any(n in v["title"] + v["channel"] for n in NG)]
cand.sort(key=lambda v: (v["published"], v.get("manual", False)), reverse=True)
keep, seen_cd, live_done = [], set(), False
for v in cand:
    is_live = v.get("live") or "ライブカメラ" in v["title"]
    if is_live:
        if live_done: continue
        live_done = True; v["live"] = True
    k = (v["channel"], v["published"])
    if k in seen_cd and not v.get("manual"): continue
    seen_cd.add(k); keep.append(v)
keep = keep[:20]
for v in keep: thumb(v["id"])
keep.sort(key=lambda v: v["published"], reverse=True)
data["videos"] = keep
json.dump(data, open(VJ, "w"), ensure_ascii=False, indent=1)
print(f"videos: {len(keep)} (added {len(added)})")
for v in added: print(f'  + {v["published"]} {v["channel"][:18]:<18} {v["title"][:50]}')
