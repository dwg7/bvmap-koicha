# bvmap-koicha

> **これは dwg7(UN Smart Maps Group)の活動であり、国土地理院の公式な製品・サービスではありません。**
> This is an activity of dwg7 (UN Smart Maps Group). It is not an official product or service of the Geospatial Information Authority of Japan (GSI).

国土地理院の最適化ベクトルタイル(bvmap)を素材にして、**建築物がたっぷり入った、濃い地図**のためのタイルセット(PMTiles)を作るプロジェクトです。
計測(chashaku)を終え、東京の範囲限定版を stars で公開しています(スタイル `https://stars.optgeo.org/style/bvmap-koicha-starlight`、タイル `https://stars.optgeo.org/bvmap-koicha-tokyo` と `https://stars.optgeo.org/bvmap-koicha-hokkaido`。D15/D21)。全国版はこれからです。

*koicha — thick tea. The same matcha as usucha (thin tea), made with less water.*
*bvmap-koicha takes the same GSI data as bvmap and brews it thicker: more buildings per tile, the same ingredients.*

## 名前の由来

濃茶(こいちゃ)は、薄茶と同じ抹茶を、少ない湯で濃く点てたものです。bvmap-koicha も、bvmap と同じ地理院のデータを、より濃く仕立てます。
違うのは濃さだけです。計測の部分は **chashaku**(茶杓、抹茶を量る匙)と呼びます。

## 何を解こうとしているか

bvmap は、公開当時の帯域とブラウザの制約に合わせてタイルの大きさを最適化したため、多くのウェブ地図と同じように、建築物が少なく見えます
(実測では、建築物は z14 から入り始め、z15 の建築物は、同じ範囲の z16 の、都市部で 1/20〜1/25、郊外で約 1/70 です)。一方、地形図の利用者は、建築物がたっぷり入った濃い地図を好みます。
この隙間を次の二つで埋められるかを、まず測ります。

1. エンコーディングに MLT(MapLibre Tile)を使い、タイルを小さくする。
2. タイルのズームレベルを、おおむね一段上にずらす(bvmap の z+1 の内容を、z で見せる)。

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
