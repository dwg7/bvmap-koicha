# CLAUDE.md — bvmap-koicha 作業規則

このファイルは、dwg7/bvmap-koicha を担当する自分自身と将来のエージェントのための作業規則。
決めたことの理由は [DECISIONS.md](DECISIONS.md)、bvmap の中身は [docs/bvmap-anatomy.md](docs/bvmap-anatomy.md)、
計測の結果は [chashaku/REPORT.md](chashaku/REPORT.md)。応答は日本語(敬語)、OSM 等の英語圏向けの成果物は英語でよい。

## これは何か

dwg7(UN Smart Maps Group)の活動で、**国土地理院の公式な製品ではない**。bvmap(国土地理院最適化ベクトルタイル)を素材に、
建築物がたっぷり入った濃い地図のタイルセット(PMTiles)を作る。名前は濃茶(薄茶と同じ抹茶を、少ない湯で濃く点てたもの)。
**比喩は茶に統一し、酒の比喩は使わない。** 計測のサブプロジェクトは chashaku(茶杓)。

## 段階と、今やらないこと

1. **計測(chashaku)** 済み(D6: maxzoom 16、D7: 描画確認)。作る前に測る。
2. **スタイル bvmap-koicha-starlight**(D8)と、**tokyo の範囲限定 PMTiles**(D9、`build/build.sh tokyo`)作成済み。← 今ここ。配信は stars(hfu/stars)で行う(D10)。`bvmap-koicha-tokyo.pmtiles` は stars に載せて MLT 配信を確認済み(D13)。スタイル bvmap-koicha-starlight も stars で公開済み(hfu/stars#14、D14/D15)。タイル圧縮は D16 で一旦結論(当面は無圧縮。Martin が MLT + gzip/brotli/zstd 未対応なので、圧縮した MLT の PMTiles を stars の data に置かない)。**北海道版 `bvmap-koicha-hokkaido.pmtiles`(空間 ID `4/14/5`、768,230 タイル、3.22GB)を作成済み(D18。stars には未配置)。** 等高線は間引かない。タイルの上限は目安 256KB・最悪 512KB(D19。北海道版の最大は 202KB で収まる)。名前の規則は D20(スタイルは複合ソース `bvmap-koicha-hokkaido,bvmap-koicha-tokyo`)。次は、北海道版の stars への配置(hfu さんの確認と Cloudflare Access の認証が要る)と、スタイルの更新 PR(hfu/stars)。stars への反映は、そのつど hfu さんの確認を得てから(本番への ssh は Cloudflare Access の認証を hfu さんが済ませる)。

計測の結果を見る前にやらない: 全国のタイルセットの生成、スタイルの作成、地物の簡略化・総描。
dwg7/evergreen の言葉では、これは Cartographer ではなく Library 側のタイルセットである。

## bvmap について確かめてあること(重要な判断の前には実タイルで再確認する)

- 配信: `https://cyberjapandata.gsi.go.jp/xyz/optimal_bvmap-v1/optimal_bvmap-v1.pmtiles`(約 17GB)。minzoom 4、maxzoom 16。
- ズームは地理院タイル(ラスター)より一段小さい(bvmap z11 = ラスター z12)。tile extent は z8〜16 が 4096、z4〜7 が 16384。
- **z17 の情報は z16 のタイルに入っている(二枚重ね)。** 見分けは `vt_flag17`(なし/0: z16 まで、1: 両方、2: z17 以上だけ)。
  キーがあるのは Anno, RailCL, RdCL, TpgphArea, WStrL の5層で、z16 のタイルだけ。RdEdg, RdCompt, RailTrCL, StrctLine は
  スタイルで `minzoom: 17`(データは z16 に入っている)。
- 建築物(BldA)は z14 から入り、`vt_flag17` で切り替えない。同じ範囲で z15 の建築物は z16 の、都市部で 1/20〜1/25、郊外(帯広)で約 1/70 しかない。
- 利用は国土地理院コンテンツ利用規約。加工したものを配るときは「国土地理院最適化ベクトルタイルを加工して作成」と明記する。
- データ更新は 2026年7月1日時点(2026-09-17 公開)。取得日や版は `chashaku/results/provenance.txt` に記録。

## 守ること

- **地理院のサーバーに負荷をかけない。** 必要な範囲だけを `pmtiles extract --bbox` で取り、`data/` に保存して使い回す。
  **必ず `--dry-run` でタイル数を確かめてから**取得する(`chashaku/fetch.sh` が強制する)。スクリプトは bash で書く
  (zsh は変数を単語分割しない)。理由と事故の記録は DECISIONS D5。
- **地物の中身を勝手に変えない。** 計測の段階で許すのは、束ねる・捨てる・エンコーディングを変える、だけ。
- **使ったツールの版を記録する。** MLT のエンコーダーは開発が速い。現在は Rust `mlt` CLI 0.4.3(DECISIONS D4)。
  結果を引用するときは版を添える。
- 第三者のバイナリ・パッケージは、取得前にユーザーの許可を得る。取得したらチェックサムを照合する(`tools/`)。
- 仕様があいまいなところ、判断が分かれそうなところは、推測で埋めずにユーザーに聞く。
- 決定は DECISIONS.md に**追記**する(消さない)。誤りが分かったら新しいエントリで訂正する。
- **main に直接コミットする**(ブランチ・PR は要らない、D17)。ただし他のリポジトリ(hfu/stars など)は、その作法に従う。
- git の author メールは `18297+hfu@users.noreply.github.com`(ID 付き)。

## 構成

- `chashaku/lib/` — PMTiles v3 リーダーと、MVT の無損失コーデック(標準ライブラリのみ。`python3 -I` で動かす)
- `chashaku/{anatomy,measure,validate,encode_mlt,layer_probe,summarize,compare}.py` — 計測の各段。順序は `run_all.sh`
- `chashaku/areas.tsv` — 測る場所(名前、経度緯度の範囲)
- `chashaku/results/` — CSV と Markdown の集計。`data/`(抽出、変種タイル、MLT 出力)は git の管理外で、再生成できる
- `tools/` — `mlt` の取得・検証(バイナリはコミットしない)
- `build/` — 範囲限定の bvmap-koicha PMTiles のビルド(`build.sh`、`build_koicha.py` は逐次処理、`regions.tsv` は空間 ID の領域、`stats_pmtiles.py`)
- `style/` — bvmap-koicha-starlight(`make_koicha_starlight.py` の生成物。手で編集しない)と、上流のスナップショット `upstream/`
- `viewer/` — 描画確認(`index.html`: 素のスタイル、`starlight.html`: starlight)

## 計測の用語

- `bvmap`(基準)、`hyp`(仮説: z+1 を束ね、z15 は flag17=2 と z17 専用層を捨て、z16 は flag17=0 を捨てる)、
  `contra`(対立案: maxzoom 15、extent 2倍)。定義は DECISIONS D3。
- 統計は中央値、95パーセンタイル(nearest-rank)、最大値。平均は使わない。最悪のタイルを必ず示す。
- 「complete」は、束ねる子がそろったタイル。縁のタイルは小さくなるので、主な統計は complete で出す。
