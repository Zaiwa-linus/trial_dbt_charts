"""e-Stat API から統計データを取得し、CSVとして保存するスクリプト。

使い方:
  python scripts/estat/download_data.py 0003317114
  python scripts/estat/download_data.py 0003317114 -o data/custom_dir/data.csv

デフォルトでは data/{統計表ID}/ ディレクトリを作成し、
その中に {統計表ID}.csv と column_summary.yml を保存する。
"""

import argparse
import csv
import json
import os
import sys
import urllib.request
import urllib.parse
import yaml

STATS_DATA_URL = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
META_URL = "https://api.e-stat.go.jp/rest/3.0/app/json/getMetaInfo"


def get_app_id() -> str:
    app_id = os.environ.get("ESTAT_API_APPID")
    if not app_id:
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
        sys.exit(1)
    return app_id


def api_get(url: str) -> dict:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_meta(app_id: str, stats_data_id: str) -> dict:
    """メタ情報を取得し、コード→名称のマッピングとテーブル情報を返す。"""
    params = {
        "appId": app_id,
        "lang": "J",
        "statsDataId": stats_data_id,
    }
    url = f"{META_URL}?{urllib.parse.urlencode(params)}"
    data = api_get(url)

    root = data.get("GET_META_INFO", {})
    if root.get("RESULT", {}).get("STATUS") != 0:
        print(f"メタ情報取得エラー: {root.get('RESULT', {}).get('ERROR_MSG')}", file=sys.stderr)
        sys.exit(1)

    metadata = root.get("METADATA_INF", {})
    table_inf = metadata.get("TABLE_INF", {})

    # 分類ID → {コード → 名称} のマッピングを作成
    code_map = {}  # {"tab": {"100": "回答数", ...}, "area": {"00000": "全体", ...}}
    class_names = {}  # {"tab": "表章項目", "area": "国籍", ...}

    class_objs = metadata.get("CLASS_INF", {}).get("CLASS_OBJ", [])
    if not isinstance(class_objs, list):
        class_objs = [class_objs]

    for obj in class_objs:
        obj_id = obj.get("@id", "")
        class_names[obj_id] = obj.get("@name", obj_id)
        classes = obj.get("CLASS", [])
        if not isinstance(classes, list):
            classes = [classes]
        code_map[obj_id] = {}
        for cls in classes:
            code_map[obj_id][cls.get("@code", "")] = cls.get("@name", "")

    return code_map, class_names, table_inf


def _get_text(val) -> str:
    """APIレスポンスの値からテキストを取得する（dict or str対応）。"""
    if isinstance(val, dict):
        return val.get("$", str(val))
    return str(val) if val else ""


def _build_meta_info(table_inf: dict) -> dict:
    """テーブル情報から基本情報のdictを構築する。"""
    meta = {
        "title": _get_text(table_inf.get("TITLE", "")),
        "stats_data_id": table_inf.get("@id", ""),
        "stat_name": _get_text(table_inf.get("STAT_NAME", "")),
    }
    if isinstance(table_inf.get("STAT_NAME"), dict):
        stat_code = table_inf["STAT_NAME"].get("@code", "")
        if stat_code:
            meta["stat_code"] = stat_code
    gov_org = _get_text(table_inf.get("GOV_ORG", ""))
    if gov_org:
        meta["gov_org"] = gov_org
    main_category = _get_text(table_inf.get("MAIN_CATEGORY", ""))
    if main_category:
        meta["main_category"] = main_category
    sub_category = _get_text(table_inf.get("SUB_CATEGORY", ""))
    if sub_category:
        meta["sub_category"] = sub_category
    for key, yaml_key in [("TITLE_NO", "title_no"), ("CYCLE", "cycle"),
                           ("SURVEY_DATE", "survey_date"), ("OPEN_DATE", "open_date"),
                           ("UPDATED_DATE", "updated_date"), ("OVERALL_TOTAL_NUMBER", "total_number")]:
        val = table_inf.get(key, "")
        if val:
            meta[yaml_key] = str(val)
    if str(table_inf.get("SMALL_AREA", "")) == "1":
        meta["small_area"] = True
    if isinstance(table_inf.get("STATISTICS_NAME_SPEC"), dict):
        desc = _get_text(table_inf["STATISTICS_NAME_SPEC"].get("DESCRIPTION", ""))
        if desc:
            meta["description"] = desc
    return meta


