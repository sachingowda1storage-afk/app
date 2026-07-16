import sys
import os
from PySide6.QtWidgets import QApplication
import database
from app import MainWindow

def main():
    # 1. Initialize and Seed the SQLite Database
    print("Initializing Database...")
    database.init_db()
    
    # 2. Start QApp
    app = QApplication(sys.argv)
    app.setApplicationName("Battery Test Report Pre-Processor")
    app.setOrganizationName("TVSM_QAD")

    # 3. Load Visual Stylesheet (QSS)
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    qss_path = os.path.join(base_dir, "assets", "style.qss")
    if os.path.exists(qss_path):
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
            print("Stylesheet applied successfully.")
        except Exception as e:
            print("Failed to apply QSS stylesheet:", e)
            
    # 4. Launch Main Window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
