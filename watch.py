#!/usr/bin/env python3
"""
KAWAZOE-ARCHITECTS Auto Build Watcher
content/*.md か articles.json が変更されたら自動で build.py を実行 → FTPアップロード
"""
import time, subprocess, sys, ftplib, os
from pathlib import Path

BASE  = Path(__file__).parent
WATCH = [BASE / "content", BASE / "articles.json"]

# FTP設定
FTP_HOST   = "153.122.170.25"
FTP_PORT   = 21
FTP_USER   = "effect"
FTP_PASS   = "login0120$$$"
REMOTE_BASE = "kawazoe-architects.com/column"

UPLOAD_FILES   = ["index.html", "articles.json", "logo.png", "logo_black.png", "logo.jpg", "logo_black.jpg"]
UPLOAD_FOLDERS = ["articles", "css", "js", "img"]

def get_mtimes():
    mtimes = {}
    for target in WATCH:
        if target.is_dir():
            for f in target.glob("*.md"):
                mtimes[str(f)] = f.stat().st_mtime
        elif target.exists():
            mtimes[str(target)] = target.stat().st_mtime
    return mtimes

def run_build():
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] change detected → building...")
    result = subprocess.run(
        [sys.executable, "build.py"],
        cwd=BASE, capture_output=True, text=True
    )
    print(result.stdout.strip())
    if result.stderr.strip():
        print("[ERROR]", result.stderr.strip())

def mkdirs(ftp, path):
    parts = path.split("/")
    for i in range(1, len(parts) + 1):
        d = "/".join(parts[:i])
        try:
            ftp.mkd(d)
        except:
            pass

def upload_file(ftp, local_path, remote_path):
    mkdirs(ftp, remote_path.rsplit("/", 1)[0])
    with open(local_path, "rb") as f:
        ftp.storbinary(f"STOR {remote_path}", f)

def run_upload():
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] uploading to server...")
    try:
        ftp = ftplib.FTP()
        ftp.connect(FTP_HOST, FTP_PORT, timeout=30)
        ftp.login(FTP_USER, FTP_PASS)

        for fname in UPLOAD_FILES:
            local = BASE / fname
            if local.exists():
                upload_file(ftp, str(local), f"{REMOTE_BASE}/{fname}")

        for folder in UPLOAD_FOLDERS:
            folder_path = BASE / folder
            for root, dirs, files in os.walk(folder_path):
                for fname in files:
                    local = os.path.join(root, fname)
                    rel = os.path.relpath(local, BASE).replace("\\", "/")
                    upload_file(ftp, local, f"{REMOTE_BASE}/{rel}")

        ftp.quit()
        print(f"[{ts}] upload complete → https://kawazoe-architects.com/column/")
    except Exception as e:
        print(f"[ERROR] upload failed: {e}")
    print()

print("KAWAZOE-ARCHITECTS Auto Build & Deploy Watcher")
print("  watching: content/*.md  articles.json")
print("  変更を検知 → ビルド → FTPアップロード 自動実行")
print("  Ctrl+C で停止")
print()

# 起動時に一度ビルド＆アップロード
run_build()
run_upload()
last = get_mtimes()

while True:
    time.sleep(1)
    current = get_mtimes()
    if current != last:
        run_build()
        run_upload()
        last = current
