# DECISIONS

bvmap-koicha の意思決定ログ。追記専用で、既存のエントリは書き換えない(誤りが分かったら、新しいエントリで訂正し、
古いエントリには「→ Dnで訂正」と一行足すだけにする)。dwg7 の他のプロジェクトと同じ書き方
(背景 → 決定 → 理由 → 保留事項)。

---

## D1: 名前は bvmap-koicha。比喩は茶に統一し、酒の比喩は使わない

**Status**: Accepted (2026-10-12)

### 背景

bvmap(国土地理院の最適化ベクトルタイル)と同じデータから、建築物などをたっぷり入れた「濃い」タイルセットを作る。
bvmap の派生物には酒の比喩(overdrive など、別の系統の名前)が混じりうるので、このプロジェクトでは基準を決めておく。

### 決定

- **名前**: `bvmap-koicha`。濃茶(こいちゃ)は、薄茶と同じ抹茶を、少ない湯で濃く点てたもの。
  bvmap と同じ地理院のデータを、より濃く仕立てる。違うのは濃さだけ、という意味を込める。
- **比喩は茶に統一する。** 酒の比喩は使わない。計測のサブプロジェクトは **chashaku**(茶杓、抹茶を量る匙)。
  将来の部品の名前も、茶の道具・所作から取る。
- 将来のスタイルは `bvmap-koicha-starlight`(dwg7/bvmap の bvmap-starlight のズーム値を一段ずらしたもの)。

### 理由

- 「同じ素材を濃くする」という関係が、そのまま名前になる。説明が一文で済む。
- 比喩の系統を一つに絞ると、後から来るエージェントや読者が、名前から役割を推測しやすい。

### 保留事項

なし。

---

## D2: 作る前に測る

**Status**: Accepted (2026-10-12)

### 背景

「MLT でタイルを小さくし、ズームを一段ずらす」という発想は、MLT の効きと、ずらしたあとのタイルの重さに依存する。
どちらも、実際の bvmap タイルで測るまで分からない。

### 決定

最初の段階は計測(chashaku)とする。全国のタイルセットの生成、スタイルの作成、地物の簡略化・総描は、
計測の結果を見てから決める。計測の段階では、**束ねる・捨てる・エンコーディングを変える**以外の加工をしない。

### 理由

- 作ってから「重すぎた」と分かると、全国分の生成のやり直しになる(bvmap は元が約17GB)。
- 地物の中身に手を入れると、「濃さ」と「データの正しさ」のどちらが測定結果に効いたのか分からなくなる。

### 保留事項

なし。

---

## D3: chashaku の計測設計

**Status**: Accepted (2026-10-12)

### 決定

**測る場所**(`chashaku/areas.tsv`): tokyo, osaka, sapporo, obihiro-rural, taisetsu。範囲は最初のプロンプトの目安どおり。
bvmap の z13〜z16 を `pmtiles extract --bbox` で取り出して使う(z13: 6〜16枚、z16: 132〜783枚、計 2,753枚)。

**組み方**(`chashaku/measure.py`):

| 名前 | koicha z13, z14 | koicha z15 | koicha z16 |
|---|---|---|---|
| `bvmap`(基準) | bvmap z13, z14 そのまま | bvmap z15 | bvmap z16 |
| `hyp`(仮説) | bvmap z14, z15 の4枚を束ねる | bvmap z16 の4枚を束ね、`vt_flag17=2` の地物と z17 専用の4層(RdEdg, RdCompt, RailTrCL, StrctLine)を捨てる | bvmap z16 から `vt_flag17=0` の地物を捨てる |
| `contra`(対立案) | hyp と同じ | bvmap z16 の4枚をそのまま束ねる(z16 + z17 の内容。extent 2倍) | なし(maxzoom 15) |

**測り方**:

- 束ねるときは座標の平行移動と extent 2倍(4096 → 8192)だけ。地物の属性・頂点は変えない。
  デルタ符号化なので、移動は各地物の最初の MoveTo を書き換えるだけで済む。
- 子タイルの buffer(tippecanoe の既定)は切り落とさず、そのまま束ねる。重複した縁の地物は残る(悲観側の見積もり)。
  検証で、束ねたあとの座標が extent×2 と buffer の範囲に収まることを確かめた(`validate.py`)。
- 縁のタイルは子が4枚そろわず小さくなる。統計は「子が全部そろったタイル(complete)」を主、全タイルを従として出す
  (`summarize.py`、`n_children` 列)。z13 は complete のタイルが 1〜16枚と少なく、統計は弱い。
