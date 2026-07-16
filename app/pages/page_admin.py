from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMessageBox, QGroupBox, QFormLayout, 
                             QFrame, QStackedWidget, QFileDialog, QScrollArea)
from PySide6.QtCore import Qt, Signal
import os
import shutil
import zipfile
from datetime import datetime
import database

class PageAdmin(QWidget):
    # Signals user login changes
    user_changed = Signal(str, str) # username, role
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_user = None
        self.current_role = None
        self.init_ui()

    def init_ui(self):
        self.layout_stack = QStackedWidget(self)
        
        # Page 1: Login Form
        self.page_login = QWidget()
        login_layout = QVBoxLayout(self.page_login)
        login_layout.setContentsMargins(40, 40, 40, 40)
        login_layout.addStretch()
        
        login_card = QFrame()
        login_card.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #D6D6D6; border-radius: 6px; padding: 25px; max-width: 380px; }")
        card_layout = QVBoxLayout(login_card)
        
        lbl_login_hdr = QLabel("Sign in to QAD Laboratory Console")
        lbl_login_hdr.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F4C81; margin-bottom: 15px;")
        card_layout.addWidget(lbl_login_hdr)
        
        f_layout = QFormLayout()
        f_layout.setSpacing(10)
        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("Enter username (admin/engineer)")
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setPlaceholderText("Enter password")
        self.txt_password.returnPressed.connect(self.attempt_login)
        
        f_layout.addRow("Username:", self.txt_username)
        f_layout.addRow("Password:", self.txt_password)
        card_layout.addLayout(f_layout)
        
        btn_login = QPushButton("Login")
        btn_login.setObjectName("PrimaryButton")
        btn_login.clicked.connect(self.attempt_login)
        card_layout.addWidget(btn_login)
        
        # Helper login hint
        lbl_hint = QLabel("Default Logins:\nAdmin: admin / admin123\nEngineer: engineer / engineer123")
        lbl_hint.setStyleSheet("color: #777777; font-size: 11px; margin-top: 10px;")
        card_layout.addWidget(lbl_hint)
        
        hbox = QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(login_card)
        hbox.addStretch()
        login_layout.addLayout(hbox)
        login_layout.addStretch()
        
        self.layout_stack.addWidget(self.page_login)

        # Page 2: Admin Panel Controls
        self.page_panel_scroll = QScrollArea()
        self.page_panel_scroll.setWidgetResizable(True)
        self.page_panel_scroll.setFrameShape(QFrame.NoFrame)

        self.page_panel = QWidget()
        panel_layout = QVBoxLayout(self.page_panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(15)
        panel_layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
        
        # User details banner
        user_banner = QHBoxLayout()
        self.lbl_user_info = QLabel("Logged in as: User (Role)")
        self.lbl_user_info.setStyleSheet("font-weight: bold; font-size: 14px; color: #0F4C81;")
        btn_logout = QPushButton("Logout")
        btn_logout.setObjectName("SecondaryButton")
        btn_logout.clicked.connect(self.logout)
        
        user_banner.addWidget(self.lbl_user_info)
        user_banner.addStretch()
        user_banner.addWidget(btn_logout)
        panel_layout.addLayout(user_banner)
        
        # Audit Logs View
        log_group = QGroupBox("System Audit Trail")
        log_layout = QVBoxLayout(log_group)
        self.table_logs = QTableWidget(0, 3)
        self.table_logs.setHorizontalHeaderLabels(["Timestamp", "Operator", "Activity Action"])
        self.table_logs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_logs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_logs.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        log_layout.addWidget(self.table_logs)
        
        # Refresh logs button
        btn_ref_logs = QPushButton("Refresh Audit Logs")
        btn_ref_logs.setObjectName("SecondaryButton")
        btn_ref_logs.clicked.connect(self.reload_audit_logs)
        log_layout.addWidget(btn_ref_logs)
        
        panel_layout.addWidget(log_group, 1)
        
        # Database Backup & Restore Group (Only accessible to Admins)
        self.db_group = QGroupBox("Database Maintenance & Recovery")
        db_layout = QHBoxLayout(self.db_group)
        
        self.btn_backup = QPushButton("Backup Database (ZIP)")
        self.btn_backup.setObjectName("SecondaryButton")
        self.btn_backup.clicked.connect(self.backup_database)
        
        self.btn_restore = QPushButton("Restore Database from ZIP")
        self.btn_restore.setObjectName("DangerButton")
        self.btn_restore.clicked.connect(self.restore_database)
        
        self.btn_export_db = QPushButton("Export DB File")
        self.btn_export_db.setObjectName("SecondaryButton")
        self.btn_export_db.clicked.connect(self.export_db_file)
        
        db_layout.addWidget(self.btn_backup)
        db_layout.addWidget(self.btn_restore)
        db_layout.addWidget(self.btn_export_db)
        
        panel_layout.addWidget(self.db_group)
        
        self.page_panel_scroll.setWidget(self.page_panel)
        self.layout_stack.addWidget(self.page_panel_scroll)
        
        # Outer Layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.layout_stack)

    def attempt_login(self):
        username = self.txt_username.text().strip()
        password = self.txt_password.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Login Error", "Please fill in username and password.")
            return
            
        user = database.authenticate_user(username, password)
        if user:
            self.current_user = user['username']
            self.current_role = user['role']
            
            # Switch view
            self.lbl_user_info.setText(f"Logged in as: {self.current_user} ({self.current_role})")
            self.layout_stack.setCurrentIndex(1)
            
            # Restrict maintenance buttons if not Admin
            is_admin = (self.current_role == "Admin")
            self.db_group.setEnabled(is_admin)
            
            # Log audit
            database.log_audit(self.current_user, "Logged in to admin portal console.")
            self.reload_audit_logs()
            
            # Clear fields
            self.txt_username.clear()
            self.txt_password.clear()
            
            # Signal mainWindow
            self.user_changed.emit(self.current_user, self.current_role)
        else:
            QMessageBox.critical(self, "Authentication Failed", "Incorrect username or password. Please try again.")

    def logout(self):
        if self.current_user:
            database.log_audit(self.current_user, "Logged out from system console.")
            
        self.current_user = None
        self.current_role = None
        self.layout_stack.setCurrentIndex(0)
        self.user_changed.emit("", "")

    def reload_audit_logs(self):
        try:
            logs = database.get_audit_logs()
            self.table_logs.setRowCount(0)
            for idx, log in enumerate(logs):
                self.table_logs.insertRow(idx)
                
                timestamp = log['timestamp'][:19].replace('T', ' ')
                self.table_logs.setItem(idx, 0, QTableWidgetItem(timestamp))
                self.table_logs.setItem(idx, 1, QTableWidgetItem(str(log['username'] or 'System')))
                self.table_logs.setItem(idx, 2, QTableWidgetItem(log['action']))
        except Exception as e:
            print("Failed to load audit logs:", e)

    def backup_database(self):
        # Choose backup directory
        file_path, _ = QFileDialog.getSaveFileName(self, "Backup Database to ZIP", f"BatteryProcessor_Backup_{datetime.now().strftime('%y%m%d')}.zip", "ZIP Archives (*.zip)")
        if not file_path:
            return
            
        try:
            data_dir = os.path.dirname(database.DB_PATH)
            # Create zip archive of the data/ folder
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for root, dirs, files in os.walk(data_dir):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, data_dir)
                        zip_file.write(full_path, rel_path)
                        
            QMessageBox.information(self, "Backup Success", f"All active data, telemetry downsampled structures, and projects database successfully zipped in:\n{file_path}")
            database.log_audit(self.current_user, f"Database backup ZIP archive generated: {os.path.basename(file_path)}")
            self.reload_audit_logs()
        except Exception as e:
            QMessageBox.critical(self, "Backup Failed", f"Error generating ZIP archive: {e}")

    def restore_database(self):
        # Warning Confirmation
        reply = QMessageBox.critical(
            self, "Restore Database Caution",
            "WARNING: Restoring database from ZIP will OVERWRITE all current projects, configurations, and raw telemetry data. This action cannot be undone.\n\nDo you want to proceed?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.No:
            return
            
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Restore ZIP File", "", "ZIP Archives (*.zip)")
        if not file_path:
            return
            
        try:
            data_dir = os.path.dirname(database.DB_PATH)
            # Extract and overwrite
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                # Close active db connection first by clearing connections (handled by garbage collector mostly, but caution)
                zip_file.extractall(data_dir)
                
            QMessageBox.information(self, "Restore Successful", "Relational database files restored successfully. It is recommended to restart the application to clear internal memory caches.")
            database.log_audit(self.current_user, f"Restored active database records from ZIP backup: {os.path.basename(file_path)}")
            self.reload_audit_logs()
        except Exception as e:
            QMessageBox.critical(self, "Restore Failed", f"Database extraction failed: {e}")

    def export_db_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export SQLite DB File", "battery_processor.db", "SQLite Database (*.db)")
        if not file_path:
            return
            
        try:
            shutil.copy2(database.DB_PATH, file_path)
            QMessageBox.information(self, "Export Complete", f"SQLite database copy successfully saved to:\n{file_path}")
            database.log_audit(self.current_user, f"Exported SQLite DB file copy to: {os.path.basename(file_path)}")
            self.reload_audit_logs()
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error copying database file: {e}")
