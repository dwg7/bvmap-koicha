# bvmap-koicha

> **これは dwg7(UN Smart Maps Group)の活動であり、国土地理院の公式な製品・サービスではありません。**
> This is an activity of dwg7 (UN Smart Maps Group). It is not an official product or service of the Geospatial Information Authority of Japan (GSI).

国土地理院の最適化ベクトルタイル(bvmap)を素材にして、**建築物がたっぷり入った、濃い地図**のためのタイルセット(PMTiles)を作るプロジェクトです。
計測(chashaku)を終え、東京の範囲限定版を stars で公開しています(スタイル `https://stars.optgeo.org/style/bvmap-koicha-starlight`、タイル `https://stars.optgeo.org/bvmap-koicha-tokyo` と `https://stars.optgeo.org/bvmap-koicha-hokkaido`。D15/D21)。スタイルは北海道と東京の複合ソースで公開済みです(D22)。全国版はこれからです。

*koicha — thick tea. The same matcha as usucha (thin tea), made with less water.*
*bvmap-koicha takes the same GSI data as bvmap and brews it thicker: more buildings per tile, the same ingredients.*

**テストページ(地図で見られます): https://dwg7.unopengis.org/bvmap-koicha/** — 左が元の bvmap-starlight、右が bvmap-koicha-starlight。位置は `#ズーム/緯度/経度` で指定できます(例: [札幌駅 z15](https://dwg7.unopengis.org/bvmap-koicha/#15/43.0687/141.3540))。

## 名前の由来

濃茶(こいちゃ)は、薄茶と同じ抹茶を、少ない湯で濃く点てたものです。bvmap-koicha も、bvmap と同じ地理院のデータを、より濃く仕立てます。
違うのは濃さだけです。計測の部分は **chashaku**(茶杓、抹茶を量る匙)と呼びます。

## 何をやろうとしているか — 低く飛ぶか、高く飛ぶか

地図を見る「高さ」を、ズームレベルにたとえます。ズームの数字が大きいほど地面に近く(低く飛ぶ)、小さいほど遠く(高く飛ぶ)なります。

**これまで(bvmap)は、低く飛ばないと建物が見えませんでした。**
ベクトルタイルは、1 枚の大きさに制約があります(公開当時の帯域とブラウザの制約に合わせて、最適化されています)。
建築物をたっぷり入れるとタイルが重くなるので、建築物がしっかり入るのは、いちばん近づいた z16 だけです。
一段高い z15 では、同じ場所の建築物が、東京で約 4,800 棟、z16 の約 1/20(大阪で 1/25、帯広郊外で 1/70)しか入っていません。

**bvmap-koicha は、一段高い所から、同じ濃さを見せます。**
bvmap の z+1(一段近い所)の内容を、z(一段遠い所)で見せます。つまり、z15 で、bvmap の z16 の内容(建築物がたっぷり)が見えます。

| 東京(測定範囲)の同じ表示ズーム | bvmap | bvmap-koicha |
|---|---|---|
| z15 の建築物(地物数、縁の重複を含む) | 約 4,800 | 約 95,000(約 20 倍) |
| z15 のタイル(中央値) | 14.5KB(MVT、gzip) | 38.5KB(MLT、gzip) |
| z15 のタイル(最大) | 17.4KB | 67.9KB |

**高く飛べるようになったのは、MLT(MapLibre Tile)のおかげです。ただし、MLT だけではありません。**
- MLT は、同じ内容を MVT より小さく符号化します(測定では、都市部で 15〜27% 小さい)。
- 一段高く飛ぶと、1 枚のタイルが覆う面積が 4 倍になるので、中身は約 4 倍になります。MLT で小さくなっても、同じ表示ズームのタイルは、bvmap の 2.7〜3.7 倍に大きくなります(都市の z13・z15)。
- それでも、タイルの大きさの上限を**目安 256KB、最悪でも 512KB** と決めて(DECISIONS D19)、その中に収まることを、実際のデータで確かめました。
  北海道全体(約 77 万枚)で、最大のタイルは 202KB(日高山地の z13、等高線が 98%)です。
