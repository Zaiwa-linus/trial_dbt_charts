#!/usr/bin/env bash
# GitHub Pages 用の静的サイトを site/ に生成する。
# 静的 HTML ではフィルターが動かないため、主要な都道府県ごとに 1 ページずつ出力する。
set -euo pipefail

cd "$(dirname "$0")/.."

PREFECTURES=(東京都 大阪府 愛知県 北海道 沖縄県)
BOARD=charts/price_index.yml
OUT=site

rm -rf "$OUT"
mkdir -p "$OUT"

links=""
for i in "${!PREFECTURES[@]}"; do
  pref="${PREFECTURES[$i]}"
  page="pref_$((i + 1)).html"
  echo "rendering ${pref} -> ${page}"
  dct render "$BOARD" --var prefecture="$pref" --var category=総合 --format html -o "$OUT/$page" >/dev/null
  links+="      <li><a href=\"${page}\">${pref}</a></li>"$'\n'
done

cat > "$OUT/index.html" <<HTML
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>都道府県別 物価水準</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 640px; margin: 48px auto; padding: 0 16px; color: #222; background: #fff; }
    li { margin: 8px 0; }
    small { color: #666; }
  </style>
</head>
<body>
  <h1>都道府県別 物価水準（消費者物価地域差指数）</h1>
  <p>dbt Charts で作成したダッシュボードの静的版です。費目は「総合」で固定しています。</p>
  <ul>
${links}  </ul>
  <p><small>出典：政府統計の総合窓口（e-Stat）、総務省「小売物価統計調査」をもとに加工して作成</small></p>
</body>
</html>
HTML

echo "done: $OUT/"
