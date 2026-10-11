#!/usr/bin/env python3
"""OpenStreetMap（Overpass API）→ structures.json（3Dマップに立てる構造物：橋・灯台・防波堤・桟橋）
形は OSM、高さは下の表。たまに作り直せば十分（毎朝は回さない）。取得は curl（この Mac の python3 は SSL 証明書が無い）。
  python3 hana_structures_fetch.py   → structures.json → python3 hana_public_build.py
高さの出典（2026-10-11 に開いて確認）:
  城ヶ島大橋   海面からの高さ 16〜23.5m   https://ja.wikipedia.org/wiki/城ヶ島大橋   → 一枚の板として最大値 23.5m に描く
  城ヶ島灯台   塔高 11.5m                https://ja.wikipedia.org/wiki/城ヶ島灯台
  安房埼灯台   高さ 16m（2020年の2代目） https://ja.wikipedia.org/wiki/城ヶ島 （カナロコ 2020-03-10 を引用）
防波堤・桟橋・突堤は高さの資料が無いので、一律の目安（NOMINAL）。名前の無い灯台（港の標識灯）は高さが分からないので載せない。"""
import json, math, pathlib, subprocess

HERE = pathlib.Path(__file__).parent
BBOX = "35.120,139.595,35.160,139.645"  # 三崎・城ヶ島
QUERY = f'[out:json][timeout:60];(way["man_made"~"^(bridge|breakwater|pier|groyne)$"]({BBOX});node["man_made"="lighthouse"]["name"]({BBOX}););out tags geom;'
DECK = 2.5  # 橋の板の厚み（目安）
NAMED = {"城ヶ島大橋": 23.5, "城ヶ島灯台": 11.5, "安房崎灯台": 16, "安房埼灯台": 16}
NOMINAL = {"breakwater": 3, "pier": 2, "groyne": 2}   # m・目安
WIDTH = {"breakwater": 5, "pier": 4, "groyne": 3}     # 線で描かれているものの幅 m・目安
COLOR = {"bridge": "#c5cbd1", "lighthouse": "#ffffff", "breakwater": "#b4b9be", "pier": "#c9c3b7", "groyne": "#b4b9be"}

def m2deg(lat):
    return 1 / 111320, 1 / (111320 * math.cos(math.radians(lat)))

def ribbon(pts, w):
    """折れ線 → 区間ごとの長方形（幅 w m）。重なってよい"""
    out = []
    for (lo1, la1), (lo2, la2) in zip(pts, pts[1:]):
        dy, dx = m2deg(la1)
        vx, vy = (lo2 - lo1) / dx, (la2 - la1) / dy
        n = math.hypot(vx, vy) or 1
        ox, oy = -vy / n * w / 2 * dx, vx / n * w / 2 * dy
        out.append([[lo1 + ox, la1 + oy], [lo2 + ox, la2 + oy], [lo2 - ox, la2 - oy], [lo1 - ox, la1 - oy], [lo1 + ox, la1 + oy]])
    return out

def disc(lon, lat, r, n=12):
    dy, dx = m2deg(lat)
    ring = [[lon + math.cos(2 * math.pi * i / n) * r * dx, lat + math.sin(2 * math.pi * i / n) * r * dy] for i in range(n)]
    return ring + [ring[0]]

def main():
    raw = subprocess.run(["curl", "-s", "-m", "90", "-A", "miura-board/1.0 (github.com/vaseata/miura-board)", "--data-urlencode", "data=" + QUERY,
                          "https://overpass-api.de/api/interpreter"], capture_output=True, text=True, check=True).stdout
    feats = []
    for e in json.loads(raw)["elements"]:
        t = e["tags"]; kind = t["man_made"]; name = t.get("name") or ""
        def add(ring, h, b=0):
            feats.append({"type": "Feature", "properties": {"kind": kind, "name": name, "h": h, "b": b, "c": COLOR[kind], "osm": f'{e["type"]}/{e["id"]}'},
                          "geometry": {"type": "Polygon", "coordinates": [[[round(x, 6), round(y, 6)] for x, y in ring]]}})
        if kind == "lighthouse":
            if name in NAMED: add(disc(e["lon"], e["lat"], 2.5), NAMED[name])
            continue
        pts = [[g["lon"], g["lat"]] for g in e["geometry"]]
        if kind == "bridge":
            if name in NAMED: add(pts, NAMED[name], NAMED[name] - DECK)
            continue
        if pts[0] == pts[-1] and len(pts) > 3: add(pts, NOMINAL[kind])
        else:
            for r in ribbon(pts, WIDTH[kind]): add(r, NOMINAL[kind])
    out = {"type": "FeatureCollection", "source": "© OpenStreetMap contributors (ODbL)・Overpass API", "features": feats}
    (HERE / "structures.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    from collections import Counter
    print("structures.json:", dict(Counter(f["properties"]["kind"] for f in feats)), [f["properties"]["name"] for f in feats if f["properties"]["name"]])

if __name__ == "__main__":
    main()
