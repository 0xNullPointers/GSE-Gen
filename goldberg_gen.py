import os
import shutil
import subprocess

EMU_FOLDER = os.path.join("assets", "goldberg_emu")

def find_dir(base_dir, target_dir, extra_check=None):
    for root, dirs, _ in os.walk(base_dir):
        if target_dir in dirs:
            found_dir = os.path.join(root, target_dir)
            if extra_check:
                if extra_check in os.listdir(found_dir):
                    return os.path.join(found_dir, extra_check)
            return found_dir
    return None

def modify_overlay_config(src_path, dst_path, disable_overlay):
    with open(src_path, 'r') as f:
        lines = f.readlines()

    with open(dst_path, 'w') as f:
        for line in lines:
            if 'enable_experimental_overlay=' in line:
                f.write(f"enable_experimental_overlay={'0' if disable_overlay else '1'}\n")
            elif 'Font_Override=' in line:
                f.write("Font_Override=Helvetica-Regular.ttf\n")
            elif 'Font_Size=' in line:
                f.write("Font_Size=16.0\n")
            else:
                f.write(line)

def generate_interfaces(dll_path):
    tools_dir = find_dir(EMU_FOLDER, "tools", "generate_interfaces")
    dll_name = os.path.basename(dll_path).lower()
    generator_exe = f"generate_interfaces_{'x64' if dll_name == 'steam_api64.dll' else 'x32'}.exe"
    
    subprocess.run([os.path.join(tools_dir, generator_exe), dll_path], capture_output=True, text=True, cwd=os.path.dirname(dll_path), creationflags=subprocess.CREATE_NO_WINDOW)
    
    return os.path.join(os.path.dirname(dll_path), "steam_interfaces.txt")

def generate_emu(game_dir, app_id, dll_path, disable_overlay=False):
    try:
        if not dll_path or not os.path.exists(dll_path):
            return False

        settings_dir = os.path.join(game_dir, "steam_settings")
        os.makedirs(settings_dir, exist_ok=True)

        # Copy experimental files
        dll_name = os.path.basename(dll_path).lower()
        exp_source = os.path.join(
            find_dir(EMU_FOLDER, "experimental"),
            "x64" if dll_name == "steam_api64.dll" else "x32"
        )
        
        for file in os.listdir(exp_source):
            if os.path.isfile(src_file := os.path.join(exp_source, file)):
                shutil.copy2(src_file, os.path.join(game_dir, file))

        # Backup original DLL
        shutil.copy2(dll_path, os.path.join(game_dir, f"{dll_name}.o"))

        # Create steam_appid.txt
        with open(os.path.join(settings_dir, "steam_appid.txt"), "w") as f:
            f.write(str(app_id))

        # Generate and move interfaces file
        shutil.move(generate_interfaces(dll_path), os.path.join(settings_dir, "steam_interfaces.txt"))

        # Copy fonts and sounds
        src_settings = os.path.join("assets", "steam_settings")
        if os.path.exists(src_settings):
            for folder in ['fonts', 'sounds']:
                if os.path.exists(src_folder := os.path.join(src_settings, folder)):
                    dst_folder = os.path.join(settings_dir, folder)
                    if os.path.exists(dst_folder):
                        shutil.rmtree(dst_folder)
                    shutil.copytree(src_folder, dst_folder)

            # Handle overlay config
            if overlay_config := find_dir(EMU_FOLDER, "steam_settings.EXAMPLE", "configs.overlay.EXAMPLE.ini"):
                modify_overlay_config(overlay_config, os.path.join(settings_dir, 'configs.overlay.ini'), disable_overlay)

        return True

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False