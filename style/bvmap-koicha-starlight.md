# bvmap-koicha-starlight

[dwg7/bvmap](https://github.com/dwg7/bvmap) の `bvmap-starlight`(低彩度・明るめ・銀灰色寄り)の**ズームの値を一段ずらした**スタイル。
bvmap-koicha のタイル(z は bvmap の z+1 の内容を持つ。DECISIONS D3/D6)に合わせる。dwg7 の活動であり、国土地理院の公式な製品ではない。

## 作り方

`style/bvmap-koicha-starlight.json` は手で編集しない。`style/make_koicha_starlight.py` が
`style/upstream/bvmap-starlight.json`(dwg7/bvmap の `9068c809`、2026-10-06 のスナップショット)から生成する。

```bash
python3 -I style/make_koicha_starlight.py --source-url pmtiles://https://example.org/bvmap-koicha.pmtiles
node style/validate.mjs style/bvmap-koicha-starlight.json   # 要: npm ci --prefix chashaku/viewer
```

変えるのは次だけ(配色・構造・フォント・スプライトは触らない):

| 対象 | 変更 |
|---|---|
| レイヤーの `minzoom` / `maxzoom`(72 / 66 か所) | −1 |
| `["step", ["zoom"], …]` の停止値(47 式) | −1(例: `vt_flag17` の切り替え 17 → 16) |
| `["interpolate…", _, ["zoom"], …]` の停止値(122 式) | −1(線幅・文字サイズ・不透明度も) |
| ソース `bvmap` | `encoding: "mlt"`、`minzoom 3`、`maxzoom 16`、`url` は引数(既定は置き換え用の仮の値) |
| `attribution` | 「国土地理院最適化ベクトルタイルを加工して作成」+ スプライトの改変の表記 |

スクリプトは、`["zoom"]` が `step` / `interpolate` 以外に現れたら止まる(上流が新しい書き方を使い始めたときの検知)。

## 確かめたこと

- `@maplibre/maplibre-gl-style-spec` のバリデーションを通る(上流・生成物とも 0 エラー)。
- MapLibre GL JS 6.14.0 で、tokyo の `hyp` タイルに対して描画できた(`chashaku/viewer/starlight.html`)。左は上流の bvmap-starlight(bvmap のタイル、z+1)、
  右は本スタイル(`hyp`、z)。z15・z16 で、道路・建物・鉄道・注記・アイコンが出て、ブラウザのエラーはなかった。z16 では道路縁や軌道も出る。

## まだ確かめていないこと

- **z3〜z12 の見た目。** タイルは z13〜z16 しか作っていない(計測の範囲)。z ≤ 14 は bvmap の z+1 を束ねる設計だが、
  z4〜z7 の bvmap は extent 16384 なので、束ねると 32768 になる。MLT で扱えるかは未確認。
- 上流との画素単位の一致(縮尺が違うので比べられない)。注記の重なり・配置の質は目視のみ。
- `source.url`(配信先)は未定。`glyphs` と `sprite` は上流のまま `stars.optgeo.org` を指す(hfu/stars の配信)。
- 上流が更新されたら、スナップショットを差し替えて再生成する(`style/upstream/README.md`)。
