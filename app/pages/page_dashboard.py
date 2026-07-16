from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout, QScrollArea
from PySide6.QtCore import Qt, Signal
import database

class PageDashboard(QWidget):
    # Signal to request navigation to other tabs
    # (e.g., 'battery', 'project', etc.)
    navigate_requested = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        # Allow scrolling of content
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        main_content = QWidget()
        layout = QVBoxLayout(main_content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)

        # Page Header
        header = QLabel("Laboratory Dashboard")
        header.setObjectName("PageHeader")
        layout.addWidget(header)

        # Subtitle
        sub = QLabel("Welcome to Battery Test Report Pre-Processor. Manage, validate, and analyze battery telemetry curves local and offline.")
        sub.setStyleSheet("color: #3C4043; font-size: 15px; margin-bottom: 10px;")
        layout.addWidget(sub)

        # Quick Statistics Grid (Equal Width Ratio Row)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)

        # Total Reports Card
        self.card_projects = QFrame()
        self.card_projects.setObjectName("CardProjects")
        self.card_projects.setProperty("class", "CardFrame")
        self.card_projects.setStyleSheet("QFrame#CardProjects { background-color: #FFFFFF; border: 1px solid #D6D6D6; border-radius: 6px; }")
        p_layout = QVBoxLayout(self.card_projects)
        p_val = QLabel("0")
        p_val.setStyleSheet("font-size: 32px; font-weight: bold; color: #0F4C81;")
        self.lbl_projects_val = p_val
        p_lbl = QLabel("Archive Reports Generated")
        p_lbl.setStyleSheet("color: #3C4043; font-size: 14px; font-weight: bold;")
        p_layout.addWidget(p_val)
        p_layout.addWidget(p_lbl)
        stats_layout.addWidget(self.card_projects, 1)

        # Preloaded Batteries Card
        self.card_bat = QFrame()
        self.card_bat.setObjectName("CardBat")
        self.card_bat.setStyleSheet("QFrame#CardBat { background-color: #FFFFFF; border: 1px solid #D6D6D6; border-radius: 6px; }")
        b_layout = QVBoxLayout(self.card_bat)
        b_val = QLabel("5")
        self.lbl_bat_val = b_val
        b_val.setStyleSheet("font-size: 32px; font-weight: bold; color: #0F4C81;")
        b_lbl = QLabel("Battery Packs Configured")
        b_lbl.setStyleSheet("color: #3C4043; font-size: 14px; font-weight: bold;")
        b_layout.addWidget(b_val)
        b_layout.addWidget(b_lbl)
        stats_layout.addWidget(self.card_bat, 1)

        # Standard Predefined Tests Card
        self.card_tests = QFrame()
        self.card_tests.setObjectName("CardTests")
        self.card_tests.setStyleSheet("QFrame#CardTests { background-color: #FFFFFF; border: 1px solid #D6D6D6; border-radius: 6px; }")
        t_layout = QVBoxLayout(self.card_tests)
        t_val = QLabel("101")
        self.lbl_tests_val = t_val
        t_val.setStyleSheet("font-size: 32px; font-weight: bold; color: #0F4C81;")
        t_lbl = QLabel("TSES Predefined Tests")
        t_lbl.setStyleSheet("color: #3C4043; font-size: 14px; font-weight: bold;")
        t_layout.addWidget(t_val)
        t_layout.addWidget(t_lbl)
        stats_layout.addWidget(self.card_tests, 1)

        layout.addLayout(stats_layout)
        layout.addSpacing(10)

        # Center Section - Active Report Overview
        self.active_frame = QFrame()
        self.active_frame.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #D6D6D6; border-radius: 6px; padding: 15px; }")
        act_layout = QVBoxLayout(self.active_frame)
        
        act_header = QLabel("Active Analysis Report")
        act_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F4C81;")
        act_layout.addWidget(act_header)
        
        self.lbl_active_desc = QLabel("No active test report is currently open. Start a new workflow to load battery details and run cycler Excel calculations.")
        self.lbl_active_desc.setWordWrap(True)
        self.lbl_active_desc.setStyleSheet("color: #202124; font-size: 14px; margin-top: 5px; margin-bottom: 15px;")
        act_layout.addWidget(self.lbl_active_desc)
        
        # Action Buttons Layout
        btn_layout = QHBoxLayout()
        self.btn_new_project = QPushButton("Start New Validation")
        self.btn_new_project.setObjectName("PrimaryButton")
        self.btn_new_project.setStyleSheet("QPushButton { background-color: #0F4C81; color: white; font-weight: bold; border-radius: 4px; padding: 8px 16px; }")
        self.btn_new_project.clicked.connect(lambda: self.navigate_requested.emit("test_selection"))
        
        self.btn_manage_bat = QPushButton("Manage Battery Packs")
        self.btn_manage_bat.setObjectName("SecondaryButton")
        self.btn_manage_bat.setStyleSheet("QPushButton { border: 1px solid #0F4C81; color: #0F4C81; font-weight: bold; border-radius: 4px; padding: 8px 16px; background-color: transparent; }")
        self.btn_manage_bat.clicked.connect(lambda: self.navigate_requested.emit("battery"))
        
        btn_layout.addWidget(self.btn_new_project)
        btn_layout.addWidget(self.btn_manage_bat)
        btn_layout.addStretch()
        
        act_layout.addLayout(btn_layout)
        layout.addWidget(self.active_frame)
        
        # Audit Logs preview frame
        self.audit_frame = QFrame()
        self.audit_frame.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #D6D6D6; border-radius: 6px; padding: 15px; }")
        aud_layout = QVBoxLayout(self.audit_frame)
        aud_hdr = QLabel("Recent System Activity")
        aud_hdr.setStyleSheet("font-size: 14px; font-weight: bold; color: #0F4C81; margin-bottom: 5px;")
        aud_layout.addWidget(aud_hdr)
        
        self.lbl_audit_1 = QLabel("- System seeded with TSES 799 v8 standard tests database.")
        self.lbl_audit_1.setStyleSheet("color: #333333; font-family: monospace;")
        self.lbl_audit_2 = QLabel("- SQLite Relational Database engine operational.")
        self.lbl_audit_2.setStyleSheet("color: #333333; font-family: monospace;")
        aud_layout.addWidget(self.lbl_audit_1)
        aud_layout.addWidget(self.lbl_audit_2)
        
        layout.addWidget(self.audit_frame)
        layout.addStretch()
        
        scroll.setWidget(main_content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        
    def refresh_stats(self):
        """Reload statistics from SQLite db."""
        try:
            # 1. Total projects count
            projects = database.get_projects()
            self.lbl_projects_val.setText(str(len(projects)))
            
            # 2. Batteries count
            batteries = database.get_all_batteries()
            self.lbl_bat_val.setText(str(len(batteries)))
            
            # Update Active report card
            if projects:
                latest = projects[0]
                self.lbl_active_desc.setText(
                    f"Last active report: '{latest['name']}' (Request: {latest['request_no']}) created on {latest['created_at'][:10]}.\n"
                    f"Battery under test: {latest['battery_name']} | TSES Standard: {latest['tses_version']}."
                )
                self.btn_new_project.setText("Configure Active Report")
            else:
                self.lbl_active_desc.setText("No active test report is currently open. Start a new workflow to load battery details and run cycler Excel calculations.")
                self.btn_new_project.setText("Start New Validation")
                
            # Recent logs
            logs = database.get_audit_logs()
            if len(logs) >= 2:
                self.lbl_audit_1.setText(f"- {logs[0]['timestamp'][:19].replace('T',' ')}: {logs[0]['action']}")
                self.lbl_audit_2.setText(f"- {logs[1]['timestamp'][:19].replace('T',' ')}: {logs[1]['action']}")
            elif len(logs) == 1:
                self.lbl_audit_1.setText(f"- {logs[0]['timestamp'][:19].replace('T',' ')}: {logs[0]['action']}")
                self.lbl_audit_2.setText("- SQLite Relational Database engine operational.")
        except Exception as e:
            print("Dashboard statistics reload error:", e)
