import os
import sqlite3
from curl_cffi import requests

def get_steam_data(output_dir='assets'):
    os.makedirs(output_dir, exist_ok=True)
    db_file = os.path.join(output_dir, 'steam_data.db')
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS apps (appid INTEGER PRIMARY KEY, name TEXT)''')
    
    cursor.execute('SELECT COUNT(*) FROM apps')
    if cursor.fetchone()[0] == 0:
        api = "https://api.steampowered.com/ISteamApps/GetAppList/v0002/"
        response = requests.get(api, timeout=30)
        app_list = response.json()['applist']['apps']
        
        cursor.execute('BEGIN TRANSACTION')
        for app in app_list:
            cursor.execute('''INSERT OR IGNORE INTO apps (appid, name) VALUES (?, ?)''', (app['appid'], app['name']))
        conn.commit()
    
    return conn

def get_steam_app_by_name(app_name):
    conn = get_steam_data()
    try:
        cursor = conn.cursor()
        cursor.execute('''SELECT appid, name FROM apps WHERE LOWER(name) = LOWER(?)''', (app_name,))
        result = cursor.fetchone()
        
        if result:
            return {'appid': result[0], 'name': result[1]}
        
        # If no match, searching
        try:
            search_url = f"https://steamcommunity.com/actions/SearchApps/{app_name}"
            response = requests.get(search_url, timeout=30)
            search_results = response.json()
            
            for result in search_results:
                if result['name'].lower() == app_name.lower():
                    cursor.execute('''INSERT OR IGNORE INTO apps (appid, name) VALUES (?, ?)''', (result['appid'], result['name']))
                    conn.commit()
                    return {'appid': result['appid'], 'name': result['name']}
                
        except Exception as e:
            print(f"Search error: {e}")
        return None
    
    finally:
        conn.close()

def get_steam_app_by_id(appid):
    conn = get_steam_data()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM apps WHERE appid = ?', (int(appid),))
        result = cursor.fetchone()
        
        if result:
            return {'appid': int(appid), 'name': result[0]}
        
        # If not found, try Steam store
        try:
            store_url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
            response = requests.get(store_url, timeout=30)
            store_data = response.json()
            
            if str(appid) in store_data and store_data[str(appid)]['success']:
                app_details = store_data[str(appid)]['data']
                name = app_details.get('name', 'Unknown')
                cursor.execute('''INSERT OR IGNORE INTO apps (appid, name) VALUES (?, ?)''', (int(appid), name))
                conn.commit()
                return {'appid': int(appid), 'name': name}
            
        except Exception as e:
            print(f"Search error: {e}")
        
        return None
    finally:
        conn.close()