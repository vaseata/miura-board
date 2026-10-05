#!/usr/bin/env python3
"""宿泊者向けハザードマップを合言葉で暗号化して m/<token>/index.html に書く。

使い方:  SHARE_PASS='合言葉' python3 share_lock.py
- 元のページは hazard-share.src.html（.gitignore。公開しない）
- 出力 m/<token>/index.html は暗号文＋合言葉の入力画面だけ。合言葉を知らないと読めない
- token は初回に m/.token へ保存して使い回す（URLを変えたいときは m/.token を消す）。m/.token は公開しない
- 合言葉はリポジトリに書かない。環境変数 SHARE_PASS か、実行時の入力で渡す
"""
import base64, getpass, os, secrets, sys
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ROOT = Path(__file__).parent
ITER = 310000
pw = os.environ.get('SHARE_PASS') or getpass.getpass('合言葉: ')
if len(pw) < 6:
    sys.exit('合言葉は6文字以上にしてください')

tokf = ROOT / 'm' / '.token'
tokf.parent.mkdir(exist_ok=True)
if not tokf.exists():
    tokf.write_text(secrets.token_urlsafe(12).replace('_', 'x').replace('-', 'y'))
token = tokf.read_text().strip()

salt, iv = os.urandom(16), os.urandom(12)
key = PBKDF2HMAC(hashes.SHA256(), 32, salt, ITER).derive(pw.encode())
plain = (ROOT / 'hazard-share.src.html').read_bytes()
ct = AESGCM(key).encrypt(iv, plain, None)
b = lambda x: base64.b64encode(x).decode()

page = '''<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>三浦A邸 宿泊者向け</title>
<style>
:root{color-scheme:light}
body{margin:0;background:#fff;color:#111827;font-family:system-ui,"Hiragino Sans",sans-serif;font-size:18px;line-height:1.7}
main{max-width:420px;margin:0 auto;padding:18vh 24px 40px}
h1{font-size:1.4rem;margin:0 0 6px}
p{margin:6px 0;color:#4b5563;font-size:.95rem}
input,button{font:inherit;width:100%;box-sizing:border-box;padding:12px 14px;border-radius:10px;border:1px solid #9ca3af;margin-top:14px}
button{background:#111827;color:#fff;border-color:#111827;font-weight:700}
#e{color:#b01c00;min-height:1.5em}
</style></head><body><main>
<h1>三浦A邸 宿泊者向け</h1>
<p>A邸に宿泊した方に、合言葉をお伝えしています。</p>
<form id="f"><input id="p" type="password" autocomplete="current-password" placeholder="合言葉" required>
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
page = page.replace('@SALT@', b(salt)).replace('@IV@', b(iv)).replace('@CT@', b(ct)).replace('@N@', str(ITER))
out = ROOT / 'm' / token
out.mkdir(exist_ok=True)
(out / 'index.html').write_text(page, encoding='utf-8')
print('書きました: m/%s/index.html' % token)
print('URL: https://vaseata.github.io/miura-board/m/%s/' % token)
