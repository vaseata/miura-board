"""合言葉を「ひらがなでも、ローマ字でも」同じものとして扱うための、そろえ方（2026-11-14 討議・海外の会員さんの指摘）。

- かな（ひらがな・カタカナ）はローマ字（訓令式に近い形）に直し、ローマ字の書き方の揺れ（shi/si・tsu/tu・fu/hu・ji/zi・
  sha/sya・ch/ty・nn/n・ou/oo/ō→o など）も同じ形にそろえる
- 同じ規則を JS（JS_NORM）にも持つ。どちらかを直したら、もう一方も必ず直し、`python3 kana_romaji.py` で照合する
"""
import re, unicodedata

_BASE = {
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "さ": "sa", "し": "si", "す": "su", "せ": "se", "そ": "so",
    "た": "ta", "ち": "ti", "つ": "tu", "て": "te", "と": "to",
    "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "hi", "ふ": "hu", "へ": "he", "ほ": "ho",
    "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "や": "ya", "ゆ": "yu", "よ": "yo",
    "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro",
    "わ": "wa", "を": "o", "ん": "n",
    "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go",
    "ざ": "za", "じ": "zi", "ず": "zu", "ぜ": "ze", "ぞ": "zo",
    "だ": "da", "ぢ": "zi", "づ": "zu", "で": "de", "ど": "do",
    "ば": "ba", "び": "bi", "ぶ": "bu", "べ": "be", "ぼ": "bo",
    "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po",
    "ゔ": "vu",
}
_SMALL_Y = {"ゃ": "a", "ゅ": "u", "ょ": "o"}
_SMALL_V = {"ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o"}

def _kana_to_romaji(s):
    out = []
    sokuon = False
    for ch in s:
        if ch in _BASE:
            r = _BASE[ch]
            if sokuon and r[0] not in "aiueon":
                r = r[0] + r
            sokuon = False
            out.append(r)
        elif ch in _SMALL_Y and out and out[-1].endswith("i") and len(out[-1]) >= 2:
            out[-1] = out[-1][:-1] + "y" + _SMALL_Y[ch]
        elif ch in _SMALL_V:
            out.append(_SMALL_V[ch])
        elif ch == "っ":
            sokuon = True
        elif ch == "ー":
            m = re.search(r"[aiueo]$", "".join(out))
            if m: out.append(m.group(0))
        else:
            out.append(ch)
    return "".join(out)

def _romaji_canon(s):
    s = s.lower()
    s = re.sub(r"[^a-z]", "", s)
    s = s.replace("tch", "tty")
    for a, b in (("shi", "si"), ("chi", "ti"), ("tsu", "tu"), ("fu", "hu"), ("ji", "zi"),
                 ("sh", "sy"), ("ch", "ty"), ("j", "zy"), ("dzu", "zu"), ("du", "zu"), ("di", "zi"), ("wo", "o")):
        s = s.replace(a, b)
    s = re.sub(r"m(?=[bpm])", "n", s)
    s = s.replace("nn", "n")
    s = re.sub(r"o[ou]", "o", s)
    s = s.replace("uu", "u")
    return s

def norm(s):
    s = unicodedata.normalize("NFKC", s)
    s = "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)   # カタカナ→ひらがな
    s = s.replace("ō", "o").replace("ū", "u").replace("Ō", "o").replace("Ū", "u")
    s = re.sub(r"[\s・\-‐ー'’]+" if False else r"[\s・\-‐'’]+", "", s)
    return _romaji_canon(_kana_to_romaji(s))

# ブラウザ側（share_lock.py の入力画面に差し込む）。上の Python と同じ規則
JS_NORM = r"""
const KB={あ:'a',い:'i',う:'u',え:'e',お:'o',か:'ka',き:'ki',く:'ku',け:'ke',こ:'ko',さ:'sa',し:'si',す:'su',せ:'se',そ:'so',た:'ta',ち:'ti',つ:'tu',て:'te',と:'to',な:'na',に:'ni',ぬ:'nu',ね:'ne',の:'no',は:'ha',ひ:'hi',ふ:'hu',へ:'he',ほ:'ho',ま:'ma',み:'mi',む:'mu',め:'me',も:'mo',や:'ya',ゆ:'yu',よ:'yo',ら:'ra',り:'ri',る:'ru',れ:'re',ろ:'ro',わ:'wa',を:'o',ん:'n',が:'ga',ぎ:'gi',ぐ:'gu',げ:'ge',ご:'go',ざ:'za',じ:'zi',ず:'zu',ぜ:'ze',ぞ:'zo',だ:'da',ぢ:'zi',づ:'zu',で:'de',ど:'do',ば:'ba',び:'bi',ぶ:'bu',べ:'be',ぼ:'bo',ぱ:'pa',ぴ:'pi',ぷ:'pu',ぺ:'pe',ぽ:'po',ゔ:'vu'};
const SY={ゃ:'a',ゅ:'u',ょ:'o'},SV={ぁ:'a',ぃ:'i',ぅ:'u',ぇ:'e',ぉ:'o'};
function k2r(s){const o=[];let so=false;for(const c of s){if(KB[c]){let r=KB[c];if(so&&!'aiueon'.includes(r[0]))r=r[0]+r;so=false;o.push(r)}else if(SY[c]&&o.length&&o[o.length-1].endsWith('i')&&o[o.length-1].length>=2){o[o.length-1]=o[o.length-1].slice(0,-1)+'y'+SY[c]}else if(SV[c]){o.push(SV[c])}else if(c==='っ'){so=true}else if(c==='ー'){const m=o.join('').match(/[aiueo]$/);if(m)o.push(m[0])}else{o.push(c)}}return o.join('')}
function rcan(s){s=s.toLowerCase().replace(/[^a-z]/g,'').split('tch').join('tty');for(const[a,b]of[['shi','si'],['chi','ti'],['tsu','tu'],['fu','hu'],['ji','zi'],['sh','sy'],['ch','ty'],['j','zy'],['dzu','zu'],['du','zu'],['di','zi'],['wo','o']])s=s.split(a).join(b);s=s.replace(/m(?=[bpm])/g,'n').split('nn').join('n').replace(/o[ou]/g,'o').split('uu').join('u');return s}
const norm=s=>{s=s.normalize('NFKC').replace(/[ァ-ヶ]/g,c=>String.fromCharCode(c.charCodeAt(0)-0x60)).replace(/[ōŌ]/g,'o').replace(/[ūŪ]/g,'u').replace(/[\s・\-‐'’]+/g,'');return rcan(k2r(s))};
"""

if __name__ == "__main__":
    # Python と JS の規則が同じかを、例で照合する
    import json, subprocess
    tests = ["まぐろ とうだい", "マグロ・トウダイ", "maguro toudai", "MAGURO-TODAI", "しおかぜ ゆうひ", "shiokaze yuhi", "siokaze yuuhi",
             "ちゃっきり", "chakkiri", "tyakkiri", "じんじゃ", "jinja", "zinzya", "しんぶん", "shimbun", "まっちゃ", "matcha", "ふじさん", "fujisan", "hudisan"]
    py = [norm(t) for t in tests]
    js = subprocess.run(["node", "-e", JS_NORM + f"console.log(JSON.stringify({json.dumps(tests, ensure_ascii=False)}.map(norm)))"],
                        capture_output=True, text=True).stdout.strip()
    js = json.loads(js)
    for t, a, b in zip(tests, py, js):
        print(("OK " if a == b else "NG ") + f"{t} → {a}" + ("" if a == b else f" / js {b}"))
