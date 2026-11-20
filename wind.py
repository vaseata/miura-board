"""城ヶ島大橋の風の目安（2026-11-20）。

橋の風速計の値は公開されていない（神奈川県・道路情報とも。2026-11-20 調べ）。
そこで、気象庁アメダス「三浦」（46211・橋の約5km北・陸の上・高さ42m）の今の風を、
見た人の端末がその場で気象庁から読む（気象庁の JSON は Access-Control-Allow-Origin: * ）。
海の上の風として、海上保安庁の剱埼灯台（横須賀海上保安部の気象現況）へリンクする。
海保のページは他サイトからの読み込みを許していないので、値は載せずリンクだけ。

利用条件：気象庁＝公共データ利用規約（出典の記載）／海上保安庁＝政府標準利用規約2.0準拠（出典の記載）。
目安の言葉は「渡れる・渡れない」と書かない（規制の基準ではないため）。
"""

AMEDAS = "46211"
JMA_PAGE = "https://www.jma.go.jp/bosai/amedas/#amdno=46211&format=table10min"
MICS = "https://www6.kaiho.mlit.go.jp/03kanku/yokosuka/kisyou.html"


def wind_html(root="", lang="ja", sfx=""):
    en = lang == "en"
    L = ({"h": "Wind on Jogashima Bridge (guide)", "now": "Now", "gust": "Today's max gust",
          "at": "observed", "calm": "calm",
          "lv": ["Light wind.", "Breezy. It is usually stronger on the bridge.",
                 "Strong wind. On the bridge it can be hard to walk. Hold the railing, or take the bus.",
                 "Very strong wind. Avoid walking across the bridge."],
          "note": "The bridge is 21 m above the sea with nothing to block the wind, so it is often much windier than this land station. "
                  "The lighthouse at Tsurugizaki, by the sea, can show about twice the wind.",
          "sea": "Wind at sea now: Tsurugizaki Lighthouse (Japan Coast Guard, in Japanese)",
          "src": "Wind: JMA AMeDAS Miura (about 5 km north of the bridge)",
          "dirs": ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"],
          "from": " wind"} if en else
         {"h": "城ヶ島大橋の風の目安", "now": "いま", "gust": "今日の最大瞬間",
          "at": "観測", "calm": "静穏",
          "lv": ["おだやかな風です。", "やや強い風です。橋の上は、これより強いことが多いです。",
                 "強い風です。橋の上は歩きにくいことがあります。手すりを持つか、バスを使ってください。",
                 "とても強い風です。橋を歩いて渡るのは控えてください。"],
          "note": "橋は海面から21mの高さで、風をさえぎる物がありません。陸の上のこの観測より、強いことが多いです。"
                  "海に突き出た剱埼灯台では、2倍ほどの風になる日もあります。",
          "sea": "海の上の今の風：剱埼灯台（海上保安庁）",
          "src": "風：気象庁アメダス「三浦」（橋の約5km北）",
          "dirs": ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"],
          "from": "の風"})
    import json
    J = json.dumps({"lv": L["lv"], "dirs": L["dirs"], "from": L["from"], "calm": L["calm"], "at": L["at"]}, ensure_ascii=False)
    return f'''<div class="wind" id="wind{sfx}" hidden><div class="wind-h">{L["h"]}</div>
<div class="wind-r"><span><b>{L["now"]}</b> <span class="wind-v" id="wind-now{sfx}"></span></span><span><b>{L["gust"]}</b> <span id="wind-gust{sfx}"></span></span></div>
<p class="wind-lv" id="wind-lv{sfx}"></p>
<p class="wind-note">{L["note"]}</p>
<p class="wind-sea"><a href="{MICS}" target="_blank" rel="noopener">{L["sea"]} ›</a></p>
<p class="wind-src"><a href="{JMA_PAGE}" target="_blank" rel="noopener">{L["src"]}</a> <span id="wind-t{sfx}"></span></p></div>
<script>(function(){{var L={J};var B='https://www.jma.go.jp/bosai/amedas/data/';
var $=function(i){{return document.getElementById(i+'{sfx}')}};
fetch(B+'latest_time.txt').then(function(r){{return r.text()}}).then(function(t){{
var m=t.trim().match(/^(\\d+)-(\\d+)-(\\d+)T(\\d+):(\\d+)/);if(!m)return;
var h=('0'+(Math.floor(+m[4]/3)*3)).slice(-2);
return fetch(B+'point/{AMEDAS}/'+m[1]+m[2]+m[3]+'_'+h+'.json').then(function(r){{return r.json()}}).then(function(d){{
var ks=Object.keys(d).sort(),k=null;for(var i=ks.length-1;i>=0;i--){{if(d[ks[i]].wind&&d[ks[i]].wind[1]===0){{k=ks[i];break}}}}if(!k)return;
var o=d[k],w=o.wind[0],dir=o.windDirection&&o.windDirection[1]===0?o.windDirection[0]:null;
$('wind-now').textContent=(w===0||dir===0?L.calm:(dir?L.dirs[dir%16]+L.from+' ':'')+w.toFixed(1)+' m/s');
if(o.gust&&o.gust[1]===0){{var g=o.gustTime||{{}};$('wind-gust').textContent=o.gust[0].toFixed(1)+' m/s'+(g.hour!=null?' ('+g.hour+':'+('0'+g.minute).slice(-2)+')':'');}}else{{$('wind-gust').textContent='—';}}
var lv=w<5?0:w<8?1:w<12?2:3;var el=$('wind-lv');el.textContent=L.lv[lv];
var box=$('wind');if(lv>=2)box.className='wind wind-warn';
$('wind-t').textContent='('+k.slice(8,10).replace(/^0/,'')+':'+k.slice(10,12)+' '+L.at+')';
box.hidden=false;}});}}).catch(function(){{}});}})();</script>'''


WIND_CSS = """.wind{margin:14px 0;padding:12px 16px;border:1.5px solid var(--sea);border-radius:12px;background:var(--sea-tint,#E6F0F6)}
.wind.wind-warn{border-color:var(--tuna,#B8243A)}.wind.wind-warn .wind-lv{color:var(--tuna,#B8243A)}
.wind-h{font-weight:700;font-size:15px}
.wind-r{display:flex;flex-wrap:wrap;gap:4px 18px;margin:6px 0 2px;font-size:16px;font-variant-numeric:tabular-nums}
.wind-r b{color:var(--sea);font-size:13px;margin-right:2px}.wind-v{font-weight:700}
.wind-lv{font-size:14px;font-weight:700;margin:4px 0 0}
.wind-note{font-size:12.5px;color:var(--mute,#4F6070);margin:4px 0 0}
.wind-sea{font-size:13.5px;margin:6px 0 0}.wind-sea a{color:var(--sea);font-weight:700}
.wind-src{font-size:11px;margin:2px 0 0;color:var(--mute,#4F6070)}.wind-src a{color:var(--mute,#4F6070)}"""
