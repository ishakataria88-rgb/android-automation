#pip install uiautomator2
import os


import io
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# === Configuration ===
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
FOLDER_ID = '1DqXglvpCJ6io0jHYNbUBuYcBWLlVi5_N'  # <-- Your folder ID

CWD = os.path.dirname(os.path.abspath(__file__))

# Paths relative to script
CLIENT_SECRET_FILE = os.path.join(CWD, 'client_secrets.json')
TOKEN_FILE         = os.path.join(CWD, 'token.json')
DOWNLOAD_DIR       = os.path.join(CWD, 'downloaded_files')
LOG_PATH           = os.path.join(CWD, 'download_log.txt')
EXCEL_PATH         = os.path.join(CWD, 'summary.xlsx')
def authenticate():
    """Authenticate with Google Drive API using OAuth2."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def download_files(service):
    """Download all files from a specific Google Drive folder."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    query = f"'{FOLDER_ID}' in parents and trashed = false"
    results = service.files().list(
        q=query,
        pageSize=1000,
        fields="files(id, name, mimeType)").execute()
    
    items = results.get('files', [])
    
    if not items:
        print('No files found in the folder.')
        return

    for item in items:
        file_id = item['id']
        file_name = item['name']
        print(f'Downloading: {file_name} ...')

        request = service.files().get_media(fileId=file_id)
        file_path = os.path.join(DOWNLOAD_DIR, file_name)
        fh = io.FileIO(file_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"   Progress: {int(status.progress() * 100)}%")
    
    print(f"\n✅ All files downloaded to: {DOWNLOAD_DIR}")

if __name__ == '__main__':
    drive_service = authenticate()
    download_files(drive_service)