def write_column_summary(table_inf: dict, headers: list[str], rows: list[list[str]], output_dir: str) -> None:
    """メタ情報とカラムごとのユニーク値を集計し、YAMLファイルとして保存する。"""
    # メタ情報
    output = {"meta": _build_meta_info(table_inf)}

    # カラムごとのユニーク値集計
    columns = {}
    for col_idx, header in enumerate(headers):
        unique_values = sorted(set(row[col_idx] for row in rows))
        total = len(unique_values)
        col_info = {"unique_count": total}
        if total > 100:
            col_info["note"] = "件数多数のためvalues値の一部を省略"
            col_info["values"] = unique_values[:90] + ["..."] + unique_values[-10:]
        else:
            col_info["values"] = unique_values
        columns[header] = col_info
    output["columns"] = columns

    # 全値を文字列として統一的にクォートするカスタムDumper
    class StrDumper(yaml.SafeDumper):
        pass

    def _str_representer(dumper, data):
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="'")

    StrDumper.add_representer(str, _str_representer)

    yaml_path = os.path.join(output_dir, "column_summary.yml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(output, f, Dumper=StrDumper, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"保存しました: {yaml_path}", file=sys.stderr)


def fetch_stats_data(app_id: str, stats_data_id: str) -> list[dict]:
    """統計データを全件取得する（ページネーション対応）。"""
    all_values = []
    start = 1
    limit = 100000

    while True:
        params = {
            "appId": app_id,
            "lang": "J",
            "statsDataId": stats_data_id,
            "metaGetFlg": "N",
            "explanationGetFlg": "N",
            "annotationGetFlg": "N",
            "startPosition": str(start),
            "limit": str(limit),
        }
        url = f"{STATS_DATA_URL}?{urllib.parse.urlencode(params)}"
        data = api_get(url)

        root = data.get("GET_STATS_DATA", {})
        result = root.get("RESULT", {})
        status = result.get("STATUS")
        if status not in (0, 2):
            print(f"データ取得エラー: {result.get('ERROR_MSG')}", file=sys.stderr)
            sys.exit(1)

        stat_data = root.get("STATISTICAL_DATA", {})
        data_inf = stat_data.get("DATA_INF", {})
        values = data_inf.get("VALUE", [])
        if not isinstance(values, list):
            values = [values]

        all_values.extend(values)

        result_inf = stat_data.get("RESULT_INF", {})
        next_key = result_inf.get("NEXT_KEY")
        if next_key:
            start = int(next_key)
            print(f"  {len(all_values)} 件取得済み、続きを取得中...", file=sys.stderr)
        else:
            break

    return all_values


def values_to_rows(values: list[dict], code_map: dict, class_names: dict) -> tuple[list[str], list[list[str]]]:
    """VALUE配列をCSV用の行データに変換する。"""
    # 使用されている分類IDを特定（@tab, @cat01, @area, @time など）
    dim_keys = []
    if values:
        for key in values[0]:
            if key.startswith("@") and key != "@unit":
                dim_id = key[1:]  # "@tab" → "tab"
                dim_keys.append(dim_id)

    # ヘッダー: 各分類のコード列 + 名称列 + 単位 + 値
    headers = []
    for dim_id in dim_keys:
        name = class_names.get(dim_id, dim_id)
        headers.append(f"{name}_code")
        headers.append(name)
    headers.extend(["unit", "value"])

    # データ行
    rows = []
    for v in values:
        row = []
        for dim_id in dim_keys:
            code = v.get(f"@{dim_id}", "")
            name = code_map.get(dim_id, {}).get(code, code)
            row.append(code)
            row.append(name)
        row.append(v.get("@unit", ""))
        row.append(v.get("$", ""))
        rows.append(row)

    return headers, rows


def main():
    parser = argparse.ArgumentParser(
        description="e-Stat API から統計データを取得しCSVに保存する",
    )
    parser.add_argument("stats_data_id", help="統計表ID")
    parser.add_argument("-o", "--output", help="出力ファイルパス（デフォルト: data/{統計表ID}.csv）")

    args = parser.parse_args()
    app_id = get_app_id()
    stats_data_id = args.stats_data_id

    output = args.output
    if not output:
        output_dir = f"data/{stats_data_id}"
        output = f"{output_dir}/{stats_data_id}.csv"
    else:
        output_dir = os.path.dirname(output)

    # 出力ディレクトリ作成
    os.makedirs(output_dir, exist_ok=True)

    print(f"メタ情報を取得中...", file=sys.stderr)
    code_map, class_names, table_inf = fetch_meta(app_id, stats_data_id)

    print(f"統計データを取得中...", file=sys.stderr)
    values = fetch_stats_data(app_id, stats_data_id)
    print(f"合計 {len(values)} 件取得", file=sys.stderr)

    headers, rows = values_to_rows(values, code_map, class_names)

    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"保存しました: {output}", file=sys.stderr)

    # カラムサマリーYAMLを生成（メタ情報 + カラムユニーク値）
    write_column_summary(table_inf, headers, rows, output_dir)


if __name__ == "__main__":
    main()
