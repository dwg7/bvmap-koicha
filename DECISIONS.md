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

- `build/build.sh tokyo` で、`data/koicha/tokyo.pmtiles` を作る(git の管理外。→ D11 で `bvmap-koicha-tokyo.pmtiles` に改名)。計 **267 タイル**(z3: 1 … z13: 6, z14: 16, z15: 49, z16: 182)、
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

---

## D11: 公開名 — PMTiles は `bvmap-koicha-<範囲>.pmtiles`、スタイルは `bvmap-koicha-starlight`

**Status**: Accepted (2026-10-12) — hfu さんがレビューして承認

### 決定

- 範囲限定版の PMTiles は **`bvmap-koicha-tokyo.pmtiles`**(`build/build.sh tokyo` の出力。中間の mbtiles も `bvmap-koicha-tokyo.mvt.mbtiles`)。
  PMTiles 内のメタデータの `name` も `bvmap-koicha-tokyo`(stars の `/catalog` はファイルのメタデータから名前を出す)。
- 将来の全国版は **`bvmap-koicha.pmtiles`**(source ID `bvmap-koicha`)。範囲限定版と全国版で ID を分け、全国版ができたら、
  スタイルの URL を差し替えるだけで済むようにする。
- スタイルは **`bvmap-koicha-starlight.json`**(stars では `/style/bvmap-koicha-starlight`)。
- stars の既存名(`bvmap`、`bvmap-starlight`)とは衝突しない。

### 理由

- stars では PMTiles のファイル名がそのまま source ID になる(D10)。`tokyo` のような汎用名は、他のデータと紛れる。

### 保留事項

- `chashaku/viewer/` の置き場所(`build/viewer/` へ移すか)と、`results/tiles_mvt.csv` の改名は、後回し(hfu さんの判断、2026-10-12)。

---

## D12: Martin での MLT 配信 — ローカルの Martin 1.8.2 で確認。本番(stars)は未反映

**Status**: Accepted (2026-10-12)

### 経緯

hfu さんの指示で、stars への反映と MLT 配信の確認に進んだ。stars の運用規則(`hfu/stars` の CLAUDE.md)は、本番への変更の前に計画を示すことを求める。
本番の確認は、`ssh spacex.optgeo.org` が **Cloudflare Access のブラウザ認証**を要求し、こちらでは認証を代行できないため、**本番には接続できなかった**
(接続は事前確認の1回のみで、何も変更していない)。そこで、先にローカルの Martin で確認した。

### ローカルでの確認(Martin 1.8.2 = `~/.cargo/bin/martin`。本番は 1.14.0)

- `martin <dir>` に `bvmap-koicha-tokyo.pmtiles` を置くだけで認識される。`/catalog` の `content_type` は **`application/vnd.maplibre-tile`**(MLT として認識)。
- タイル(`/bvmap-koicha-tokyo/{z}/{x}/{y}`)は、`mlt convert` の出力と**バイト単位で一致**(`Content-Encoding` なし。タイル圧縮が「なし」のため)。
- TileJSON 経由(`"url": "http://127.0.0.1:3010/bvmap-koicha-tokyo"`)で、bvmap-koicha-starlight が z4, 9, 13, 15, 16 を描画した。エラーなし。

### 見つけた不具合と直し方

1. **`mlt convert` が PMTiles のメタデータに `tiles: []`・`bounds`・`tilejson` などを書き込み、Martin 1.8.2 が TileJSON にもう一度展開するため、キーが重複**
   (`"tiles":[url]` のあとに `"tiles":[]`)。後勝ちで `tiles` が空になり、MapLibre は何も読まなかった。
   → `build/build.sh` が `pmtiles edit --metadata` で、メタデータを `name / description / attribution / version / vector_layers` だけに整理する。
   (ヘッダーの tile type 6 とタイル圧縮は変わらない。1.14.0 で同じ重複が起きるかは未確認だが、整理しておけば起きない。)
2. **`vector_layers` が、実際にタイルに入っている層だけだった**。スタイルは tokyo のタイルにない `Isbt`(等深線)も参照するので、MapLibre が警告を出す。
   → 元の bvmap のメタデータの `vector_layers`(24 層)を使い、`minzoom` を −1、`maxzoom` を 16 にする。

### 本番(stars)への反映手順(未実施、hfu さんの確認と認証が要る)

1. `bvmap-koicha-tokyo.pmtiles`(5.7MB)を `/home/stars/data/` へ転送する(新規ファイル。上書きや restart は不要。Martin のファイル監視で自動発見される)。
   転送前に `df -h /home/stars/data` で空きを確認する。
2. `https://stars.optgeo.org/bvmap-koicha-tokyo` と `/catalog` を、キャッシュを避ける `?cb=$(date +%s)` で確認する(Cloudflare のエッジに最大4時間キャッシュされる)。
   `content_type` が MLT か、`tiles` が1つか。
