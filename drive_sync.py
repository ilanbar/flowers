import os
import os.path
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io
import tkinter.messagebox as messagebox
import httplib2
from google_auth_httplib2 import AuthorizedHttp
from urllib.parse import urlparse

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']

class DriveSync:
    def __init__(self, local_dir):
        self.local_dir = local_dir
        self.creds = None
        self.service = None
        self.folder_name = "FlowerShopData"
        self.folder_id = None
        
    def authenticate(self):
        """Shows basic usage of the Drive v3 API.
        """
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        token_path = os.path.join(self.local_dir, 'token.json')
        creds_path = os.path.join(self.local_dir, 'credentials.json')
        
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(creds_path):
                    print("credentials.json not found.")
                    return False
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print(f"Authentication failed: {e}")
                    return False
            
            # Save the credentials for the next run
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

        self.creds = creds
        try:
            # Check for proxy settings
            proxy_url = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
            if proxy_url:
                try:
                    parsed = urlparse(proxy_url)
                    proxy_host = parsed.hostname
                    proxy_port = parsed.port
                    
                    if proxy_host and proxy_port:
                        print(f"Configuring Drive API with proxy: {proxy_host}:{proxy_port}")
                        proxy_info = httplib2.ProxyInfo(
                            httplib2.socks.PROXY_TYPE_HTTP,
                            proxy_host,
                            proxy_port
                        )
                        http = httplib2.Http(proxy_info=proxy_info)
                        authed_http = AuthorizedHttp(creds, http=http)
                        self.service = build('drive', 'v3', http=authed_http)
                    else:
                        # Fallback if parsing fails
                        self.service = build('drive', 'v3', credentials=creds)
                except Exception as e:
                    print(f"Error configuring proxy: {e}")
                    self.service = build('drive', 'v3', credentials=creds)
            else:
                self.service = build('drive', 'v3', credentials=creds)
                
            return True
        except Exception as e:
            print(f"Failed to build service: {e}")
            return False

    def get_folder_id(self):
        if self.folder_id:
            return self.folder_id
            
        # Search for the folder
        results = self.service.files().list(
            q=f"name='{self.folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            spaces='drive',
            fields='nextPageToken, files(id, name)').execute()
        items = results.get('files', [])

        if not items:
            # Create the folder
            file_metadata = {
                'name': self.folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            file = self.service.files().create(body=file_metadata, fields='id').execute()
            self.folder_id = file.get('id')
            print(f"Created folder {self.folder_name} with ID {self.folder_id}")
        else:
            self.folder_id = items[0]['id']
            print(f"Found folder {self.folder_name} with ID {self.folder_id}")
            
        return self.folder_id

    def upload_files(self, files_to_sync, orders_dir="orders"):
        if not self.service:
            if not self.authenticate():
                return

        folder_id = self.get_folder_id()
        
        # 1. Upload root files
        for filename in files_to_sync:
            filepath = os.path.join(self.local_dir, filename)
            if os.path.exists(filepath):
                self._upload_single_file(filename, filepath, folder_id)

        # 2. Upload orders folder
        # First, find or create the 'orders' subfolder in Drive
        orders_folder_id = self._get_or_create_subfolder("orders", folder_id)
        
        local_orders_path = os.path.join(self.local_dir, orders_dir)
        if os.path.exists(local_orders_path):
            for filename in os.listdir(local_orders_path):
                if filename.endswith('.xlsx') or filename.endswith('.json'):
                    filepath = os.path.join(local_orders_path, filename)
                    self._upload_single_file(filename, filepath, orders_folder_id)

    def upload_file(self, filepath, remote_filename=None):
        if not self.service:
            if not self.authenticate():
                return

        folder_id = self.get_folder_id()
        filename = remote_filename if remote_filename else os.path.basename(filepath)
        
        self._upload_single_file(filename, filepath, folder_id)

    def _get_or_create_subfolder(self, name, parent_id):
        query = f"name='{name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        
        if not items:
            file_metadata = {
                'name': name,
                'parents': [parent_id],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            file = self.service.files().create(body=file_metadata, fields='id').execute()
            return file.get('id')
        else:
            return items[0]['id']

    def _upload_single_file(self, filename, filepath, parent_id):
        print(f"Uploading {filename}...")
        # Check if file exists in Drive folder
        query = f"name='{filename}' and '{parent_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        
        media = MediaFileUpload(filepath, resumable=True)
        
        if items:
            # Update
            file_id = items[0]['id']
            self.service.files().update(fileId=file_id, media_body=media).execute()
            print(f"Updated {filename}")
        else:
            # Create
            file_metadata = {'name': filename, 'parents': [parent_id]}
            self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            print(f"Created {filename}")

    def download_files(self, files_to_sync, orders_dir="orders"):
        if not self.service:
            if not self.authenticate():
                return

        folder_id = self.get_folder_id()
        
        # 1. Download root files
        # List all files in the folder
        query = f"'{folder_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(id, name, mimeType)').execute()
        items = results.get('files', [])
        
        for item in items:
            name = item['name']
            file_id = item['id']
            mime_type = item['mimeType']
            
            if mime_type == 'application/vnd.google-apps.folder':
                if name == 'orders':
                    self._download_folder(file_id, os.path.join(self.local_dir, orders_dir))
            elif name in files_to_sync or (name.startswith("DefaultPricing_") and name.endswith(".xlsx")):
                dest_path = os.path.join(self.local_dir, name)
                self._download_single_file(file_id, dest_path)

    def download_file_as(self, remote_filename, local_filename):
        if not self.service:
            if not self.authenticate():
                return False

        folder_id = self.get_folder_id()
        
        # Search for the file in the folder
        query = f"name='{remote_filename}' and '{folder_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        
        if not items:
            print(f"File {remote_filename} not found in Drive folder.")
            return False
            
        file_id = items[0]['id']
        dest_path = os.path.join(self.local_dir, local_filename)
        self._download_single_file(file_id, dest_path)
        return True

    def _download_folder(self, folder_id, local_dest_dir):
        if not os.path.exists(local_dest_dir):
            os.makedirs(local_dest_dir)
            
        query = f"'{folder_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        
        for item in items:
            self._download_single_file(item['id'], os.path.join(local_dest_dir, item['name']))

    def _download_single_file(self, file_id, dest_path):
        print(f"Downloading to {dest_path}...")
        request = self.service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        with open(dest_path, 'wb') as f:
            f.write(fh.getbuffer())
        print(f"Downloaded {dest_path}")
