import os
import shutil
import subprocess

EMU_FOLDER = os.path.join("assets", "goldberg_emu")

def find_exp_dir():
    for root, dirs, _ in os.walk(EMU_FOLDER):
        if "experimental" in dirs:
            return os.path.join(root, "experimental")

def find_tools_dir():
    for root, dirs, _ in os.walk(EMU_FOLDER):
        if "tools" in dirs:
            tools_dir = os.path.join(root, "tools")
            if "generate_interfaces" in os.listdir(tools_dir):
                return os.path.join(tools_dir, "generate_interfaces")

def generate_interfaces(dll_path):
    tools_dir = find_tools_dir()
    dll_name = os.path.basename(dll_path).lower()
    generator_exe = "generate_interfaces_x64.exe" if dll_name == "steam_api64.dll" else "generate_interfaces_x32.exe"
    generator_path = os.path.join(tools_dir, generator_exe)

    subprocess.run([generator_path, dll_path], capture_output=True, text=True, cwd=os.path.dirname(dll_path), creationflags=subprocess.CREATE_NO_WINDOW)
        
    interfaces_path = os.path.join(os.path.dirname(dll_path), "steam_interfaces.txt")
    return interfaces_path

def generate_emu(game_dir, app_id, dll_path, disable_overlay=False):
    try:        
        # File picker for og steam_api(64).dll
        if not dll_path:
            return False
        
        # Create steam_settings
        settings_dir = os.path.join(game_dir, "steam_settings")
        os.makedirs(settings_dir, exist_ok=True)
        
        dll_name = os.path.basename(dll_path).lower()
        experimental_path = find_exp_dir()
        source_path = os.path.join(experimental_path, "x64" if dll_name == "steam_api64.dll" else "x32")
        
        for file in os.listdir(source_path):
            src_file = os.path.join(source_path, file)
            dst_file = os.path.join(game_dir, file)
            if os.path.isfile(src_file):
                shutil.copy2(src_file, dst_file)
        
        backup_dll_name = f"{dll_name}.o"
        backup_dll_path = os.path.join(game_dir, backup_dll_name)
        shutil.copy2(dll_path, backup_dll_path)
        
        # steam_appid.txt
        appid_path = os.path.join(settings_dir, "steam_appid.txt")
        with open(appid_path, "w") as f:
            f.write(str(app_id))
        
        # steam_interfaces.txt
        interfaces_path = generate_interfaces(dll_path)
        settings_interfaces_path = os.path.join(settings_dir, "steam_interfaces.txt")
        shutil.move(interfaces_path, settings_interfaces_path)
        
        src_steam_settings_dir = os.path.join("assets", "steam_settings")
        if os.path.exists(src_steam_settings_dir):
            for folder in ['fonts', 'sounds']:
                src_folder = os.path.join(src_steam_settings_dir, folder)
                if os.path.exists(src_folder):
                    dst_folder = os.path.join(settings_dir, folder)
                    if os.path.exists(dst_folder):
                        shutil.rmtree(dst_folder)
                    shutil.copytree(src_folder, dst_folder)
            
            # Handle overlay config
            overlay_src = os.path.join(src_steam_settings_dir, 'disabled.ini' if disable_overlay else 'enabled.ini')
            if os.path.exists(overlay_src):
                overlay_dst = os.path.join(settings_dir, 'configs.overlay.ini')
                shutil.copy2(overlay_src, overlay_dst)
              
        return True
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False