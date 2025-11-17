# バグ修正レポート：二重変換による0.0表示問題

## 概要
- 修正日: 2025-10-31
- バグID: データ取得不良（実際は二重変換バグ）
- 影響範囲: firstByte.load、LCP、その他時間系メトリクスの約61%

## 問題の詳細

### 症状
CSVファイルで以下のメトリクスが実際に計測されているのに `0.0` と表示される：
- `builtin:synthetic.browser.firstByte.load`（初回バイト受信時間）
- `builtin:synthetic.browser.largestContentfulPaint.load`（LCP）
- `builtin:synthetic.browser.speedIndex.load`（一部）

### 具体例：SUUMO SP

**詳細ログ（正常）**：
```
メトリクス: builtin:synthetic.browser.firstByte.load
データポイント数: 24
統計値: {'min': 0.07, 'max': 0.16, 'avg': 0.09, 'median': 0.08, 'stdev': 0.02}
```

**CSV出力（バグ）**：
```csv
RealEstate_https://suumo.jp/sp/_SP,...,firstByte.load,...,0.0,0.0,0.0,0.0,0.0
```

### 影響範囲
- 修正前：90メトリクス中55件（61.1%）が0.0と誤表示
- 修正後：90メトリクス中90件（100%）が正常な値

## 根本原因

### 二重変換バグ

データが2箇所で変換され、1000^2 = 1,000,000で割られていた：

1. **Dynatrace API**: 90ms（ミリ秒）を返す
2. **dynatrace_client.py** (471-474行目):
   ```python
   is_time_metric = self._is_time_metric(metric_key) if metric_key else False
   if is_time_metric and time_unit == 's':
       # ミリ秒から秒に変換
       values_array = values_array / 1000  # 90ms → 0.09s（正しい）
   ```

3. **helpers.py** (旧371-372行目):
   ```python
   if metric_type == 'time':
       df.loc[idx, col] = round(df.loc[idx, col] / 1000, 2)  # 0.09s → 0.00009s
   ```

4. **round処理**: `round(0.00009, 2)` → **0.0**

### なぜ発生したか

- `dynatrace_client.py`で既に秒単位に変換済み
- `helpers.py`でさらに変換しようとした（実装の重複）
- 結果として、値が1,000,000分の1になり、小数点以下2桁に丸められて0.0に

## 修正内容

### 変更ファイル
- `src/helpers.py`

### 修正前（338-382行目）

```python
def convert_units(self, time_unit: str = 'ms') -> 'MetricsDataFrame':
    """時間単位の変換を行う"""
    df = self.df.copy()

    # 監視間隔を分から時間に変換（生データモードのみ）
    if 'frequency' in df.columns:
        df['frequency'] = df['frequency'].apply(
            lambda x: round(float(x) / 60, 2) if isinstance(x, (int, float)) else x
        )

    # メトリクス定義を取得
    metrics_def = self.config.get_metrics()

    # 時間系メトリクスの単位変換（ms → s）とメトリクス説明の更新
    if time_unit == 's':
        # 数値列のみを対象に変換
        numeric_columns = df.select_dtypes(include=['int64', 'float64']).columns
        for col in numeric_columns:
            if col in ['min', 'max', 'avg', 'median', 'stdev']:
                for idx in df.index:
                    # ... 省略 ...
                    metric_type = self._get_metric_type(metric_name, metrics_def)

                    # 時間系メトリクスのみ変換 ← ここで二重変換が発生
                    if metric_type == 'time':
                        df.loc[idx, col] = round(df.loc[idx, col] / 1000, 2)

        # メトリクス説明の単位を更新（生データモードのみ）
        if 'metric_description' in df.columns:
            df['metric_description'] = df.apply(
                lambda row: self._adjust_metric_description(row['metric_description'], time_unit),
                axis=1
            )

    self.df = df
    return self
```

### 修正後（338-360行目）

