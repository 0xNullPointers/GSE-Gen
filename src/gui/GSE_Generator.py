import os
import sys
import queue
import configparser
from PySide6.QtWidgets import QMainWindow, QWidget, QGridLayout, QLabel, QLineEdit, QFrame, QHBoxLayout, QVBoxLayout, QCheckBox, QPushButton, QPlainTextEdit, QFileDialog
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPalette, QIcon

# Get the path of the resource files
def get_resource_path(filename):
    try:
        base_path = sys._MEIPASS  # type: ignore
    except AttributeError:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_path, filename)

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
        
        # Initialize basic attributes
        self.msg_queue = queue.Queue()
        self.assets_dir = os.path.join(os.getcwd(), "assets")
        os.makedirs(self.assets_dir, exist_ok=True)
        self.settings_path = os.path.join(self.assets_dir, 'settings.ini')
        
        # Lazy initialize thread manager
        self._thread_manager = None
        
        # Connect signals
        self.status_update.connect(self._update_status)
        self.message_received.connect(self.update_output)
        self.request_dll_selection.connect(self.select_dll)
        
        # Setup UI and window properties
        self.init_ui()
        self.load_saved_username()
        self.setup_window()
        self.setup_queue_checker()
        self.show_help_text()  # Add guide in output_text-box

    def setup_window(self):
        # Setup window prop and icon
        self.setWindowTitle("GSE Generator")
        self.resize(700, 500)
        self.setMinimumSize(500, 500)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowCloseButtonHint)    # Disable maximize button
        icon_path = get_resource_path('icon.ico')
        self.setWindowIcon(QIcon(icon_path))

    def setup_queue_checker(self):
        # Start the queue checker
        self.queue_timer = QTimer()
        self.queue_timer.timeout.connect(self.check_queue)
        self.queue_timer.start(100)

    @property
    def thread_manager(self):
        if self._thread_manager is None:
            from src.core.threadManager import ThreadManager    # import
            self._thread_manager = ThreadManager()
        return self._thread_manager

    def show_help_text(self):
        help_text = """GSE Generator - Quick Guide

  • Account Name: Optional (default used if empty)
  • Game Name: Full game name (e.g. "Counter-Strike 2")  
  • AppID: Steam AppID number (e.g. 730)

REQUIRED: Either Game Name OR AppID must be provided — not both.
TIPS: Hover over the options for more info

Click Generate to start the process."""

        self.output_text.setPlainText(help_text)
        self.output_text.setStyleSheet("""QPlainTextEdit { font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 14px; padding: 10px; color: #888888; }""")

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
        self.user_account_entry.setPlaceholderText("e.g. gse orca")
        self.user_account_entry.textChanged.connect(self.save_username)
        input_layout.addWidget(account_label, 0, 0)
        input_layout.addWidget(self.user_account_entry, 0, 1)

    # Game name input
    def init_game_name(self, input_layout):
        game_label = QLabel("Game Name:")
        self.game_name_entry = QLineEdit()
        self.game_name_entry.setMinimumHeight(24)
        self.game_name_entry.setPlaceholderText("e.g. Counter-Strike 2")
        self.game_name_entry.textChanged.connect(self.on_game_name_change)
        input_layout.addWidget(game_label, 1, 0)
        input_layout.addWidget(self.game_name_entry, 1, 1)

    # AppID input
    def init_app_id(self, input_layout):
        appid_label = QLabel("AppID:")
        self.app_id_entry = QLineEdit()
        self.app_id_entry.setMinimumHeight(24)
        self.app_id_entry.setPlaceholderText("e.g. 730")
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

        # Init config parser
        self.config = configparser.ConfigParser(comment_prefixes='/', allow_no_value=True)
        self.config.optionxform = str  # type: ignore
        if os.path.exists(self.settings_path):
            self.config.read(self.settings_path)
        if 'Settings' not in self.config:
            self.config['Settings'] = {}

        # Create checkbox function
        def create_checkbox(name, label, tooltip):
            checkbox = QCheckBox(label)
            checkbox.setToolTip(tooltip)
            checkbox.setToolTipDuration(5000)
            # Get config value, default is False
            checkbox.setChecked(self.config.getboolean('Settings', name, fallback=False))
            
            def on_change(state):
                self.config['Settings'][name] = str(bool(state))
                with open(self.settings_path, 'w') as f:
                    self.config.write(f)
            
            checkbox.stateChanged.connect(on_change)
            return checkbox

        # Create checkboxes
        self.use_steam = create_checkbox('use_steam', "Use Steam", "Use Steam Community to fetch achievements data")
        self.use_local_save = create_checkbox('use_local_save', "Local Save", "Save game data inside game folder")
        self.disable_lan_only = create_checkbox('disable_lan_only', "Disable LAN Only", "Allow connecting to online servers instead of LAN only")
        self.achievements_only = create_checkbox('achievements_only', "Achievements Only", "Only generate achievement files, skip other emulator files")
        self.disable_overlay = create_checkbox('disable_overlay', "Disable Overlay", "Disable the Experimental Steam overlay in-game (recommended)")
        self.auto_replace = create_checkbox('auto_replace', "Auto Replace", "Automatically replace GSE files in Game dir")

        # Add checkboxes to layout
        checkbox_layout.addWidget(self.use_steam, 0, 0)
        checkbox_layout.addWidget(self.use_local_save, 1, 0)
        checkbox_layout.addWidget(self.disable_overlay, 2, 0)
        checkbox_layout.addWidget(self.disable_lan_only, 0, 1)
        checkbox_layout.addWidget(self.achievements_only, 1, 1)
        checkbox_layout.addWidget(self.auto_replace, 2, 1)

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
        button_layout.addWidget(self.generate_btn, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

        controls_layout.addWidget(button_frame)

    # Output Frame
    def init_output_text(self, main_layout):
        self.output_text = QPlainTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        self.status_frame.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Raised)
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
            bg_color = QColor(253, 231, 231)
            text_color = "rgb(211, 47, 47)"
        elif "successfully" in message.lower():
            bg_color = QColor(237, 255, 237)
            text_color = "rgb(46, 125, 50)"
        else:
            # Use system colors
            bg_color = self.palette().color(QPalette.ColorRole.Window)
            text_color = self.palette().color(QPalette.ColorRole.WindowText).name()
        
        palette.setColor(QPalette.ColorRole.Window, bg_color)
        self.status_frame.setPalette(palette)
        self.status_frame.setAutoFillBackground(True)
        self.status_label.setStyleSheet(f"color: {text_color}")

    # Event handlers
    def on_game_name_change(self):
        game_name = self.game_name_entry.text().strip()
        self.app_id_entry.setReadOnly(bool(game_name))

    def on_app_id_change(self):
        app_id = self.app_id_entry.text().strip()
        self.game_name_entry.setReadOnly(bool(app_id))

    # Save and load username from settings.ini
    def save_username(self):
        try:
            username = self.user_account_entry.text().strip()
            if 'Settings' not in self.config:
                self.config['Settings'] = {}
            self.config['Settings']['username'] = username
            with open(self.settings_path, 'w') as f:
                self.config.write(f)
        except Exception as e:
            self.write_output(f"Failed to save username: {str(e)}")

    def load_saved_username(self):
        try:
            username = self.config.get('Settings', 'username', fallback='')
            if username:
                self.user_account_entry.setText(username)
        except Exception as e:
            self.write_output(f"Failed to load username: {str(e)}")

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
        self.write_output("Select Original Game folder...")
        try:
            # Create a new QFileDialog
            dialog = QFileDialog(self)
            dialog.setWindowTitle("Select original Game folder")
            dialog.setFileMode(QFileDialog.FileMode.Directory)
            dialog.setViewMode(QFileDialog.ViewMode.Detail)
        
            if dialog.exec() == QFileDialog.DialogCode.Accepted:
                selected_files = dialog.selectedFiles()
                if selected_files:
                    folder_path = os.path.normpath(selected_files[0])
                    if os.access(folder_path, os.R_OK):
                        self.selected_dll_path = folder_path
                        self.continue_generation()
                    else:
                        self.write_output(f"Permission denied - {folder_path}")
                        self.set_status("Permission denied", True)
                        self.generate_btn.setEnabled(True)
                else:
                    self.write_output("No folder selected")
                    self.set_status("No folder selected", True)
                    self.generate_btn.setEnabled(True)
            else:
                self.write_output("No folder selected")
                self.set_status("No folder selected", True)
                self.generate_btn.setEnabled(True)
                
        except Exception as e:
            self.write_output(f"Error selecting folder: {str(e)}")
            self.set_status("Error in folder selection", True)
            self.generate_btn.setEnabled(True)

    # Process input
    def process_input(self, app_id, game_name):
        from src.core.appID_finder import get_steam_app_by_id, get_steam_app_by_name    # import

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
        from src.core.setupEmu import download_goldberg, extract_archive    # import
        
        EMU_FOLDER = os.path.join("assets", "goldberg_emu")
        if os.path.exists(EMU_FOLDER):
            return True
            
        self.write_output("Setting up GBE(Detanup01 fork)...")
        
        try:
            archive_path = download_goldberg()
            extract_archive(archive_path)
            self.write_output("GBE setup successfully.")
            return True
        except Exception as e:
            raise Exception(f"Failed to setup GBE: {str(e)}")

    # Generate files
    def generate_files(self, app_id, file_path, use_steam):
        from src.core.appID_finder import get_steam_app_by_id    # import
        import shutil
        
        app_index = get_steam_app_by_id(app_id)
        if not app_index or 'name' not in app_index:
            raise Exception(f"Could not find game info for AppID '{app_id}'")
        
        game_name = "".join(c if c not in '<>:"/\\|?*' else '_' for c in app_index['name'])
        game_dir = f"{game_name} ({app_id})"
        settings_dir = os.path.join(game_dir, "steam_settings")
        
        try:
            os.makedirs(game_dir, exist_ok=True)
            os.makedirs(settings_dir, exist_ok=True)
            
            dll_path = None
            if not self.achievements_only.isChecked():
                # Setup emulator
                dll_path = self._generate_core_files(game_dir, app_id, file_path)
            
            self._generate_achievements(settings_dir, app_id, use_steam)
            self.create_user_config(settings_dir)
            
            # Copying files after all files are generated
            if self.auto_replace.isChecked() and dll_path:
                try:
                    target_dir = os.path.dirname(dll_path)
                    for root, dirs, files in os.walk(game_dir):
                        rel_path = os.path.relpath(root, game_dir)
                        for dir_name in dirs:
                            target_path = os.path.join(target_dir, rel_path, dir_name)
                            os.makedirs(target_path, exist_ok=True)
                        for file_name in files:
                            source_file = os.path.join(root, file_name)
                            target_file = os.path.join(target_dir, rel_path, file_name)
                            try:
                                if os.path.exists(target_file):
                                    os.remove(target_file)
                            except PermissionError:
                                continue
                            shutil.copy2(source_file, target_file)
                    self.write_output("Files copied to Game dir successfully!")
                except Exception as e:
                    self.write_output(f"Warning: Failed to copy files: {str(e)}")
                    self.set_status("Failed to copy files", True)

            return game_dir
        except Exception as e:
            raise Exception(f"Failed to generate files: {str(e)}")

    # Generate Goldberg emu files
    def _generate_core_files(self, game_dir, app_id, file_path):
        from src.core.goldberg_gen import generate_emu    # import
        from src.core.dlc_gen import fetch_dlc, create_dlc_config    # import
        
        self.write_output("Generating GSE...")
        
        # Resolve DLL path
        ignore_folders = ['gse', 'crack']
        ignore_folders = [folder.lower() for folder in ignore_folders]
        file_path = os.path.abspath(file_path)
        dll_path = None
        for root, dirs, files in os.walk(file_path, topdown=True):
            dirs[:] = [d for d in dirs if d.lower() not in ignore_folders]
            if 'steam_api.dll' in files:    # Check for steam_api.dll
                dll_path = os.path.join(root, 'steam_api.dll')
            if 'steam_api64.dll' in files:    # If no steam_api.dll, check for steam_api64.dll
                dll_path = os.path.join(root, 'steam_api64.dll')
        
        if not dll_path:
            raise Exception("Could not find steam_api.dll or steam_api64.dll")
            
        if not generate_emu(game_dir, app_id, dll_path, self.disable_overlay.isChecked()):
            raise Exception("Failed to generate Goldberg emu files")
        
        self.write_output("Fetching DLCs...")
        dlc_details = fetch_dlc(app_id)
        create_dlc_config(game_dir, dlc_details)
        return dll_path
                
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
        from src.core.achievements import fetch_from_steamcommunity, fetch_from_steamdb    # import
        
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
        self.output_text.clear()    # Clear guide text
        self.output_text.setStyleSheet("""QPlainTextEdit { font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 14px; padding: 10px; }""")

        game_name = self.game_name_entry.text().strip()
        app_id = self.app_id_entry.text().strip()

        if not (game_name or app_id):
            self.set_status("Enter GameName or AppID to continue", True)
            return

        self._prepare_generation()
        
        signals = self.thread_manager.run_function(self.process_input, app_id, game_name)
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
        # Stop queue timer
        if hasattr(self, 'queue_timer'):
            self.queue_timer.stop()
        
        # Clear message queue
        if hasattr(self, 'msg_queue'):
            while not self.msg_queue.empty():
                try:
                    self.msg_queue.get_nowait()
                except queue.Empty:
                    break
        
        self.hide()  # Hide window immediately
        event.accept()  # Accept close event
        
        # Cleanup thread manager in background
        if self._thread_manager is not None:
            QTimer.singleShot(0, self._thread_manager.cleanup)