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

    def get_time_metrics_keywords(self) -> List[str]:
        """
        時間系メトリクスのキーワードリストを取得

        Returns:
            List[str]: 時間系メトリクスのキーワードリスト
        """
        return self.config.get('time_metrics_keywords', [])

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
        return 'Other'

    def get_output_modes(self) -> Dict[str, Any]:
        """
        出力モード設定を取得

        Returns:
            Dict[str, Any]: 出力モード設定
        """
        return self.config.get('output_modes', {})

    def get_csv_columns_evaluation(self) -> List[Dict[str, Any]]:
        """
        評価付きモード用CSV列定義を取得（順序付き）

        Returns:
            List[Dict[str, Any]]: 評価付きモード用列定義のリスト
        """
        columns = self.config.get('csv_columns_evaluation', [])
        return sorted(columns, key=lambda x: x.get('order', 999))

    def get_metric_full_name(self, metric_key: str, description: str = None) -> str:
        """
        メトリクス名:説明の組み合わせ文字列を生成

        Args:
            metric_key: メトリクスキー
            description: メトリクス説明（省略時は設定から取得）

        Returns:
            str: "メトリクス名:説明" 形式の文字列
        """
        if description is None:
            # 設定からメトリクス説明を取得
            metric_def = self.get_metric_definition(metric_key)
            description = metric_def.get('description', '') if metric_def else ''

        # メトリクス名の表示名を取得
        metric_def = self.get_metric_definition(metric_key)
        metric_name = metric_def.get('name', metric_key) if metric_def else metric_key

        return f"{metric_name}:{description}"

    def is_evaluation_mode(self, output_mode: str) -> bool:
        """
        評価付きモードかどうかを判定

        Args:
            output_mode: 出力モード ('raw' or 'evaluation')

        Returns:
            bool: 評価付きモードの場合True
        """
        return output_mode == 'evaluation'

    def get_evaluation_criteria(self) -> Dict[str, Any]:
        """
        評価基準設定を取得

        Returns:
            Dict[str, Any]: 評価基準設定
        """
        return self.config.get('evaluation_criteria', {})

    def get_evaluation_value_type(self) -> str:
        """
        評価に使用する統計値のタイプを取得

        Returns:
            str: 統計値のタイプ（デフォルト: avg）
        """
        criteria = self.get_evaluation_criteria()
        return criteria.get('evaluation_value', 'avg')

    def get_metric_threshold(self, metric_key: str, unit: str = None) -> float:
        """
        メトリクスの基準値を取得

        Args:
            metric_key: メトリクスキー
            unit: 単位（ms/s等）

        Returns:
            float: 基準値（基準値未設定の場合はNone）
        """
        criteria = self.get_evaluation_criteria()
        time_thresholds = criteria.get('time_thresholds', {})
        ratio_thresholds = criteria.get('ratio_thresholds', {})

        # 複製メトリクスの場合、対応する基準値キーを取得
        threshold_key = self._get_threshold_key_for_duplicate(metric_key)
        if threshold_key:
            # 複製メトリクス用の基準値を取得
            threshold = time_thresholds.get(threshold_key)
            if threshold is not None and unit == 'ms':
                return threshold * 1000  # 秒をミリ秒に変換
            return threshold

        # 通常のメトリクス処理
        # メトリクスキーから基準値を特定
        if 'actionDuration' in metric_key:
            threshold = time_thresholds.get('actionDuration')
        elif 'visuallyComplete' in metric_key:
            threshold = time_thresholds.get('visuallyComplete')
        elif 'largestContentfulPaint' in metric_key:
            threshold = time_thresholds.get('largestContentfulPaint')
        elif 'firstByte' in metric_key:
            threshold = time_thresholds.get('firstByte')
        elif 'speedIndex' in metric_key:
            threshold = time_thresholds.get('speedIndex')
        elif 'availability' in metric_key:
            return ratio_thresholds.get('availability')
        elif 'cumulativeLayoutShift' in metric_key:
            return ratio_thresholds.get('cumulativeLayoutShift')
        else:
            return None

        # 時間系メトリクスの単位変換
        if threshold is not None and unit == 'ms':
            return threshold * 1000  # 秒をミリ秒に変換

        return threshold

    def get_metric_duplicates(self) -> List[Dict[str, Any]]:
        """
        Action Durationの2つの基準設定を取得

        Returns:
            List[Dict[str, Any]]: Action Duration用の2基準設定
        """
        return self.config.get('action_duration_dual_criteria', [])

    def _get_threshold_key_for_duplicate(self, metric_key: str) -> str:
        """
        Action Durationメトリクス用の基準値キーを取得

        Args:
            metric_key: メトリクスキー

        Returns:
            str: 基準値キー（通常メトリクスの場合はNone）
        """
        # Action Duration以外は通常処理
        return None

    def get_duplicate_display_info(self, metric_key: str) -> Dict[str, str]:
        """
        削除予定のメソッド（互換性のため残す）
        """
        return {'display_name': '', 'description': ''}

    def evaluate_metric(self, metric_key: str, value: float, time_unit: str = 'ms') -> int:
        """
        メトリクス値を評価基準と比較

        Args:
            metric_key: メトリクスキー
            value: 評価する値
            time_unit: 時間単位

        Returns:
            int: 合格なら1、不合格なら0、基準値がない場合は-1
        """
        threshold = self.get_metric_threshold(metric_key, time_unit)

        if threshold is None:
            return -1  # 基準値未設定

        # 可用性は値が基準値以上で合格
        if 'availability' in metric_key:
            return 1 if value >= threshold else 0

        # その他のメトリクスは値が基準値以下で合格
        return 1 if value <= threshold else 0

    def get_csv_columns_evaluation_excel(self) -> List[Dict[str, Any]]:
        """
        Excel形式評価付きモード用CSV列定義を取得（順序付き）

        Returns:
            List[Dict[str, Any]]: Excel形式評価付きモード用列定義のリスト
        """
        columns = self.config.get('csv_columns_evaluation_excel', [])
        return sorted(columns, key=lambda x: x.get('order', 999))

    def get_excel_metric_column_mapping(self) -> Dict[str, str]:
        """
        メトリクスとExcel列の対応関係を取得

        Returns:
            Dict[str, str]: メトリクスキーと列キーのマッピング
        """
        return self.config.get('excel_metric_column_mapping', {})

    def is_excel_format_enabled(self) -> bool:
        """
        Excel形式が有効かどうかを判定

        Returns:
            bool: Excel形式が有効な場合True
        """
        excel_config = self.config.get('output_format_excel', {})
        return excel_config.get('enabled', False)

    def get_excel_format_mode(self) -> str:
        """
        Excel形式のモードを取得

        Returns:
            str: Excel形式のモード（"standard" または "excel"）
        """
        excel_config = self.config.get('output_format_excel', {})
        return excel_config.get('mode', 'standard')

    def get_excel_metric_order(self) -> List[Dict[str, Any]]:
        """
        Excel形式専用のメトリクス順序定義を取得

        Returns:
            List[Dict[str, Any]]: Excel形式のメトリクス順序定義
        """
        return self.config.get('excel_metric_order', [])

    def get_metric_no_mapping(self) -> Dict[str, str]:
        """
        メトリクス別no値マッピングを取得

        Returns:
            Dict[str, str]: メトリクス名をキーとしたno値のマッピング
        """
        return self.config.get('metric_no_mapping', {})
