import os
import sys
import queue
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QLabel, QLineEdit, QFrame, QHBoxLayout, QVBoxLayout, QCheckBox, QPushButton, QPlainTextEdit, QFileDialog
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPalette, QIcon
from appID_finder import get_steam_app_by_id, get_steam_app_by_name
from achievements import fetch_from_steamcommunity, fetch_from_steamdb
from dlc_gen import fetch_dlc, create_dlc_config
from threadManager import ThreadManager

# Get the path of the resource files
def get_resource_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(__file__), filename)

# Redirect stdout to GUI
class RedirectText:
    def __init__(self, output_callback):
        self.output_callback = output_callback
        self.last_line = ""
    
    def write(self, string):
        cleaned_string = string.replace('\r', '').replace('\n', '').strip()
        if cleaned_string:
            self.output_callback(cleaned_string + '\n')
    
    def flush(self):
        pass

# GUI class
class AchievementFetcherGUI(QMainWindow):
    status_update = Signal(str, bool)
    message_received = Signal(str)
    request_dll_selection = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GSE Generator")
        self.resize(700, 500)
        self.setMinimumSize(500, 500)
        icon_path = get_resource_path('icon.ico')   # Get the icon path
        self.setWindowIcon(QIcon(icon_path))    # Set the window icon
        
        self.msg_queue = queue.Queue()
        self.assets_dir = os.path.join(os.getcwd(), "assets")
        os.makedirs(self.assets_dir, exist_ok=True)
        self.username_file = os.path.join(self.assets_dir, "username.txt")
        
        # Initialize thread manager
        self.thread_manager = ThreadManager()
        
        # Connect signals
        self.status_update.connect(self._update_status)
        self.message_received.connect(self.update_output)
        self.request_dll_selection.connect(self.select_dll)
        
        # Setup UI
        self.init_ui()
        self.load_saved_username()
        
        # Start queue checker
        self.queue_timer = QTimer()
        self.queue_timer.timeout.connect(self.check_queue)
        self.queue_timer.start(100)

    # Initialize the UI
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QGridLayout(central_widget)

        self.init_input_frame(main_layout)
        self.init_output_text(main_layout)
        self.init_status_frame(main_layout)
        
    # input frame
    def init_input_frame(self, main_layout):
        input_frame = QFrame()
        input_layout = QGridLayout(input_frame)
        input_layout.setContentsMargins(8, 8, 8, 4)

        self.init_account_name(input_layout)
        self.init_game_name(input_layout)
        self.init_app_id(input_layout)
        self.init_controls_frame(input_layout)

        main_layout.addWidget(input_frame, 0, 0)

    # Account name input
    def init_account_name(self, input_layout):
        account_label = QLabel("Account Name:")
        self.user_account_entry = QLineEdit()
        self.user_account_entry.setMinimumHeight(24)
        self.user_account_entry.textChanged.connect(self.save_username)
        input_layout.addWidget(account_label, 0, 0)
        input_layout.addWidget(self.user_account_entry, 0, 1)

    # Game name input
    def init_game_name(self, input_layout):
        game_label = QLabel("Game Name:")
        self.game_name_entry = QLineEdit()
        self.game_name_entry.setMinimumHeight(24)
        self.game_name_entry.textChanged.connect(self.on_game_name_change)
        input_layout.addWidget(game_label, 1, 0)
        input_layout.addWidget(self.game_name_entry, 1, 1)

    # AppID input
    def init_app_id(self, input_layout):
        appid_label = QLabel("AppID:")
        self.app_id_entry = QLineEdit()
        self.app_id_entry.setMinimumHeight(24)
        self.app_id_entry.textChanged.connect(self.on_app_id_change)
        input_layout.addWidget(appid_label, 2, 0)
        input_layout.addWidget(self.app_id_entry, 2, 1)

    # Controls frame
    def init_controls_frame(self, input_layout):
        controls_frame = QFrame()
        controls_frame.setFixedHeight(100)
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(5, 2, 5, 2)
        controls_layout.setSpacing(10)

        self.init_checkbox_frame(controls_layout)
        self.init_button_frame(controls_layout)

        input_layout.addWidget(controls_frame, 3, 0, 1, 2)

    # Checkbox frame
    def init_checkbox_frame(self, controls_layout):
        checkbox_frame = QFrame()
        checkbox_frame.setFixedWidth(270)
        checkbox_frame.setFixedHeight(80)
        checkbox_layout = QGridLayout(checkbox_frame)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)

        self.use_steam = QCheckBox("Use Steam")
        self.use_steam.setToolTip("Use Steam Community to fetch achievements data")
        self.use_steam.setToolTipDuration(5000)

        self.use_local_save = QCheckBox("Local Save")
        self.use_local_save.setToolTip("Save game data inside game folder")
        self.use_local_save.setToolTipDuration(5000)

        self.disable_lan_only = QCheckBox("Disable LAN Only")
        self.disable_lan_only.setToolTip("Allow connecting to online servers instead of LAN only")
        self.disable_lan_only.setToolTipDuration(5000)

        self.achievements_only = QCheckBox("Achievements Only")
        self.achievements_only.setToolTip("Only generate achievement files, skip other emulator files")
        self.achievements_only.setToolTipDuration(5000)

        self.disable_overlay = QCheckBox("Disable Overlay")
        self.disable_overlay.setToolTip("Disable the Experimental Steam overlay in-game (recommended)")
        self.disable_overlay.setToolTipDuration(5000)

        checkbox_layout.addWidget(self.use_steam, 0, 0)
        checkbox_layout.addWidget(self.use_local_save, 1, 0)
        checkbox_layout.addWidget(self.disable_overlay, 2, 0)
        checkbox_layout.addWidget(self.disable_lan_only, 0, 1)
        checkbox_layout.addWidget(self.achievements_only, 1, 1)

        controls_layout.addWidget(checkbox_frame, stretch=1)

    # Generate Button
    def init_button_frame(self, controls_layout):
        button_frame = QFrame()
        button_layout = QVBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 0, 0, 0)

        self.generate_btn = QPushButton("Generate")
        self.generate_btn.setMinimumHeight(35)
        self.generate_btn.setFixedWidth(90)
        self.generate_btn.clicked.connect(self.start_generate)

        button_layout.addStretch(1)
        button_layout.addWidget(self.generate_btn, alignment=Qt.AlignRight | Qt.AlignBottom)

        controls_layout.addWidget(button_frame)

    # Output Frame
    def init_output_text(self, main_layout):
        self.output_text = QPlainTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFocusPolicy(Qt.NoFocus)
        self.output_text.setStyleSheet(""" QPlainTextEdit { font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 14px; padding: 10px; } """)
        main_layout.addWidget(self.output_text, 1, 0)

    def write_output(self, message):
        self.msg_queue.put(message + '\n')

    def update_output(self, message):
        self.output_text.appendPlainText(message.rstrip())

    # Checks the message queue for any new messages
    # and emit them to display in the GUI output text area
    def check_queue(self):
        while True:
            try:
                msg = self.msg_queue.get_nowait()
                self.message_received.emit(msg)
            except queue.Empty:
                break

    # Status frame
    def init_status_frame(self, main_layout):
        self.status_frame = QFrame()
        self.status_frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
        status_layout = QGridLayout(self.status_frame)
        self.status_label = QLabel("Status: Ready")
        status_layout.addWidget(self.status_label, 0, 0)
        main_layout.addWidget(self.status_frame, 2, 0)

    def set_status(self, message, is_error=False):
        self.status_update.emit(message, is_error)

    def _update_status(self, message, is_error):
        prefix = "Error: " if is_error else "Status: "
        self.status_label.setText(prefix + message)
        
        palette = self.status_frame.palette()
        if is_error:
            palette.setColor(QPalette.Window, QColor(253, 231, 231))
            self.status_label.setStyleSheet("color: rgb(211, 47, 47)")
        elif "successfully" in message.lower():
            palette.setColor(QPalette.Window, QColor(237, 247, 237))
            self.status_label.setStyleSheet("color: rgb(46, 125, 50)")
        else:
            palette.setColor(QPalette.Window, QColor(240, 240, 240))
            self.status_label.setStyleSheet("color: black")
        
        self.status_frame.setPalette(palette)
        self.status_frame.setAutoFillBackground(True)

    # Event handlers
    def on_game_name_change(self):
        game_name = self.game_name_entry.text().strip()
        self.app_id_entry.setReadOnly(bool(game_name))

    def on_app_id_change(self):
        app_id = self.app_id_entry.text().strip()
        self.game_name_entry.setReadOnly(bool(app_id))

    # Save and load username from username.txt
    def load_saved_username(self):
        if os.path.exists(self.username_file):
            try:
                with open(self.username_file, 'r', encoding='utf-8') as f:
                    saved_username = f.read().strip()
                    if saved_username:
                        self.user_account_entry.setText(saved_username)
            except Exception as e:
                self.write_output(f"Failed to load username: {str(e)}")

    def save_username(self):
        username = self.user_account_entry.text().strip()
        try:
            with open(self.username_file, 'w', encoding='utf-8') as f:
                f.write(username)
        except Exception as e:
            self.write_output(f"Failed to save username: {str(e)}")

    # Generate configs.main.ini and configs.user.ini
    def create_user_config(self, settings_dir: str):
        user_account = self.user_account_entry.text().strip()
        use_local_save = self.use_local_save.isChecked()

        if self.disable_lan_only.isChecked() and not self.achievements_only.isChecked():
            config_main_path = os.path.join(settings_dir, "configs.main.ini")
            with open(config_main_path, "w", encoding="utf-8") as f:
                f.write("[main::connectivity]\ndisable_lan_only=1\n")
    
        if not user_account and not use_local_save:
            return

        config_content = ""
        if user_account:
            config_content += f"[user::general]\naccount_name={user_account}\nlanguage=english\n"
        if use_local_save:
            config_content += "[user::saves]\nlocal_save_path=./GSE Saves\n"
        if config_content and not self.achievements_only.isChecked():
            config_path = os.path.join(settings_dir, "configs.user.ini")
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(config_content)

    # Select steam_api(64).dll dialog
    def select_dll(self):
        self.write_output("Select steam_api(64).dll of the Game...")
        try:
            # Create a new QFileDialog instance instead of using static method
            dialog = QFileDialog(self)
            dialog.setWindowTitle("Select steam_api.dll or steam_api64.dll of the Game")
            dialog.setNameFilter("Steam API DLL (steam_api*.dll)")
            dialog.setFileMode(QFileDialog.ExistingFile)
            dialog.setViewMode(QFileDialog.Detail)
            
            if dialog.exec() == QFileDialog.Accepted:
                selected_files = dialog.selectedFiles()
                if selected_files:
                    dll_path = selected_files[0]
                    self.selected_dll_path = dll_path
                    self.continue_generation()
                else:
                    self.write_output("No DLL file selected")
                    self.set_status("No DLL selected", True)
                    self.generate_btn.setEnabled(True)
            else:
                self.write_output("DLL selection cancelled")
                self.set_status("No DLL selected", True)
                self.generate_btn.setEnabled(True)
                
        except Exception as e:
            self.write_output(f"Error selecting DLL: {str(e)}")
            self.set_status("Error in DLL selection", True)
            self.generate_btn.setEnabled(True)

    # Process input
    def process_input(self, app_id, game_name):
        result = {}
        
        if app_id:
            self.write_output("Parsing AppID...")
            app_index = get_steam_app_by_id(app_id)
            if not app_index or 'name' not in app_index:
                raise Exception(f"Could not find game name for AppID '{app_id}'")
            result = {'game_name': app_index['name'], 'app_id': app_id}
        
        elif game_name:
            self.write_output("Parsing game name...")
            app_info = get_steam_app_by_name(game_name)
            if not app_info or 'appid' not in app_info:
                raise Exception(f"Could not find AppID for '{game_name}'")
            result = {'game_name': game_name, 'app_id': str(app_info['appid'])}
        
        return result

    # Setup Goldberg Emu
    def setup_emu(self):
        EMU_FOLDER = os.path.join("assets", "goldberg_emu")
        if os.path.exists(EMU_FOLDER):
            return True
            
        self.write_output("Setting up GBE(Detanup01 fork)...")
        from setupEmu import download_goldberg, extract_archive
        
        try:
            archive_path = download_goldberg()
            extract_archive(archive_path)
            self.write_output("GBE setup successfully.")
            return True
        except Exception as e:
            raise Exception(f"Failed to setup GBE: {str(e)}")

    # Generate files
    def generate_files(self, app_id, file_path, use_steam):
        app_index = get_steam_app_by_id(app_id)
        if not app_index or 'name' not in app_index:
            raise Exception(f"Could not find game info for AppID '{app_id}'")
        
        game_name = "".join(c if c not in '<>:"/\\|?*' else '_' for c in app_index['name'])
        game_dir = f"{game_name} ({app_id})"
        settings_dir = os.path.join(game_dir, "steam_settings")
        
        try:
            os.makedirs(game_dir, exist_ok=True)
            os.makedirs(settings_dir, exist_ok=True)
            
            if not self.achievements_only.isChecked():
                self._generate_core_files(game_dir, app_id, file_path)
            
            self._generate_achievements(settings_dir, app_id, use_steam)
            self.create_user_config(settings_dir)
            
            return game_dir
        except Exception as e:
            raise Exception(f"Failed to generate files: {str(e)}")

    # Generate Goldberg emu files
    def _generate_core_files(self, game_dir, app_id, file_path):
        self.write_output("Generating GSE...")
        from goldberg_gen import generate_emu
        if not generate_emu(game_dir, app_id, file_path, self.disable_overlay.isChecked()):
            raise Exception("Failed to generate Goldberg emu files")
        
        self.write_output("Fetching DLCs...")
        dlc_details = fetch_dlc(app_id)
        create_dlc_config(game_dir, dlc_details)

    # Fetch and generate achievements.json
    def _generate_achievements(self, settings_dir, app_id, use_steam):
        self.write_output("Fetching Achievements...")
        original_cwd = os.getcwd()
        
        try:
            os.chdir(settings_dir)
            achievements = self._fetch_achievements(app_id, use_steam)
            if not achievements:
                self.write_output("No achievements found.")
        finally:
            os.chdir(original_cwd)

    def _fetch_achievements(self, app_id, use_steam):
        if use_steam:
            try:
                return fetch_from_steamcommunity(app_id, silent=True)
            except Exception:
                return None
        
        try:
            achievements = fetch_from_steamdb(app_id, silent=True) or fetch_from_steamcommunity(app_id, silent=True)
            return achievements
        except Exception:
            return None

    # Start generating GSE
    def start_generate(self):
        game_name = self.game_name_entry.text().strip()
        app_id = self.app_id_entry.text().strip()

        if not (game_name or app_id):
            self.set_status("Enter GameName or AppID to continue", True)
            return

        self._prepare_generation()
        
        signals = self.thread_manager.run_function(
            self.process_input,
            app_id,
            game_name
        )
        signals.result.connect(self.on_input_processed)
        signals.error.connect(self.on_error)

    def _prepare_generation(self):
        self.set_status("Generating GSE...")
        self.generate_btn.setEnabled(False)
        self.output_text.clear()
        sys.stdout = RedirectText(self.write_output)

    def on_input_processed(self, result):
        self.app_id_entry.setText(result['app_id'])
        self.game_name_entry.setText(result['game_name'])
        
        if not self.achievements_only.isChecked():
            # Setup emulator
            signals = self.thread_manager.run_function(self.setup_emu)
            signals.result.connect(lambda _: self.request_dll_selection.emit())
            signals.error.connect(self.on_error)
        else:
            self.continue_generation(skip_dll=True)

    def continue_generation(self, skip_dll=False):
        # Generate files
        signals = self.thread_manager.run_function(
            self.generate_files,
            self.app_id_entry.text().strip(),
            getattr(self, 'selected_dll_path', None) if not skip_dll else None,
            self.use_steam.isChecked()
        )
        signals.result.connect(self.on_generation_complete)
        signals.error.connect(self.on_error)

    def on_generation_complete(self, game_dir):
        self.write_output("Files generated successfully!")
        self.write_output(f"Location: {game_dir}")
        self.set_status("GSE generated successfully")
        self.generate_btn.setEnabled(True)
        sys.stdout = sys.__stdout__

    # Error handling
    def on_error(self, error):
        self.write_output(str(error))
        self.generate_btn.setEnabled(True)
        sys.stdout = sys.__stdout__

    def closeEvent(self, event):
        try:
            self.thread_manager.cleanup()
        except Exception:
            pass
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    gui = AchievementFetcherGUI()
    gui.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()