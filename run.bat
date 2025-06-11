@echo off
REM Dynatrace Synthetic Metrics Export Tool
REM Windows用実行スクリプト
REM Created: 2025-05-30

setlocal enabledelayedexpansion

REM スクリプトのディレクトリに移動
cd /d "%~dp0"

REM .envファイルの存在チェック
if not exist ".env" (
    echo ❌ エラー: .envファイルが見つかりません
    echo 📝 env.exampleを参考に.envファイルを作成してください
    echo.
    echo 手順:
    echo   1. copy env.example .env
    echo   2. .envファイルを編集してDynatraceの設定を入力
    echo   3. 再度このスクリプトを実行
    pause
    exit /b 1
)

REM Python仮想環境の確認（オプション）
if exist "venv\Scripts\activate.bat" (
    echo 🐍 Python仮想環境を有効化中...
    call venv\Scripts\activate.bat
)

REM 必要なパッケージのインストール確認
echo 📦 依存関係を確認中...
python -m pip install -r requirements.txt --quiet

REM Pythonスクリプトを実行
echo 🚀 Dynatrace Synthetic メトリクス エクスポートを開始...
echo.

python src\export_synthetic_metrics.py %*

set exit_code=!ERRORLEVEL!

if !exit_code! equ 0 (
    echo.
    echo ✅ 正常に完了しました
) else (
    echo.
    echo ❌ エラーで終了しました (終了コード: !exit_code!)
    echo 📄 詳細はlogsディレクトリのログファイルを確認してください
)

pause
exit /b !exit_code! 