- サイズは MVT+gzip(-9)、MLT のみ、MLT+gzip(-9)の3通り。**gzip -9 は bvmap の保存サイズと 2,753枚すべてで一致した**
  ので、bvmap 側の基準と同じ条件で比べられている。
- 統計は中央値、95パーセンタイル、最大値(nearest-rank)。最悪のタイルは `max_tile` 列に z/x/y を残す。
- `contra` の z15 は、z16 と z17 の両方の内容を含む。maxzoom 15 で z16 表示のときも同じタイルを使うため。

### 理由

- `hyp` は最初のプロンプトの第一の仮説、`contra` は対立案。この二つを同じ土俵で比べるのが目的。
- 「完全タイル」の区別を入れないと、縁のタイルが中央値を押し下げて `hyp` が実際より軽く見える。

### 保留事項

- 測った5範囲の外(新宿・渋谷など最も密な場所)には、もっと重いタイルがありうる。全国の最悪値は未測定。

---

## D4: MLT エンコーダーは maplibre-tile-spec の Rust 版 `mlt` CLI 0.4.3

**Status**: Accepted (2026-10-12)

### 背景

MLT のエンコーダーは開発が速く、実装も複数ある。調べた時点(2026-10-12)の状況:

| 実装 | 版 | 備考 |
|---|---|---|
| Rust `mlt` CLI(maplibre-tile-spec) | 0.4.3(2026-10-12 公開) | `mlt convert` が MVT/PBF ディレクトリ・mbtiles・pmtiles を再エンコード。`--verify` で復号して入力と照合できる |
| Java `mlt-encode.jar` | java-v0.0.4 | bvmap-overdrive が使用 |
| npm `@maplibre/mlt` | 1.3.0 | JS のエンコーダー兼デコーダー |
| Martin(`convert_to_mlt`) | – | 配信時の変換。アーカイブ生成には向かない |
| `mlt-py`, `mlt-core`, `mlt-wasm` | 0.2.12, 0.20.3, 0.1.45 | Rust コアのバインディング |

### 決定

**Rust 版 `mlt` CLI 0.4.3** を使う。取得元は `maplibre/maplibre-tile-spec` の公式リリース `rust-mlt-v0.4.3` の
`mlt-aarch64-apple-darwin.tar.gz`(6,171,657 B、sha256 `c3796143…ba2a68` を公式の digest と照合して一致)。
`tools/fetch-mlt.sh` で再取得・検証できる。バイナリはコミットしない。

変換のオプションは**既定のまま**(`--sort none`、FastPFOR・FSST・共有辞書はすべて有効)に、`--verify` を付ける。

- `--sort none` は「元の順序を保つ」で、これは描画順であり注記の優先順位でもある。地物の並べ替えは描画を変えうるので使わない。
  参考として `--sort auto` も測り、MLT+gz の中央値の変化は −5.0%〜+2.5%(`summary_sortauto.csv`。主な範囲では 1〜2% 小さくなる程度)で、結論は変わらない。
- `--verify` で、全 6,266 タイル(15組)が復号して入力と一致した(`results/mlt_convert.log`)。

### 理由

- bvmap と同じ MVT を入力にでき、ディレクトリ単位で速い(全 6,266 タイルが数秒)。
- 検証(`--verify`)が組み込みで、「エンコーダーの不具合で小さく見えている」可能性を潰せる。
- 公式リポジトリの最新で、開発が最も活発。Java 版(java-v0.0.4)より新しい。
- 手元の Rust は 1.96.1 で、0.4.3 のソースビルドには 1.98 が必要だったため、ビルド済みを取得した
  (取得はユーザーの許可を得て行った)。0.1.x〜0.4.x の全版が 1.98 を要求していて、古い版へ逃げる道もなかった。

### 使ったツールの版

- `mlt` 0.4.3(上記)、`pmtiles` 1.28.0(commit 9a400a68d039dfa71e1706f154139558cbd1999f)、Python 3.9.6(標準ライブラリのみ)、
  macOS 27.0.1 / arm64。
- **MLT のエンコーダーの版が上がると、サイズが変わる。** 結果を引用するときは版を添えること。

### bvmap-overdrive から引き継いだこと・変えたこと

