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
                       default='ms', help='時間系メトリクスの単位 (ms=ミリ秒, s=秒)')
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
                    
                    # 統計値計算
                    stats = client.calculate_statistics(data_points, metric_key)
                    
                    # CSV行データ作成
                    row_data = {
                        'monitor_name': monitor['name'],
                        # 'url': monitor.get('url', ''),  # URL取得が不完全なためコメントアウト
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
        csv_file = export_to_csv(all_metrics_data, args.start, args.end, args.encoding, output_dir, args.time_unit)
        
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