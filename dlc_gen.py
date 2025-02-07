import os
import concurrent.futures
from bs4 import BeautifulSoup
from curl_cffi import requests

def create_session():
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br"
    }
    
    session = requests.Session(
        impersonate="safari15_5", 
        headers=headers, 
        timeout=10
    )

    try:
        session.cipher = ("TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384:TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256:TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384:TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256:TLS_RSA_WITH_AES_256_GCM_SHA384:TLS_RSA_WITH_AES_128_GCM_SHA256:TLS_RSA_WITH_AES_256_CBC_SHA:TLS_RSA_WITH_AES_128_CBC_SHA:TLS_ECDHE_ECDSA_WITH_3DES_EDE_CBC_SHA:TLS_ECDHE_RSA_WITH_3DES_EDE_CBC_SHA:TLS_RSA_WITH_3DES_EDE_CBC_SHA")
        session.curve = "X25519:P-256:P-384:P-521"
        session.sign_algo = ("ecdsa_secp256r1_sha256,rsa_pss_rsae_sha256,rsa_pkcs1_sha256,ecdsa_secp384r1_sha384,ecdsa_sha1,rsa_pss_rsae_sha384,rsa_pss_rsae_sha384,rsa_pkcs1_sha384,rsa_pss_rsae_sha512,rsa_pkcs1_sha512,rsa_pkcs1_sha1")
        return session
    except Exception:
        return None

def fetch_steam_dlcs(session, app_id):
    url = f"https://store.steampowered.com/api/appdetails/?filters=basic&appids={app_id}"
    
    try:
        response = session.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        dlc_ids = data[str(app_id)].get('data', {}).get('dlc', [])
        if not dlc_ids:
            return {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            def fetch_dlc_details(dlc_id):
                dlc_url = f"https://store.steampowered.com/api/appdetails/?filters=basic&appids={dlc_id}"
                try:
                    dlc_response = session.get(dlc_url, timeout=3)
                    dlc_response.raise_for_status()
                    dlc_data = dlc_response.json()
                    
                    if str(dlc_id) in dlc_data and dlc_data[str(dlc_id)].get('success'):
                        dlc_name = dlc_data[str(dlc_id)].get('data', {}).get('name', f'DLC {dlc_id}')
                        return (dlc_id, dlc_name)
                except Exception:
                    return None
            
            steam_dlcs = dict(filter(None, executor.map(fetch_dlc_details, dlc_ids)))
        
        return steam_dlcs
    
    except Exception:
        return {}

def fetch_steamdb_dlcs(session, app_id):
    url = f"https://steamdb.info/app/{app_id}/dlc/"
    
    try:
        response = session.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        dlc_section = soup.find("div", {"id": "dlc", "class": "tab-pane selected"})
        if not dlc_section:
            return {}
        
        table = dlc_section.find("table", {"class": "table"})
        if not table:
            return {}
        
        dlc_rows = table.select("tbody tr.app")
        steamdb_dlcs = {}
        
        for row in dlc_rows:
            try:
                dlc_id_cell = row.select_one("td:nth-child(1)")
                dlc_name_cell = row.select_one("td:nth-child(2)")
                
                if dlc_id_cell and dlc_name_cell:
                    dlc_id = int(dlc_id_cell.text.strip())
                    dlc_name = dlc_name_cell.text.strip()
                    steamdb_dlcs[dlc_id] = dlc_name
            except Exception:
                pass
        
        return steamdb_dlcs
    
    except Exception:
        return {}

def fetch_dlc(app_id):
    with create_session() as session:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            steamapi_future = executor.submit(fetch_steam_dlcs, session, app_id)
            steamdb_future = executor.submit(fetch_steamdb_dlcs, session, app_id)
            
            steam_dlcs = steamapi_future.result() or {}
            steamdb_dlcs = steamdb_future.result() or {}

    unq_dlcs = {}
    all_dlc_sources = [steamdb_dlcs, steam_dlcs]
    
    for source in all_dlc_sources:
        for dlc_id, dlc_name in source.items():
            if dlc_id not in unq_dlcs:
                unq_dlcs[dlc_id] = dlc_name

    return unq_dlcs

def create_dlc_config(game_dir, dlc_details):
    if not dlc_details:
        return
    
    settings_dir = os.path.join(game_dir, "steam_settings")
    os.makedirs(settings_dir, exist_ok=True)
    
    config_path = os.path.join(settings_dir, "configs.app.ini")
    
    try:
        with open(config_path, 'w', encoding='utf-8') as config_file:
            config_file.write("[app::dlcs]\n")
            config_file.write("unlock_all=0\n")
            
            for dlc_id, dlc_name in dlc_details.items():
                config_file.write(f"{dlc_id} = {dlc_name}\n")
    
    except Exception:
        pass