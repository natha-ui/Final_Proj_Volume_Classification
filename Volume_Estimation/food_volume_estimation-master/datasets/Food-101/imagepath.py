#!/usr/bin/env python3
"""
Google Drive Image Path Extractor
Extracts paths to image files from Google Drive and saves them to a text file.
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Google Drive API scope
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Common image file extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.svg', '.ico'}

def authenticate_gdrive():
    """Authenticate and return Google Drive service object."""
    creds = None
    
    # Token file stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no valid credentials, request authorization
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('drive', 'v3', credentials=creds)

def get_image_files(service, folder_id=None):
    """Get all image files from Google Drive."""
    images = []
    page_token = None
    
    # Build query for image files
    query = "trashed=false"
    if folder_id:
        query += f" and '{folder_id}' in parents"
    
    while True:
        # Search for files
        results = service.files().list(
            q=query,
            pageSize=1000,
            fields="nextPageToken, files(id, name, parents, webViewLink, webContentLink)",
            pageToken=page_token
        ).execute()
        
        files = results.get('files', [])
        
        for file in files:
            name = file.get('name', '')
            file_ext = os.path.splitext(name.lower())[1]
            
            if file_ext in IMAGE_EXTENSIONS:
                images.append({
                    'name': name,
                    'id': file['id'],
                    'web_view_link': file.get('webViewLink', ''),
                    'web_content_link': file.get('webContentLink', ''),
                    'parents': file.get('parents', [])
                })
        
        page_token = results.get('nextPageToken')
        if not page_token:
            break
    
    return images

def get_folder_path(service, folder_id, folder_cache=None):
    """Get the full path of a folder by traversing up the parent chain."""
    if folder_cache is None:
        folder_cache = {}
    
    if folder_id in folder_cache:
        return folder_cache[folder_id]
    
    try:
        folder = service.files().get(fileId=folder_id, fields='name, parents').execute()
        folder_name = folder.get('name', '')
        parents = folder.get('parents', [])
        
        if parents:
            parent_path = get_folder_path(service, parents[0], folder_cache)
            full_path = f"{parent_path}/{folder_name}" if parent_path else folder_name
        else:
            full_path = folder_name
        
        folder_cache[folder_id] = full_path
        return full_path
    
    except Exception as e:
        print(f"Error getting folder path for {folder_id}: {e}")
        return "Unknown"

def save_image_paths(images, service, output_file='image_paths.txt', include_links=True):
    """Save image paths to a text file."""
    folder_cache = {}
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Google Drive Image Paths\n")
        f.write(f"# Total images found: {len(images)}\n")
        f.write("# Format: [Full Path] | [File ID] | [View Link] | [Download Link]\n\n")
        
        for img in images:
            # Get folder path
            if img['parents']:
                folder_path = get_folder_path(service, img['parents'][0], folder_cache)
                full_path = f"{folder_path}/{img['name']}"
            else:
                full_path = img['name']
            
            # Write different formats based on preference
            if include_links:
                f.write(f"{full_path} | {img['id']} | {img['web_view_link']} | {img['web_content_link']}\n")
            else:
                f.write(f"{full_path}\n")
    
    print(f"Image paths saved to {output_file}")

def main():
    """Main function to extract and save image paths."""
    try:
        # Authenticate
        print("Authenticating with Google Drive...")
        service = authenticate_gdrive()
        
        # Get specific folder ID if needed (optional)
        folder_id = input("Enter folder ID (press Enter for entire Drive): ").strip()
        if not folder_id:
            folder_id = None
        
        # Get image files
        print("Searching for image files...")
        images = get_image_files(service, folder_id)
        
        if not images:
            print("No image files found.")
            return
        
        print(f"Found {len(images)} image files.")
        
        # Save paths
        output_file = input("Output filename (default: image_paths.txt): ").strip()
        if not output_file:
            output_file = 'image_paths.txt'
        
        include_links = input("Include download links? (y/n, default: y): ").strip().lower() != 'n'
        
        save_image_paths(images, service, output_file, include_links)
        
        # Also save as JSON for programmatic use
        json_file = output_file.replace('.txt', '.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(images, f, indent=2, ensure_ascii=False)
        
        print(f"Also saved JSON data to {json_file}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
