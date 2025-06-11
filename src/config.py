"""
設定ファイル読み込みモジュール
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional, List

class Config:
    """設定管理クラス"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        設定を初期化
        
        Args:
            config_path: 設定ファイルのパス（省略時はデフォルトパス）
        """
        self.config_path = config_path or os.path.join('config', 'metrics.yaml')
        self.config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """設定ファイルを読み込み"""
        try:
            if not os.path.exists(self.config_path):
                logging.warning(f"設定ファイルが見つかりません: {self.config_path}")
                self.config = self._get_default_config()
                return
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
                
            logging.info(f"設定ファイルを読み込みました: {self.config_path}")
            
        except Exception as e:
            logging.error(f"設定ファイル読み込みエラー: {e}")
            self.config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を返す"""
        return {
            'metrics': [],
            'output_format': {
                'csv': {
                    'columns': [
                        {'key': 'monitor_name', 'display_name': 'モニター名', 'order': 1},
                        {'key': 'frequency', 'display_name': '監視間隔(h)', 'order': 2},
                        {'key': 'device', 'display_name': 'デバイス', 'order': 3},
                        {'key': 'location', 'display_name': 'ロケーション', 'order': 4},
                        {'key': 'metric_name', 'display_name': 'メトリクス名', 'order': 5},
                        {'key': 'metric_description', 'display_name': 'メトリクス説明', 'order': 6},
                        {'key': 'min', 'display_name': 'Min', 'order': 7},
                        {'key': 'max', 'display_name': 'Max', 'order': 8},
                        {'key': 'avg', 'display_name': 'Avg', 'order': 9},
                        {'key': 'median', 'display_name': 'Median', 'order': 10},
                        {'key': 'stdev', 'display_name': 'Stdev', 'order': 11},
                        {'key': 'tags', 'display_name': 'タグ', 'order': 12}
                    ]
                },
                'time_metrics': {
                    'keywords': [
                        'duration', 'time', 'byte', 'paint', 'complete',
                        'interactive', 'contribution', 'response', 'event', 'index'
                    ]
                }
            },
            'defaults': {
                'monitor': {
                    'type': 'BROWSER',
                    'interval': 15,
                    'resolution': '15m',
                    'location': 'DEFAULT'
                },
                'api': {
                    'request_interval': 100,
                    'timeout': 30
                },
                'output': {
                    'time_unit': 'ms',
                    'encoding': 'utf8-bom',
                    'time_range': {
                        'min': 24,
                        'max': 120
                    }
                },
                'fallback': {
                    'stats': {
                        'default': 0.0
                    },
                    'location': 'DEFAULT'
                }
            }
        }
    
    def get_metrics(self) -> list:
        """メトリクス定義を取得"""
        return self.config.get('metrics', [])
    
    def get_metric_definition(self, metric_key: str) -> Optional[Dict[str, Any]]:
        """
        指定されたキーに一致するメトリクス定義を取得
        
        Args:
            metric_key: 検索するメトリクスキー
        
        Returns:
            Optional[Dict[str, Any]]: メトリクス定義辞書、見つからない場合はNone
        """
        metrics = self.get_metrics()
        for metric in metrics:
            if metric.get('key') == metric_key:
                return metric
        return None
    
    def get_time_metrics_keywords(self) -> list:
        """時間系メトリクスのキーワードを取得"""
        return self.config.get('output_format', {}).get('time_metrics', {}).get('keywords', [])
    
    def is_counter_metric(self, metric_key: str) -> bool:
        """
        メトリクスがカウンター型かどうかを判定
        
        Args:
            metric_key: メトリクスキー
            
        Returns:
            bool: カウンター型の場合True
        """
        metrics = self.get_metrics()
        for metric in metrics:
            if metric.get('key') == metric_key:
                return metric.get('aggregation') == 'counter'
        return False
    
    def get_default(self, category: str, key: str) -> Any:
        """
        デフォルト値を取得
        
        Args:
            category: カテゴリ（monitor/api/output/fallback）
            key: キー
            
        Returns:
            Any: 設定値
        """
        try:
            return self.config['defaults'][category][key]
        except KeyError:
            logging.warning(f"設定が見つかりません: {category}.{key}")
            return None

    def get_csv_columns(self) -> List[Dict[str, Any]]:
        """
        CSV列定義を取得（順序付き）
        
        Returns:
            List[Dict[str, Any]]: 列定義のリスト
        """
        columns = self.config.get('output_format', {}).get('csv', {}).get('columns', [])
        return sorted(columns, key=lambda x: x.get('order', 999))

    def get_column_names(self) -> List[str]:
        """
        CSV列の表示名リストを取得
        
        Returns:
            List[str]: 列の表示名リスト
        """
        return [col['display_name'] for col in self.get_csv_columns()]

    def get_column_keys(self) -> List[str]:
        """
        CSV列のキーリストを取得
        
        Returns:
            List[str]: 列のキーリスト
        """
        return [col['key'] for col in self.get_csv_columns()]

    def get_sort_settings(self) -> Dict[str, Any]:
        """
        ソート設定を取得
        
        Returns:
            Dict[str, Any]: ソート設定
        """
        return self.config.get('sort_settings', {})
    
    def get_category_order(self) -> Dict[str, int]:
        """
        カテゴリーの表示順を辞書として取得
        
        Returns:
            Dict[str, int]: カテゴリー名とその順序のマッピング
        """
        categories = self.config.get('sort_settings', {}).get('category_order', [])
        return {cat: idx for idx, cat in enumerate(categories)}
    
    def get_metric_order(self) -> Dict[str, Dict[str, int]]:
        """
        メトリクスの表示順を辞書として取得
        
        Returns:
            Dict[str, Dict[str, int]]: カテゴリーごとのメトリクス順序のマッピング
        """
        metric_order = self.config.get('sort_settings', {}).get('metric_order', {})
        return {
            category: {metric: idx for idx, metric in enumerate(metrics)}
            for category, metrics in metric_order.items()
        }
    
    def get_metric_category(self, metric_key: str) -> str:
        """
        メトリクスのカテゴリーを取得
        
        Args:
            metric_key: メトリクスキー
            
        Returns:
            str: カテゴリー名（見つからない場合は'Other'）
        """
        metrics = self.get_metrics()
        for metric in metrics:
            if metric.get('key') == metric_key:
                return metric.get('category', 'Other') 