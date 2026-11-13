#!/usr/bin/env python3
"""宿泊者向けのページを合言葉で暗号化して m/<token>/index.html に書く。

使い方:
  python3 share_lock.py                 … ハザードマップ（hazard-share.src.html → m/<m/.token>/）
  python3 share_lock.py --save-pass     … 合言葉をこの Mac にだけ保存する（m/.pass・公開しない）。一度やれば、毎朝の自動更新でも使える
  ほかのページは arrival_build.py のように lock() を呼ぶ

- 元のページ（*.src.html）は .gitignore。公開しない
- 出力は暗号文＋合言葉の入力画面だけ。合言葉を知らないと読めない
- token は m/.token（ハザード）・m/.token-arrival（到着カード）に保存して使い回す（URLを変えたいときは消す）。公開しない
- 合言葉はリポジトリに書かない。環境変数 SHARE_PASS → m/.pass → 実行時の入力 の順に探す
- 合言葉は一度入れると、その端末では宿泊者向けページ全部に使える（localStorage の 'hz'）
"""
import base64, getpass, os, secrets, sys
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ROOT = Path(__file__).parent
ITER = 310000
PASS_FILE = ROOT / 'm' / '.pass'
BASE = 'https://vaseata.github.io/miura-board/'

def get_pass():
    pw = os.environ.get('SHARE_PASS')
    if not pw and PASS_FILE.exists():
        pw = PASS_FILE.read_text().strip()
    if not pw:
        if not sys.stdin.isatty():
            sys.exit('合言葉が未保存です。ターミナルで `python3 share_lock.py --save-pass` を一度実行してください')
        pw = getpass.getpass('合言葉: ')
    if len(pw) < 6:
        sys.exit('合言葉は6文字以上にしてください')
    return pw

def token_for(name):
    tokf = ROOT / 'm' / name
    tokf.parent.mkdir(exist_ok=True)
    if not tokf.exists():
        tokf.write_text(secrets.token_urlsafe(12).replace('_', 'x').replace('-', 'y'))
    return tokf.read_text().strip()

PAGE = '''<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>@TITLE@</title>
<link rel="icon" href="../../img/brand/logo.png">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@800&family=Zen+Kaku+Gothic+New:wght@400;700&display=swap">
<style>
:root{color-scheme:light;--bg:#fff;--ink:#14202B;--mute:#4F6070;--hair:#D9E1E8;--sea:#0A5A8C;--tuna:#B8243A}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Zen Kaku Gothic New","Hiragino Sans",sans-serif;font-size:17px;line-height:1.7}
main{max-width:440px;margin:0 auto;padding:24px 16px 40px}
.hd{display:block;width:100%;height:auto;border-radius:10px;margin:0 0 18px}
.brand{display:flex;align-items:center;gap:8px;font-size:12px;font-weight:700;letter-spacing:.16em;color:var(--sea)}
.brand img{width:40px;height:40px}
h1{font-family:"Shippori Mincho",serif;font-weight:800;font-size:1.6rem;margin:6px 0 4px}
p{margin:6px 0;color:var(--mute);font-size:.95rem}
input,button{font:inherit;width:100%;box-sizing:border-box;padding:12px 14px;border-radius:999px;border:1px solid var(--hair);margin-top:14px}
input{border-radius:10px}
button{background:var(--sea);color:#fff;border-color:var(--sea);font-weight:700}
input:focus-visible,button:focus-visible{outline:2px solid var(--sea);outline-offset:2px}
#e{color:var(--tuna);min-height:1.5em;font-weight:700}
</style></head><body><main>
<img class="hd" src="../../img/brand/header-maguro.jpg" alt="" width="1500" height="500">
<div class="brand"><img src="../../img/brand/logo.png" alt="" width="40" height="40">MIURA A-TEI · 宿泊者向け</div>
<h1>@TITLE@</h1>
<p>A邸に泊まる方に、合言葉をお伝えしています。一度入れると、この端末では次から自動で開きます。</p>
<form id="f"><input id="p" type="password" autocomplete="current-password" placeholder="合言葉" aria-label="合言葉" required>
<button>ひらく</button><p id="e" role="alert"></p></form>
</main>
<script>
const D={salt:"@SALT@",iv:"@IV@",ct:"@CT@",n:@N@};
const u=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
async function open_(pw){
  const k0=await crypto.subtle.importKey('raw',new TextEncoder().encode(pw),'PBKDF2',false,['deriveKey']);
  const k=await crypto.subtle.deriveKey({name:'PBKDF2',salt:u(D.salt),iterations:D.n,hash:'SHA-256'},k0,{name:'AES-GCM',length:256},false,['decrypt']);
  const t=await crypto.subtle.decrypt({name:'AES-GCM',iv:u(D.iv)},k,u(D.ct));
  document.open();document.write(new TextDecoder().decode(t));document.close();
}
const e=document.getElementById('e');
async function go(pw,quiet){
  e.textContent=quiet?'':'確認しています…';
  try{await open_(pw);try{localStorage.setItem('hz',pw)}catch(_){}}
  catch(_){ if(!quiet)e.textContent='合言葉が違うようです';try{localStorage.removeItem('hz')}catch(_){} }
}
document.getElementById('f').onsubmit=ev=>{ev.preventDefault();go(document.getElementById('p').value.trim(),false)};
try{const s=localStorage.getItem('hz');if(s)go(s,true)}catch(_){}
</script></body></html>
'''

def lock(plain: bytes, token_name: str, title: str, pw: str = None) -> str:
    """plain（HTML）を暗号化して m/<token>/index.html に書き、URL を返す。"""
    pw = pw or get_pass()
    token = token_for(token_name)
    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(hashes.SHA256(), 32, salt, ITER).derive(pw.encode())
    ct = AESGCM(key).encrypt(iv, plain, None)
    b = lambda x: base64.b64encode(x).decode()
    page = (PAGE.replace('@TITLE@', title).replace('@SALT@', b(salt)).replace('@IV@', b(iv))
            .replace('@CT@', b(ct)).replace('@N@', str(ITER)))
    out = ROOT / 'm' / token
    out.mkdir(parents=True, exist_ok=True)
    (out / 'index.html').write_text(page, encoding='utf-8')
    return f'{BASE}m/{token}/'

if __name__ == '__main__':
    if '--save-pass' in sys.argv:
        pw = getpass.getpass('合言葉（ハザードマップと同じもの）: ')
        if len(pw) < 6:
            sys.exit('合言葉は6文字以上にしてください')
        PASS_FILE.parent.mkdir(exist_ok=True)
        PASS_FILE.write_text(pw)
        os.chmod(PASS_FILE, 0o600)
        print('保存しました: m/.pass（この Mac だけ。公開しません）')
    else:
        url = lock((ROOT / 'hazard-share.src.html').read_bytes(), '.token', '防災マップ')
        print('書きました:', url)