3. スタイル: `make_koicha_starlight.py --source-url https://stars.optgeo.org/bvmap-koicha-tokyo` で生成し、`hfu/stars/styles/` へ PR する
   (新しいスタイルファイルは Martin の restart が要る。その restart は別途確認する)。

---

## D13: bvmap-koicha-tokyo.pmtiles を stars に載せ、MLT 配信を確認した

**Status**: Accepted (2026-10-12) — hfu さんの指示(「B」: 認証後に実行)

### 実施したこと(本番への変更はこの1点のみ)

- hfu さんが Cloudflare Access の認証を済ませたあと、`ssh spacex.optgeo.org` で事前確認(空き 1.3T、Martin 1.14.0 稼働、同名ファイルなし)。
- `bvmap-koicha-tokyo.pmtiles`(5,704,019 B)を `/home/stars/data/` へ、拡張子の違う仮名(`.partial`)で転送し、**sha256 を照合**(`2306825581e86089…ade4`)してから `mv` で公開した
  (途中のファイルを Martin のファイル監視に拾わせないため)。**新規ファイルのみ。上書き・Martin の再起動・設定変更はしていない。**

### 確認したこと(`?cb=` でキャッシュを避け、`cf-cache-status: MISS`)

- `https://stars.optgeo.org/catalog` に `bvmap-koicha-tokyo` が現れた。`content_type` は **`application/vnd.maplibre-tile`**。
- TileJSON(`/bvmap-koicha-tokyo`)は `tiles` が1つ、`minzoom 3`、`maxzoom 16`、`bounds` が tokyo、`vector_layers` が 24 層。
  **重複キーの問題(D12)は、本番の Martin 1.14.0 では起きていない**(整理したメタデータのため。整理前の挙動は未確認)。
- タイル(15/29102/12905)は、ローカルの `mlt convert` 出力と**バイト単位で一致**。
- `make_koicha_starlight.py --source-url https://stars.optgeo.org/bvmap-koicha-tokyo` のスタイルを MapLibre GL JS 6.14.0 で読み、
  z5, 10, 14, 15, 16 を描画した。エラーなし。`glyphs`/`sprite`(stars 配信)も含めた注記・アイコンも出た。

### まだ

- スタイル `bvmap-koicha-starlight.json` は、まだ stars の `styles/` に載っていない(`hfu/stars` への PR と、新規スタイルファイルのための Martin の restart が要る。どちらも確認のうえ)。
  今は、ローカルで生成したスタイルの `source.url` を本番の TileJSON に向けて確認した段階。
- タイル圧縮は「なし」のまま(約 9% の余地、D9)。Cloudflare 経由の転送では、圧縮の扱いを別途確認する。

---

## D14: スタイルは hfu/stars へ PR(hfu/stars#14)。マージ・デプロイは stars の gatekeeper の手順に従う

**Status**: Accepted (2026-10-12) — hfu さんの指示