- つまり、「MLT による縮小」と「上限の引き上げ」の両方で、同じタイルの重さの感覚のまま、一段高い所から濃い地図を見せられます。

*English: bvmap kept buildings out of coarser zooms because vector tiles had to stay small ("flying low"). bvmap-koicha shows bvmap's z+1 content at z ("flying one level higher"): MLT encodes the same data 15–27% smaller in cities (measured), and the tile-size budget is set to 256 KB (512 KB at worst). Hokkaido's largest tile is 202 KB.*

**MLT について、技術的に正確に言うと**(詳しくは [DECISIONS](DECISIONS.md) の D4・D7・D16):
- 配信しているタイルは、本物の MLT です(Content-Type `application/vnd.maplibre-tile`、PMTiles の tile type 6)。公式の `mlt` ツール(0.4.3)で作り、`--verify` で「復号して元の MVT と一致する」ことを全タイルで確かめています。
- 元の bvmap は MVT なので、koicha は「MVT を束ねて MLT に変換」したものです(MLT を最初から作ったわけではありません)。
- MLT の仕様と実装は発展中です。結果を引用するときは、エンコーダーの版(0.4.3)を添えてください。
- 描画は MapLibre GL JS 6.14.0 で確認しています(スタイルで `encoding: "mlt"` を指定)。MLT に対応しているクライアントが必要です。MapLibre Native などは未確認です。
- いまのサーバー(Martin 1.14.0)は、MLT の PMTiles を、タイル圧縮なしでしか扱えません(gzip・brotli・zstd は未対応)。

実際に比べるには、[テストページ](https://dwg7.unopengis.org/bvmap-koicha/#15/43.0687/141.3540)を開いてください。左が bvmap、右が bvmap-koicha で、同じ位置・同じズームです。
計測の詳細は [chashaku/REPORT.md](chashaku/REPORT.md)、決めたことは [DECISIONS.md](DECISIONS.md) にあります。

この仕組みを、次の二つで実現しています。

1. エンコーディングに MLT(MapLibre Tile)を使い、タイルを小さくする。
2. タイルのズームレベルを、一段ずらす(bvmap の z+1 の内容を、z で見せる)。

## 今あるもの

| | |
|---|---|
| [chashaku/REPORT.md](chashaku/REPORT.md) | 計測の結果と、maxzoom・間引きへの答え |
| [docs/bvmap-anatomy.md](docs/bvmap-anatomy.md) | bvmap タイルの中身(層、`vt_flag17`、extent、建築物のズーム) |
| [DECISIONS.md](DECISIONS.md) | 決めたことと、その理由(追記専用) |
| [CLAUDE.md](CLAUDE.md) | 作業規則(人とエージェント向け) |
| [style/bvmap-koicha-starlight.md](style/bvmap-koicha-starlight.md) | bvmap-starlight のズーム値を一段ずらしたスタイル |
| `chashaku/` | 計測のコード(Python 標準ライブラリのみ)と `results/`(CSV) |
| `build/` | 範囲限定の PMTiles のビルド(tokyo は bbox、hokkaido は空間 ID `4/14/5`) |
| `viewer/` | 描画確認用の MapLibre GL JS ページ(npm パッケージは `node_modules`、git の管理外) |
| `tools/` | 取得・検証用スクリプト(バイナリはコミットしない) |

再現: `chashaku/run_all.sh`(取得は `chashaku/fetch.sh`。地理院のサーバーには必要な範囲だけ、ドライランで確認してから取りに行きます)。

## 出典・ライセンス

- 素材は国土地理院最適化ベクトルタイル(https://github.com/gsi-cyberjapan/optimal_bvmap)で、
  [国土地理院コンテンツ利用規約](https://www.gsi.go.jp/kikakuchousei/kikakuchousei40182.html)に従って利用しています。
  このプロジェクトが将来配るタイルには「国土地理院最適化ベクトルタイルを加工して作成」と明記します。
- このリポジトリのコードと文書は CC0 1.0(`LICENSE`)。bvmap のタイルやその抽出物は含みません(`data/` は git の管理外)。
