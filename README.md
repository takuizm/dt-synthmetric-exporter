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
- **評価モード**: メトリクス基準値に基づく合否判定機能
- **Excel形式対応**: Excel貼り付け用の列配置で出力
- 詳細なログ出力

## 必要条件
- Python 3.8以上（Python 3.13.4完全対応）
- Dynatraceテナント
- Dynatrace APIトークン（必要な権限: `entities.read`, `metrics.read`）

## 初回セットアップ手順（重要）

### 1. Python環境の確認
まず、お使いのコンピューターにPython 3.8以上がインストールされているか確認します。

**Windows の場合：**
1. コマンドプロンプトを開く（Windowsキー + R → `cmd` と入力 → Enter）
2. 以下のコマンドを実行：
```cmd
python --version
```
または
```cmd
python3 --version
```

**Mac/Linux の場合：**
1. ターミナルを開く
2. 以下のコマンドを実行：
```bash
python3 --version
```

**結果の確認：**
- `Python 3.8.x` 以上が表示されればOK
- 表示されない場合は、[Python公式サイト](https://www.python.org/downloads/)からダウンロードしてインストールしてください

### 2. ツールのダウンロードと配置
1. このツールのフォルダー全体をお使いのコンピューターにコピーします
2. フォルダー名を確認：`dt-synthmetric-exporter`

### 3. 必要なライブラリのインストール

**重要：この手順は初回のみ実行します**

**Windows の場合：**
1. エクスプローラーで `dt-synthmetric-exporter` フォルダーを開く
2. フォルダー内でShift + 右クリック →「PowerShellウィンドウをここで開く」を選択
3. 以下のコマンドを実行：
```powershell
python -m pip install --upgrade pip --user
python -m pip install -r requirements.txt --user
```

**Mac/Linux の場合：**

**方法1：直接インストール（推奨・もっとも簡単）**
```bash
cd パス/to/dt-synthmetric-exporter
python3 -m pip install -r requirements.txt --break-system-packages
```

**方法2：仮想環境を使用（より安全だが手間がかかる）**
```bash
cd パス/to/dt-synthmetric-exporter

# 仮想環境を作成
python3 -m venv venv

# 仮想環境を有効化
source venv/bin/activate

# 必要なライブラリをインストール
python3 -m pip install -r requirements.txt
```

**注意：** 方法1がもっとも簡単です。`--break-system-packages` フラグによりシステムの制限を回避できます。企業環境では一般的に使用されている方法です。

### 4. Dynatrace API設定の準備

#### 4-1. APIトークンの取得
1. Dynatraceにログイン
2. 左メニューから「Access tokens」を検索して選択
3. 「Generate new token」をクリック
4. トークン名を入力（例：`SyntheticMetricsExporter`）
5. 以下の権限にチェックを入れる：
   - `entities.read`
   - `metrics.read`
6. 「Generate token」をクリック
7. **表示されたトークンをコピーして安全な場所に保存**（後で使用）

#### 4-2. テナントURLの確認
1. DynatraceのURLを確認します
2. 例：`https://abc12345.live.dynatrace.com` の形式

### 5. 環境設定ファイルの作成

**重要：この手順を正確に実行してください**

1. `dt-synthmetric-exporter` フォルダー内の `env.example` ファイルを確認
2. このファイルをコピーして `.env` という名前で保存
   - **Windows：** `env.example` を右クリック → コピー → 同じフォルダーに貼り付け → 名前を `.env` に変更
   - **Mac/Linux：** ターミナルで `cp env.example .env` を実行

3. `.env` ファイルをテキストエディターで開く
4. 以下の部分を実際の値に変更：
```
DT_TENANT=https://あなたのテナントID.live.dynatrace.com
DT_TOKEN=あなたのAPIトークン
```

**例：**
```
DT_TENANT=https://abc12345.live.dynatrace.com
DT_TOKEN=dt0c01.ST2EY72KQINMH4J7LRS56XCK
```

5. ファイルを保存

## 使用方法

### 基本的な使い方（推奨）

**Windows の場合：**
1. `dt-synthmetric-exporter` フォルダーを開く
2. `run.bat` ファイルをダブルクリック
3. 画面の指示にしたがって以下を入力：
   - 開始日（例：20241201）
   - 終了日（例：20241207）

**Mac/Linux の場合：**
1. ターミナルで `dt-synthmetric-exporter` フォルダーに移動
2. 以下のコマンドを実行：
```bash
./run.sh --start 20241201 --end 20241207
```

**注意：** セットアップで方法2（仮想環境）を選択した場合のみ、実行前に以下が必要です：
```bash
source venv/bin/activate
```

### 詳細オプション付きの実行

より詳細な設定で実行したい場合：

**Windows：**
```cmd
run.bat --start 20241201 --end 20241207 --tags "env:prod" --encoding sjis
```

**Mac/Linux：**
```bash
./run.sh --start 20241201 --end 20241207 --tags "env:prod" --encoding sjis
```

### コマンドラインオプション
```bash
--start YYYYMMDD    取得開始日 (必須)
--end YYYYMMDD      取得終了日 (必須)
--tags TEXT         タグフィルター (例: "env:prod AND team:web")
--output-mode       出力モード [standard/evaluation] (デフォルト: standard)
--encoding          CSVエンコーディング [utf8-bom/sjis] (デフォルト: utf8-bom)
--time-unit         時間単位 [ms/s] (デフォルト: ms)
--verbose           詳細ログを表示
```

## 出力モード

### 標準モード（standard）
すべてのメトリクスを統計値（Min/Max/Avg/Median/Stdev）と共に出力します。

**使用例：**
```bash
./run.sh --start 20241201 --end 20241207
# または明示的に指定
./run.sh --start 20241201 --end 20241207 --output-mode standard
```

### 評価モード（evaluation）
メトリクスの基準値に基づいて合否判定を行い、評価結果と平均値のみを出力します。

**使用例：**
```bash
./run.sh --start 20241201 --end 20241207 --output-mode evaluation
```

**評価基準の設定：**
`config/metrics.yaml`で各メトリクスの基準値を設定できます。

**評価基準例：**
- Action Duration: 2.0秒以下（通常基準）/ 1.0秒以下（厳格基準）
- Largest Contentful Paint (LCP): 2.0秒以下
- 稼働率: 99.9%以上
- Cumulative Layout Shift (CLS): 0.1以下
- Time to first byte: 0.2秒以下
- Speed Index: 0.4秒以下

**出力例：**
```csv
code,corporate,no,code+no,メトリクス名:説明,評価,AVG,URL,index,タグ
,,,,"モニター名：Action Duration（表示速度）は2.0秒以下",1,1.8,,1,env:prod
,,,,"モニター名：稼働率は99.9％以上",0,99.5,,2,env:prod
```

評価列の値：
- `1`: 合格（基準値をクリア）
- `0`: 不合格（基準値を超過）
- `-1`: 基準値未設定

### Excel形式対応
評価モードでExcel貼り付け用の列配置で出力できます。

**設定方法：**
`config/metrics.yaml`で以下を設定：
```yaml
output_format_excel:
  enabled: true
  mode: "excel"
```

**Excel形式の列構成：**
- Action Duration
- Largest Contentful Paint（LCP）
- 稼働率
- Cumulative Layout Shift（CLS）
- Time to first byte
- Speed Index

各行のメトリクスは該当する列にのみ値が入り、他の列は空欄になります。

詳細は `docs/20250101_excel_format_test_v1.md` を参照してください。

## 出力ファイルの確認

実行が完了すると、以下の場所にファイルが作成されます：

1. **CSVファイル：** `output` フォルダー内
   - ファイル名例：`synthetic_metrics_20241201_20241207.csv`

2. **ログファイル：** `logs` フォルダー内
   - 実行結果の詳細が記録されます

## トラブルシューティング

### よくあるエラーと対処法

**1. "externally-managed-environment" エラー（Mac/Linux）**
- 対処法：仮想環境を使用する（セットアップ手順3を参照）
- または、以下のコマンドで強制インストール（非推奨）：
```bash
python3 -m pip install -r requirements.txt --break-system-packages
```

**2. "python は認識されません" エラー（Windows）**
- 対処法：`python3` を `python` に置き換えて実行

**3. ".envファイルが見つかりません" エラー**
- 対処法：セットアップ手順5を再度実行

**4. "API接続に失敗しました" エラー**
- 対処法：
  - `.env` ファイルのテナントURLとAPIトークンを確認
  - ネットワーク接続を確認
  - Dynatraceにログインできるか確認

**5. "モニターが見つかりませんでした" エラー**
- 対処法：
  - Dynatraceに合成モニターが設定されているか確認
  - タグフィルターを指定している場合は、正しいタグ名か確認

**6. "Permission denied" エラー（Mac/Linux）**
- 対処法：実行権限を付与
```bash
chmod +x run.sh
```

### サポート情報

問題が解決しない場合は、以下の情報を管理者に報告してください：
- エラーメッセージの全文
- 実行したコマンド
- `logs` フォルダー内の最新ログファイルの内容

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
│   ├── config.py                   # 設定読み込み
│   ├── helpers.py                  # ヘルパー関数
├── config/
│   └── metrics.yaml                # メトリクス設定・評価基準
├── docs/                           # ドキュメント
│   ├── dynatrace_synthetic_metrics_requirements_ja.md  # 初期要件定義
│   ├── 20250101_excel_format_test_v1.md               # Excel形式実装報告
│   ├── 20251031_bugfix_double_conversion_v1.md        # バグ修正レポート
│   └── 20251031_pc_monitor_check_v1.md                # 調査報告
├── output/                         # CSVファイル出力ディレクトリ
│   └── synthetic_metrics_*.csv     # 出力されるCSVファイル
├── logs/                          # ログファイル格納ディレクトリ
│   └── *.log                      # 実行ログファイル
├── run.sh                         # Unix/Linux/Mac用実行スクリプト
├── run.bat                        # Windows用実行スクリプト
├── requirements.txt               # Python依存関係
├── env.example                    # 環境変数設定例
└── README.md                      # このファイル
```
