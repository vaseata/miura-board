#!/usr/bin/env python3
"""3D版ハザードマップ（宿泊者向け）の元ファイル hazard-share.src.html を書く。

- テンプレート hazard3d.tpl.html に、A邸の座標を home.local.json（非公開）から差し込む
- 出力 hazard-share.src.html は .gitignore。公開しない。share_lock.py が合言葉で暗号化する
- 使い方:  python3 hazard3d_build.py   →   python3 share_lock.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
home = json.loads((ROOT / 'home.local.json').read_text(encoding='utf-8'))
h = {'name': home.get('name', '三浦A邸'), 'lat': home['lat'], 'lon': home['lon']}
html = (ROOT / 'hazard3d.tpl.html').read_text(encoding='utf-8').replace('%%HOME%%', json.dumps(h, ensure_ascii=False))
(ROOT / 'hazard-share.src.html').write_text(html, encoding='utf-8')
print('書きました: hazard-share.src.html（%d バイト）' % len(html))