- [hfu/stars#14](https://github.com/hfu/stars/pull/14): `styles/bvmap-koicha-starlight.json` を**1ファイルだけ新規追加**(`config/martin.yaml` は変更しない)。
  ソースは `https://stars.optgeo.org/bvmap-koicha-tokyo`(範囲限定版。全国版 `bvmap-koicha` ができたら差し替える)。
- 生成: `make_koicha_starlight.py --source-url https://stars.optgeo.org/bvmap-koicha-tokyo`。stars の `bvmap-starlight.json` と、
  変換の入力(dwg7/bvmap `9068c809`)のレイヤー・ソースが同一であることを確認してから出した。
- **新規スタイルファイルなので、デプロイには Martin の restart が要る**(`hfu/stars` の CONTRIBUTING)。restart は stars 側の手順と、hfu さんの確認で行う。こちらからは行わない。
- PR の作成者とレビュー・マージの役割は分ける(CONTRIBUTING の先例どおり)。マージ後の stars 側の反映は、gatekeeper が行う。

---

## D15: bvmap-koicha-starlight と bvmap-koicha-tokyo が stars で公開された

**Status**: Accepted (2026-10-12)

- hfu さんが hfu/stars#14 をマージし(2026-10-12 12:03Z)、配置と Martin の再起動を行った。こちらからは何も変更していない。
- 再起動後に確認した(`?cb=` でキャッシュを避け、`cf-cache-status: MISS`):
  - `https://stars.optgeo.org/style/bvmap-koicha-starlight` が **200**。123 層、ソースは `https://stars.optgeo.org/bvmap-koicha-tokyo`(`encoding: "mlt"`)、
    `glyphs`/`sprite` は stars の既存 URL。**配信されたスタイルは、こちらで生成した JSON と完全に一致**。
  - `/catalog` の `styles` に `bvmap-koicha-starlight`、`tiles` に `bvmap-koicha-tokyo`。
  - 公開 URL のスタイルだけを MapLibre GL JS 6.14.0 に渡して、z5, 10, 14, 15, 16 を描画した(エラーなし、注記・アイコンも出る)。
- 公開 URL(いずれも範囲限定版 = 東京 139.73–139.80, 35.65–35.71):
  - スタイル: `https://stars.optgeo.org/style/bvmap-koicha-starlight`
  - タイル(TileJSON): `https://stars.optgeo.org/bvmap-koicha-tokyo`

### 次の課題(未着手)

- タイル圧縮(今は「なし」、約 9% の余地、D9)。
- 全国版 `bvmap-koicha`(D2/D11): 元データの取得量が約 17GB で、取得方法と量を hfu さんと相談してから。
- 間引き: タイルの大きさの目標値が決まれば判断できる(D6)。
- 後回しにした整理(`chashaku/viewer/` の置き場所、`tiles_mvt.csv` の改名、D11)。

---

## D16: タイル圧縮の見積もり — 当面は無圧縮のまま。MLT + gzip/brotli/zstd は Martin が未対応

**Status**: Accepted (2026-10-12) — 圧縮の話は概ね落ち着かせて次へ進む(hfu さん、2026-10-13)

### 訂正

D13 の直前に私が示した「同じタイル 15/29102/12905 で、MLT が 20,541 B、bvmap が gzip で 15,657 B」という比較は、**別の内容のタイル**
(koicha の z15 は bvmap の z16 の内容)どうしで、公平ではなかった。圧縮が配信サイズの主因だという言い方は誤りで、圧縮の効果は次のとおり約 1 割。

### 見積もり(`chashaku/compress_estimate.py`、5範囲の `hyp` 全 2,753 タイル。結果は `results/compress_*.csv|md`)

| MLT の設定 | 無圧縮 | gzip -9 | brotli -11 | zstd -19 |
|---|---|---|---|---|
| default(`mlt` 0.4.3) | 30.07MB(1.000) | 0.909 | 0.888 | 0.904 |
| `--no-fastpfor` | 1.103 | 0.876 | **0.818** | 0.867 |
| `--sort auto` | 0.985 | 0.894 | 0.874 | 0.890 |
| `--no-fsst`、`--no-shared-dict` | default と同じ | 同じ | 同じ | 同じ |

- 比は「default の無圧縮」に対する割合。z13 の最悪タイル(最大): 無圧縮 120.6KB → gzip 104.8KB → brotli 100.0KB(default)。`--no-fastpfor` + brotli で 89.2KB。
- FSST と共有辞書は、この 5 範囲のタイルでは効いていない(オフにしても同じバイト数)。
- FastPFOR は、無圧縮では 10% 効く(整数列を詰める)が、そのぶん後段の圧縮の余地が減る。**圧縮が掛かる配信なら `--no-fastpfor` のほうが約 8% 小さい**(brotli で 0.818 対 0.888)。
- 並べ替え(`--sort auto`)は約 1.5% で、描画順を変えうるので採らない(D4)。

### 配信側の事実(Martin 1.14.0 = stars 本番と同じ版を、公式リリースの macOS arm64 版で手元に取得・sha256 照合して確認)

- **`Format Mlt and compression Gzip/Brotli/Zstd are not yet supported`**。MLT の PMTiles は**タイル圧縮「なし」でしか読み込めず**、
  それ以外のファイルがあると、そのディレクトリの読み込みが警告で止まる(1.8.2 も同じ)。
  → **stars の `/home/stars/data` に、圧縮した MLT の PMTiles を置いてはいけない**(Martin の起動に失敗しうる)。
- 無圧縮のタイルは、`Accept-Encoding` に何を指定しても `Content-Encoding` なしで返る。stars 経由(Cloudflare)でも同じで、
  Cloudflare は `application/vnd.maplibre-tile` を既定では圧縮しない。
- `pmtiles.js` の既定の復号は none と gzip のみ(brotli/zstd は「未対応」エラー)。ただし stars では Martin 経由なので、直接は関係しない。

### 決定

- **当面は無圧縮のまま配信し、MLT の設定は default(FastPFOR あり)を使う。** 無圧縮が前提なら、default が最小(30.07MB 対 33.18MB)。
- 圧縮を効かせるなら、**配信経路での圧縮**になる。選択肢(いずれも未実施):
  1. Cloudflare の圧縮ルールで `application/vnd.maplibre-tile` を brotli/gzip にする(hfu さんの Cloudflare 設定。効果は約 1 割、`--no-fastpfor` を併用すると約 2 割弱)。
  2. Martin の上流で、MLT + タイル圧縮への対応を待つ・働きかける(上流の issue は探したが、見つけられなかった)。
  どちらを採るか、`--no-fastpfor` に切り替えるかは、配信経路が決まってから決める。
- `build/pack_compressed.py`(タイルを圧縮して PMTiles に詰め直す。ヘッダーのバイトを書き換える)は、将来の検証用に残す。**stars には載せない。**

### 保留事項

- `--no-fastpfor` のクライアント側の復号時間は測っていない(MapLibre GL JS の MLT デコーダーでは、どちらも標準のはず)。

---

## D17: 作業の進め方 — main に直接コミットする(ブランチ + PR は要らない)

**Status**: Accepted (2026-10-13) — hfu さんの指示(PR #1 のマージ後)

- このリポジトリ(dwg7/bvmap-koicha)では、**main に直接コミットして push する**。作業ごとのブランチと PR は作らない。
- 範囲: このリポジトリだけ。**他のリポジトリ(hfu/stars など)は、それぞれの作法に従う**(hfu/stars は PR + gatekeeper。D14)。
- 引き続き、対外的な変更(stars への反映、地理院からの大量取得、第三者のバイナリ・パッケージの取得)は、そのつど hfu さんの確認を得る。
  main に直接入れるので、コミット前に検証(テスト・`validate.py` など)を済ませる。
- 経緯: PR #1(計測・文書・スタイル・PMTiles のビルド、D1〜D14)は 2026-10-12 12:02Z にマージされた。
  マージ後の D15・D16 は、この運用に切り替えて、main に直接入れた。

---

## D18: 北海道版 `bvmap-koicha-hokkaido.pmtiles` を作った(領域は空間 ID `4/14/5`)

**Status**: Accepted (2026-10-24) — hfu さんの指示(領域・名前・取得の承認、2026-10-22)

### 決定

- **領域は空間 ID `4/14/5`(z4 のセル 1 つ。東経 135.0°〜157.5°、北緯 40.98°〜55.78°)。** 北海道全体と、千島列島、青森県の北部(下北など。青森市は南端の外)を含む。
  セルは下位ズームのセルと入れ子で境界が一致するので、**z4 以上の koicha タイルは、束ねる bvmap の子がすべてそろう(縁の欠けなし)**。
  D9 の範囲限定版(bbox)の「縁が欠ける」問題は、この方式では z4 以上で出ない。z3 は 4 分の 1 しか埋まらないので作らない(`minzoom 4`)。
  (最初に提案した `5/28/11` は、北海道と北東北の一部に絞れるが、千島を含まない。hfu さんが `4/14/5` を選んだ。)
- 名前は **`bvmap-koicha-hokkaido.pmtiles`**(D11 の規則 `bvmap-koicha-<範囲>`。説明欄に `spatial-ID cell 4/14/5` と明記)。
- 作り方: `build/build.sh hokkaido`(領域は `build/regions.tsv`)。`build/build_koicha.py` を、タイルを 1 つずつ読む**逐次処理**に書き直した
  (PMTiles の索引だけをメモリに置く `PMTilesIndex`、複数プロセス)。**tokyo の全 267 タイルで、書き直し前の出力と中身が完全に一致**することを確認してから使った。

### 取得(地理院)

- `pmtiles extract --bbox`(セルの外接矩形、z4〜16)、ドライランで 763,697 タイル・約 2.6GB を確認してから、2 スレッドで取得。
  **1 時間 0 分、2.6GB 転送、約 0.5〜0.9MB/s**(地理院側の応答が遅かった)。取得日時 2026-10-22T13:48:04Z(UTC)、
  `Last-Modified: Thu, 17 Sep 2026 07:32:00 GMT`、データは 2026年7月1日時点(tokyo と同じ版)。
- 外接矩形がセルの外にはみ出して取ったタイルは、ビルドでは使わない(セル内だけ)。

### 結果

- **768,230 タイル、z4〜z16、3.22GB(MLT、タイル圧縮なし。D16)。** sha256 `a91a906a9493d47a083a2da7a1965d3d1ff021080c2e7b63485c46748249cada`。
  `mlt convert --verify`(0.4.3)は全タイルで成功(重複排除で実体は 698,765 枚)。ビルドは約 1 時間台(取得を除く)。
- **見積もり(3.0〜3.2GB)の上端をわずかに超えた**(3.22GB)。見積もりは 5 範囲の比(bvmap の 1.19〜1.28 倍)で、実際は
  bvmap 2.5GB の 1.29 倍。低ズームと離島を含むぶん、比がやや上に出た。全国版の見積もり(約 20〜22GB)は、**約 21〜23GB** に直す。
- ズーム別(`chashaku/results/hokkaido_stats.md`、`build/stats_pmtiles.py`。保存サイズ=無圧縮の MLT):

| z | 枚数 | 合計 (MB) | 中央値 (KB) | p95 (KB) | 最大 (KB) | 最大のタイル |
|---|---|---|---|---|---|---|
| 4 | 1 | 0.0 | 10.5 | 10.5 | 10.5 | 4/14/5 |
| 5 | 2 | 0.0 | 2.5 | 18.7 | 18.7 | 5/28/11 |
| 6 | 5 | 0.0 | 1.8 | 18.0 | 18.0 | 6/57/23 |
| 7 | 12 | 0.1 | 3.7 | 20.1 | 20.1 | 7/114/47 |
| 8 | 36 | 0.6 | 5.3 | 62.0 | 62.0 | 8/229/94 |
| 9 | 126 | 2.4 | 0.7 | 78.3 | 129.1 | 9/462/187 |
| 10 | 352 | 7.9 | 2.1 | 82.8 | 129.5 | 10/918/378 |
| 11 | 1,356 | 11.8 | 0.1 | 32.3 | 52.5 | 11/1835/754 |
| 12 | 5,193 | 21.0 | 0.1 | 13.8 | 54.6 | 12/3656/1504 |
| 13 | 9,577 | 442.6 | 43.0 | 109.0 | 201.8 | 13/7348/3025 |
| 14 | 36,811 | 671.1 | 17.9 | 40.4 | 84.6 | 14/14701/5986 |
| 15 | 144,087 | 994.0 | 6.7 | 14.9 | 54.8 | 15/29256/12027 |
| 16 | 570,672 | 1072.6 | 1.8 | 4.1 | 17.6 | 16/58544/24104 |

全体: 768,230 枚(ディレクトリ展開後)、3.22GB(重複排除前の合計。ファイルは 3.22GB)

最悪の 8 枚:
  13/7348/3025  201.8 KB
  13/7347/3024  187.9 KB
  13/7344/3022  181.1 KB
  13/7348/3024  180.7 KB
  13/7349/3026  179.4 KB
  10/918/378  129.5 KB
  9/462/187  129.1 KB
  10/917/377  119.3 KB

- **最悪のタイルは z13 の日高山地**(13/7348/3025、東経 142.93°、北緯 42.51°)で **201.8KB**(MVT の生で 298KB)。
  **等高線 `Cntr` が 98%(5,992 地物)**。上位 5 枚は、すべて日高山地付近の z13 で 179〜202KB。
  **tokyo の最大 120.6KB を大きく超えた**(D6 で「5 範囲の外にもっと重いタイルがありうる」と書いたとおり)。D6 の判断(間引きは今は不要)は、
  この結果で**見直しの対象**になる(下記)。
- 低ズームの最大は z9 の 129.1KB(9/462/187、釧路湿原付近、`TpgphArea` 48%)と z10 の 129.5KB(10/918/378、日高、`Cntr` 85%)。
- 描画確認(MapLibre GL JS 6.14.0、ローカル、`pmtiles://` + Range): 札幌駅周辺 z15(建物が密に出る)、日高山地 z13、稚内 z11、
  函館 z13、択捉島 z8、下北 z11、北海道全体 z5 が、エラーなしで描画された。

### 保留事項

- **間引きの要否**(D6 の再検討): z13・z14 の等高線 `Cntr` が、山地のタイルの 85〜98%。タイルの大きさの目標値(上限)が決まれば、
  数値で程度を出せる(z13 の p95 は 109KB、最大 202KB)。**目標値を hfu さんに確認する。**
- stars への配置(`/home/stars/data/` に 3.2GB を置く。空きは 1.3T)は、まだ。配置の前に、hfu さんの確認(D10)。
  スタイルは `source.url` が `bvmap-koicha-tokyo` を指すので、北海道版を使うなら、別のスタイル(または差し替え)が要る。
- Martin 1.14.0 が 3.2GB・77 万タイルの PMTiles を問題なく扱うか(読み込み時間、メモリ)は、stars で確かめる。

---

## D19: 等高線は間引かない。タイルの大きさの上限は目安 256KB、最悪 512KB

**Status**: Accepted (2026-10-24) — hfu さんの指示

### 決定

- **等高線(`Cntr`)は間引かない。** 山地では地図の濃さそのものなので、サイズで削らない。
- **タイルの大きさの上限は、目安 256KB(MLT、無圧縮、保存サイズ)、最悪でも 512KB。** D6 の保留事項(目標値の確認)は、これで解決。
- 北海道版(D18)の最大は 201.8KB(13/7348/3025、日高山地、等高線 98%)で、**目安(256KB)の 79%、最悪値(512KB)の 39%** であり、**間引きは不要**。
  D6 の「間引きは今は要らない」は、北海道版でも成り立つ(D18 で「見直しの対象」とした点は、これで決着)。
- 目安を超えるタイルが出たら、そのときに対処を相談する(層ごとの占有率は `chashaku/results/layers_size.csv` と D18 の統計)。
  監視は `build/stats_pmtiles.py` の「最大」と「p95」で行う。全国版では、再度この上限と照らす。

### 確認した事実(複合ソース、本番と同じ Martin 1.14.0 をローカルで)

- `bvmap-koicha-hokkaido.pmtiles` と `bvmap-koicha-tokyo.pmtiles` を同じディレクトリに置くと、`/bvmap-koicha-hokkaido,bvmap-koicha-tokyo` の
  **複合ソースが 1 つの TileJSON(48 層は両方の `vector_layers` の合算、bounds は両方を覆う)で返り、両方のタイルが取れる**(北海道のタイルも東京のタイルも 200)。
- 範囲を空間 ID のセルで切れば、セルどうしは排他的(タイルが重ならない)なので、複合しても重複しない。tokyo(bbox で切った範囲限定版)は、
  北海道のセル `4/14/5` の外なので重ならない(ただし z3〜z12 の縁は欠ける。D9)。
- 重なるタイルの複合(同じ z/x/y が両方にある場合)は、未確認。MLT のタイルを結合できるかは分からないので、重ねないことを規則にする。

---

## D20: 名前の整理 — stars の公開名は規則化、リポジトリ内は `viewer/` と `tiles_mvt_only.csv`

**Status**: Accepted (2026-10-24) — hfu さんの指示(「配置についてはファイル名整理」→ stars の名前とリポジトリ内の両方)

### stars で公開する名前

| 種類 | 名前 | 備考 |
|---|---|---|
| 範囲ごとのタイル | `bvmap-koicha-<範囲>.pmtiles`(source ID は同名) | 現在: `bvmap-koicha-hokkaido`(空間 ID `4/14/5`)、`bvmap-koicha-tokyo`(bbox) |
| 全国版(将来) | `bvmap-koicha.pmtiles` | できたら、スタイルの `source.url` をこれ 1 つにして、範囲ごとのファイルを退役する |
| スタイル | `bvmap-koicha-starlight` | 1 つのスタイルを全範囲で使う(範囲ごとにスタイルを分けない) |

- **スタイルの `source.url` は、範囲ごとのタイルの Martin 複合ソース**: `https://stars.optgeo.org/bvmap-koicha-hokkaido,bvmap-koicha-tokyo`
  (`style/make_koicha_starlight.py` の既定値 `DEFAULT_URL`)。範囲を足したら、この列を増やして再生成し、stars のスタイルを更新する。
- **規則**: 範囲どうしは**重ならないこと**(空間 ID のセルで切れば排他的。D19)。重なるタイルの複合は未確認で、使わない。
- ローカルの確認: 本番と同じ Martin 1.14.0 に `bvmap-koicha-hokkaido` と `bvmap-koicha-tokyo` を載せ、複合ソースのスタイルを MapLibre GL JS で表示し、
  札幌 z14・z16、東京 z14・z16、宗谷岬 z10、択捉 z8 が、エラーなしで描画された。
- stars に載せる順序(この順で、配置は hfu さんの確認と Cloudflare Access の認証のもとで行う): ①`bvmap-koicha-hokkaido.pmtiles`(3.2GB)を `/home/stars/data/` へ
  (仮名で転送、sha256 照合、`mv`)→ ②`/catalog` と複合 TileJSON を `?cb=` で確認 → ③`hfu/stars` へ PR(`styles/bvmap-koicha-starlight.json` の既存ファイルの編集。
  **既存スタイルの編集なので Martin の restart は不要**、CONTRIBUTING の表)→ ④マージ後に stars 側が反映。

### リポジトリ内の名前

- **`chashaku/viewer/` → `viewer/`**(トップレベル)。計測とビルドの両方が使うため。npm パッケージの `node_modules` も一緒に移した(git の管理外)。
  URL は `http://127.0.0.1:8765/viewer/...`、起動は `python3 viewer/serve.py`、`style/validate.mjs` の参照先も直した。
- **`chashaku/results/tiles_mvt.csv` → `tiles_mvt_only.csv`**(MVT だけの中間ファイル。`tiles.csv` が MLT も入った最終版)。`measure.py` と `encode_mlt.py` を直した。
- D7〜D9、D11 などの過去の記述は、書いた時点の名前(`chashaku/viewer/`、`tiles_mvt.csv`)のまま残す(追記専用)。現在の名前は `CLAUDE.md` と各 README が正。
- D11 の保留事項(これらの整理)は、これで解決。

---

## D21: `bvmap-koicha-hokkaido.pmtiles` を stars に配置し、スタイル更新の PR を出した(hfu/stars#15)

**Status**: Accepted (2026-10-24) — hfu さんの指示(「進めよう」)と、Cloudflare Access の認証

### 本番への変更(この 1 点のみ。Martin の再起動・設定変更はしていない)

- `/home/stars/data/bvmap-koicha-hokkaido.pmtiles`(3,221,824,917 B)を新規追加。仮名 `.partial` で転送(約 5MB/s、約 10 分)→ リモートで sha256 を照合
  (`a91a906a9493d47a083a2da7a1965d3d1ff021080c2e7b63485c46748249cada`、ローカルと一致)→ 同名ファイルがないことを確認して `mv` で公開。事前の空きは 1.3T(事後も 1.3T)。

### 確認したこと(`?cb=` でキャッシュを避け、`cf-cache-status: MISS`)

- `/catalog` に `bvmap-koicha-hokkaido`(`application/vnd.maplibre-tile`)が、**Martin の再起動なしで**ファイル監視により出た(`bvmap-koicha-tokyo` も同様)。
- `/bvmap-koicha-hokkaido` の TileJSON: `minzoom 4`、`maxzoom 16`、bounds `135.0,40.979898,157.5,55.776573`、24 層。
- 複合 `/bvmap-koicha-hokkaido,bvmap-koicha-tokyo`: 200、`minzoom 3`、`maxzoom 16`、bounds は両方を覆い、48 層。
  タイル: 札幌 15/29256/12027(56,099 B)、東京 15/29102/12905(20,541 B)、最大の日高山地 13/7348/3025(**206,630 B** = 201.8KB。D18 の数字と一致)がいずれも 200。
- 稼働中の Martin の RSS は約 595MB(稼働 17 分時点)。**再起動したときの起動時間と、77 万タイルを読み込むメモリは未確認。**

### スタイルの更新(hfu/stars#15)

- [hfu/stars#15](https://github.com/hfu/stars/pull/15): `styles/bvmap-koicha-starlight.json` の `sources.bvmap.url` の 1 行だけを
  `https://stars.optgeo.org/bvmap-koicha-hokkaido,bvmap-koicha-tokyo` に変える(既存スタイルの編集なので Martin の restart は不要、CONTRIBUTING の表)。
  差分が 1 行だけであることを確認してから出した。マージと反映は stars 側の手順(gatekeeper)に従う。
- マージされるまで、公開中のスタイルは東京だけを指す(北海道は出ない)。マージ後は、`https://stars.optgeo.org/style/bvmap-koicha-starlight` を
  `?cb=` で確認し、北海道・東京の両方が描画されることを確かめる(こちらの仕事)。

### 保留事項

- stars の Martin を再起動するときの、読み込み時間とメモリ(3.2GB・77 万タイルの PMTiles)の確認。
- 全国版 `bvmap-koicha`(D2/D19: 約 21〜23GB の見積もり。セルごとに作る。取得量が大きいので、方法を相談してから)。

---

## D22: bvmap-koicha-starlight が、北海道と東京の複合ソースで公開された(hfu/stars#15)

**Status**: Accepted (2026-10-24)

### 経緯

- hfu さんの指示「あなたと stars で協調して実行してくれればいい」に従い、stars の gatekeeper セッション(`stars`)と、セッション間メッセージで連携した。
  stars から質問(配信・スタイルの方針、ズーム下限、容量の見通し)が来たので、D18〜D21 に基づいて回答した。
  マージと本番反映は、**stars 側が hfu さんに直接確認してから実施**した(こちらは本番を変更していない。中継した承認を確認として扱わない、という stars の規則に従った)。
- [hfu/stars#15](https://github.com/hfu/stars/pull/15) は 2026-10-24T06:58Z に squash マージ(`ad7dfb8`)。stars 側の記録: 既存ファイルの backup → マージ済みの版を配置
  → sha256 照合 → `?cb=` で確認 → backup 削除。**Martin の再起動なし、全断なし**(既存ファイルの編集のため)。

### こちらで独立に確認したこと(stars の報告を鵜呑みにせず、実際の状態を見た)

- `https://stars.optgeo.org/style/bvmap-koicha-starlight`(`?cb=`、200、`cf-cache-status: MISS`): `sources.bvmap.url` が
  `https://stars.optgeo.org/bvmap-koicha-hokkaido,bvmap-koicha-tokyo`、123 層で、**このリポジトリの `style/bvmap-koicha-starlight.json` と完全に一致**。
- 公開 URL のスタイルだけを MapLibre GL JS 6.14.0 に渡して描画(エラーなし):
  札幌 z14・z15・z16、東京 z14、宗谷岬 z11、択捉島(島内の座標 146.90E, 44.45N)z12、色丹島 z12、日高山地 z13。札幌駅周辺 z15 は建物が密に出る。
- stars の報告のうち、択捉島の一点(147.90E, 44.90N)で z13/z14/z16 が 204(空タイル)になる件は、**座標が海上だったため**で、データの欠落ではない
  (島内の座標では全ズームで 200)。こちらの確認でも、島内では地物が描画された。

### 結果

- bvmap-koicha は、**stars で北海道(`4/14/5`)と東京の 2 範囲をカバーする、公開されたタイルセット + スタイル**になった。
- stars の `docs/KNOWN_FACTS.md`(`5c2937e`)にも記録された。**注意**: そこにある「MLT PMTiles は無圧縮限定」は、こちらの申告(D16。Martin 1.14.0 をローカルで確認)であり、stars 側では未検証と明記されている。
- 範囲を足すときの手順: セルごとに `build/build.sh` で作る → `/home/stars/data` に置く(再起動なしで自動発見)→ `style/make_koicha_starlight.py` の `DEFAULT_URL` に ID を足して再生成 →
  hfu/stars へ既存スタイルの編集 PR(再起動は不要)。全国版 `bvmap-koicha` に統合したら、`source.url` を 1 つに戻す(D20)。

### 保留事項

- Martin 再起動時の、3.2GB・77 万タイルの読み込み時間とメモリ(D21)。
- 全国版(約 21〜23GB の見積もり、セルごとに作る)。取得量の大きさから、方法を相談してから進める。

---

## D23: テストサイトは GitHub Pages(`docs/`)で公開する — https://dwg7.unopengis.org/bvmap-koicha/

**Status**: Accepted (2026-10-27) — hfu さんの指示

### 背景

公開されていたのは stars のスタイルとタイルの URL だけで、人が見る場所は Martin のダッシュボードだけだった。
スタイル `https://stars.optgeo.org/style/bvmap-koicha-starlight` を単独で開いても、地図の初期位置が東京にも北海道にも当たらず、何も見えない。
ダッシュボードの検査画面は、`bvmap-koicha-hokkaido` の地図が空白で(原因は未確認)、スタイルのカードのプレビューも、地図として確認できなかった。
HTML のテストページは、depot(`/home/stars/data` の静的配信)ではなく、**このリポジトリの GitHub Pages** に置くべき、という hfu さんの判断。

### 決定

- `docs/index.html` を、GitHub Pages(`main` の `/docs`)で公開する。**URL: https://dwg7.unopengis.org/bvmap-koicha/**
  (組織のカスタムドメイン `dwg7.unopengis.org` の下。`https://dwg7.github.io/bvmap-koicha/` も同じ場所。plateau-juice と同じ形)。
  Pages の有効化はこの指示のもとで私が行った(`gh api`、`source: main /docs`)。
- ページの中身: 左に元の `bvmap-starlight`、右に `bvmap-koicha-starlight`(どちらも stars のスタイルの URL)を、**同じ位置・同じ表示ズーム**で連動して並べる(濃さの違いが見える)。
  - 位置は URL の **`#ズーム/緯度/経度`** で指定できる(MapLibre の `hash`)。例: `#15/43.0687/141.3540`(札幌駅)。
  - 「場所」のボタン: 札幌駅 z15、東京駅 z15、日高山地 z13(等高線が最も重い)、稚内 z11、択捉島 z12、釧路湿原 z9、北海道全体 z6。
  - 表示位置が bvmap-koicha の範囲外(北海道のセル `4/14/5` と東京の小矩形の外)のときは、警告を出す。
  - 「bvmap-koicha だけを表示」で単独表示。幅 700px 以下では上下に並べる。出典(国土地理院最適化ベクトルタイルを加工して作成)と、公式ではない旨を、ページとフッターに入れた。
- MapLibre GL JS 6.14.0 を `docs/vendor/maplibre-gl-6.14.0/`(ESM 3 ファイル + CSS + LICENSE、約 1.7MB)に**同梱**し、第三者の CDN に依存しない。`docs/.nojekyll` で Jekyll を無効にした。
- Martin のダッシュボード(`?tab=tiles&inspect=...#map=z/lat/lng`)は、位置を指定できるが、MLT のタイルの検査画面が空白だった。
  このページが、人が見る正式な確認場所になる。

### 確認したこと

- ローカル(`viewer/serve.py`)と、公開 URL(`https://dwg7.unopengis.org/bvmap-koicha/#15/43.0687/141.3540`)の両方で、左右とも描画された(エラーなし)。
  東京駅・日高山地へのボタン、範囲外(沖縄)の警告、スマホ幅(375px)の縦並びも確認した。
- 出典の欄(MapLibre の `<details open>`)は、読み込み後に閉じようとしても開き直すため、高さを抑える CSS(小さい文字、3 行)にした。全文はフッターにも常に出ている。

### 保留事項

- Pages は `https_enforced=false` のまま(`https://` では動く)。HTTPS の強制は、hfu さんの判断。
- ページは、stars のスタイルと、地理院の PMTiles を配信する stars に依存する。
- 範囲を足したら(D20)、「範囲外」の判定の座標と、場所のボタンを更新する。

