
# Dynatrace Synthetic メトリクス CSV エクスポートツール — 要件定義  
*作成日: 2025-05-30*

---

## 1. 概要  
本ツールは **Dynatrace Synthetic（Browser Test）** のモニターをタグで絞り込み、指定期間（現時刻から過去◯時間）における各メトリクスの統計値を取得し、単一の CSV ファイルとして出力します。  
非エンジニアにも配布できるよう、`.env` を用意して `run.sh` または `run.bat` を実行するだけで完了する設計とします。

---

## 2. 対象範囲  

| カテゴリ | 含む | 含まない |
|----------|------|----------|
| **モニター種別** | Browser Test | HTTP Monitor |
| **メトリクス粒度** | そのモニター／ロケーションに紐づく全メトリクス（細粒度） | カスタムイベント、プライベートロケーションのホストメトリクス |
| **統計値** | `min`, `max`, `avg`, `median`, `stdev` | パーセンタイル (p90, p95 など) |
| **時間ウィンドウ** | 24h / 48h / 72h / 96h / 120h (JST 基準) | 日付指定方式 |
| **実行方法** | 手動のみ（ローカル PC） | 定期ジョブ、スケジューラ |
| **出力** | 単一 CSV (UTF‑8 BOM デフォルト) | データベース登録、ダッシュボード生成 |

---

## 3. 機能要件  

| ID | 要件 |
|----|------|
| **F-01** | タグフィルターを `key:value` AND 結合で受け取り、対象モニターを抽出する。 |
| **F-02** | `--hours` オプションで過去◯時間を受け取り、JST で開始・終了時刻を算出する。 |
| **F-03** | Dynatrace Metrics v2 API で `builtin:synthetic.browser.*` 系メトリクスを取得する。 |
| **F-04** | モニター × ロケーション × メトリクス ごとに `min/max/avg/median/stdev` を API 関数で集計する。 |
| **F-05** | CSV 列順を次の通り固定:  
`モニター名,URL,監視間隔(s),デバイス,ロケーション,メトリクス名,メトリクス説明,Min,Max,Avg,Median,Stdev,タグ` |
| **F-06** | タグ列はカンマ区切り文字列として格納する。 |
| **F-07** | 出力ファイル名は `synthetic_metrics_<YYMMDD>-<YYMMDD>.csv` (期間は開始・終了日)。 |
| **F-08** | ログを `logs/YYYYMMDD_HHMMSS.log` に INFO/ERROR レベルで記録し、ERROR は標準出力にも表示する。 |
| **F-09** | API が 4xx/5xx を返した場合は非ゼロ終了コードで終了する。 |

---

## 4. 非機能要件  

| ID | 要件 |
|----|------|
| **NF-01** | Python 3.10 以上。追加ライブラリは `requests`, `python-dotenv`, `pandas` のみ。 |
| **NF-02** | OS 依存コードを排除し、Mac/Linux 用 `run.sh` と Windows 用 `run.bat` ラッパーで実行可能。 |
| **NF-03** | CSV は既定で UTF‑8 BOM。Excel 互換性のため `--encoding sjis` オプションで Shift‑JIS も選択可。 |
| **NF-04** | PAT とテナント URL は `.env` から読み込み、ログ等に出力しない。 |
| **NF-05** | 100 モニター × 5 ロケーション程度で 60 秒以内に完了し、API レート制限を考慮。 |

---

## 5. CLI 仕様  

```text
usage: python export_synthetic_metrics.py --tags "env:prod AND team:web" --hours 72 [--encoding utf-8] [--verbose]

  --tags       タグフィルタ (Dynatrace 構文)
  --hours      取得期間 (h) 24/48/72/96/120
  --encoding   utf-8 (既定) | sjis
  --verbose    INFO ログをコンソールにも出力
```

---

## 6. ディレクトリ構成  

```text
synthetic-export/
├─ src/
│  ├─ export_synthetic_metrics.py
│  ├─ dynatrace_client.py
│  ├─ helpers.py
│  └─ __init__.py
├─ run.sh
├─ run.bat
├─ .env.example
├─ requirements.txt
└─ logs/
```

---

## 7. .env 例  

```env
DT_TENANT=https://xxxxx.live.dynatrace.com
DT_TOKEN=dt0c01.XXXXXXXXXXXXXXXXXXXX
```

---

## 8. ログ仕様  

* 書式: `{timestamp} [{level}] {message}`  
* 例: `2025-05-30 11:15:42 [INFO] モニター 5 件を取得 (タグ: env:prod AND team:web)`

---

## 9. CSV サンプル行  

```csv
Sample Shop,https://sample.co.jp,300,DESKTOP_CHROME,Tokyo (AWS),builtin:synthetic.browser.totalDuration,"Total duration (ms)",421,685,532.8,530,72.4,env:prod,team:web
```

---

## 10. 将来拡張（Backlog）  

| 優先度 | アイデア |
|--------|----------|
| ☆ | パーセンタイル統計 (`p90`,`p95`) 追加 |
| ☆ | HTTP Monitor 対応 |
| △ | GitHub Actions などによる定期実行 |
| △ | XLSX 形式出力・グラフ自動生成 |

---

## 11. 参照資料  

* Dynatrace API v2 — Metrics リファレンス  
* RFC 4180 付録 B — CSV と BOM  

---

*以上*
