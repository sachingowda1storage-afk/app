from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QRadioButton, QButtonGroup, QComboBox, QLineEdit, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QGroupBox, QCheckBox, QFormLayout, QMessageBox, QFrame, QScrollArea)
from PySide6.QtCore import Qt, Signal
import database
from datetime import datetime

class PageTestSelection(QWidget):
    # Signals active project test selection
    # (project_id, list_of_selected_test_ids, is_combined)
    tests_selected = Signal(int, list, bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tses_version_id = 1 # default to TSES v8 (id=1)
        self.all_tests = []
        self.selected_tests = []
        self.init_ui()

    def set_tses_version(self, tses_id):
        self.tses_version_id = tses_id
        self.reload_tests()

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
        header = QLabel("Test Selection & Configuration")
        header.setObjectName("PageHeader")
        layout.addWidget(header)

        # 1. Report Mode Selection (Individual vs Combined)
        mode_group = QGroupBox("Select Report Structure")
        mode_layout = QHBoxLayout(mode_group)
        
        self.mode_group_btns = QButtonGroup(self)
        self.rb_individual = QRadioButton("Individual Test Report (Generate detailed analysis of a single test curve)")
        self.rb_individual.setChecked(True)
        self.rb_combined = QRadioButton("Combined Test Report (Compile multiple tests into a summary table without curves)")
        
        self.mode_group_btns.addButton(self.rb_individual, 0)
        self.mode_group_btns.addButton(self.rb_combined, 1)
        self.rb_individual.toggled.connect(self.toggle_mode)
        
        mode_layout.addWidget(self.rb_individual)
        mode_layout.addWidget(self.rb_combined)
        mode_layout.addStretch()
        layout.addWidget(mode_group)

        # 2. Search & Filter Block
        filter_group = QGroupBox("Search and Filter Predefined Tests")
        filter_layout = QVBoxLayout(filter_group)
        
        search_row = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search by Class ID, Test Name, or keyword...")
        self.txt_search.textChanged.connect(self.apply_filter)
        search_row.addWidget(self.txt_search)
        
        self.cb_category = QComboBox()
        self.cb_category.addItems(["All Categories", "Electrical", "Mechanical", "Thermal / Climatic", "Life / Aging", "Functional Safety"])
        self.cb_category.currentIndexChanged.connect(self.apply_filter)
        search_row.addWidget(self.cb_category)
        
        filter_layout.addLayout(search_row)
        layout.addWidget(filter_group)

        # 3. Test Selection List View
        self.list_frame = QFrame()
        self.list_frame.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #D6D6D6; border-radius: 4px; }")
        list_layout = QVBoxLayout(self.list_frame)
        
        self.lbl_select_instructions = QLabel("Select a test from the checklist below:")
        self.lbl_select_instructions.setStyleSheet("font-weight: bold; color: #202124; font-size: 14px;")
        list_layout.addWidget(self.lbl_select_instructions)
        
        # Test checklist table
        self.table_tests = QTableWidget(0, 5)
        self.table_tests.setMinimumHeight(800)
        self.table_tests.setHorizontalHeaderLabels(["", "Class", "Test Name", "Category", "Acceptance Criteria"])
        self.table_tests.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_tests.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_tests.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_tests.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_tests.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table_tests.itemChanged.connect(self.on_item_changed)
        self.table_tests.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_tests.setSelectionMode(QTableWidget.NoSelection) # rely on checkbox toggle for simple selections
        self.table_tests.cellClicked.connect(self.on_cell_clicked)
        list_layout.addWidget(self.table_tests)
        
        layout.addWidget(self.list_frame)

        # 4. Collapsible Custom Test Creator
        self.btn_expand_custom = QPushButton("▶ Create Custom Test Standard Clause")
        self.btn_expand_custom.setCheckable(True)
        self.btn_expand_custom.setStyleSheet("""
        QPushButton {
            text-align: left;
            padding: 8px;
            font-weight: bold;
        }
        """)

        self.custom_container = QFrame()
        self.custom_container.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #D6D6D6; border-radius: 6px; padding: 15px; }")
        custom_layout = QFormLayout(self.custom_container)
        custom_layout.setSpacing(6)
        
        self.txt_cust_id = QLineEdit()
        self.txt_cust_id.setPlaceholderText("e.g. 8.102")
        self.txt_cust_name = QLineEdit()
        self.txt_cust_name.setPlaceholderText("e.g. Thermal Propagation Safety Test")
        self.txt_cust_desc = QLineEdit()
        self.txt_cust_desc.setPlaceholderText("Explain objective of the custom test...")
        self.txt_cust_inputs = QLineEdit()
        self.txt_cust_inputs.setText("Current, Voltage, Time, Cell Temperature")
        self.txt_cust_crit = QLineEdit()
        self.txt_cust_crit.setPlaceholderText("Criteria for pass verdict...")
        self.cb_cust_cat = QComboBox()
        self.cb_cust_cat.addItems(["Electrical", "Mechanical", "Thermal / Climatic", "Life / Aging", "Functional Safety"])
        
        custom_layout.addRow("Test Class ID *:", self.txt_cust_id)
        custom_layout.addRow("Test Name *:", self.txt_cust_name)
        custom_layout.addRow("Objective/Description:", self.txt_cust_desc)
        custom_layout.addRow("Required Inputs:", self.txt_cust_inputs)
        custom_layout.addRow("Acceptance Criteria *:", self.txt_cust_crit)
        custom_layout.addRow("Category:", self.cb_cust_cat)
        
        btn_create_custom = QPushButton("Add Custom Test to standard")
        btn_create_custom.setObjectName("SecondaryButton")
        btn_create_custom.setStyleSheet("QPushButton { border: 1px solid #0F4C81; color: #0F4C81; font-weight: bold; border-radius: 4px; padding: 6px 12px; }")
        btn_create_custom.clicked.connect(self.create_custom_test)
        custom_layout.addRow("", btn_create_custom)
        
        self.custom_container.setVisible(False)
        self.btn_expand_custom.clicked.connect(self.toggle_custom_form)
        
        layout.addWidget(self.btn_expand_custom)
        layout.addWidget(self.custom_container)

        # 5. Page navigation button
        nav_layout = QHBoxLayout()
        self.btn_next = QPushButton("Next: Data Ingestion & Validation →")
        self.btn_next.setObjectName("PrimaryButton")
        self.btn_next.setStyleSheet("QPushButton { background-color: #0F4C81; color: white; font-weight: bold; border-radius: 4px; padding: 10px 20px; }")
        self.btn_next.clicked.connect(self.submit_selection)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_next)
        layout.addLayout(nav_layout)

        # Active tracking variables
        self.is_combined = False
        
        scroll.setWidget(main_content)
        # Outer layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.reload_tests()

    def toggle_custom_form(self):
        expanded = self.btn_expand_custom.isChecked()
        self.custom_container.setVisible(expanded)
        if expanded:
            self.btn_expand_custom.setText("▼ Create Custom Test Standard Clause")
        else:
            self.btn_expand_custom.setText("▶ Create Custom Test Standard Clause")

    def on_cell_clicked(self, row, col):
        # Don't double trigger if they click exactly on the checkbox
        if col == 0:
            return
        item = self.table_tests.item(row, 0)
        if item:
            if item.checkState() == Qt.Checked:
                item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.Checked)

    def toggle_mode(self):
        # Toggle checkbox behaviors or update prompt text
        self.is_combined = self.rb_combined.isChecked()
        if self.is_combined:
            self.lbl_select_instructions.setText("Combined Test Report: Select multiple tests below:")
        else:
            self.lbl_select_instructions.setText("Individual Test Report: Select exactly ONE test below:")
            self.clear_all_except_last()

    def clear_all_except_last(self, active_row=-1):
        """If individual mode, keep only one checkbox ticked."""
        if self.is_combined:
            return
            
        self.table_tests.blockSignals(True)
        for r in range(self.table_tests.rowCount()):
            if r != active_row:
                item = self.table_tests.item(r, 0)
                if item and item.checkState() == Qt.Checked:
                    item.setCheckState(Qt.Unchecked)
        self.table_tests.blockSignals(False)

    def reload_tests(self):
        try:
            self.all_tests = database.get_tests_for_tses(self.tses_version_id)
            self.apply_filter()
        except Exception as e:
            print("Failed to reload tests list:", e)

    def apply_filter(self):
        search_text = self.txt_search.text().lower().strip()
        category_filter = self.cb_category.currentText()
        
        self.table_tests.blockSignals(True)
        self.table_tests.setRowCount(0)
        
        row_idx = 0
        for t in self.all_tests:
            # Filters checks
            if search_text and not (search_text in t['id'].lower() or search_text in t['name'].lower() or search_text in t['description'].lower()):
                continue
            if category_filter != "All Categories" and t['category'] != category_filter:
                continue
                
            self.table_tests.insertRow(row_idx)
            
            # 0. Checkbox item
            chk_item = QTableWidgetItem()
            chk_item.setCheckState(Qt.Unchecked)
            chk_item.setFlags(
                Qt.ItemIsUserCheckable |
                Qt.ItemIsEnabled |
                Qt.ItemIsSelectable
            )
            self.table_tests.setItem(row_idx, 0, chk_item)
            
            # 1. Class ID
            self.table_tests.setItem(row_idx, 1, QTableWidgetItem(t['id']))
            # 2. Name
            self.table_tests.setItem(row_idx, 2, QTableWidgetItem(t['name']))
            # 3. Category
            self.table_tests.setItem(row_idx, 3, QTableWidgetItem(t['category']))
            # 4. Acceptance Criteria
            self.table_tests.setItem(row_idx, 4, QTableWidgetItem(t['acceptance_criteria']))
            
            row_idx += 1
            
        self.table_tests.blockSignals(False)

    def on_item_changed(self, item):
        if item.column() != 0:
            return
            
        row = item.row()
        if item.checkState() == Qt.Checked and not self.is_combined:
            # Uncheck other entries
            self.clear_all_except_last(row)

    def create_custom_test(self):
        cust_id = self.txt_cust_id.text().strip()
        cust_name = self.txt_cust_name.text().strip()
        cust_crit = self.txt_cust_crit.text().strip()
        
        if not cust_id or not cust_name or not cust_crit:
            QMessageBox.warning(self, "Validation Error", "Class ID, Name, and Acceptance Criteria are required.")
            return
            
        success = database.add_test(
            cust_id,
            cust_name,
            self.txt_cust_desc.text().strip() or "Custom user-defined test protocol.",
            self.txt_cust_inputs.text().strip(),
            cust_crit,
            self.cb_cust_cat.currentText(),
            self.tses_version_id,
            is_custom=1
        )
        
        if success:
            QMessageBox.information(self, "Success", f"Custom test '{cust_id}' registered successfully.")
            database.log_audit("user", f"Added custom test: Class {cust_id} - {cust_name}")
            
            # Clear fields
            self.txt_cust_id.clear()
            self.txt_cust_name.clear()
            self.txt_cust_desc.clear()
            self.txt_cust_crit.clear()
            
            # Refresh list
            self.reload_tests()
        else:
            QMessageBox.critical(self, "Error", f"A test with Class ID '{cust_id}' already exists.")

    def submit_selection(self):
        # Scan checked tests
        selected_ids = []
        for r in range(self.table_tests.rowCount()):
            item = self.table_tests.item(r, 0)
            if item and item.checkState() == Qt.Checked:
                test_id = self.table_tests.item(r, 1).text()
                selected_ids.append(test_id)
                
        if not selected_ids:
            QMessageBox.warning(self, "Selection Required", "Please select at least one test to proceed with the validation report.")
            return
            
        if not self.is_combined and len(selected_ids) > 1:
            # Fallback constraint check
            QMessageBox.warning(self, "Mode Error", "In Individual Report mode, only one test can be evaluated.")
            return
            
        # Create Project in Database first
        try:
            # Fetch active battery info (mainwindow handles setting project details, but we seed a default)
            battery_id = 1 # fallback U701
            project_data = {
                'name': f"Report validation run ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
                'request_no': f"TVSM/QAD/REF/{datetime.now().strftime('%y%m%d%H%M')}",
                'battery_id': battery_id,
                'tses_version_id': self.tses_version_id,
                'customer': "TVS Motor Company",
                'project_name': "NPD Validation Run",
                'engineer': "Testing Engineer",
                'team_members': "S Shivram, C Varunkumar",
                'comments': "Report compiles battery laboratory data processing cycles."
            }
            project_id = database.create_project(project_data)
            
            # Add project tests link
            for t_id in selected_ids:
                database.add_project_test(project_id, t_id, "") # empty excel path initially
                
            database.log_audit("user", f"Started new report id: {project_id} (Combined: {self.is_combined})")
            
            # Emit tests_selected signal
            self.tests_selected.emit(project_id, selected_ids, self.is_combined)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to initialize report: {e}")
