# -*- coding: utf-8 -*-
import os
import json
import xbmcgui
import urllib2
import time
import requests

# Source folder on Xbox
SOURCE_FOLDER = "E:/UDATA"
# Paths to ID.txt containing Title ID mappings & dropbox.txt containing your Dropbox API access token.
ID_TXT_PATH = "Q:/scripts/Cortana Cloud/id.txt"
TOKEN_PATH = xbmc.translatePath('special://home/userdata/profiles/{}/dropbox.txt'.format(xbmc.getInfoLabel('System.ProfileName')))
ID_TXT_PATH = "Q:/scripts/Cortana Cloud/timestamp.txt"

def load_token():
    """Loads Dropbox Access Token from token.txt."""
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "r") as f:
            return f.read().strip()
    return ""

# Load Dropbox token
DROPBOX_ACCESS_TOKEN = load_token()

# Define chunk size (4MB to keep memory usage low)
CHUNK_SIZE = 4 * 1024 * 1024  # 4MB

def load_title_id_mapping():
    """Loads Title ID mappings from ID.txt."""
    title_id_map = {}
    if os.path.exists(ID_TXT_PATH):
        with open(ID_TXT_PATH, "r") as f:
            for line in f:
                parts = line.strip().split("\t")  # Split by tab
                if len(parts) >= 3:  # Ensure correct format
                    title_id = parts[1].strip().lower().replace("0x", "")  # Normalize title ID
                    game_name = parts[2].strip()
                    title_id_map[title_id] = game_name
    return title_id_map

def get_dropbox_metadata(remote_path):
    """Fetches metadata for a file or folder from Dropbox, including last modified time."""
    url = "https://api.dropboxapi.com/2/files/get_metadata"
    headers = {
        "Authorization": "Bearer " + DROPBOX_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    data = json.dumps({"path": remote_path})

    response = requests.post(url, headers=headers, data=data)

    if response.status_code == 200:
        metadata = response.json()
        if "server_modified" in metadata:
            return metadata["server_modified"][:10]  # Return only the date part
    return None

def load_timestamps():
    """Loads timestamps from timestamp.txt, ensuring missing values are handled."""
    timestamps = {}
    if os.path.exists(TIMESTAMP_PATH):
        with open(TIMESTAMP_PATH, "r") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) == 2:  # If only "folder_name" and "uploaded" exist
                    timestamps[parts[0]] = {"uploaded": parts[1], "downloaded": ""}
                elif len(parts) == 3:  # Correct format
                    timestamps[parts[0]] = {"uploaded": parts[1], "downloaded": parts[2]}
    return timestamps

def save_timestamp(folder_name, action):
    """Saves timestamp for a given folder by fetching it from Dropbox metadata."""
    timestamps = load_timestamps()
    remote_path = "/UDATA/" + folder_name
    cloud_timestamp = get_dropbox_metadata(remote_path)

    if cloud_timestamp:
        if folder_name not in timestamps:
            timestamps[folder_name] = {"uploaded": "", "downloaded": ""}
        timestamps[folder_name][action] = cloud_timestamp

        with open(TIMESTAMP_PATH, "w") as f:
            for key, value in timestamps.items():
                f.write("{}\t{}\t{}\n".format(key, value["uploaded"], value["downloaded"]))

def list_local_saves(title_id_map):
    """Lists save folders stored locally with game names and timestamps, sorted alphabetically."""
    timestamps = load_timestamps()
    local_saves = []
    if os.path.exists(SOURCE_FOLDER):
        for folder_name in os.listdir(SOURCE_FOLDER):
            folder_path = os.path.join(SOURCE_FOLDER, folder_name)
            if os.path.isdir(folder_path):
                game_name = title_id_map.get(folder_name.lower(), folder_name)
                upload_time = timestamps.get(folder_name, {}).get("uploaded", "")
                download_time = timestamps.get(folder_name, {}).get("downloaded", "")
                timestamp_display = ""
                if upload_time and download_time:
                    timestamp_display = "Uploaded: {} | Downloaded: {}".format(upload_time, download_time)
                elif upload_time:
                    timestamp_display = "Uploaded: {}".format(upload_time)
                elif download_time:
                    timestamp_display = "Downloaded: {}".format(download_time)
                display_name = "{} ({})".format(game_name, timestamp_display) if timestamp_display else game_name
                local_saves.append((display_name, folder_name))
    
    # Sort saves alphabetically by game name
    local_saves.sort(key=lambda x: x[0].lower())
    return local_saves

