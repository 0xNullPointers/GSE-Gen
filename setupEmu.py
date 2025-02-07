import os
import subprocess
from curl_cffi import requests

# Supress subprocess window
startupinfo = subprocess.STARTUPINFO()
startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startupinfo.wShowWindow = subprocess.SW_HIDE

SEVENZIP_PATH = os.path.join("assets", "7zip", "7z.exe")
GOLDBERG_URL = "https://github.com/Detanup01/gbe_fork/releases/latest/download/emu-win-release.7z"
EMU_FOLDER = os.path.join("assets", "goldberg_emu")
ARCHIVE_NAME = "emu-win-release.7z"

# Debug
# print(f"EMU Dir: {EMU_FOLDER}")
# print(f"7z Path: {SEVENZIP_PATH}")

# Setting-Up Latest Emulator
def download_goldberg():
    os.makedirs(EMU_FOLDER, exist_ok=True)
    archive_path = os.path.join(EMU_FOLDER, ARCHIVE_NAME)
    
    if os.path.exists(archive_path):
        return archive_path
    
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15"}
    
    try:
        with requests.Session(headers=headers) as session:
            response = session.get(GOLDBERG_URL)
            response.raise_for_status()
            
            with open(archive_path, 'wb') as f:
                f.write(response.content)
        
        print("Download completed.")
        return archive_path
    except Exception as e:
        print(f"Failed to download Goldberg emulator: {str(e)}")
        raise

def extract_archive(archive_path):
    try:
        cmd = [SEVENZIP_PATH, 'x', f'-o{EMU_FOLDER}', '-y', archive_path]
        subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        
        os.remove(archive_path)
        print("Extraction completed.")
        
    except Exception as e:
        print(f"Failed to extract archive: {str(e)}")
        raise