| | bvmap-overdrive | bvmap-koicha chashaku |
|---|---|---|
| 目的 | bvmap 全体を MLT に変換した PMTiles を作る | 作る前に、範囲を限って大きさを測る |
| エンコーダー | Java `mlt-encode.jar` java-v0.0.4 | Rust `mlt` 0.4.3 |
| 入力 | 全国の PMTiles を丸ごと取得し、tile-join で mbtiles へ | `pmtiles extract --bbox` で必要な範囲だけ |
| 中間形式 | mbtiles | ディレクトリの `z/x/y.mvt`(PMTiles を自前の読み取りで展開) |
| 引き継いだ点 | 入力は GSI の公式 PMTiles、go-pmtiles の使用 | 同左(go-pmtiles は 1.28.0) |

(bvmap-overdrive は README と Justfile のみを読んだ。実際の出力サイズの記録は見つからなかった。)

### 保留事項

- npm `@maplibre/mlt`(JS)でのクロスチェックは、今回は取得しなかった。別実装との比較が必要になったら、改めて許可を得て行う。
- 現時点の MLT エンコーダーが正しく使いこなせているか(列の型の指定 `--fields` など、サイズに効く可能性のあるオプション)は
  未調査。属性が大きな層(Anno の `vt_text` など)で効くかもしれない。

---

## D5: 取得事故の記録 — 全国分を約10GB 取得してしまった。再発防止の規則

**Status**: Accepted (2026-10-12)

### 経緯

最初の抽出で、シェルのループを zsh で書いたため、`for r in "tokyo 139.73,…"; do set -- $r` が単語分割されず(zsh は変数を分割しない)、
`--bbox=` が空になった。`pmtiles extract` は bbox なしで**全国**(約 288 万タイル、約16GB)を対象に取得を始めた。
tokyo(約 9.8GB)と osaka(約 0.5GB)の途中で気づいて停止した。GSI のサーバーから**約 10GB を取得した**ことになる。
「地理院のサーバーに負荷をかけない」という規則に反する。出力は壊れていたので削除し、正しい bbox で取り直した
(正しい取得は5範囲で計 約 24MB)。

### 決定(規則)

1. `pmtiles extract` は、**必ず `--dry-run` でタイル数を確かめてから**実行する。`chashaku/fetch.sh` が、
   タイル数が `MAX_TILES`(既定 5,000)を超えるか空なら取得せずに止まる。
2. 取得のスクリプトは `bash` で書く(`#!/usr/bin/env bash` を使い、zsh の単語分割の違いに頼らない)。
3. 取得した範囲は `data/bvmap/` に保存し、再実行しても取り直さない(`fetch.sh` は既存の抽出をスキップする)。
4. 出所の記録(取得日時、`Last-Modified`、ETag、サイズ)は、実際に取得したときだけ書き換える。

### 理由

- 空の引数が「全部」を意味するツールは、引数の検証を自分で持たないと危ない。ドライランを必須の関門にすれば、
  同種の誤り(変数が空、範囲が広すぎる)を取得前に捕まえられる。

### 保留事項

- GSI 側にこの取得の通知や謝罪が必要かどうかは、hfu さんの判断に委ねる(約10GB、単発、約10分間、2スレッド)。

---

## D6: maxzoom は 16(`hyp`)を採用する。間引きは今は要らない

**Status**: Accepted (2026-10-12) — hfu さんが採用を承認(同日)

### 決定

- **maxzoom 16(`hyp`)を第一候補とする。** 詳細と数値は `chashaku/REPORT.md`。
  - 同じ土地を覆うのに要する量は、`contra` のほうが多い。表示 z15 で `hyp` の 1.23〜1.31 倍(都市・郊外の4範囲、MLT+gz)、
    表示 z16 で 1.07〜1.12 倍。山地(taisetsu)では差がない(1.00 倍と 0.96 倍)。
  - 最悪のタイルも `hyp` のほうが小さい(z15、MLT+gz、tokyo の最大 68KB 対 78KB)。
  - 代償として、アーカイブは `contra` の約 1.7 倍(z15 と z16 の両方に建築物が入るため)。z16 表示時のリクエスト数は4倍。
- **間引きは、今は要らない。** 最悪のタイルでも MLT+gz で約 105KB(tokyo z13、5範囲全体で 100KB を超えるのはこの1枚だけ)に収まる。
  次の段階で効きそうな候補(層ごとの占有率は REPORT.md)は、z13/z14 の RdCL(49〜66%)、山地の Cntr(70〜92%)。
  建築物(z15 で 71〜78%)は、このプロジェクトが増やしたいものなので、間引かない。

### 保留事項

- タイルの大きさの上限(目標値)が決まれば、間引きの要否は数値で判断できる。目標値を hfu さんに確認する。

