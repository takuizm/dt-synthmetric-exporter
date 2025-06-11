#!/bin/bash
# Dynatrace Synthetic Metrics Export Tool
# Unix/Linux/Mac用実行スクリプト
# Created: 2025-05-30

set -e  # エラー時に終了

# スクリプトのディレクトリに移動
cd "$(dirname "$0")"

# .envファイルの存在チェック
if [ ! -f ".env" ]; then
    echo "❌ エラー: .envファイルが見つかりません"
    echo "📝 env.exampleを参考に.envファイルを作成してください"
    echo ""
    echo "手順:"
    echo "  1. cp env.example .env"
    echo "  2. .envファイルを編集してDynatraceの設定を入力"
    echo "  3. 再度このスクリプトを実行"
    exit 1
fi

# Python仮想環境の確認（オプション）
if [ -d "venv" ]; then
    echo "🐍 Python仮想環境を有効化中..."
    source venv/bin/activate
fi

# 現在のディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# PYTHONPATHを設定
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH}"

# 必要なパッケージのインストール確認
echo "📦 依存関係を確認中..."

# pipをアップグレード（--user オプションを追加）
python3 -m pip install --upgrade pip --user

# 依存関係をインストール（--user オプションを追加）
if ! python3 -m pip install -r requirements.txt --user; then
    echo "❌ 依存関係のインストールに失敗しました"
    exit 1
fi

# Pythonスクリプトを実行
echo "🚀 Dynatrace Synthetic メトリクス エクスポートを開始..."
echo ""

python3 "${SCRIPT_DIR}/src/export_synthetic_metrics.py" "$@"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "✅ 正常に完了しました"
else
    echo ""
    echo "❌ エラーで終了しました (終了コード: $exit_code)"
    echo "📄 詳細はlogsディレクトリのログファイルを確認してください"
fi

exit $exit_code 