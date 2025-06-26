#!/usr/bin/env python3
"""
Dynatrace Synthetic メトリクス CSV エクスポートツール

Created: 2025-05-30
"""

import os
import sys
import argparse
import logging
from dotenv import load_dotenv
import re

# src モジュールをインポート
sys.path.append(os.path.dirname(__file__))
from helpers import setup_logging, parse_date_range, export_to_csv
from dynatrace_client import DynatraceClient


def main():
    """メイン処理"""

    # 引数解析
    parser = argparse.ArgumentParser(description='Dynatrace Synthetic メトリクス CSV エクスポートツール')
    parser.add_argument('--tags', help='タグフィルター (例: "env:prod AND team:web")')
    parser.add_argument('--start', required=True, help='取得開始日 (YYYYMMDD)')
    parser.add_argument('--end', required=True, help='取得終了日 (YYYYMMDD)')
    parser.add_argument('--encoding', choices=['utf8-bom', 'sjis'],
                       default='utf8-bom', help='CSV エンコーディング')
    parser.add_argument('--time-unit', choices=['ms', 's'],
                       default='s', help='時間系メトリクスの単位 (ms=ミリ秒, s=秒)')
    parser.add_argument('--output-mode', choices=['raw', 'evaluation'],
                       default='raw', help='出力モード (raw=生データ, evaluation=評価付き)')
    parser.add_argument('--verbose', action='store_true', help='詳細ログを表示')

    args = parser.parse_args()

    # ログ設定
    log_file = setup_logging(verbose=args.verbose)

    # 環境変数読み込み
    load_dotenv()

    tenant_url = os.getenv('DT_TENANT')
    api_token = os.getenv('DT_TOKEN')

    if not tenant_url or not api_token:
        logging.error("環境変数 DT_TENANT と DT_TOKEN を設定してください")
        return 1

    try:
        # DynatraceClient 初期化
        client = DynatraceClient(tenant_url, api_token)

        # 接続テスト
        if not client.test_connection():
            logging.error("Dynatrace API への接続に失敗しました")
            return 1

        # 時間範囲計算
        start_time, end_time = parse_date_range(args.start, args.end)
        logging.info(f"取得期間: {start_time} ～ {end_time}")

        # モニター取得
        monitors = client.get_synthetic_monitors(args.tags)

        if not monitors:
            if args.tags and args.tags != "*":
                logging.warning(f"指定したタグフィルター '{args.tags}' に一致するモニターが見つかりませんでした")
            else:
                logging.warning("Synthetic モニターが見つかりませんでした")
            return 1

        logging.info(f"対象モニター数: {len(monitors)}")

        # OUTPUTフォルダを作成
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        logging.info(f"出力フォルダを作成: {output_dir}")

        # 全モニターのメトリクス収集
        all_metrics_data = []

        for monitor in monitors:
            logging.info(f"処理中: {monitor['name']}")

            # 各ロケーションからメトリクス取得
            locations = monitor.get('locations', [{'entityId': 'DEFAULT', 'name': 'Default Location'}])

            for location in locations:
                metrics = client.get_monitor_metrics(
                    monitor['entityId'],
                    start_time,
                    end_time
                )

                if not metrics:
                    logging.warning(f"メトリクスが見つかりませんでした: {monitor['name']} @ {location['name']}")
                    continue

                # メトリクスデータを処理
                for metric in metrics:
                    metric_key_raw = metric.get('metricId', 'unknown')

                    # APIレスポンスに含まれる可能性のある変換子(:splitByなど)を削除
                    match = re.match(r"(builtin:[^:]+:[^:]+)", metric_key_raw)
                    if match:
                        metric_key = match.group(1)
                    else:
                        metric_key = metric_key_raw

                    data_points = []

                    # データポイントを収集
                    for data_result in metric.get('data', []):
                        values = data_result.get('values', [])
                        for value in values:
                            if value is not None:
                                data_points.append(value)

                    if not data_points:
                        continue

                    # 統計値計算（設定からデフォルト単位を取得）
                    default_time_unit = client.config.get_default('output', 'time_unit')
                    actual_time_unit = args.time_unit if hasattr(args, 'time_unit') and args.time_unit else default_time_unit
                    stats = client.calculate_statistics(data_points, metric_key, actual_time_unit)

                    # 評価値の選択（設定から取得）
                    eval_value_type = client.config.get_evaluation_value_type()
                    eval_value = stats.get(eval_value_type, stats.get('avg', 0))

                    # 評価実行
                    evaluation = client.config.evaluate_metric(metric_key, eval_value, actual_time_unit)

                    # Action Durationは2つの基準で評価
                    if 'actionDuration' in metric_key:
                        dual_criteria = client.config.get_metric_duplicates()
                        for criteria in dual_criteria:
                            threshold_key = criteria.get('threshold_key')
                            display_suffix = criteria.get('display_suffix', '')
                            description = criteria.get('description', '')

                            # 基準値別の評価
                            threshold = client.config.get_evaluation_criteria().get('time_thresholds', {}).get(threshold_key)
                            if threshold is not None:
                                # 実際の時間単位が秒の場合、基準値もそのまま使用
                                if actual_time_unit == 's':
                                    criteria_evaluation = 1 if eval_value <= threshold else 0
                                else:
                                    # ミリ秒の場合は基準値を1000倍
                                    threshold_ms = threshold * 1000
                                    criteria_evaluation = 1 if eval_value <= threshold_ms else 0
                            else:
                                criteria_evaluation = -1

                            # Action Duration用のCSV行データ作成
                            if client.config.is_evaluation_mode(args.output_mode):
                                # 評価付きモード用のデータ構造
                                action_row_data = {
                                    'code': '',  # 空欄
                                    'corporate': '',  # 空欄
                                    'no': '',  # 空欄
                                    'code_no': '',  # 空欄
                                    'metric_full_name': client.config.get_metric_full_name(f"{metric_key}{display_suffix}", description),
                                    'evaluation': criteria_evaluation,
                                    'avg': stats['avg'],
                                    'url': '',  # 空欄
                                    'index': 0,  # 後で連番を設定
                                    'tags': ', '.join([f"{tag['key']}:{tag['value']}" for tag in monitor.get('tags', [])])
                                }
                            else:
                                # 生データモード用のデータ構造（従来通り）
                                action_row_data = {
                                    'monitor_name': monitor['name'],
                                    'frequency': monitor.get('frequencyMin', 15),
                                    'device': client.get_device_type(monitor),
                                    'location': location['name'],
                                    'metric_name': f"{metric_key}{display_suffix}",
                                    'metric_description': description,
                                    'min': stats['min'],
                                    'max': stats['max'],
                                    'avg': stats['avg'],
                                    'median': stats['median'],
                                    'stdev': stats['stdev'],
                                    'tags': ', '.join([f"{tag['key']}:{tag['value']}" for tag in monitor.get('tags', [])])
                                }

                            all_metrics_data.append(action_row_data)
                    else:
                        # 通常メトリクスのCSV行データ作成
                        if client.config.is_evaluation_mode(args.output_mode):
                            # 評価付きモード用のデータ構造
                            row_data = {
                                'code': '',  # 空欄
                                'corporate': '',  # 空欄
                                'no': '',  # 空欄
                                'code_no': '',  # 空欄
                                'metric_full_name': client.config.get_metric_full_name(metric_key, client.get_metric_description(metric_key)),
                                'evaluation': evaluation,
                                'avg': stats['avg'],
                                'url': '',  # 空欄
                                'index': 0,  # 後で連番を設定
                                'tags': ', '.join([f"{tag['key']}:{tag['value']}" for tag in monitor.get('tags', [])])
                            }
                        else:
                            # 生データモード用のデータ構造（従来通り）
                            row_data = {
                                'monitor_name': monitor['name'],
                                'frequency': monitor.get('frequencyMin', 15),
                                'device': client.get_device_type(monitor),
                                'location': location['name'],
                                'metric_name': metric_key,
                                'metric_description': client.get_metric_description(metric_key),
                                'min': stats['min'],
                                'max': stats['max'],
                                'avg': stats['avg'],
                                'median': stats['median'],
                                'stdev': stats['stdev'],
                                'tags': ', '.join([f"{tag['key']}:{tag['value']}" for tag in monitor.get('tags', [])])
                            }

                        all_metrics_data.append(row_data)

        if not all_metrics_data:
            logging.warning("エクスポートするメトリクスデータがありません")
            return 1

        # CSV エクスポート（OUTPUTフォルダに出力）
        csv_file = export_to_csv(all_metrics_data, args.start, args.end, args.encoding, output_dir, args.time_unit, args.output_mode)

        logging.info(f"エクスポート完了")
        logging.info(f"出力ファイル: {csv_file}")
        logging.info(f"レコード数: {len(all_metrics_data)}")
        logging.info(f"ログファイル: {log_file}")

        return 0

    except ValueError as e:
        logging.error(f"パラメータエラー: {e}")
        return 1
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
