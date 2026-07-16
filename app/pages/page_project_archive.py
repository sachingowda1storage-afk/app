from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMessageBox, QFrame, QScrollArea)
from PySide6.QtCore import Qt, Signal
import database

class PageProjectArchive(QWidget):
    # Signals request to reopen a project in preview mode
    project_reopened = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.projects_list = []
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

        # Title
        header = QLabel("Historical Report Archive")
        header.setObjectName("PageHeader")
        layout.addWidget(header)

        # Search Bar
        search_frame = QFrame()
        search_frame.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #D6D6D6; border-radius: 4px; }")
        search_layout = QHBoxLayout(search_frame)
        
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search archive by Report Name, Request Reference, or Customer...")
        self.txt_search.textChanged.connect(self.apply_search)
        search_layout.addWidget(self.txt_search)
        
        self.btn_refresh = QPushButton("Refresh List")
        self.btn_refresh.setObjectName("SecondaryButton")
        self.btn_refresh.clicked.connect(self.reload_projects)
        search_layout.addWidget(self.btn_refresh)
        
        layout.addWidget(search_frame)

        # Table of Reports
        self.table_projects = QTableWidget(0, 7)
        self.table_projects.setHorizontalHeaderLabels([
            "ID", "Report Name", "Request No", "Battery Pack", "TSES Standard", "Status", "Date Created"
        ])
        self.table_projects.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_projects.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_projects.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_projects.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_projects.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_projects.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table_projects.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.table_projects.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_projects.setSelectionMode(QTableWidget.SingleSelection)
        self.table_projects.doubleClicked.connect(self.reopen_selected_project)
        layout.addWidget(self.table_projects)

        # Action Buttons
        btn_row = QHBoxLayout()
        self.btn_reopen = QPushButton("Re-open and Edit Report")
        self.btn_reopen.setObjectName("PrimaryButton")
        self.btn_reopen.setStyleSheet("QPushButton { background-color: #0F4C81; color: white; font-weight: bold; padding: 8px 16px; border-radius: 4px; }")
        self.btn_reopen.clicked.connect(self.reopen_selected_project)
        
        btn_row.addWidget(self.btn_reopen)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        scroll.setWidget(main_content)
        # Outer layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.reload_projects()

    def reload_projects(self):
        try:
            self.projects_list = database.get_projects()
            self.apply_search()
        except Exception as e:
            print("Failed to load archive projects:", e)

    def apply_search(self):
        search_text = self.txt_search.text().lower().strip()
        
        self.table_projects.setRowCount(0)
        row_idx = 0
        
        for p in self.projects_list:
            # Search matches
            name = str(p.get('name', '')).lower()
            req = str(p.get('request_no', '')).lower()
            cust = str(p.get('customer', '')).lower()
            
            if search_text and not (search_text in name or search_text in req or search_text in cust):
                continue
                
            self.table_projects.insertRow(row_idx)
            
            self.table_projects.setItem(row_idx, 0, QTableWidgetItem(str(p['id'])))
            self.table_projects.setItem(row_idx, 1, QTableWidgetItem(p['name']))
            self.table_projects.setItem(row_idx, 2, QTableWidgetItem(p['request_no']))
            self.table_projects.setItem(row_idx, 3, QTableWidgetItem(p['battery_name']))
            self.table_projects.setItem(row_idx, 4, QTableWidgetItem(p['tses_version']))
            
            status_item = QTableWidgetItem(p.get('status', 'Draft'))
            # Format status color
            if p.get('status') == 'Complete':
                status_item.setForeground(Qt.darkGreen)
            self.table_projects.setItem(row_idx, 5, status_item)
            
            created_str = p['created_at'][:19].replace('T', ' ')
            self.table_projects.setItem(row_idx, 6, QTableWidgetItem(created_str))
            
            row_idx += 1

    def reopen_selected_project(self):
        selected_ranges = self.table_projects.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, "Selection Required", "Please select a report from the table to re-open.")
            return
            
        row = selected_ranges[0].topRow()
        project_id = int(self.table_projects.item(row, 0).text())
        
        # Signal reopen request
        self.project_reopened.emit(project_id)
