import ftplib, os
from pathlib import Path

BASE = Path(__file__).parent
FTP_HOST = '153.122.170.25'
FTP_PORT = 21
FTP_USER = 'effect'
FTP_PASS = 'login0120$$$'
REMOTE_BASE = 'kawazoe-architects.com/column'

UPLOAD_FILES = [
    'index.html', 'articles.json', 'sitemap.xml',
    'privacy.html', 'llms.txt', 'robots.txt', 'ogp.jpg'
]
UPLOAD_FOLDERS = ['articles', 'css', 'js', 'img']

def mkdirs(ftp, path):
    parts = path.split('/')
    for i in range(1, len(parts) + 1):
        d = '/'.join(parts[:i])
        try: ftp.mkd(d)
        except: pass

def upload_file(ftp, local_path, remote_path):
    mkdirs(ftp, remote_path.rsplit('/', 1)[0])
    with open(local_path, 'rb') as f:
        ftp.storbinary(f'STOR {remote_path}', f)
    print(f'  uploaded: {remote_path}')

ftp = ftplib.FTP()
ftp.connect(FTP_HOST, FTP_PORT, timeout=30)
ftp.login(FTP_USER, FTP_PASS)

for fname in UPLOAD_FILES:
    local = BASE / fname
    if local.exists():
        upload_file(ftp, str(local), f'{REMOTE_BASE}/{fname}')

for folder in UPLOAD_FOLDERS:
    folder_path = BASE / folder
    for root, dirs, files in os.walk(folder_path):
        for fname in files:
            local = os.path.join(root, fname)
            rel = os.path.relpath(local, str(BASE)).replace('\\', '/')
            upload_file(ftp, local, f'{REMOTE_BASE}/{rel}')

ftp.quit()
print('Done!')
