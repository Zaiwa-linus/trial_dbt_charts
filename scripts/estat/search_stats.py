"""e-Stat API で統計表を検索し、一覧表示するスクリプト。

使い方:
  python scripts/estat/search_stats.py "人口"
  python scripts/estat/search_stats.py "GDP" --field 07        # 統計分野で絞り込み
  python scripts/estat/search_stats.py "労働" --limit 20       # 取得件数指定
  python scripts/estat/search_stats.py --list-fields            # 統計分野コード一覧を表示
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse

BASE_URL = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsList"

# 統計分野コード（大分類）
STATS_FIELDS = {
    "01": "人口・世帯",
    "02": "自然環境",
    "03": "経済基盤構造",
    "04": "政府・財政・金融",
    "05": "農林水産業",
    "06": "鉱工業",
    "07": "商業・サービス業",
    "08": "企業活動",
    "09": "住宅・土地・建設",
    "10": "エネルギー・水",
    "11": "運輸・観光",
    "12": "情報通信・科学技術",
    "13": "教育・文化・スポーツ・生活",
    "14": "行財政",
    "15": "司法・安全・環境",
    "16": "社会保障・衛生",
    "17": "国際",
    "18": "その他",
}


def get_app_id() -> str:
    app_id = os.environ.get("ESTAT_API_APPID")
    if not app_id:
        # .env ファイルからも試す
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ESTAT_API_APPID="):
                        app_id = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    if not app_id:
        print("エラー: 環境変数 ESTAT_API_APPID が設定されていません。", file=sys.stderr)
        print("  export ESTAT_API_APPID='あなたのAppID'", file=sys.stderr)
        sys.exit(1)
    return app_id


def search_stats(
    keyword: str | None = None,
    stats_field: str | None = None,
    limit: int = 50,
    survey_years: str | None = None,
) -> dict:
    params = {
        "appId": get_app_id(),
        "lang": "J",
        "limit": str(limit),
        "explanationGetFlg": "N",
    }
    if keyword:
        params["searchWord"] = keyword
    if stats_field:
        params["statsField"] = stats_field
    if survey_years:
        params["surveyYears"] = survey_years

    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def format_title(title) -> str:
    if isinstance(title, dict):
        return title.get("$", str(title))
    return str(title)


def format_stat_name(stat_name) -> str:
    if isinstance(stat_name, dict):
        return stat_name.get("$", str(stat_name))
    return str(stat_name)


def print_results(data: dict) -> None:
    root = data.get("GET_STATS_LIST", {})
    result = root.get("RESULT", {})

    if result.get("STATUS") != 0:
        print(f"エラー: {result.get('ERROR_MSG')}", file=sys.stderr)
        sys.exit(1)

    datalist = root.get("DATALIST_INF", {})
    total = datalist.get("NUMBER", 0)
    tables = datalist.get("TABLE_INF", [])

    if not isinstance(tables, list):
        tables = [tables]

    print(f"\n検索結果: {total} 件中 {len(tables)} 件を表示\n")
    print(f"{'No':>4}  {'統計表ID':<16}  {'調査名':<30}  {'タイトル':<50}  {'周期':<6}  {'調査日':<12}  {'データ件数':>10}")
    print("-" * 140)

    for i, table in enumerate(tables, 1):
        table_id = table.get("@id", "")
        stat_name = format_stat_name(table.get("STAT_NAME", ""))
        title = format_title(table.get("TITLE", ""))
        cycle = table.get("CYCLE", "-")
        survey_date = table.get("SURVEY_DATE", "-")
        total_number = table.get("OVERALL_TOTAL_NUMBER", "-")

        # 長すぎる場合は切り詰め
        stat_name = stat_name[:28] + ".." if len(stat_name) > 30 else stat_name
        title = title[:48] + ".." if len(title) > 50 else title

        print(f"{i:>4}  {table_id:<16}  {stat_name:<30}  {title:<50}  {cycle:<6}  {survey_date:<12}  {total_number:>10}")

    if total > len(tables):
        print(f"\n※ 残り {total - len(tables)} 件あります。--limit で取得件数を増やせます。")


def list_fields() -> None:
    print("\n統計分野コード一覧（--field オプションで使用）\n")
    print(f"{'コード':<6}  {'分野名'}")
    print("-" * 30)
    for code, name in STATS_FIELDS.items():
        print(f"  {code}    {name}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="e-Stat API で統計表を検索して一覧表示する",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python scripts/estat/search_stats.py "人口"
  python scripts/estat/search_stats.py "GDP" --field 07
  python scripts/estat/search_stats.py "労働力" --years 2023
  python scripts/estat/search_stats.py --list-fields
        """,
    )
    parser.add_argument("keyword", nargs="?", help="検索キーワード")
    parser.add_argument("--field", dest="stats_field", help="統計分野コード（2桁）")
    parser.add_argument("--limit", type=int, default=50, help="取得件数（デフォルト: 50）")
    parser.add_argument("--years", dest="survey_years", help="調査年月（例: 2023, 202301-202312）")
    parser.add_argument("--list-fields", action="store_true", help="統計分野コード一覧を表示")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")

    args = parser.parse_args()

    if args.list_fields:
        list_fields()
        return

    if not args.keyword and not args.stats_field:
        parser.error("検索キーワードまたは --field を指定してください")

    data = search_stats(
        keyword=args.keyword,
        stats_field=args.stats_field,
        limit=args.limit,
        survey_years=args.survey_years,
    )

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_results(data)


if __name__ == "__main__":
    main()
