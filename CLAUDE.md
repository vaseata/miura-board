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

## 「行ってみたい」ボタン（2026-09-15 追加）

- `category: "イベント"` で**終わっていない**項目に、`build.py` が「行ってみたい」ボタンを付ける。押すと「iPhone のカレンダーに追加」（`ics/<id>.ics`）と「Google カレンダーに追加」（Google の予定作成画面）が出る
- 日時・場所は `items.json` の `cal` から取る：`{"title": 正式名, "place": 会場名（住所）, "start": "HH:MM", "end": "HH:MM", "note": 例外（最終日の時間など）}`
  - `start`/`end` が無ければ**終日**で登録。複数日で時間があれば「毎日その時間×日数」で登録
  - `cal` が無くても動く（title=headline、place=area、終日）。でも**時間と会場は出典本文で確かめて `cal` に書く**。書いていない時間を作らない
- `ics/` は build のたびに作り直す。GitHub Pages 版で使う（Artifact 版は iPhone カレンダーのリンクが動かない場合がある）
- 押したかどうかは閲覧者の端末（localStorage）にだけ残る。サーバーには何も送らない

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
- 定期タスク: `miura-board-daily`（毎朝7:00、アプリ起動中のみ動く。2026-09-15 に Miura フォルダ紐付けで作り直し。旧 `miura-daily` は削除）

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

## 参加予定の行事（`going: true`・2026-09-15 追加）

- ヤヌキが「参加するかもしれない」と言った行事は `items.json` の項目に `"going": true` を付ける。`build.py` が **残り日数**（あとN日）と **下調べ** の欄を出す
- 下調べは `research: [{h, t, confidence, sources}]`（見出し／本文／確信度／開いた出典）と `open_questions: [...]`（まだ分からないこと）で持つ
- **毎朝タスクは going の項目を優先して調べ直す**：公式ページの更新（時間・コース・規制）、当日1週間前からは天気、`open_questions` が解けたら research に移して消す。当日を過ぎたら `going` を外す（記録は残す）
- 出典は開いたものだけ。去年の実績と今年の案内は分けて書く（混ぜない）
- **「行ってみたい」タグ（2026-09-15 追加）**：押した記事が1件でもあると「前回は…」の並びの右端に「行ってみたい N」が出る。押すとその記事だけに絞る（期間は無視）。各記事の欄名の横にも「行ってみたい」の札が付く。パネル内の「行ってみたいを外す」で解除。すべて閲覧者の端末（localStorage）だけで完結
- **「おすすめ」タグ（2026-09-15 追加）**：`items.json`・`calendar.json` の `tags`（神輿／祭り／ラン／食／海／伝統 など）で判定。「行ってみたい」を押した記事の tags と1語でも重なる **これからの イベント／季節** に「おすすめ」の札が付き、「おすすめ N」で絞れる（「これから」の欄も絞る）。新しい行事を足すときは必ず `tags` を付ける。類似候補として 横須賀のみこしパレード（横須賀市観光協会）、海南神社夏例大祭・面神楽（海南神社年間行事）、みちくさマラソン（スポーツエントリー）を出典を開いて追加済み

## レイアウト（2026-09-21 刷新）

- 白地、アクセントは海の青（`--sea` #0A5A8C）とマグロの赤（`--tuna` #B8243A）。見出しは Shippori Mincho、本文は Zen Kaku Gothic New
- トップは「これから・開催中」「最近のできごと」「毎年の定番」「映像欄」の4面。各記事はサムネイル付きカードのグリッドで、各面の先頭が大きく出る（一面）
- カードには 見出し・日付・話のタネ1行 だけを出す。事実・行ってみたい・下調べ・出典は、タップで開く詳細シート（`<dialog>`）に入れる
- 見出しは `headline` を使う（無ければ fact の先頭を切る）。**新しい項目には必ず `headline` を付ける**（25字程度）

## ガイドブック（guide/・2026-10-05 新設）

- **目的**：A邸のゲストに「おすすめのお店・場所・イベントは？」と聞かれたら「このページ」で済む。URL は https://vaseata.github.io/miura-board/guide/ 。近況ボードとは別ページで、データ（items／calendar／places／videos）を共有する
- **生成**：`guide_build.py`（自己完結。`python3 build.py` の末尾からも呼ばれるので毎朝の手順は変えない）→ `guide/index.html`（ゲスト用・1ページ・カテゴリタブ）、`guide/review.html`（候補の確認用・noindex）、`guide/manifest.webmanifest`
- **台帳は `spots.json`**。A邸の座標は公開しない：`home.local.json`（`.gitignore`。`{"name","lat","lon"}`）にだけ置き、`spots.json` の `home` には名前だけ。ファイルが無い環境では徒歩時間を出さない。各項目：`id name category tags area lat lon address hours closed closed_note closed_until season price access note image links sources confidence status last_checked owner_note`
  - `category` は7値固定：食べる／見る・歩く／体験する／買う／移動／困ったとき／季節（季節だけは `season` の月に「今の季節」面へ出る）
  - `closed` は定休曜日の配列 0=月…6=日。不明は `null`（「今日やっている」では表示＋「定休日 要確認」）。臨時休業は `closed_until`
  - `status`：`候補`（review にだけ出る）／`◎`（公開）／`休止`（非表示・記録は残す）。**◎にできるのはヤヌキだけ。Claude は必ず 候補 で足す**
  - `hours／closed／price` は公式か観光協会の個別ページを開いた日を `last_checked` に書く。開けない数字は `null` にして `owner_note` に理由
  - 徒歩時間は JSON に書かない。build が home からの直線距離×1.3÷80m/分 を切り上げて「徒歩N分」。ページには「目安」と明記。lat/lon は地理院の住所検索（`msearch.gsi.go.jp/address-search/AddressSearch?q=`）か Wikipedia の座標で取り、`sources` に残す
- **候補→◎の流れ**：Claude が候補を足す → `python3 build.py` → `guide/review.html` をヤヌキに見せる → 「◎: id, id」の返事で `status` を書き換え → push
- **毎朝タスクに追加の1行**：月初と、`last_checked` が90日より古い◎項目は公式ページを開いて `hours／closed／price／closed_until` を確認し `last_checked` を更新。変化（閉店・休業・時間変更）があれば `items.json` にも出来事として追記。変化なしなら触らない
- **ダイヤモンド富士はガイドに常設しない**（2026-10-05 ヤヌキ指示）。次回が30日以内に入ったときだけ「今の季節」にカードで出る（自動）。4月末・8月上旬が近づいたら items.json にも記事として追記する
- 出典ルールは items と同じ（開いたものだけ）。絞り込み状態は URL ハッシュ（`#cat=食べる&tag=マグロ&open=1&near=1`）で共有できる