```python
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
    # 値の変換は dynatrace_client.py で既に完了しているため、ここでは行わない
    if time_unit == 's' and 'metric_description' in df.columns:
        df['metric_description'] = df.apply(
            lambda row: self._adjust_metric_description(row['metric_description'], time_unit),
            axis=1
        )

    self.df = df
    return self
```

### 変更のポイント

1. **削除**: 数値データの変換処理（1000で割る処理）を削除
2. **保持**: メトリクス説明文の単位表記更新のみ保持（「（ms）」→「（s）」）
3. **追加**: コメントで意図を明確化

### 理由

- データの変換は`dynatrace_client.py`で一度だけ行うべき
- `helpers.py`は表示フォーマット（説明文の単位表記）のみを担当
- 責任の分離により、将来的なバグを防止

## 検証結果

### テストケース：SUUMO SP（2025-10-30）

| メトリクス | 修正前（バグ） | 修正後（正常） | 期待値 |
|---|---|---|---|
| firstByte.load (Min) | 0.0 | **0.07** | ✓ |
| firstByte.load (Max) | 0.0 | **0.16** | ✓ |
| firstByte.load (Avg) | 0.0 | **0.09** | ✓ |
| LCP (Min) | 0.0 | **0.36** | ✓ |
| LCP (Max) | 0.0 | **0.51** | ✓ |
| LCP (Avg) | 0.0 | **0.41** | ✓ |

### 全体統計（対象：firstByte、LCP、speedIndex）

| 項目 | 修正前 | 修正後 |
|---|---|---|
| 総メトリクス数 | 90 | 90 |
| 値が0.0（異常） | 55件（61.1%） | 0件（0%） |
| 正常な値 | 35件（38.9%） | 90件（100%） |

## 影響評価

### 過去データへの影響
- 2025-10-22以降に出力された全CSVファイルが影響を受けている可能性
- 修正前のデータは再エクスポートが必要

### 再エクスポートの必要性
既存の分析やレポートで以下のメトリクスを使用している場合、再エクスポートが必要：
- `builtin:synthetic.browser.firstByte.load`
- `builtin:synthetic.browser.largestContentfulPaint.load`
- その他の時間系メトリクス

### 実行コマンド（再エクスポート用）
```bash
python3 src/export_synthetic_metrics.py \
  --tags "Industry:RealEstate" \
  --start 20251022 \
  --end 20251030 \
  --time-unit s
```

## 今後の対策

### 1. ユニットテストの追加
```python
def test_no_double_conversion():
    """時間単位が二重変換されないことを確認"""
    # dynatrace_client.py で変換済みのデータを準備
    data = [{'metric_name': 'firstByte.load', 'avg': 0.09}]  # 90ms → 0.09s

    # helpers.py で処理
    df = MetricsDataFrame(data, config)
    df.convert_units('s')

    # 値が変わらないことを確認
    assert df.df['avg'][0] == 0.09  # 0.00009 になっていないこと
```

### 2. コードレビューチェックリスト
- [ ] 単位変換が複数箇所で行われていないか
- [ ] 変換処理の責任が明確に分離されているか
- [ ] コメントで意図が明確に記載されているか

### 3. ログ出力の改善
```python
# 変換前後の値をログ出力
logging.debug(f"変換前: {value_ms}ms")
logging.debug(f"変換後: {value_s}s")
```

## まとめ

### 原因
- データ変換処理が`dynatrace_client.py`と`helpers.py`の2箇所に実装されていた
- 結果として二重変換が発生し、値が1,000,000分の1になった

### 修正
- `helpers.py`から数値変換処理を削除
- 説明文の単位表記更新のみを保持

### 効果
- 61.1%のデータが正常に表示されるようになった
- データの精度が100%に改善

### 今後
- ユニットテストの追加
- コードレビュー基準の強化
- ログ出力の改善

---

**修正者**: AI Assistant
**承認者**: （要確認）
**適用ブランチ**: main
**関連Issue**: データ取得不良調査





