# dbt Charts と Evidence の比較

- 対象：dbt Charts 0.8.0（このリポジトリ）と Evidence 40.x（[japan-info-dashboard](https://github.com/Zaiwa-linus/japan-info-dashboard)）
- 実施日：2026-09-18
- 題材：e-Stat の消費者物価地域差指数（0003441258）を dbt + DuckDB でモデル化し、1枚のダッシュボードにした
- 公開先：https://zaiwa-linus.github.io/trial_dbt_charts/

## 結論

- **社内・手元で使う、dbt と一体で管理するダッシュボード**なら dbt Charts が向いている。YAML が短く、`ref()` で dbt モデルに直結し、CI で検査できる。
- **GitHub Pages などの静的配信で、閲覧者に操作させたい**なら Evidence が向いている。dbt Charts の静的 HTML ではフィルターが動かない。

## 閲覧者から見た違い

| 観点 | dbt Charts | Evidence |
|---|---|---|
| 静的配信でのフィルター | **動かない**。初期値で描いたスナップショットになる（`dct serve` のときだけ操作できる） | **動く**。mart を parquet で配り、ブラウザ内の DuckDB（WASM）でクエリを実行する |
| 見た目 | 何も調整しなくても整っている。KPI・表の色分け・凡例などが揃っている | 標準の部品は素朴。KPI カードや地図は自作の Svelte 部品で補っていた |
| 読み込み | 1ページ約870KB（うちフォントが約620KB）。データは描画済みの SVG | 最初にデータ（parquet）と WASM を読み込む |
| ページ構成 | 1つのボード＝1ページ。複数のボードは `dct serve` でパンくずから行き来する | Markdown のページ階層がそのままサイドバーになる |

## 作成者から見た違い

| 観点 | dbt Charts | Evidence |
|---|---|---|
| 書き方 | YAML（queries / charts / variables / rows）に SQL を埋め込む | Markdown に SQL ブロックと Svelte 部品を書く |
| 実装量 | ボード1枚（フィルター・KPI・推移・表・ランキング）で171行。部品の自作は不要 | ページは1枚あたり約110〜270行。それに加えて、KPI カードや地図の自作部品が計464行 |
| dbt との連携 | ボードの SQL で `{{ ref('mart_...') }}` が使える。接続も dbt profile をそのまま使う | 別のデータ取り込み層（`sources/*.sql` の `select * from mart_...`）を経由する。`ref()` は使えず、DuckDB ファイルのパスを直接指定する |
| 検査 | `dct validate` が YAML・参照・列を検査する（DB 接続なしで動く）。`dct impact <列>` で影響を受けるボードがわかる | `evidence build:strict` でビルド時のエラーを検出する |
| 環境 | Python だけ（`uv tool install dbt-charts`）。CI は約1分 | Node / npm と、データ源ごとのプラグインが必要 |
| 成熟度 | ベータ（pre-1.0）。ドキュメントと実装の食い違いがある（下記） | 安定している。情報も多い |

## dbt Charts で詰まった点

1. **静的 HTML ではフィルターが動かない**。ソースのコメントにも「状態を表示するだけで、何も接続されていない」とある。今回は主要5県を別ページとして出力して代わりにした。全組み合わせ（47都道府県 × 12費目 = 564ページ）は約490MB・約47分かかる見込みで、現実的ではない。
2. **select に勝手に「All」が付く**。ドキュメントには「"All" は追加しない」とあるが、`required: true` を付けないと未選択の選択肢が出る。未選択のときは `{{ filter() }}` が条件なしになるため、KPI が複数行を受け取ってエラー（`ERR-KPI-MULTIROW`）になった。
3. **日本語のラベルが切れる**。線の右端の凡例ラベルは「…」になり、横棒グラフの地域名も切れた。通常の凡例に切り替える、縦棒にしてラベルを90度回転させる、という方法で回避した。
4. **組み込みの書式 `delta` は整数に丸める**。+0.2 が「+0」と表示されたので、`"+,.1f"` を明示した。
5. **`{{ filter() }}` を使うと、dbt モデルに対する列の検査が効かなくなる**（`WARN-DBT-QUERY-COLUMNS-INDETERMINATE` が出る）。
6. **公式の hosted 版（dbt Charts Cloud）は DuckDB ファイルを読めない**。BigQuery・Snowflake・Postgres・Redshift か、コミットした CSV・Parquet が必要になる。

## 良かった点

- dbt モデルの隣に `charts/` を置くだけで、`ref()` と profile をそのまま使える。モデルとダッシュボードの変更を1つの PR にまとめられる。
- KPI（前年差つき）・表の色分け・レイアウトが YAML の数行で書ける。見た目の調整がほとんど要らない。
- `dct validate` はデータベースにつながずに動くので、書く → 検査する、の繰り返しが速い。
- `dct render` で PNG・PDF・HTML を出せるので、レポートや画像の共有に使いやすい。
