# 最近の三浦 — 三浦A邸の近況ボード

久しぶりに三浦A邸（ゲストハウス）に来た会員さんに「最近の三浦はどうですか？」と聞かれたとき、
ヤヌキが **iPhoneでパッと見て話題にする** ための1ページ。読者はヤヌキ本人（会員さんに見せてもよい）。

## 構成

| ファイル | 役割 |
|---|---|
| `CLAUDE.md` | このファイル。方針 |
| `items.json` | **唯一の可変データ**。日付つきの項目（出来事・店・イベント・交通・A邸まわり） |
| `calendar.json` | 毎年くり返す定番（花・魚・ダイヤモンド富士・祭り）。月日だけ持つ |
| `build.py` | `items.json` + `calendar.json` → `index.html` を生成 |
| `index.html` / `artifact.html` | 生成物（Pages用の完全HTML／Artifact用の断片）。手で編集しない |

## 項目の書き方（2行ルール）

- **fact**：事実1行。日付・場所・固有名詞を入れる
- **talk**：話の振り方1行。「〜なら行けますよ」「〜だったそうです」
- **confidence**：🟢 出典を開いて確認／🟡 一次でない・日付が「頃」／🗣 伝聞（誰から聞いたか）
- **source.url は実際に開いたものだけ**。検索結果の要約で数字を確定しない
- 事故・事件は淡々と事実だけ。感想を足さない

## 期間の考え方

読者は「前回来てから」を知りたい。ページ側で 1ヶ月／3ヶ月／半年／1年 を切り替え、
`items.json` の `date` で絞る。古い項目は消さない（1年を超えたら自然に隠れる）。

## 毎朝の集計（定期タスク）

1. 三浦市公式・観光協会・号外NET横須賀三浦・カナロコ横須賀三浦・タウンニュース三浦・京急/三崎観光のリリースを見る
2. 新しい項目があれば **出典を開いてから** `items.json` に追記（2行ルール）
3. `python3 build.py` → Artifact を同じURLで再公開
4. 追記ゼロの日は何もしない（空更新しない）

## 禁止

- 出典を開かずに数字・日付を書く
- 伝聞を🟢にする
- `index.html` を直接編集する

## 公開先

- Artifact URL: https://claude.ai/code/artifact/5e63a0ef-6d92-4428-a9da-26e837d9ed5c
- 再公開は `index.html` を同じURL（`url` 指定）で publish する。創刊 2026-09-12
- 定期タスク: `miura-daily`（毎朝7:00、アプリ起動中のみ動く）

## 写真サムネイル（2026-09-12 追加）

- 台帳は `places.json`。`items.json` / `calendar.json` の `image` はそのキー。`build.py` が `img/<key>.jpg` を描く
- **2段構え**：①出典記事に本物の写真（og:image）があればそれ ②なければ場所の定番写真（Wikimedia Commons の CC0／CC BY。クレジットはページ末尾に自動）
- 事故・事件は報道写真を使わない。場所写真（灯台など）にする
- 作り方：`img/raw/` に原本を落とし、PIL で 480×300 に切り出して `img/<key>.jpg`（品質78）。公開時は Artifact の `files` に `img/*.jpg` を渡す（`img/raw/` は公開しない）
- 新しい場所写真が要るときは Commons API（`action=query&generator=categorymembers&gcmtitle=Category:...&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=640`）。カテゴリ例：Jōgashima Lighthouse／Jogashima Bridge／Port of Misaki (Kanagawa)／Misaki, Miura／Miura Beach／Jōgashima, Kanagawa
- ⚠️ この Mac の python3 は SSL 証明書が無く `urllib` が失敗する。取得は `curl` を使う

## 動画（2026-09-12 追加）

- `videos.json` は `yt_fetch.py` が管理。城ヶ島／三崎港／三浦海岸／油壺／小網代／三浦市 で YouTube 検索し、
  タイトルかチャンネル名に三浦の地名を含むものだけ残す（人名の「三浦」「三崎」は NG リストで除外）
- 直近60日・同じチャンネルの同じ日は1本・ライブカメラは全体で1本・合計20本。サムネイルは `img/yt/<id>.jpg`（YouTube の mqdefault）
- ヤヌキから動画URLをもらったら `python3 yt_fetch.py <videoId>`（manual 扱い＝古くなっても消さない）
- 公開時は `img/yt/*.jpg` も `files` に渡す
- ⚠️ YouTube の並び替えパラメータは効きが弱い。`published` は「N日前」表記からの概算（🟡相当）

## GitHub（2026-09-12）

- リポジトリ: https://github.com/vaseata/miura-board（public・2026-09-12 に切替）。`img/raw/` は除外
- 更新のたびに `git add -A && git commit -m "YYYY-MM-DD 更新: 追記の要点" && git push`

## 公開URL（2026-09-12 追記）

- **GitHub Pages: https://vaseata.github.io/miura-board/** ← 会員さんに見せる／iPhoneに置くのはこちら（ログイン不要）。`main` に push すると数十秒で反映
- Artifact（claude.ai）は下書き確認用。Share 設定に依存する
- `build.py` は2本書く：`index.html`（完全なHTML・Pages用）と `artifact.html`（断片・Artifact用。同じURLに `url` 指定で publish）