### 承認時の補足

- 採用は maxzoom 16 の組み方(`hyp`)のみ。間引きの要否は、タイルの大きさの目標値が決まるまで保留のまま。
- 描画の確認(MapLibre GL JS での extent 8192 の MLT、z16 の層構成)は未実施で、次の段階の前提として残る。

---

## D7: 描画の確認 — `hyp` の MLT は MapLibre GL JS で正しく描ける

**Status**: Accepted (2026-10-12)

### 決定・結果

D6 の前提として残っていた描画の確認を行った(`chashaku/viewer/`)。ブラウザ(Claude のビルトインブラウザ)で
MapLibre GL JS **6.14.0**(`encoding: "mlt"`)に tokyo の `data/mlt/tokyo/{bvmap,hyp}` を読ませ、左右を連動させて比べた。

- **extent 8192 の MLT(z13〜z15)は問題なく復号・描画できた。** 継ぎ目(束ねた4枚の境界)も目視で見えない。
- **z14 表示は bvmap z15 の内容**、**z15 表示は bvmap z16 の内容**、**z16 表示は bvmap z17 の内容**(道路縁・線路の軌道など)で描かれた。
  GSI の `std.json` の `step ["zoom"]` と `minzoom: 17` を、ズーム値だけ −1 した(`bvmap-koicha-starlight` の素朴な代用)もので足りた。
  `hyp` の z15 が `vt_flag17=2` を、z16 が `vt_flag17=0` を捨てていても、スタイルのフィルターと矛盾しない。
- 使った版: maplibre-gl 6.14.0(同梱の `@maplibre/mlt` ^1.3.0 がデコーダー)、pmtiles 4.5.0(今回は未使用)。
  パッケージはユーザーの許可を得て `npm install --ignore-scripts`(固定版)で取得した。

### 限界

- 確認は tokyo の中心(東京駅周辺)で z14〜z16 を目視。注記(symbol 層)は描いていない(グリフ・スプライトを GSI から取らないため)。
- 他のクライアント(MapLibre Native、Martin 経由の配信など)は未確認。
- 描画の性能(複雑な z13 タイルのデコード・描画時間)は測っていない。

---

## D8: bvmap-koicha-starlight は、bvmap-starlight の生成物を機械的に −1 ずらして作る

**Status**: Accepted (2026-10-12)

### 背景

D6 で maxzoom 16(`hyp`)を採用した。タイルの z は bvmap の z+1 の内容を持つので、スタイルのズームの値も一段ずらす必要がある。
最初のプロンプトでは「dwg7/bvmap の bvmap-starlight のズームの値を一段ずらしたもの」と定められていた。

### 決定

- dwg7/bvmap の `style/bvmap-starlight.json`(`generator/` が `bvmap-dark.json` から生成する成果物)を**入力のスナップショット**として
  `style/upstream/` に置き(コミット `9068c809`)、`style/make_koicha_starlight.py` でズームの値だけを −1 する。
  生成の対象はレイヤーの `minzoom`/`maxzoom`、`step` と `interpolate` の停止値。配色などは触らない。
- dwg7/bvmap の `generator/`(YAML 駆動)には手を入れない。ズームの値の移動はその下流の機械的な変換で足り、
  配色の磨き上げ(上流の仕事)と、タイルに合わせる調整(こちらの仕事)を分けられる。
- ソースは MLT(`encoding: "mlt"`)、`minzoom 3`、`maxzoom 16`。`attribution` に「国土地理院最適化ベクトルタイルを加工して作成」を入れる。
- `["zoom"]` が `step` / `interpolate` 以外の形で現れたら、スクリプトは失敗する。

### 理由

- 上流を再生成するたびに、同じ変換を再実行できる。差分は「−1」だけと言い切れるので、レビューも簡単。
- 描画の確認(D7)で、ズーム値を −1 しただけの素朴なスタイルで `hyp` のタイルが矛盾なく描けると分かっていた。
  bvmap-starlight で改めて確かめ、道路縁・軌道・注記まで描けた。

### 保留事項

- z3〜z12 は未作成・未確認(D3: 計測は z13〜z16)。bvmap の z4〜z7 は extent 16384 で、束ねると 32768 になる。
- 線幅・文字サイズも停止値を −1 したので、同じ表示ズームで線や文字が、上流の一段下の大きさになる。
  見た目として望ましいかは、実際の閲覧で判断する(hfu さんの確認が要る)。
- `source.url` の配信先、`glyphs`/`sprite` の扱い(今は上流のまま)。

