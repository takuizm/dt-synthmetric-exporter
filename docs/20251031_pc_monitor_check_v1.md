# PCモニターのデータ取得不可に関する調査結果

## 概要
- 実行日時: 2025-10-31
- 対象期間: 2025-10-22 ～ 2025-10-30
- タグフィルター: `Industry:RealEstate`

## 問題の詳細

### 取得できなかったモニター（11件）

全て `_PC`（PCデバイス）でのモニタリングです：

1. RealEstate_https://www.hulic.co.jp/sustainability/_PC
2. RealEstate_https://www.leben.co.jp/sustainability/index.html_PC
3. RealEstate_https://www.leopalace21.co.jp/ir/_PC
4. RealEstate_https://sfc.jp/information/sustainability/_PC
5. RealEstate_https://www.nomura-re-hd.co.jp/sustainability/_PC
6. RealEstate_https://www.mitsuifudosan.co.jp/esg_csr/_PC
7. RealEstate_https://tokyu-fudosan-hd-csr.disclosure.site/ja_PC
8. RealEstate_https://www.jinushi-jp.com/sustainability/_PC
9. RealEstate_https://tatemono.com/sustainability/_PC
10. RealEstate_https://www.heiwa-net.co.jp/sustainability/_PC
11. RealEstate_https://www.toseicorp.co.jp/sustainability/_PC

### 共通点
- 全てPCデバイス（`_PC`）での計測
- 全て企業情報ページ（sustainability、ESG、IR等）
- メトリクスのデータポイントが0件

### 技術的な原因

Dynatrace API v2からメトリクスクエリを実行した結果、これらのモニターについては：
- メトリクスは取得できる（空のリスト[]が返される）
- しかし `data_points` が空のため、ツール側でスキップされる

```python
# export_synthetic_metrics.py 122-123行目
if not data_points:
    continue
```

## 推定される原因

### 1. モニターが無効化されている
- Dynatrace UI上でモニターが無効（disabled）になっている可能性

### 2. 計測スケジュールが停止している
- スケジュールが一時停止、または実行頻度が極めて低い可能性

### 3. 計測が全て失敗している
- タイムアウト、ネットワークエラー等で全ての計測が失敗している可能性

## 確認手順

### Dynatrace Web UIでの確認

1. **モニター一覧画面で確認**
   ```
   Synthetic > Monitors
   → 該当のPCモニターを検索
   → ステータスを確認（Enabled/Disabled）
   ```

2. **個別モニターの詳細確認**
   - 各PCモニターの詳細画面を開く
   - 「Availability」タブで実行履歴を確認
   - 直近の実行結果（Success/Failed）を確認

3. **計測頻度の確認**
   - モニターの設定で「Frequency」を確認
   - 計測期間中に実行されるはずの回数を計算

4. **エラーログの確認**
   - 「Events」タブでエラーイベントを確認
   - タイムアウト、DNS解決失敗等のエラーを確認

### APIでの直接確認

以下のコマンドで特定モニターの状態を確認できます：

```bash
# 環境変数を設定
export DT_TENANT="your-tenant-url"
export DT_TOKEN="your-api-token"

# 特定モニターのエンティティ情報を取得
curl -X GET \
  "${DT_TENANT}/api/v2/entities?entitySelector=type(SYNTHETIC_TEST),tag(Industry:RealEstate)&fields=+properties,+tags" \
  -H "Authorization: Api-Token ${DT_TOKEN}"
```

確認ポイント：
- `properties.monitorStatus`: モニターの状態
- `properties.enabled`: 有効/無効
- `properties.frequency`: 計測頻度

## 対応方針

### 短期対応
1. Dynatrace UIで該当PCモニターの状態を確認
2. 無効化されている場合は有効化
3. スケジュールが停止している場合は再開

### 中期対応
1. ツールにwarningログを追加
   - データポイントが0件の場合に明示的にログ出力
   - どのモニター/メトリクスでデータが取得できなかったか記録

2. サマリーレポート機能の追加
   - 処理されたモニター数 vs 出力されたモニター数の差分を表示
   - データが取得できなかったモニターのリストを出力

### 長期対応
1. 計測失敗時の自動アラート設定
2. モニターの稼働状況を定期的に確認する仕組みの構築

## 補足：SPモニターは正常

- 全てのSPモニター（30件）は正常にデータ取得できている
- データポイント数: 20-24件/メトリクス
- Action Duration、可用性、Core Web Vitals等、全メトリクスが取得済み

## まとめ

- **原因**: PCモニターについてDynatraceが計測データを記録していない
- **影響**: 11モニター（全41モニター中）のデータが欠落
- **次のアクション**: Dynatrace UIで該当モニターの状態を確認し、必要に応じて再有効化





