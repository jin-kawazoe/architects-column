@echo off
cd /d "%~dp0"
echo KAWAZOE-ARCHITECTS 自動ビルド＆アップロード起動中...
echo このウィンドウを開いたまま記事を編集してください。
echo 閉じると自動アップロードが停止します。
echo.
python3 watch.py
pause
