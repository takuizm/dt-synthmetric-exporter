"""
Dynatrace API v2 Client
Dynatrace API v2との通信を担当するクライアントクラス

Created: 2025-05-30
"""

import requests
import logging
import time
from typing import List, Dict, Any, Optional
import statistics
from urllib.parse import urljoin
import re
from config import Config
import numpy as np


class DynatraceClient:
    """Dynatrace API v2 クライアント"""

    def __init__(self, tenant_url: str, api_token: str):
        """
        クライアントを初期化

        Args:
            tenant_url: Dynatraceテナントの URL
            api_token: API トークン
        """
        self.tenant_url = tenant_url.rstrip('/')
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Api-Token {api_token}',
            'Content-Type': 'application/json'
        })

        # 設定読み込み
        self.config = Config()

        # レート制限対応
        self.last_request_time = 0
        self.min_request_interval = self.config.get_default('api', 'request_interval') / 1000  # msを秒に変換

    def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        """
        API リクエストを実行

        Args:
            method: HTTPメソッド
            endpoint: APIエンドポイント
            params: クエリパラメータ
            data: リクエストボディ

        Returns:
            Dict: レスポンスデータ

        Raises:
            requests.RequestException: API エラー
        """
        # レート制限対応
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)

        url = urljoin(f"{self.tenant_url}/", f"api/v2/{endpoint}")

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=self.config.get_default('api', 'timeout')
            )

            self.last_request_time = time.time()

            # エラーレスポンスのチェック
            if response.status_code >= 400:
                error_msg = f"API エラー {response.status_code}: {response.text}"
                logging.error(error_msg)
                response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logging.error(f"API リクエストに失敗しました: {e}")
            raise

    def get_synthetic_monitors(self, tag_filter: str = None) -> List[Dict[str, Any]]:
        """
        Synthetic モニターを取得（エンティティAPI使用）

        Args:
            tag_filter: タグフィルター文字列（例: "env:prod AND team:web"）
                       Noneまたは"*"の場合は全モニターを取得

        Returns:
            List[Dict]: モニターのリスト
        """
        if tag_filter:
            logging.info(f"Synthetic モニターを取得中... (タグフィルター: {tag_filter})")
        else:
            logging.info("Synthetic モニターを取得中... (タグフィルターなし)")

        # エンティティAPIを使用してSYNTHETIC_TESTを取得
        params = {
            'pageSize': 500,
            'fields': '+tags,+properties'
        }

        # エンティティセレクタの設定
        if tag_filter and tag_filter != "*":
            # 有効なタグフィルターが指定された場合
            params['entitySelector'] = f"type(SYNTHETIC_TEST),tag({tag_filter})"
        else:
            # タグフィルターなしまたは"*"の場合
            params['entitySelector'] = "type(SYNTHETIC_TEST)"

        monitors = []
        next_page_key = None

        while True:
            if next_page_key:
                params['nextPageKey'] = next_page_key

            try:
                response = self._make_request('GET', 'entities', params=params)

                entities = response.get('entities', [])

                # エンティティをモニター形式に変換
                for entity in entities:
                    monitor = self._convert_entity_to_monitor(entity)
                    if monitor:
                        monitors.append(monitor)

                next_page_key = response.get('nextPageKey')

                if not next_page_key:
                    break

            except Exception as e:
                logging.error(f"モニター取得中にエラーが発生しました: {e}")
                raise

        logging.info(f"取得したモニター数: {len(monitors)}")
        return monitors

    def _convert_entity_to_monitor(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """
        エンティティをモニター形式に変換

        Args:
            entity: エンティティデータ

        Returns:
            Dict: モニター形式のデータ
        """
        try:
            # デフォルト値を設定から取得
            default_type = self.config.get_default('monitor', 'type')
            default_interval = self.config.get_default('monitor', 'interval')

            # 基本情報
            monitor = {
                'entityId': entity.get('entityId'),
                'name': entity.get('displayName', 'Unknown'),
                'type': default_type,
                'tags': entity.get('tags', []),
                'frequencyMin': default_interval,
                'locations': [],
                'url': ''
            }

            # プロパティから詳細情報を取得
            properties = entity.get('properties', {})

            # モニタータイプの判定
            monitor_type = properties.get('monitorType', default_type)
            monitor['type'] = monitor_type

            # 監視間隔の取得（syntheticMonitorFrequencyを使用）
            frequency_min = default_interval  # デフォルト値（分）

            # syntheticMonitorFrequencyが正しいプロパティ（分単位）
            synthetic_freq = properties.get('syntheticMonitorFrequency')
            if synthetic_freq:
                try:
                    frequency_min = int(synthetic_freq)
                except:
                    pass
            else:
                # フォールバック: frequencyプロパティも確認（ミリ秒単位の場合）
                frequency = properties.get('frequency')
                if frequency:
                    try:
                        frequency_min = int(frequency) // 60000  # ミリ秒から分に変換
                    except:
                        pass

            monitor['frequencyMin'] = frequency_min

            # URLの取得（複数のソースから試行）
            url = ''
            if 'browserMonitorUrl' in properties:
                url = properties.get('browserMonitorUrl', '')
            elif 'url' in properties:
                url = properties.get('url', '')
            elif 'monitorUrl' in properties:
                url = properties.get('monitorUrl', '')

            monitor['url'] = url

            # script情報を構築
            device_profile = properties.get('deviceProfile', 'Desktop')

            monitor['script'] = {
                'configuration': {
                    'userActionsConfiguration': {
                        'loadActionSettings': {
                            'url': url
                        }
                    },
                    'device': {
                        'deviceName': device_profile
                    }
                }
            }

            # ロケーション情報を取得（実際のAPIから）
            monitor['locations'] = self._get_monitor_locations(entity.get('entityId'))

            return monitor

        except Exception as e:
            logging.warning(f"エンティティ変換エラー {entity.get('entityId', 'Unknown')}: {e}")
            return None

    def _get_monitor_locations(self, monitor_id: str) -> List[Dict[str, Any]]:
        """
        モニターに実際に割り当てられたロケーション情報を取得

        Args:
            monitor_id: モニターID

        Returns:
            List[Dict]: ロケーション情報のリスト
        """
        try:
            # まずモニターのエンティティ情報から割り当てロケーションを取得
            params = {
                'entitySelector': f'type(SYNTHETIC_TEST),entityId("{monitor_id}")',
                'fields': '+properties'
            }

            response = self._make_request('GET', 'entities', params=params)
            entities = response.get('entities', [])

            default_location = {
                'entityId': self.config.get_default('monitor', 'location'),
                'name': 'Default Location'
            }

            if not entities:
                logging.warning(f"モニター {monitor_id} の情報が取得できませんでした")
                return [default_location]

            # 割り当てロケーションIDリストを取得
            properties = entities[0].get('properties', {})
            assigned_location_ids = properties.get('assignedLocations', [])

            if not assigned_location_ids:
                logging.warning(f"モニター {monitor_id} に割り当てられたロケーションがありません")
                return [default_location]

            # 各ロケーションIDの詳細を取得
            locations = []
            for location_id in assigned_location_ids:
                try:
                    # 個別ロケーションの詳細を取得
                    location_params = {
                        'entitySelector': f'type(SYNTHETIC_LOCATION),entityId("{location_id}")',
                        'fields': '+properties'
                    }

                    location_response = self._make_request('GET', 'entities', params=location_params)
                    location_entities = location_response.get('entities', [])

                    if location_entities:
                        location_entity = location_entities[0]
                        location_properties = location_entity.get('properties', {})

                        # カスタマイズ名または検出名を使用
                        location_name = (
                            location_properties.get('customizedName') or
                            location_properties.get('detectedName') or
                            location_entity.get('displayName', 'Unknown Location')
                        )

                        # クラウドプロバイダー情報があれば追加
                        cloud_provider = location_properties.get('cloudProvider', '')
                        if cloud_provider:
                            if 'Amazon' in cloud_provider:
                                location_name += ' (AWS)'
                            elif 'Azure' in cloud_provider:
                                location_name += ' (Azure)'
                            elif cloud_provider not in location_name:
                                location_name += f' ({cloud_provider})'

                        locations.append({
                            'entityId': location_id,
                            'name': location_name
                        })
                    else:
                        logging.warning(f"ロケーション {location_id} の詳細情報が取得できませんでした")
                        locations.append({
                            'entityId': location_id,
                            'name': f'Location-{location_id[-4:]}'
                        })

                except Exception as e:
                    logging.warning(f"ロケーション {location_id} の取得でエラー: {e}")
                    continue

            return locations if locations else [default_location]

        except Exception as e:
            logging.warning(f"モニターロケーション取得エラー {monitor_id}: {e}")
            # エラー時はデフォルトロケーションを返す
            return [
                {
                    'entityId': self.config.get_default('monitor', 'location'),
                    'name': 'Default Location'
                }
            ]

    def get_monitor_metrics(self, monitor_id: str, start_time: str, end_time: str) -> List[Dict[str, Any]]:
        """
        特定のモニター・ロケーションのメトリクスを取得

        Args:
            monitor_id: モニターID
            start_time: 開始時刻（ISO形式）
            end_time: 終了時刻（ISO形式）

        Returns:
            List[Dict]: メトリクスデータのリスト
        """
        # 設定ファイルからメトリクス定義を取得
        metrics = self.config.get_metrics()
        metric_keys = [metric['key'] for metric in metrics]

        all_metrics = []

        for metric_key in metric_keys:
            # configからメトリクス定義を特定
            metric_def = self.config.get_metric_definition(metric_key)
            aggregation = metric_def.get('aggregation') if metric_def else None

            try:
                metric_data = self._get_single_metric(
                    metric_key, monitor_id, start_time, end_time, aggregation
                )
                if metric_data:
                    all_metrics.extend(metric_data)

            except Exception as e:
                logging.warning(f"メトリクス {metric_key} の取得に失敗: {e}")
                continue

        return all_metrics

    def _get_single_metric(self, metric_key: str, monitor_id: str,
                          start_time: str, end_time: str, aggregation: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        単一メトリクスを取得

        Args:
            metric_key: メトリクスキー
            monitor_id: モニターID
            start_time: 開始時刻
            end_time: 終了時刻
            aggregation: 集計タイプ (avg, sum, max, min, median, etc.)

        Returns:
            List[Dict]: メトリクスデータ
        """
        # 解像度を設定（今回は固定で1hとする）
        resolution = '1h'

        # メトリクスセレクタを構築
        selector = metric_key
        # 有効な集計タイプの場合のみ、セレクタに追加
        valid_aggregations = ['avg', 'sum', 'max', 'min', 'median', 'count']
        if aggregation and aggregation in valid_aggregations:
            selector = f"{metric_key}:{aggregation}"

        # パラメータ設定
        params = {
            'metricSelector': selector,
            'entitySelector': f'type(SYNTHETIC_TEST),entityId("{monitor_id}")',
            'from': start_time,
            'to': end_time,
            'resolution': resolution
        }

        try:
            # :splitBy()はentitySelectorと共存できないため、基本的なクエリのみ実行
            # ロケーション別のデータが必要な場合は、今後の改修で対応
            response = self._make_request('GET', 'metrics/query', params=params)
            return response.get('result', [])

        except Exception as e:
            # APIが400を返す場合、集計なしでリトライするフォールバック処理
            if '400' in str(e):
                logging.warning(f"集計付きクエリ失敗 ({selector})。集計なしでリトライします...")
                try:
                    params['metricSelector'] = metric_key
                    response = self._make_request('GET', 'metrics/query', params=params)
                    return response.get('result', [])
                except Exception as retry_e:
                    logging.error(f"リトライ失敗 ({metric_key}): {retry_e}")
                    return []
            else:
                logging.error(f"メトリクス取得で予期せぬエラー ({metric_key}): {e}")
                return []

    def calculate_statistics(self, values: List[float], metric_key: str = None, time_unit: str = 'ms') -> Dict[str, float]:
        """
        値のリストから統計値を計算

        Args:
            values: 値のリスト
            metric_key: メトリクスキー（カウンター型判定用）
            time_unit: 時間単位 ('ms' または 's')

        Returns:
            Dict: 統計値（min, max, avg, median, stdev）
        """
        default_value = self.config.get_default('fallback', 'stats')['default']

        if not values:
            return {
                'min': default_value,
                'max': default_value,
                'avg': default_value,
                'median': default_value,
                'stdev': default_value
            }

        try:
            # 成功/失敗メトリクスの場合は合計値をそのまま使用
            if metric_key in ['builtin:synthetic.browser.success', 'builtin:synthetic.browser.success.geo',
                            'builtin:synthetic.browser.failure', 'builtin:synthetic.browser.failure.geo']:
                total = sum(values)
                return {
                    'min': total,
                    'max': total,
                    'avg': total,
                    'median': total,
                    'stdev': 0
                }

            # その他のメトリクスは通常の統計値を計算
            values_array = np.array(values)

            # 時間系メトリクスで秒単位が指定された場合の変換
            is_time_metric = self._is_time_metric(metric_key) if metric_key else False
            if is_time_metric and time_unit == 's':
                # ミリ秒から秒に変換
                values_array = values_array / 1000

            stats = {
                'min': float(np.min(values_array)),
                'max': float(np.max(values_array)),
                'avg': float(np.mean(values_array)),
                'median': float(np.median(values_array)),
                'stdev': float(np.std(values_array))
            }

            # メトリクス別の丸め処理
            if is_time_metric and time_unit == 's':
                # 時間系メトリクス（秒単位）は小数点以下2位に丸める
                for key in stats:
                    stats[key] = round(stats[key], 2)
            elif metric_key and 'cumulativeLayoutShift' in metric_key:
                # CLSは小数点第3位まで丸める
                for key in stats:
                    stats[key] = round(stats[key], 3)

            return stats

        except Exception as e:
            logging.warning(f"統計値の計算に失敗: {e}")
            return {
                'min': default_value,
                'max': default_value,
                'avg': default_value,
                'median': default_value,
                'stdev': default_value
            }

    def _is_time_metric(self, metric_key: str) -> bool:
        """
        メトリクスが時間系かどうかを判定

        Args:
            metric_key: メトリクスキー

        Returns:
            bool: 時間系メトリクスの場合True
        """
        if not metric_key:
            return False

        # 時間系メトリクスのキーワードを取得
        time_keywords = self.config.get_time_metrics_keywords()

        # メトリクスキーに時間系キーワードが含まれているかチェック
        for keyword in time_keywords:
            if keyword.lower() in metric_key.lower():
                return True

        return False

    def get_metric_description(self, metric_key: str) -> str:
        """
        メトリクスキーから日本語説明文を取得

        Args:
            metric_key: メトリクスキー

        Returns:
            str: メトリクス説明（日本語）
        """
        # メトリクスキーから変換子（:sum, :splitByなど）を除去
        clean_metric_key = re.split(r':(sum|avg|max|min|median|count|splitBy)', metric_key)[0]

        # 設定ファイルからメトリクス定義を取得
        metrics = self.config.get_metrics()

        # クリーンなメトリクスキーに一致する説明を検索
        for metric in metrics:
            if metric.get('key') == clean_metric_key:
                return metric.get('description', clean_metric_key)

        # 見つからない場合は元のキーをそのまま返す
        return metric_key

    def get_device_type(self, monitor: Dict[str, Any]) -> str:
        """
        モニターからデバイスタイプを取得

        Args:
            monitor: モニター情報

        Returns:
            str: デバイスタイプ
        """
        script = monitor.get('script', {})
        device_config = script.get('configuration', {}).get('device', {})
        return device_config.get('deviceName', 'Desktop')

    def test_connection(self) -> bool:
        """
        API 接続をテスト

        Returns:
            bool: 接続成功かどうか
        """
        try:
            self._make_request('GET', 'synthetic/monitors', params={'pageSize': 1})
            logging.info("Dynatrace API 接続テスト: 成功")
            return True
        except Exception as e:
            logging.error(f"Dynatrace API 接続テスト: 失敗 - {e}")
            return False
