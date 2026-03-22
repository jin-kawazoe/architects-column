@echo off
cd /d "H:\共有ドライブ\HP_\architects-column"
echo [%date% %time%] START >> daily_log.txt

python -X utf8 generate_article.py >> daily_log.txt 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] generate_article.py failed >> daily_log.txt
    exit /b 1
)

python -X utf8 build.py >> daily_log.txt 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] build.py failed >> daily_log.txt
    exit /b 1
)

python -X utf8 deploy.py >> daily_log.txt 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] deploy.py failed >> daily_log.txt
    exit /b 1
)

python -X utf8 tweet.py >> daily_log.txt 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] tweet.py failed >> daily_log.txt
    exit /b 1
)

echo [%date% %time%] DONE >> daily_log.txt
