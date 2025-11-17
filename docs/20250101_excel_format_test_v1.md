# Excel形式対応 実装完了報告

## 実装概要

評価モードの出力フォーマットをExcel貼り付け用の形式に変更いたしました。

### 変更内容

#### 1. 設定ファイル修正（config/metrics.yaml）
- Excel形式用CSV列定義を追加
- メトリクスとExcel列の対応関係を定義
- Excel形式有効化設定を追加

#### 2. 設定読み込み機能追加（src/config.py）
- `get_csv_columns_evaluation_excel()` - Excel形式列定義取得
- `get_excel_metric_column_mapping()` - メトリクス列マッピング取得
- `is_excel_format_enabled()` - Excel形式有効判定
- `get_excel_format_mode()` - Excel形式モード取得

#### 3. 出力処理修正（src/helpers.py）
- `format_for_evaluation_export_excel()` - Excel形式整形メソッド追加
- `export_to_csv()` - Excel形式判定ロジック追加

## 出力フォーマット

### 列構成（K列～P列）
| 列 | 内容 | 対応メトリクス |
|---|---|---|
| K列 | Action Duration | builtin:synthetic.browser.actionDuration.load |
| L列 | Largest Contentful Paint（LCP） | builtin:synthetic.browser.largestContentfulPaint.load |
| M列 | 稼働率 | builtin:synthetic.browser.availability |
| N列 | Cumulative Layout Shift（CLS） | builtin:synthetic.browser.cumulativeLayoutShift.load |
| O列 | Time to first byte | builtin:synthetic.browser.firstByte.load |
| P列 | Speed Index | builtin:synthetic.browser.speedIndex.load |

### 出力例
```
指標名 | K列 | L列 | M列 | N列 | O列 | P列
ESGトップページ：Action Duration（表示速度）は2.0秒以下 | 1.8 | (空欄) | (空欄) | (空欄) | (空欄) | (空欄)
ESGトップページ：Action Duration（表示速度）は1.0秒以下 | 1.8 | (空欄) | (空欄) | (空欄) | (空欄) | (空欄)
ESGトップページ：Largest Contentful Paint（LCP）は2.0秒以下 | (空欄) | 1.5 | (空欄) | (空欄) | (空欄) | (空欄)
ESGトップページ：計測期間中の稼働率は99.9％以上 | (空欄) | (空欄) | 99.8 | (空欄) | (空欄) | (空欄)
ESGトップページ：Cumulative Layout Shift（CLS）は0.1秒以下 | (空欄) | (空欄) | (空欄) | 0.05 | (空欄) | (空欄)
ESGトップページ：Time to first byteは0.2秒以下 | (空欄) | (空欄) | (空欄) | (空欄) | 0.15 | (空欄)
ESGトップページ：Speed Indexは0.4秒以下 | (空欄) | (空欄) | (空欄) | (空欄) | (空欄) | 0.35
```

## 使用方法

### 現在の使用方法（変更なし）
```bash
python src/export_synthetic_metrics.py --start 20241201 --end 20241207 --output-mode evaluation
```

### Excel形式を有効にする場合
`config/metrics.yaml`の設定を確認：
```yaml
output_format_excel:
  enabled: true
  mode: "excel"  # "standard" または "excel"
```

- `enabled: true` - Excel形式を有効化
- `mode: "excel"` - Excel形式で出力
- `mode: "standard"` - 従来形式で出力

## 実装確認事項

### ✅ 完了項目
1. 設定ファイルにExcel形式定義を追加
2. 設定読み込み機能を追加
3. Excel形式出力処理を実装
4. メトリクス値の適切な列への配置ロジックを実装
5. Action Durationの複数基準対応を維持

### 📝 注意事項
1. Excel形式では評価値（合格/不合格）は出力されません
2. 各指標行では該当するメトリクスの列にのみ実測値が入り、他の列は空欄になります
3. Action Durationの2つの基準（2.0秒、1.0秒）は両方ともK列に出力されます

## テスト推奨項目
1. 評価モードでの動作確認
2. Excel形式有効/無効の切り替え確認
3. 各メトリクスが適切な列に配置されることの確認
4. Action Durationの複数基準が正常に動作することの確認
