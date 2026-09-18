# trial_dbt_charts

[dbt Charts](https://github.com/dbt-labs/dbt-charts)（`dct`）をローカルで試すリポジトリ。
e-Stat の統計データを dbt + DuckDB でモデル化し、dbt Charts でダッシュボードにする。

## 使用データ

- 小売物価統計調査「10大費目別消費者物価地域差指数（全国平均＝100）」（統計表ID: `0003441258`）
- 出典：政府統計の総合窓口（e-Stat）（https://www.e-stat.go.jp/）、総務省「小売物価統計調査」をもとに加工して作成

## セットアップ

```bash
uv tool install dbt-charts   # dct CLI
uv sync                      # dbt-core / dbt-duckdb
export ESTAT_API_APPID="あなたのAppID"   # または .env に記載
```

## 実行手順

```bash
# 1. e-Stat からデータ取得（data/0003441258/ に保存）
uv run python scripts/estat/download_data.py 0003441258

# 2. dbt でモデル構築（target/dev.duckdb）
uv run dbt build --profiles-dir .

# 3. ダッシュボード
dct validate
dct serve
dct render charts/price_index.yml --format html

# 4. GitHub Pages 用の静的サイト（site/）
./scripts/build_site.sh
```

静的 HTML ではフィルターが動かない（初期値のスナップショットになる）ため、
GitHub Pages には主要 5 県（費目は総合）のページを個別に出力して載せている。
main への push で `.github/workflows/deploy.yml` がビルドとデプロイを行う。

## 構成

```
data/            e-Stat から取得した CSV
scripts/estat/   e-Stat API スクリプト（japan-info-dashboard から流用）
models/          dbt モデル（staging → marts）
charts/          dbt Charts のボード定義（YAML）
dbt_charts.yml   dbt Charts のソース設定（dbt profile を利用）
```
