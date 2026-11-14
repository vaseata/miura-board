#!/usr/bin/env python3
"""公開禁止の自動点検（release_plan の6・2026-11-14）。push の前に必ず通す。

使い方:
  python3 check_public.py            … いまの公開ファイル（git が追っているもの＋今回 add したもの）を点検
  python3 check_public.py --history  … 過去のコミット全部も点検（時間がかかる）
  見つかったら終了コード 1。秘密の文字そのものは画面に出さない（種類と場所だけ）

調べるもの（どれもこの Mac の中だけのファイルから読む。公開リポジトリには書かない）:
  - 合言葉（m/.pass）と、そのローマ字の形
  - A邸の座標（home.local.json の lat/lon。小数4桁の組が同じファイルにあれば）
  - 予約台帳（宿泊者.json）の泊まる人の本名・ニックネーム
  - オープンチャットの URL（oc.local.json。参加コードを変えて code_changed が true になるまでは載せない）
  - public_check.local.json の "secrets"（キーボックスの番号・Wi-Fi の名前とパスワード・OC の参加コード・住人の名前・番地など。ヤヌキが書く）
  - 写真の位置情報（EXIF の GPS）
"""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parent
LEDGER = Path('/Users/yanudon/claude/mameden-trio/apps/miura-watcher/data/宿泊者.json')
TEXT = re.compile(r'\.(html?|json|js|css|md|txt|py|ics|xml|csv|ya?ml|webmanifest|svg)$', re.I)
IMG = re.compile(r'\.(jpe?g|png|webp|heic|tiff?)$', re.I)

def load_terms():
    """(種類, 文字) の一覧。文字は画面に出さない。"""
    terms = []
    p = ROOT / 'm' / '.pass'
    if p.exists():
        pw = p.read_text().strip()
        terms.append(('合言葉', pw))
        try:
            from kana_romaji import norm
            if len(norm(pw)) >= 6:
                terms.append(('合言葉（ローマ字）', norm(pw)))
        except Exception:
            pass
    oc = ROOT / 'oc.local.json'
    if oc.exists():
        o = json.loads(oc.read_text())
        if o.get('url') and not o.get('code_changed'):
            terms.append(('オープンチャットのURL（参加コード変更前）', o['url'].split('?')[0].split('/')[-1]))
    if LEDGER.exists():
        for e in json.loads(LEDGER.read_text()).get('events', []):
            m = re.match(r'^\S+　(.+?)(?:（(.+?)）)?$', e.get('summary', '').replace('【取消】', ''))
            if not m:
                continue
            for n in m.groups():
                if n and len(n.strip()) >= 2:
                    terms.append(('泊まる人の名前', n.strip()))
    lc = ROOT / 'public_check.local.json'
    if lc.exists():
        for k, v in json.loads(lc.read_text()).get('secrets', {}).items():
            for x in (v if isinstance(v, list) else [v]):
                if x and len(str(x)) >= 2:
                    terms.append((k, str(x)))
    # 同じ文字の重複を除く
    seen, out = set(), []
    for k, v in terms:
        if v not in seen:
            seen.add(v); out.append((k, v))
    return out

def home_coords():
    h = ROOT / 'home.local.json'
    if not h.exists():
        return None
    d = json.loads(h.read_text())
    import math
    tr = lambda x: f"{math.floor(float(x) * 1e4) / 1e4:.4f}"   # 小数4桁で切り捨て（5桁以上で書かれていても当たる）
    return (tr(d['lat']), tr(d['lon']))

def tracked_files():
    out = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True).stdout.decode().split('\0')
    staged = subprocess.run(['git', 'diff', '--cached', '--name-only', '-z'], cwd=ROOT, capture_output=True).stdout.decode().split('\0')
    return sorted({f for f in out + staged if f and (ROOT / f).exists()})

def gps_in(path):
    try:
        from PIL import Image
        ex = Image.open(path).getexif()
        return bool(ex.get_ifd(0x8825)) if hasattr(ex, 'get_ifd') else (34853 in ex)
    except Exception:
        return False

def check_now(terms, coords):
    found = []
    for f in tracked_files():
        p = ROOT / f
        if IMG.search(f):
            if gps_in(p):
                found.append(('写真の位置情報（GPS）', f))
            continue
        if not TEXT.search(f):
            continue
        try:
            t = p.read_text(errors='ignore')
        except Exception:
            continue
        for k, v in terms:
            if v in t:
                found.append((k, f))
        if coords and re.search(re.escape(coords[0]) + r'\d*\D{1,40}' + re.escape(coords[1]), t):
            found.append(('A邸の座標', f))   # 緯度と経度が組で並んでいるときだけ（近くの名所と別々に当たるのを除く）
    return found

def check_history(terms, coords):
    found = []
    pats = [v for _k, v in terms] + (list(coords) if coords else [])
    if not pats:
        return found
    revs = subprocess.run(['git', 'rev-list', '--all'], cwd=ROOT, capture_output=True, text=True).stdout.split()
    kinds = {v: k for k, v in terms}
    for i in range(0, len(revs), 40):
        args = ['git', 'grep', '-I', '-l', '-F']
        for v in pats:
            args += ['-e', v]
        r = subprocess.run(args + revs[i:i + 40], cwd=ROOT, capture_output=True, text=True)
        for line in r.stdout.splitlines():
            rev, _, f = line.partition(':')
            # どの文字が当たったかを調べ直す（文字は出さない）
            body = subprocess.run(['git', 'show', f'{rev}:{f}'], cwd=ROOT, capture_output=True).stdout.decode(errors='ignore')
            for v in pats:
                if v in kinds and v in body:
                    found.append((kinds[v], f'{rev[:7]}:{f}'))
            if coords and re.search(re.escape(coords[0]) + r'\d*\D{1,40}' + re.escape(coords[1]), body):
                found.append(('A邸の座標', f'{rev[:7]}:{f}'))
    return sorted(set(found))

def main():
    terms, coords = load_terms(), home_coords()
    kinds = sorted({k for k, _v in terms})
    print(f'点検する種類：{"・".join(kinds) or "（秘密の控えが見つからない）"}' + ('・A邸の座標' if coords else ''))
    if not (ROOT / 'public_check.local.json').exists():
        print('⚠️ public_check.local.json がありません。キーボックスの番号・Wi-Fi・参加コード・住人の名前・番地は、まだ点検していません')
    found = check_now(terms, coords)
    if '--history' in sys.argv:
        found += [(k, '履歴 ' + f) for k, f in check_history(terms, coords)]
    if found:
        print(f'❌ 公開してはいけないものが {len(found)} 件あります（文字は出しません）:')
        for k, f in found:
            print(f'  - {k}：{f}')
        sys.exit(1)
    print('✅ 見つかりませんでした')

if __name__ == '__main__':
    main()
