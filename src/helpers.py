"""
Dynatrace Synthetic Metrics Export Tool - Helper Functions
ヘルパー関数モジュール

Created: 2025-05-30
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import pandas as pd
import csv
import re
from config import Config


def setup_logging(verbose: bool = False) -> str:
    """
    ログ設定を初期化し、ログファイルパスを返す

    Args:
        verbose: コンソールにINFOレベルのログも出力するか

    Returns:
        str: ログファイルのパス
    """
    # ログディレクトリが存在しない場合は作成
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # ログファイル名: YYYYMMDD_HHMMSS.log
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"{timestamp}.log")

    # ログ設定
    log_level = logging.INFO if verbose else logging.ERROR

    # ルートロガーの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler() if verbose else logging.StreamHandler()
        ]
    )

    # コンソールハンドラーのレベルを調整
    console_handler = logging.getLogger().handlers[1]
    console_handler.setLevel(log_level)

    return log_file


def parse_date_range(start_date_str: str, end_date_str: str) -> tuple[str, str]:
    """
    YYYYMMDD形式の日付文字列(JST)をAPI用のUTC ISO 8601形式のタイムスタンプに変換する。

    Args:
        start_date_str: 開始日 (YYYYMMDD) - JSTとして解釈
        end_date_str: 終了日 (YYYYMMDD) - JSTとして解釈

    Returns:
        tuple: (開始時刻UTC ISO文字列, 終了時刻UTC ISO文字列)

    Raises:
        ValueError: 日付形式が不正な場合
    """
    if not re.match(r"^\d{8}$", start_date_str) or not re.match(r"^\d{8}$", end_date_str):
        raise ValueError("日付は YYYYMMDD 形式で指定してください。")

    try:
        # JSTタイムゾーンを定義
        JST = timezone(timedelta(hours=9))

        # 入力文字列を naive datetime オブジェクトとしてパース
        start_date_naive = datetime.strptime(start_date_str, "%Y%m%d")
        end_date_naive = datetime.strptime(end_date_str, "%Y%m%d")

    except ValueError:
        raise ValueError("日付の形式が正しくありません (YYYYMMDD)。")

    if start_date_naive > end_date_naive:
        raise ValueError("開始日は終了日より前に設定してください。")

    # JSTの日の始まりと終わりをタイムゾーン付きで表現
    start_dt_jst = datetime(start_date_naive.year, start_date_naive.month, start_date_naive.day, 0, 0, 0, tzinfo=JST)
    end_dt_jst = datetime(end_date_naive.year, end_date_naive.month, end_date_naive.day, 23, 59, 59, tzinfo=JST)

    # UTCに変換
    start_dt_utc = start_dt_jst.astimezone(timezone.utc)
    end_dt_utc = end_dt_jst.astimezone(timezone.utc)

    # APIで要求されるISO形式 (Z-suffix) に変換
    start_iso = start_dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end_dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    return start_iso, end_iso


def get_date_range_for_filename(start_date: str, end_date: str) -> str:
    """
    ファイル名用の日付範囲文字列を生成 (YYYYMMDD または YYYYMMDD-YYYYMMDD)

    Args:
        start_date: 開始日 (YYYYMMDD)
        end_date: 終了日 (YYYYMMDD)

    Returns:
        str: YYYYMMDD-YYYYMMDD形式の文字列
    """
    start_yyyymmdd = datetime.strptime(start_date, "%Y%m%d").strftime("%Y%m%d")
    end_yyyymmdd = datetime.strptime(end_date, "%Y%m%d").strftime("%Y%m%d")

    if start_yyyymmdd == end_yyyymmdd:
        return start_yyyymmdd
    else:
        return f"{start_yyyymmdd}-{end_yyyymmdd}"


def format_tags_for_csv(tags: List[Dict[str, str]]) -> str:
    """
    タグリストをCSV用の文字列に変換

    Args:
        tags: タグのリスト [{"key": "env", "value": "prod"}, ...]

    Returns:
        str: カンマ区切りのタグ文字列
    """
    if not tags:
        return ""

    tag_strings = [f"{tag['key']}:{tag['value']}" for tag in tags]
    return ",".join(tag_strings)


def create_output_filename(start_date: str, end_date: str) -> str:
    """
    出力CSVファイル名を生成

    Args:
        start_date: 開始日 (YYYYMMDD)
        end_date: 終了日 (YYYYMMDD)

    Returns:
        str: ファイル名
    """
    date_range = get_date_range_for_filename(start_date, end_date)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"synthetic_metrics_{date_range}_{timestamp}.csv"


def sort_metrics_data(df: pd.DataFrame, config: Config) -> pd.DataFrame:
    """
    メトリクスデータをソート

    Args:
        df: ソート対象のDataFrame
        config: 設定オブジェクト

    Returns:
        pd.DataFrame: ソート済みのDataFrame
    """
    # カテゴリー順序の取得
    category_order = config.get_category_order()
    metric_order = config.get_metric_order()

    # カテゴリーとメトリクス順序の列を一時的に追加
    df['category_order'] = df['metric_name'].apply(
        lambda x: category_order.get(config.get_metric_category(x), 999)
    )

    df['metric_order'] = df.apply(
        lambda row: metric_order.get(
            config.get_metric_category(row['metric_name']), {}
        ).get(row['metric_name'], 999),
        axis=1
    )

    # ソート実行
    df = df.sort_values([
        'monitor_name',      # モニター名で第一ソート
        'category_order',    # カテゴリー順で第二ソート
        'metric_order',      # メトリクス順で第三ソート
        'location'           # ロケーションで第四ソート
    ])

    # 一時列を削除
    df = df.drop(['category_order', 'metric_order'], axis=1)

    return df


def save_metrics_to_csv(metrics_data: List[Dict[str, Any]],
                       filename: str,
                       encoding: str = 'utf-8') -> None:
    """
    メトリクスデータをCSVファイルに保存

    Args:
        metrics_data: メトリクスデータのリスト
        filename: 出力ファイル名
        encoding: エンコーディング（utf-8 または sjis）
    """
    if not metrics_data:
        logging.warning("保存するデータがありません")
        return

    # 設定を取得
    config = Config()
    columns = config.get_csv_columns()

    # DataFrameを作成（内部キーを使用）
    df = pd.DataFrame(metrics_data)

    # ソート処理を実行
    df = sort_metrics_data(df, config)

    # 列名を表示名に変換
    column_mapping = {col['key']: col['display_name'] for col in columns}
    df = df.rename(columns=column_mapping)

    # 必要な列のみを選択し、設定された順序で並び替え
    display_names = [col['display_name'] for col in sorted(columns, key=lambda x: x.get('order', 999))]
    df = df[display_names]

    # エンコーディング設定
    if encoding.lower() == 'sjis':
        encoding_name = 'shift_jis'
    else:
        encoding_name = 'utf-8-sig'  # BOM付きUTF-8

    try:
        # CSVファイルに保存
        df.to_csv(filename, index=False, encoding=encoding_name)

        logging.info(f"CSVファイルを保存しました: {filename}")
        logging.info(f"  - 行数: {len(df)}")
        logging.info(f"  - エンコーディング: {encoding}")

    except Exception as e:
        logging.error(f"CSVファイル保存に失敗しました: {e}")
        raise


def validate_hours(hours: int) -> bool:
    """
    時間の値が有効かチェック

    Args:
        hours: チェックする時間値

    Returns:
        bool: 有効かどうか
    """
    valid_hours = [24, 48, 72, 96, 120]
    return hours in valid_hours


def validate_encoding(encoding: str) -> bool:
    """
    エンコーディングの値が有効かチェック

    Args:
        encoding: チェックするエンコーディング

    Returns:
        bool: 有効かどうか
    """
    valid_encodings = ['utf-8', 'sjis']
    return encoding.lower() in valid_encodings


class MetricsDataFrame:
    """メトリクスデータを扱うDataFrameラッパークラス"""

    def __init__(self, metrics_data: List[Dict[str, Any]], config: Config):
        """
        Args:
            metrics_data: APIから取得したメトリクスデータ
            config: 設定オブジェクト
        """
        self.config = config
        self.df = self._create_dataframe(metrics_data)

    def _create_dataframe(self, metrics_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """メトリクスデータからDataFrameを作成"""
        if not metrics_data:
            raise ValueError("メトリクスデータが空です")
        return pd.DataFrame(metrics_data)

    def _is_time_metric(self, metric_key: str, metrics_def: List[Dict[str, Any]]) -> bool:
        """時間系メトリクスかどうかを判定"""
        # 除外するメトリクスパターン
        exclude_patterns = [
            'total',           # カウンター系
            'availability',    # パーセンテージ系
            'success',        # パーセンテージ系
            'failure',        # パーセンテージ系
        ]

        # 除外パターンに一致する場合はFalse
        if any(pattern in metric_key.lower() for pattern in exclude_patterns):
            return False

        # メトリクス定義から判定
        for metric in metrics_def:
            if metric['key'] == metric_key:
                desc = metric.get('description', '').lower()
                # 時間を表す単位が説明文に含まれているか確認
                return '（ms）' in desc or '(ms)' in desc or 'duration' in metric_key.lower()

        return False

    def _get_metric_type(self, metric_key: str, metrics_def: List[Dict[str, Any]]) -> str:
        """メトリクスの種類を判定"""
        for metric in metrics_def:
            if metric['key'] == metric_key:
                desc = metric.get('description', '').lower()
                if '（%）' in desc or '(%)' in desc:
                    return 'percentage'
                elif metric.get('aggregation') == 'counter':
                    return 'counter'
                elif '（ms）' in desc or '(ms)' in desc or 'duration' in metric_key.lower():
                    return 'time'
        return 'other'

    def _adjust_metric_description(self, description: str, time_unit: str) -> str:
        """メトリクス説明の単位表記を調整"""
        if time_unit == 's':
            description = description.replace('（ms）', '（s）').replace('(ms)', '(s)')
        return description

    def convert_units(self, time_unit: str = 'ms') -> 'MetricsDataFrame':
        """時間単位の変換を行う

        注意: dynatrace_client.py で既に時間単位の変換が行われているため、
        このメソッドでは単位変換は行わず、説明文の単位表記のみ更新する。
        """
        df = self.df.copy()

        # 監視間隔を分から時間に変換（生データモードのみ）
        if 'frequency' in df.columns:
            df['frequency'] = df['frequency'].apply(
                lambda x: round(float(x) / 60, 2) if isinstance(x, (int, float)) else x
            )

        # メトリクス説明の単位を更新（生データモードのみ）
        if time_unit == 's' and 'metric_description' in df.columns:
            df['metric_description'] = df.apply(
                lambda row: self._adjust_metric_description(row['metric_description'], time_unit),
                axis=1
            )

        self.df = df
        return self

    def sort_by_monitor(self) -> 'MetricsDataFrame':
        """モニター名とメトリクス設定に基づいてソート"""
        df = self.df.copy()

        # カテゴリーとメトリクスの順序を取得
        category_order = self.config.get_category_order()
        metric_order = self.config.get_metric_order()

        # 評価付きモードかどうかで列名を判定
        if 'metric_full_name' in df.columns:
            # 評価付きモード: metric_full_nameからメトリクス名を抽出
            def get_metric_name(metric_full_name):
                return metric_full_name.split(':')[0] if ':' in metric_full_name else metric_full_name

            # ソート用の一時的な列を追加
            df['category_order'] = df['metric_full_name'].apply(
                lambda x: category_order.get(self.config.get_metric_category(get_metric_name(x)), 999)
            )
            df['metric_order'] = df.apply(
                lambda row: metric_order.get(
                    self.config.get_metric_category(get_metric_name(row['metric_full_name'])), {}
                ).get(get_metric_name(row['metric_full_name']), 999),
                axis=1
            )

            # 評価付きモードでは簡単なソート
            df = df.sort_values([
                'category_order',    # カテゴリー順で第一ソート
                'metric_order'       # メトリクス順で第二ソート
            ])
        else:
            # 生データモード: 従来の処理
            df['category_order'] = df['metric_name'].apply(
                lambda x: category_order.get(self.config.get_metric_category(x), 999)
            )
            df['metric_order'] = df.apply(
                lambda row: metric_order.get(
                    self.config.get_metric_category(row['metric_name']), {}
                ).get(row['metric_name'], 999),
                axis=1
            )

            # ソートを実行
            df = df.sort_values([
                'monitor_name',      # モニター名で第一ソート
                'category_order',    # カテゴリー順で第二ソート
                'metric_order',      # メトリクス順で第三ソート
                'location'           # ロケーションで第四ソート
            ])

        # 一時列を削除
        df = df.drop(['category_order', 'metric_order'], axis=1)

        self.df = df
        return self

    def format_for_export(self) -> 'MetricsDataFrame':
        """出力用にデータを整形"""
        df = self.df.copy()
        columns = self.config.get_csv_columns()

        # 列名を表示名に変換
        column_mapping = {col['key']: col['display_name'] for col in columns}
        df = df.rename(columns=column_mapping)

        # 列の順序を設定
        display_names = [
            col['display_name']
            for col in sorted(columns, key=lambda x: x.get('order', 999))
        ]
        df = df[display_names]

        self.df = df
        return self

    def format_for_evaluation_export(self) -> 'MetricsDataFrame':
        """評価付きモード用にデータを整形"""
        df = self.df.copy()

        # index番号を設定（1から開始）
        df['index'] = range(1, len(df) + 1)

        # 評価付きモード用の列定義を取得
        columns = self.config.get_csv_columns_evaluation()

        # 列名を表示名に変換
        column_mapping = {col['key']: col['display_name'] for col in columns}
        df = df.rename(columns=column_mapping)

        # 列の順序を設定
        display_names = [
            col['display_name']
            for col in sorted(columns, key=lambda x: x.get('order', 999))
        ]
        df = df[display_names]

        self.df = df
        return self

    def format_for_evaluation_export_excel(self) -> 'MetricsDataFrame':
        """Excel形式評価付きモード用にデータを整形"""
        df = self.df.copy()

        # index番号を設定（1から開始）
        df['index'] = range(1, len(df) + 1)

        # メトリクスと列の対応関係を取得
        metric_column_mapping = self.config.get_excel_metric_column_mapping()

        # 各メトリクス用の列を初期化（空欄）
        for column_key in metric_column_mapping.values():
            df[column_key] = ""

        # 各行について、該当するメトリクスの列にのみ平均値を設定
        for idx in df.index:
            if 'metric_full_name' in df.columns:
                # 評価付きモード: metric_full_nameからメトリクス名を抽出
                metric_full_name = df.loc[idx, 'metric_full_name']

                # 正規表現を使ってメトリクス名を確実に抽出
                import re
                if metric_full_name.startswith('builtin:'):
                    # Action Durationの場合のサフィックス（1）（2）を除去
                    if '（1）' in metric_full_name or '（2）' in metric_full_name:
                        metric_name = 'builtin:synthetic.browser.actionDuration.load'
                    else:
                        # "builtin:synthetic.browser.xxxxx.load:説明"から"builtin:synthetic.browser.xxxxx.load"を抽出
                        pattern = r'^(builtin:synthetic\.browser\.[^:]+)'
                        match = re.match(pattern, metric_full_name)
                        if match:
                            metric_name = match.group(1)
                        else:
                            # フォールバック: 最初の:で分割
                            metric_name = metric_full_name.split(':')[0] if ':' in metric_full_name else metric_full_name
                else:
                    metric_name = metric_full_name.split(':')[0] if ':' in metric_full_name else metric_full_name
            else:
                # 生データモード: metric_nameを使用
                metric_name = df.loc[idx, 'metric_name']

            # メトリクスに対応する列を特定
            target_column = metric_column_mapping.get(metric_name)
            if target_column:
                # 該当する列に平均値を設定
                avg_value = df.loc[idx, 'avg']
                if avg_value is not None and avg_value != "":
                    df.loc[idx, target_column] = avg_value
                    logging.debug(f"設定: {metric_name} -> {target_column} = {avg_value}")
                else:
                    logging.warning(f"平均値が空です: {metric_name}, avg={avg_value}")
            else:
                logging.warning(f"対応する列が見つかりません: {metric_name} (元: {metric_full_name if 'metric_full_name' in df.columns else 'N/A'})")

                # Excel形式専用のソート処理（URL内でのメトリクス順序）
        excel_order = self.config.get_excel_metric_order()
        if excel_order:
            def get_excel_sort_order(metric_full_name):
                for i, order_def in enumerate(excel_order):
                    pattern = order_def.get('metric_pattern', '')
                    if pattern in metric_full_name:
                        return order_def.get('order', 999)
                return 999  # 定義されていないメトリクスは最後に

            # monitor_nameでグループ化（同じモニターのデータをグループ化）
            df['excel_sort_order'] = df['metric_full_name'].apply(get_excel_sort_order)
            df = df.sort_values(['monitor_name', 'excel_sort_order'])
            df = df.drop('excel_sort_order', axis=1)

        # Excel形式用の列定義を取得
        columns = self.config.get_csv_columns_evaluation_excel()

        # 列名を表示名に変換
        column_mapping = {col['key']: col['display_name'] for col in columns}
        df = df.rename(columns=column_mapping)

        # 列の順序を設定
        display_names = [
            col['display_name']
            for col in sorted(columns, key=lambda x: x.get('order', 999))
        ]
        df = df[display_names]

        self.df = df
        return self

    def to_csv(self, filepath: str, encoding: str = 'utf-8-sig') -> None:
        """CSVファイルに保存"""
        self.df.to_csv(filepath, index=False, encoding=encoding)


def export_to_csv(metrics_data: List[Dict[str, Any]], start_date: str, end_date: str,
                 encoding: str = 'utf8-bom', output_dir: str = ".",
                 time_unit: str = 'ms', output_mode: str = 'raw') -> str:
    """
    メトリクスデータを整形してCSVファイルに出力

    Args:
        metrics_data: Dynatraceから取得したメトリクスデータのリスト
        start_date: 開始日 (YYYYMMDD)
        end_date: 終了日 (YYYYMMDD)
        encoding: CSVのエンコーディング
        output_dir: 出力先ディレクトリ
        time_unit: 時間の単位 ('ms' or 's')
        output_mode: 出力モード ('raw' or 'evaluation')

    Returns:
        str: 出力したCSVファイルのパス
    """
    if not metrics_data:
        logging.warning("エクスポートするデータがありません。")
        return ""

    # ファイル名生成
    filename = create_output_filename(start_date, end_date)
    filepath = os.path.join(output_dir, filename)

    # 設定読み込み
    config = Config()

    try:
        # MetricsDataFrame を使用して処理
        metrics_df = MetricsDataFrame(metrics_data, config)

        if config.is_evaluation_mode(output_mode):
            # 評価付きモード: Excel形式か従来形式かを判定
            if config.is_excel_format_enabled() and config.get_excel_format_mode() == 'excel':
                # Excel形式での出力（独自ソートを使用）
                (metrics_df.convert_units(time_unit)
                           .format_for_evaluation_export_excel())
            else:
                # 従来の評価付きモード処理
                (metrics_df.convert_units(time_unit)
                           .sort_by_monitor()
                           .format_for_evaluation_export())
        else:
            # 生データモード: 従来の処理
            (metrics_df.convert_units(time_unit)
                       .sort_by_monitor()
                       .format_for_export())

        # CSV保存
        actual_encoding = 'shift_jis' if encoding.lower() == 'sjis' else 'utf-8-sig'
        metrics_df.to_csv(filepath, encoding=actual_encoding)

        logging.info(f"  - エンコーディング: {encoding}")

    except Exception as e:
        logging.error(f"CSVエクスポート処理中にエラー: {e}", exc_info=True)
        raise

    return filepath
