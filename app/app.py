from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QStackedWidget, QLabel, QFrame, QStatusBar)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
import os

# Import views
from pages.page_dashboard import PageDashboard
from pages.page_battery import PageBattery
from pages.page_tses import PageTses
from pages.page_test_selection import PageTestSelection
from pages.page_test_input import PageTestInput
from pages.page_report_preview import PageReportPreview
from pages.page_project_archive import PageProjectArchive
from pages.page_admin import PageAdmin

import database

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Battery Test Report Pre-Processor")
        self.resize(1100, 750)
        
        self.active_project_id = None
        self.active_battery_name = "None selected"
        self.active_tses_name = "TSES 799 v8"
        self.operator_name = "Guest"
        self.operator_role = "Engineer"
        
        self.init_ui()
        
    def init_ui(self):
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Left Sidebar Navigation Frame
        self.sidebar = QFrame()
        self.sidebar.setObjectName("SidebarFrame")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(2)
        
        # Logo and Title
        title_box = QHBoxLayout()
        title_box.setContentsMargins(10, 15, 10, 15)
        
        logo_label = QLabel()
        import sys
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(base_dir, "assets", "logo.png")
        if os.path.exists(logo_path):
            logo_pix = QPixmap(logo_path).scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pix)
            title_box.addWidget(logo_label)
            
        title_label = QLabel("TVSM QAD LAB")
        title_label.setStyleSheet("font-size: 18px; font-weight: 900; color: #0F4C81; letter-spacing: 0.5px;")
        title_box.addWidget(title_label, 1)
        sidebar_layout.addLayout(title_box)
        
        # Navigation Buttons
        self.nav_buttons = {}
        pages_config = [
            ("dashboard", "Dashboard Overview"),
            ("battery", "Battery Master Spec"),
            ("tses", "TSES Config"),
            ("test_selection", "Test Selection"),
            ("test_input", "Ingest Test Logs"),
            ("report_preview", "Report Preview & Export"),
            ("project_archive", "Report Archive"),
            ("admin", "Admin Panel")
        ]
        
        for tab_id, text in pages_config:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setObjectName("SidebarButton")
            btn.setProperty("tab_id", tab_id)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #3C4043;
                    border: none;
                    border-radius: 4px;
                    text-align: left;
                    padding: 10px 15px;
                    margin: 2px 10px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #F1F3F4;
                    color: #202124;
                }
                QPushButton:checked {
                    background-color: #E8F0FE;
                    color: #0F4C81;
                    font-weight: bold;
                }
            """)
            btn.clicked.connect(self.on_nav_clicked)
            sidebar_layout.addWidget(btn)
            self.nav_buttons[tab_id] = btn
            
        # Active status block on sidebar
        sidebar_layout.addStretch()
        
        self.status_box = QFrame()
        self.status_box.setStyleSheet("QFrame { background-color: #F8F9FA; border-top: 1px solid #D6D6D6; padding: 12px; }")
        status_layout = QVBoxLayout(self.status_box)
        status_layout.setSpacing(4)
        
        self.lbl_side_battery = QLabel(f"Battery: {self.active_battery_name}")
        self.lbl_side_battery.setStyleSheet("font-size: 13px; color: #202124; font-weight: 500;")
        self.lbl_side_tses = QLabel(f"TSES: {self.active_tses_name}")
        self.lbl_side_tses.setStyleSheet("font-size: 13px; color: #202124; font-weight: 500;")
        self.lbl_side_project = QLabel("Report: None active")
        self.lbl_side_project.setStyleSheet("font-size: 13px; color: #202124; font-weight: 500;")
        self.lbl_side_operator = QLabel(f"Op: {self.operator_name}")
        self.lbl_side_operator.setStyleSheet("font-size: 13px; color: #0F4C81; font-weight: bold;")
        
        status_layout.addWidget(self.lbl_side_battery)
        status_layout.addWidget(self.lbl_side_tses)
        status_layout.addWidget(self.lbl_side_project)
        status_layout.addWidget(self.lbl_side_operator)
        
        sidebar_layout.addWidget(self.status_box)
        main_layout.addWidget(self.sidebar)

        # 2. Right Stacked Widget Area
        self.stack = QStackedWidget()
        
        self.page_dashboard = PageDashboard()
        self.page_battery = PageBattery()
        self.page_tses = PageTses()
        self.page_test_selection = PageTestSelection()
        self.page_test_input = PageTestInput()
        self.page_report_preview = PageReportPreview()
        self.page_project_archive = PageProjectArchive()
        self.page_admin = PageAdmin()
        
        self.stack.addWidget(self.page_dashboard)
        self.stack.addWidget(self.page_battery)
        self.stack.addWidget(self.page_tses)
        self.stack.addWidget(self.page_test_selection)
        self.stack.addWidget(self.page_test_input)
        self.stack.addWidget(self.page_report_preview)
        self.stack.addWidget(self.page_project_archive)
        self.stack.addWidget(self.page_admin)
        
        main_layout.addWidget(self.stack, 1)

        # 3. Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Systems initialized. SQLite relational backend connected.")
        
        # Connect View Signals
        self.page_dashboard.navigate_requested.connect(self.switch_to_tab)
        self.page_battery.battery_selected.connect(self.on_battery_selected)
        if self.page_battery.active_battery:
            self.on_battery_selected(self.page_battery.active_battery['id'], self.page_battery.active_battery['name'])
        self.page_tses.tses_changed.connect(self.on_tses_changed)
        self.page_test_selection.tests_selected.connect(self.on_tests_selected)
        self.page_test_input.processing_completed.connect(self.on_processing_completed)
        self.page_report_preview.project_id = None # initial placeholder
        self.page_project_archive.project_reopened.connect(self.on_project_reopened)
        self.page_admin.user_changed.connect(self.on_user_changed)

        # Set default active tab
        self.switch_to_tab("dashboard")

    def on_nav_clicked(self):
        btn = self.sender()
        tab_id = btn.property("tab_id")
        self.switch_to_tab(tab_id)

    def switch_to_tab(self, tab_id):
        # 1. Uncheck other buttons
        for tid, btn in self.nav_buttons.items():
            btn.blockSignals(True)
            btn.setChecked(tid == tab_id)
            btn.blockSignals(False)
            
        # 2. Switch stack widget
        pages_map = {
            "dashboard": 0,
            "battery": 1,
            "tses": 2,
            "test_selection": 3,
            "test_input": 4,
            "report_preview": 5,
            "project_archive": 6,
            "admin": 7
        }
        self.stack.setCurrentIndex(pages_map.get(tab_id, 0))
        
        # Refresh dynamic listings on tab show
        if tab_id == "dashboard":
            self.page_dashboard.refresh_stats()
        elif tab_id == "project_archive":
            self.page_project_archive.reload_projects()

    def on_battery_selected(self, battery_id, name):
        self.active_battery_name = name
        self.lbl_side_battery.setText(f"Battery: {self.active_battery_name}")
        # Update active battery in test selection screen for project seeding
        self.page_test_selection.battery_id = battery_id

    def on_tses_changed(self, tses_id, version):
        self.active_tses_name = version
        self.lbl_side_tses.setText(f"TSES: {self.active_tses_name}")
        self.page_test_selection.set_tses_version(tses_id)
        self.page_test_input.tses_version_id = tses_id

    def on_tests_selected(self, project_id, test_ids, is_combined):
        self.switch_to_tab("test_input")
        self.active_project_id = project_id
        self.lbl_side_project.setText(f"Report: ID {project_id} (Active)")
        print("Entered on_tests_selected")
        
        # Sync active battery into project in Database
        # User selected a battery on PageBattery, update project battery id link
        if self.page_battery.active_battery:
            battery_id = self.page_battery.active_battery['id']
            conn = database.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE projects SET battery_id = ? WHERE id = ?", (battery_id, project_id))
            conn.commit()
            conn.close()

        print("Current TSES in TestSelection:", self.page_test_selection.tses_version_id)

        self.page_test_input.tses_version_id = self.page_test_selection.tses_version_id

        print("Assigned TSES to TestInput:", self.page_test_input.tses_version_id)
            
        # Configure input tab
        self.page_test_input.set_project_selection(project_id, test_ids, is_combined)
        self.switch_to_tab("test_input")
        self.status_bar.showMessage(f"Report ID {project_id} configured. Select cycler files for processing.")

    def on_processing_completed(self, project_id):
        self.page_report_preview.set_project(project_id)
        self.switch_to_tab("report_preview")
        self.status_bar.showMessage(f"Telemetry processed for Report ID {project_id}. Report preview generated.")

    def on_project_reopened(self, project_id):
        self.active_project_id = project_id
        self.lbl_side_project.setText(f"Report: ID {project_id} (Active)")
        self.page_report_preview.set_project(project_id)
        self.switch_to_tab("report_preview")
        self.status_bar.showMessage(f"Report ID {project_id} loaded from archive.")

    def on_user_changed(self, username, role):
        if username:
            self.operator_name = username
            self.operator_role = role
            self.lbl_side_operator.setText(f"Op: {self.operator_name} ({self.operator_role})")
            self.status_bar.showMessage(f"Authenticated as {username} ({role}).")
        else:
            self.operator_name = "Guest"
            self.operator_role = "Engineer"
            self.lbl_side_operator.setText(f"Op: {self.operator_name}")
            self.status_bar.showMessage("Operator logged out.")