def get_game_name(udata_folder, title_id_map):
    """Retrieves the game name from TitleMeta.xbx, ID.txt, or falls back to folder name."""
    folder_name = os.path.basename(udata_folder).lower()
    if folder_name in title_id_map:
        return title_id_map[folder_name]
    
    title_file = os.path.join(udata_folder, "TitleMeta.xbx")
    if os.path.exists(title_file):
        try:
            with open(title_file, "r") as f:
                for line in f:
                    if "Title" in line:
                        return line.split("=")[-1].strip().strip('"')
        except:
            pass
    return folder_name  # Fallback to folder name

def scan_udata(title_id_map):
    """Scans the UDATA folder and returns a list of game save entries."""
    game_saves = []
    if os.path.exists(SOURCE_FOLDER):
        for folder in os.listdir(SOURCE_FOLDER):
            full_path = os.path.join(SOURCE_FOLDER, folder)
            if os.path.isdir(full_path):
                game_saves.append((get_game_name(full_path, title_id_map), full_path))
    return game_saves

def list_cloud_saves(title_id_map):
    """Lists save folders stored in Dropbox with game names and timestamps, sorted alphabetically."""
    timestamps = load_timestamps()
    url = "https://api.dropboxapi.com/2/files/list_folder"
    headers = {
        "Authorization": "Bearer " + DROPBOX_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    data = json.dumps({"path": "/UDATA"})
    try:
        request = urllib2.Request(url, data, headers)
        response = urllib2.urlopen(request)
        result = json.loads(response.read())
        
        if "entries" not in result:
            xbmcgui.Dialog().ok("Error", "Unexpected response from Dropbox API.")
            return []
        
        cloud_saves = []
        for entry in result["entries"]:
            if entry.get(".tag") == "folder":
                folder_name = entry["name"].lower()
                game_name = title_id_map.get(folder_name, folder_name)
                metadata_timestamp = get_dropbox_metadata("/UDATA/" + folder_name)
                timestamp = timestamps.get(folder_name, {}).get("downloaded", "")
                
                timestamp_display = ""
                if metadata_timestamp:
                    timestamp_display = "Last Modified: {}".format(metadata_timestamp)
                if timestamp:
                    if timestamp_display:
                        timestamp_display += " | Downloaded: {}".format(timestamp)
                    else:
                        timestamp_display = "Downloaded: {}".format(timestamp)
                
                display_name = "{} ({})".format(game_name, timestamp_display) if timestamp_display else game_name
                cloud_saves.append((display_name, entry["name"]))
        
        if not cloud_saves:
            xbmcgui.Dialog().ok("No Cloud Saves Found", "No saves found in Dropbox.")
        
        # Sort saves alphabetically by game name
        cloud_saves.sort(key=lambda x: x[0].lower())
        
        return cloud_saves
    except Exception as e:
        xbmcgui.Dialog().ok("Error", "Failed to retrieve cloud saves: {}".format(str(e)))
        return []


def download_file(dropbox_path, local_path):
    """Downloads a file from Dropbox to the Xbox."""
    url = "https://content.dropboxapi.com/2/files/download"
    headers = {
        "Authorization": "Bearer " + DROPBOX_ACCESS_TOKEN,
        "Dropbox-API-Arg": json.dumps({"path": dropbox_path})
    }
    try:
        request = urllib2.Request(url, headers=headers)
        response = urllib2.urlopen(request)
        with open(local_path, "wb") as f:
            f.write(response.read())
    except urllib2.HTTPError as e:
        xbmcgui.Dialog().ok("Error", "Failed to download: " + dropbox_path, "HTTP Error: " + str(e.code) + "\n" + e.read())

def browse_cloud_saves():
    """Displays cloud saves for the user to select and download."""
    title_id_map = load_title_id_mapping()
    saves = list_cloud_saves(title_id_map)
    if not saves:
        xbmcgui.Dialog().ok("No Cloud Saves Found", "No saves found in Dropbox.")
        return
    game_names = [s[0] for s in saves]
    selected = xbmcgui.Dialog().select("Select a save to download", game_names)
    if selected != -1:
        download_folder(saves[selected][1])

def download_folder(folder_name):
    """Handles downloading a folder from Dropbox back to UDATA."""
    list_url = "https://api.dropboxapi.com/2/files/list_folder"
    download_url = "https://content.dropboxapi.com/2/files/download"
    headers = {
        "Authorization": "Bearer " + DROPBOX_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    data = json.dumps({"path": "/UDATA/" + folder_name})
    local_folder = os.path.join(SOURCE_FOLDER, folder_name)
    
    try:
        if not os.path.exists(local_folder):
            os.makedirs(local_folder)
        
        # List files in the folder
        request = urllib2.Request(list_url, data, headers)
        response = urllib2.urlopen(request)
        result = json.loads(response.read())
        
        for entry in result.get("entries", []):
            if entry[".tag"] == "file":
                file_name = entry["name"]
                file_path = os.path.join(local_folder, file_name)
                
                # Download each file
                file_headers = {
                    "Authorization": "Bearer " + DROPBOX_ACCESS_TOKEN,
                    "Dropbox-API-Arg": json.dumps({"path": entry["path_lower"]})
                }
                
                file_request = urllib2.Request(download_url, headers=file_headers)
                file_response = urllib2.urlopen(file_request)
                
                with open(file_path, "wb") as f:
                    f.write(file_response.read())
        
        xbmcgui.Dialog().ok("Download Complete", "Save data downloaded successfully.")
    except urllib2.HTTPError as e:
        xbmcgui.Dialog().ok("Download Failed", "Error: " + str(e.code))

def upload_file(file_path, dropbox_path):
    """Uploads a single file to Dropbox using streaming."""
    url = "https://content.dropboxapi.com/2/files/upload"
    headers = {
        "Authorization": "Bearer " + DROPBOX_ACCESS_TOKEN,
        "Dropbox-API-Arg": json.dumps({
            "path": dropbox_path,
            "mode": "add",
            "autorename": False,
            "mute": False,
            "strict_conflict": False
        }),
        "Content-Type": "application/octet-stream"
    }
    try:
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                request = urllib2.Request(url, chunk)
                for key, value in headers.items():
                    request.add_header(key, value)
                urllib2.urlopen(request)
    except urllib2.HTTPError as e:
        xbmcgui.Dialog().ok("Error", "Failed to upload: " + file_path, "HTTP Error: " + str(e.code) + "\n" + e.read())

def upload_folder(game_path, folder_name):
    """Uploads a selected game save folder while keeping the folder structure intact."""
    for root, _, files in os.walk(game_path):
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, SOURCE_FOLDER).replace("\\", "/")
            dropbox_path = "/UDATA/" + relative_path
            upload_file(local_path, dropbox_path)
    xbmcgui.Dialog().ok("Upload Complete", "{} save uploaded successfully!".format(folder_name))

def show_game_list():
    """Displays local saves for the user to select and upload."""
    title_id_map = load_title_id_mapping()
    saves = list_local_saves(title_id_map)
    if not saves:
        xbmcgui.Dialog().ok("No Local Saves Found", "No saves found in UDATA.")
        return
    game_names = [s[0] for s in saves]
    selected = xbmcgui.Dialog().select("Select a save to upload", game_names)
    if selected != -1:
        local_path = os.path.join(SOURCE_FOLDER, saves[selected][1])
        remote_path = "/UDATA/" + saves[selected][1]  # Preserve folder name
        upload_folder(local_path, remote_path)
        save_timestamp(saves[selected][1], "uploaded")

def bulk_upload():
    """Uploads all local save folders to Dropbox."""
    title_id_map = load_title_id_mapping()
    saves = list_local_saves(title_id_map)
    for _, folder_name in saves:
        local_path = os.path.join(SOURCE_FOLDER, folder_name)
        remote_path = "/UDATA/" + folder_name
        upload_folder(local_path, remote_path)
        save_timestamp(folder_name, "uploaded")
    xbmcgui.Dialog().ok("Bulk Upload Complete", "All local saves uploaded successfully.")

def bulk_download():
    """Downloads all cloud save folders to local storage."""
    title_id_map = load_title_id_mapping()
    saves = list_cloud_saves(title_id_map)
    for _, folder_name in saves:
        download_folder(folder_name)
        save_timestamp(folder_name, "downloaded")
    xbmcgui.Dialog().ok("Bulk Download Complete", "All cloud saves downloaded successfully.")

def main_menu():
    options = ["Upload Save", "Download Save", "Bulk Download Saves", "Bulk Upload Saves"]
    selected = xbmcgui.Dialog().select("Cortana Cloud", options)
    if selected == 0:
        show_game_list()
    elif selected == 1:
        browse_cloud_saves()
    elif selected == 2:
        bulk_download()
    elif selected == 3:
        bulk_upload()

# Run the script
main_menu()