---

## D9: 最初の bvmap-koicha PMTiles は tokyo の範囲限定版(z3〜z16、MLT)

**Status**: Accepted (2026-10-12)

### 決定

- `build/build.sh tokyo` で、`data/koicha/tokyo.pmtiles` を作る(git の管理外)。計 **267 タイル**(z3: 1 … z13: 6, z14: 16, z15: 49, z16: 182)、
  **5.7MB**(MLT、タイルは無圧縮。各タイルを gzip -9 すると 5.2MB)。組み方は `hyp`(D3/D6)で、z3〜z14 は bvmap の z+1 を束ねる。
- 範囲は計測と同じ tokyo。z4〜z13 は追加で 19 タイルを取得した(ドライランで枚数を確認、約 0.57MB)。
- 変換は `mlt convert --verify`(0.4.3、D4)。PMTiles のヘッダーは tile type = 6(MLT)、タイル圧縮 = なし。
- 範囲限定版: 束ねる子が取得範囲の外にあるタイルは、あるぶんだけで束ねる。低ズームでは bvmap の1タイルが範囲より大きいので、
  z3〜z12 は bvmap タイルの縁で欠ける(`build/README.md`)。全国版には出ない。

### 確認したこと

- ブラウザ(MapLibre GL JS 6.14.0 + pmtiles 4.5.0、`pmtiles://` プロトコル、HTTP Range)で bvmap-koicha-starlight と組み合わせ、
  z3, 5, 7, 9, 11, 12, 13, 14, 15, 16 を表示した。エラーなし、注記・アイコン・出典表示も出た。
- **z4〜z7 を束ねた extent 32768 の MLT も復号・描画できた**(D8 の保留事項が解消)。
- タイルの大きさ: 最大は z13 の 120.6KB(MLT)/104.8KB(MLT+gz)で、計測(`chashaku/REPORT.md`)と一致。z3〜z12 は最大 76KB(z10、MLT)。

### 保留事項

- **タイル圧縮が「なし」**。`mlt convert` が PMTiles に直接書くため。配信では、MLT+gzip(約 9% 小さい)にしたい。
  タイルごとに gzip して PMTiles に詰め直す方法(mbtiles 経由など)を、配信先が決まるときに決める。
- 配信先(`source.url`)、PMTiles の `vector_layers` メタデータ(今は mbtiles 経由の簡易版)。
- 全国版は未生成(D2: 計測の結果を見てから。取得量は元の約17GB、`pmtiles extract` を使わず丸ごと取るか要相談)。

---

## D10: 配信は stars(hfu/stars)で行う。開発中はローカルで動かす

**Status**: Accepted (2026-10-12) — hfu さんの指示

### 決定

- **本番の配信は stars(stars.optgeo.org、Martin)。** このリポジトリは配信設定を持たない(dwg7/bvmap と同じ役割分担)。
  配信物は `hfu/stars` に置く: PMTiles は `/home/stars/data/` に置くと、`config/martin.yaml` の `pmtiles.paths` の自動発見で
  ファイル名が source ID になって配信される(`docs/KNOWN_FACTS.md`)。スタイルは `hfu/stars/styles/` に PR する。
- **開発中はローカル**(`chashaku/viewer/serve.py` と `build/`)で動かしてよい。stars には載せない。
- stars への反映(PMTiles のアップロード、スタイル PR、`martin.yaml` の変更)は、いずれも対外的な変更なので、**そのつど hfu さんの確認を得てから**行う。

### stars 側で確認が要ること(未確認、stars を読んだだけ)

- stars の Martin が、tile type 6(MLT)の PMTiles を正しく配信するか(Content-Type、`encoding` の伝え方)。
  stars のスタイルが `pmtiles://` を直接読むか、Martin の TileJSON(`"url": "https://stars.optgeo.org/<id>"`、bvmap-starlight と同じ形)を読むかで、
  `make_koicha_starlight.py --source-url` の値と、`encoding: "mlt"` の置き場所が変わる。
- タイル圧縮(D9 の保留事項)。Martin は gzip の PMTiles を、そのまま `Content-Encoding: gzip` で返せる。MLT のタイルを gzip 済みにしたほうがよい。
- `sprite` と `glyphs` は、すでに stars が配信している(`/sprite/bvmap-starlight`、`/font/...`)ので、スタイルは今のまま使える。
- stars の `styles/` には `bvmap-starlight.json` が既にある。`bvmap-koicha-starlight.json` を並べて置く形になる。

