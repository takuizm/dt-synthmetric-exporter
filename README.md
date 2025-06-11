# Dynatrace Synthetic メトリクス エクスポーター

## 概要
Dynatraceの合成モニタリング（Synthetic Monitoring）のメトリクスデータをCSVファイルとしてエクスポートするツールです。
複数のモニターの測定結果を一括で取得し、分析可能な形式で出力します。

## 機能
- 合成モニターのメトリクスデータをCSVファイルとして出力
- タグベースのモニターフィルタリング
- 日付による柔軟な期間指定
- 複数のエンコーディング対応（UTF-8 with BOM, Shift-JIS）
- 時間単位の選択（ミリ秒/秒）
- 詳細なログ出力

## 必要条件
- Python 3.8以上
- Dynatraceテナント
- Dynatrace APIトークン（必要な権限: `entities.read`, `metrics.read`）

## セットアップ
1. 必要なパッケージのインストール:
```bash
pip install -r requirements.txt
```

2. 環境変数の設定:
`.env.example`を`.env`にコピーし、以下の値を設定:
```
DT_TENANT=https://[your-environment-id].live.dynatrace.com
DT_TOKEN=your-api-token
```

## 使用方法
### 基本的な使用方法
```bash
# Windows
run.bat

# Linux/Mac
./run.sh
```

### コマンドラインオプション
```bash
python src/export_synthetic_metrics.py [options]

オプション:
  --tags TEXT         タグフィルター (例: "env:prod AND team:web")
  --start YYYYMMDD    取得開始日 (必須)
  --end YYYYMMDD      取得終了日 (必須)
  --encoding          CSVエンコーディング [utf8-bom/sjis] (デフォルト: utf8-bom)
  --time-unit         時間単位 [ms/s] (デフォルト: ms)
  --verbose           詳細ログを表示
```

## 出力メトリクス一覧

### 基本情報フィールド
- `monitor_name`: モニター名
- `frequency`: 監視間隔（分）
- `device`: デバイスタイプ
- `location`: 測定ロケーション
- `tags`: 設定されているタグ

### メトリクス
1. **基本的なパフォーマンスメトリクス**
   - `builtin:synthetic.browser.actionDuration.load`: ページロードアクション時間
   - `builtin:synthetic.browser.firstByte.load`: 最初のバイト受信時間
   - `builtin:synthetic.browser.speedIndex.load`: スピードインデックス
   - `builtin:synthetic.browser.visuallyComplete.load`: 視覚的完了時間
   - `builtin:synthetic.browser.domInteractive.load`: DOMインタラクティブ時間
   - `builtin:synthetic.browser.totalDuration`: 合計実行時間

2. **Core Web Vitals**
   - `builtin:synthetic.browser.cumulativeLayoutShift.load`: 累積レイアウトシフト（CLS）
   - `builtin:synthetic.browser.largestContentfulPaint.load`: 最大コンテンツ描画時間（LCP）

3. **ネットワークパフォーマンス**
   - `builtin:synthetic.browser.networkContribution.load`: ネットワーク寄与時間
   - `builtin:synthetic.browser.serverContribution.load`: サーバー寄与時間
   - `builtin:synthetic.browser.responseEnd.load`: レスポンス完了時間

4. **ロードイベント**
   - `builtin:synthetic.browser.loadEventEnd.load`: ロードイベント完了時間
   - `builtin:synthetic.browser.loadEventStart.load`: ロードイベント開始時間

5. **可用性と成功/失敗**
   - `builtin:synthetic.browser.availability`: 可用性
   - `builtin:synthetic.browser.availability.location.total`: ロケーション別総可用性
   - `builtin:synthetic.browser.availability.location.totalWoMaintenanceWindow`: メンテナンスウィンドウを除く可用性
   - `builtin:synthetic.browser.success`: 成功数
   - `builtin:synthetic.browser.failure`: 失敗数
   - `builtin:synthetic.browser.total`: 総実行数

注: 各メトリクスには地理情報バージョン（`.geo`サフィックス）も利用可能です。

### 統計値
各メトリクスに対して以下の統計値が計算されます：
- `min`: 最小値
- `max`: 最大値
- `avg`: 平均値
- `median`: 中央値
- `stdev`: 標準偏差

## 出力例
```csv
monitor_name,frequency,device,location,metric_name,metric_description,min,max,avg,median,stdev,tags
ホームページ監視,15,BROWSER,Tokyo,synthetic.browser.totalDuration,ページロード合計時間,2264.0,3163.0,2659.7,2650.0,234.5,env:prod,team:web
```

## エラー処理
- API接続エラー時は詳細なエラーメッセージを出力
- データ取得失敗時は該当モニターをスキップして処理継続
- ログファイルは`logs`ディレクトリに出力

## 注意事項
- APIレート制限に対応（リクエスト間隔制御実装済み）
- 一度に長期間（数ヶ月など）を指定すると、APIの制限によりデータが取得できない場合があります。
- 出力ファイルは`output`ディレクトリに生成

## ファイル構成

```
dt-synthmetric-exporter/
├── src/
│   ├── __init__.py
│   ├── export_synthetic_metrics.py  # メインスクリプト
│   ├── dynatrace_client.py         # Dynatrace APIクライアント
│   ├── helpers.py                  # ヘルパー関数
├── OUTPUT/                         # CSVファイル出力ディレクトリ
│   └── synthetic_metrics_*.csv     # 出力されるCSVファイル
├── logs/                          # ログファイル格納ディレクトリ
│   └── *.log                      # 実行ログファイル
├── run.sh                         # Unix/Linux/Mac用実行スクリプト
├── run.bat                        # Windows用実行スクリプト
├── requirements.txt               # Python依存関係
├── env.example                    # 環境変数設定例
└── README.md                      # このファイル
```
