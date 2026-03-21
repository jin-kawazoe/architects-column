@echo off
cd /d "H:\共有ドライブ\HP_\architects-column"
echo [%date% %time%] 自動処理開始 >> daily_log.txt

echo 記事生成中...
python -X utf8 generate_article.py >> daily_log.txt 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 記事生成失敗 >> daily_log.txt
    exit /b 1
)

echo ビルド中...
python -X utf8 build.py >> daily_log.txt 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] ビルド失敗 >> daily_log.txt
    exit /b 1
)

echo デプロイ中...
python -X utf8 deploy.py >> daily_log.txt 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] デプロイ失敗 >> daily_log.txt
    exit /b 1
)

echo X投稿中...
python -X utf8 tweet.py >> daily_log.txt 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] X投稿失敗 >> daily_log.txt
    exit /b 1
)

echo [%date% %time%] 完了 >> daily_log.txt
