"""お店の「いま営業中か」（2026-11-14 ヤヌキ依頼「その曜日・時間に空いているかを可能な限り表示」）。

spots.json の hours（自由な書き方）と closed（定休の曜日 0=月…6=日）から、曜日ごとの営業時間を読み取る。
確実に読める書き方だけを読み、読めないもの（季節で変わる・「前後」「要確認」など）は None にして、
ページでは定休日だけを使った控えめな表示にする（作った時間を出さない）。

  parse(hours, closed) -> {"d": [[開始分, 終了分], ...] × 7（月〜日）} か None
  OPEN_JS … ページに入れる JavaScript。window.shopStatus(sched, closed, known) が {s: "open|soon|closed|off|unknown", t: "表示の文"} を返す
"""
import re

_DAYS = "月火水木金土日"
_TIME = r"(\d{1,2}):(\d{2})"
_RANGE = re.compile(_TIME + r"\s*[〜~ー－-]\s*" + _TIME)
_UNSURE = ("要確認", "前後", "変動", "季節", "月は", "月 ", "〜9月", "〜3月", "夏季", "冬季", "予約制", "切れ", "記載", "便", "／LO", "（観光協会）")


def _days(expr):
    """「平日」「土日祝」「月・水〜金」「日曜」などを曜日の集合に。読めなければ None。"""
    e = expr.replace("曜日", "").replace("曜", "").replace("祝", "").strip()
    if not e:
        return None
    if e == "平日":
        return {0, 1, 2, 3, 4}
    if e in ("土日", "土・日", "週末"):
        return {5, 6}
    out = set()
    for part in re.split(r"[・,、]", e):
        m = re.fullmatch(r"([月火水木金土日])(?:[〜~ー－-]([月火水木金土日]))?", part)
        if not m:
            return None
        a = _DAYS.index(m.group(1))
        b = _DAYS.index(m.group(2)) if m.group(2) else a
        out |= set(range(a, b + 1)) if a <= b else set(range(a, 7)) | set(range(0, b + 1))
    return out


def parse(hours, closed):
    if not hours or not isinstance(closed, list):
        return None   # 定休日が分からないお店は、時間も決めない
    h = hours.strip()
    if any(w in h for w in _UNSURE):
        return None
    if h in ("24時間", "終日"):
        week = [[[0, 1440]] for _ in range(7)]
    else:
        h = re.sub(r"[（(]L\.?O\.?[^）)]*[）)]", "", h)   # ラストオーダーの注記は外す
        if "（" in h or "(" in h:
            return None
        week = [None] * 7
        for seg in re.split(r"[／/]", h):
            seg = seg.strip()
            m = re.match(r"^([^\d]*?)\s*(\d.*)$", seg)
            if not m:
                return None
            prefix, rest = m.group(1).strip(), m.group(2)
            days = _days(prefix) if prefix else set(range(7))
            if days is None:
                return None
            ranges = []
            for part in re.split(r"[、,・]\s*", rest):
                part = re.sub(r"^(昼|夜)\s*", "", part.strip())
                r = _RANGE.fullmatch(part)
                if not r:
                    return None
                a = int(r.group(1)) * 60 + int(r.group(2))
                b = int(r.group(3)) * 60 + int(r.group(4))
                if b <= a:
                    return None
                ranges.append([a, b])
            for d in days:
                if prefix == "":
                    week[d] = (week[d] or []) + ranges   # 曜日なしの区切りは、同じ日の時間を足す
                else:
                    week[d] = ranges
        if any(w is None for w in week):
            # 書いていない曜日がある（「平日…／土日祝…」で全部うまる前提）。定休の曜日だけなら許す
            for d in range(7):
                if week[d] is None and d not in closed:
                    return None
                week[d] = week[d] or []
    for d in closed:
        week[d] = []
    return {"d": week}


OPEN_JS = r"""<script>
window.shopStatus=function(sc,closed,known){
  var now=new Date(new Date().toLocaleString('en-US',{timeZone:'Asia/Tokyo'}));
  var wd=(now.getDay()+6)%7, m=now.getHours()*60+now.getMinutes();
  function hm(x){return Math.floor(x/60)+':'+('0'+x%60).slice(-2);}
  if(closed&&closed.indexOf(wd)>=0)return {s:'off',t:'今日は定休日'};
  if(!sc){return known?{s:'unknown',t:'今日は営業日（時間は詳細で）'}:{s:'unknown',t:'定休日は要確認'};}
  var r=sc.d[wd]||[];
  if(!r.length)return {s:'off',t:'今日はお休み'};
  if(r[0][0]===0&&r[0][1]===1440)return {s:'open',t:'24時間'};
  for(var i=0;i<r.length;i++){
    if(m>=r[i][0]&&m<r[i][1]){var left=r[i][1]-m;return {s:'open',t:(left<=60?'まもなく閉店 ':'営業中・')+hm(r[i][1])+'まで'};}
    if(m<r[i][0])return {s:'soon',t:(i>0?'休憩中・':'')+hm(r[i][0])+'から'};
  }
  return {s:'closed',t:'今日は終了（'+hm(r[r.length-1][1])+'まで）'};
};
</script>"""

STATUS_CSS = """
.ost{display:inline-flex;align-items:center;gap:4px;font-size:12px;font-weight:700;line-height:1.4}
.ost::before{content:"";width:8px;height:8px;border-radius:50%;background:currentColor;flex:none}
.ost[data-s="open"]{color:var(--sea)}
.ost[data-s="soon"],.ost[data-s="closed"],.ost[data-s="unknown"]{color:var(--mute);font-weight:400}
.ost[data-s="off"]{color:var(--mute);font-weight:400}
.ost[data-s="off"]::before,.ost[data-s="closed"]::before,.ost[data-s="unknown"]::before{background:none;border:1.5px solid currentColor;width:6px;height:6px}
"""


if __name__ == "__main__":
    import json, sys
    doc = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "spots.json"))
    ok = ng = 0
    for s in doc["spots"]:
        if not s.get("hours"):
            continue
        r = parse(s["hours"], s.get("closed"))
        if r: ok += 1
        else: ng += 1
        print("○" if r else "×", s["hours"], s.get("closed"), (r["d"] if r else ""))
    print(f"読めた {ok} 件／読めない {ng} 件")
