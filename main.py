import sys
from PySide6.QtWidgets import QApplication
from src.gui.GSE_Generator import AchievementFetcherGUI

def main():
    app = QApplication(sys.argv)
    gui = AchievementFetcherGUI()
    gui.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()