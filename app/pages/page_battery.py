from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QLineEdit, QGroupBox, QFormLayout, 
                             QPushButton, QMessageBox, QFrame, QScrollArea, QGridLayout, QDateEdit)
from PySide6.QtCore import Qt, Signal,QDate
import database

class PageBattery(QWidget):
    # Signals active project updates with selected battery ID
    battery_selected = Signal(int, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.battery_list = []
        self.active_battery = None
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
        header = QLabel("Battery Pack Master Database")
        header.setObjectName("PageHeader")
        layout.addWidget(header)

        # Dropdown selection block
        selector_group = QGroupBox("Select Active Battery Pack under Test")
        sel_layout = QHBoxLayout(selector_group)
        self.cb_batteries = QComboBox()
        self.cb_batteries.setMinimumWidth(300)
        self.cb_batteries.currentIndexChanged.connect(self.on_battery_changed)
        sel_layout.addWidget(self.cb_batteries)
        sel_layout.addStretch()
        layout.addWidget(selector_group)

        # Dynamic Specs Grid
        self.specs_group = QGroupBox("Selected Battery Parameters & Calculations")
        specs_layout = QGridLayout(self.specs_group)
        specs_layout.setSpacing(10)

        # Spec labels & read-only fields
        def add_spec_row(layout, label_text, row, col, is_editable=False):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-weight: bold; color: #202124; font-size: 14px;")
            edit = QLineEdit()
            if not is_editable:
                edit.setReadOnly(True)
                edit.setStyleSheet("background-color: #F1F3F4; border: 1px solid #D6D6D6;")
            else:
                edit.setStyleSheet("background-color: #FFFFFF; border: 1px solid #0F4C81;")
            layout.addWidget(lbl, row, col * 2)
            layout.addWidget(edit, row, col * 2 + 1)
            return edit

        # Left Column specs
        self.txt_cell_type = add_spec_row(specs_layout, "Cell Type:", 0, 0)
        self.txt_config = add_spec_row(specs_layout, "Configuration (s/p):", 1, 0)
        self.txt_nominal_v = add_spec_row(specs_layout, "Nominal Voltage (V):", 2, 0)
        self.txt_capacity = add_spec_row(specs_layout, "Rated Capacity (Ah):", 3, 0)
        self.txt_energy = add_spec_row(specs_layout, "Total Energy (Wh):", 4, 0)
        
        # Right Column specs (including weight calculations)
        self.txt_chemistry = add_spec_row(specs_layout, "Battery Chemistry:", 0, 1)
        self.txt_weight = add_spec_row(specs_layout, "Weight (kg):", 1, 1, is_editable=True)
        self.txt_weight.textChanged.connect(self.recalculate_densities)
        
        self.txt_energy_density = add_spec_row(specs_layout, "Energy Density (Wh/kg):", 2, 1)
        self.txt_power_density = add_spec_row(specs_layout, "Est. Power Density (W/kg):", 3, 1)
        self.txt_part_no = add_spec_row(specs_layout, "Part Number:", 4, 1, is_editable=True)
        
        # Extra tracking parameters
        self.txt_serial_no = add_spec_row(specs_layout, "Serial Number:", 5, 0, is_editable=True)
        lbl_test_date = QLabel("Testing Date:")
        lbl_test_date.setStyleSheet("font-weight: bold; color: #202124; font-size: 14px;")

        self.test_date = QDateEdit()
        self.test_date.setCalendarPopup(True)
        self.test_date.setDate(QDate.currentDate())
        self.test_date.setDisplayFormat("yyyy-MM-dd")

        specs_layout.addWidget(lbl_test_date, 5, 2)
        specs_layout.addWidget(self.test_date, 5, 3)
        
        layout.addWidget(self.specs_group)

        # ====================================
        # Collapsible Add New Battery Section
        # ====================================
        self.btn_expand = QPushButton("▶ Add New Battery Pack Configuration")
        self.btn_expand.setCheckable(True)

        self.btn_expand.setStyleSheet("""
        QPushButton {
            text-align:left;
            padding:8px;
            font-weight:bold;
        }
        """)
        
        # Container for the form
        self.form_container = QWidget()
        form_layout = QFormLayout(self.form_container)
        form_layout.setSpacing(8)

        self.new_name = QLineEdit()
        self.new_name.setPlaceholderText("e.g. U703")

        self.new_cell = QLineEdit()
        self.new_cell.setPlaceholderText("e.g. M50LT cells")

        self.new_config = QLineEdit()
        self.new_config.setPlaceholderText("e.g. 14s10p")

        self.new_volt = QLineEdit()
        self.new_volt.setPlaceholderText("e.g. 52")

        self.new_cap = QLineEdit()
        self.new_cap.setPlaceholderText("e.g. 50")

        self.new_chem = QLineEdit()
        self.new_chem.setText("Li-ion NMC")

        self.new_wt = QLineEdit()
        self.new_wt.setPlaceholderText("e.g. 14.2")

        self.new_part = QLineEdit()
        self.new_part.setPlaceholderText("e.g. TVS-U703-01")

        self.new_serial = QLineEdit()
        self.new_serial.setPlaceholderText("e.g. SN-U703-0001")

        # Date Picker
        self.new_test_date = QDateEdit()
        self.new_test_date.setCalendarPopup(True)
        self.new_test_date.setDate(QDate.currentDate())
        self.new_test_date.setDisplayFormat("yyyy-MM-dd")

        form_layout.addRow("Battery Pack Name *:", self.new_name)
        form_layout.addRow("Cell Type:", self.new_cell)
        form_layout.addRow("Configuration:", self.new_config)
        form_layout.addRow("Nominal Voltage (V) *:", self.new_volt)
        form_layout.addRow("Capacity (Ah) *:", self.new_cap)
        form_layout.addRow("Chemistry:", self.new_chem)
        form_layout.addRow("Weight (kg):", self.new_wt)
        form_layout.addRow("Part Number:", self.new_part)
        form_layout.addRow("Serial Number:", self.new_serial)
        form_layout.addRow("Testing Date:", self.new_test_date)

        btn_save = QPushButton("Save Battery to Database")
        btn_save.setObjectName("PrimaryButton")
        btn_save.clicked.connect(self.save_new_battery)

        form_layout.addRow("", btn_save)

        # Initially collapsed
        self.form_container.setVisible(False)

        layout.addWidget(self.btn_expand)
        layout.addWidget(self.form_container)
        
        self.btn_expand.clicked.connect(self.toggle_add_form)
        scroll.setWidget(main_content)
        # Outer layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0,0,0,0)
        outer.addWidget(scroll)

        # Load initial values from Database
        self.reload_batteries()

    def reload_batteries(self):
        try:
            self.battery_list = database.get_all_batteries()
            self.cb_batteries.blockSignals(True)
            self.cb_batteries.clear()
            for b in self.battery_list:
                self.cb_batteries.addItem(f"{b['name']} - {b['configuration']} - {b['cell_type']}", b['id'])
            self.cb_batteries.blockSignals(False)
            if self.battery_list:
                self.on_battery_changed(0)
        except Exception as e:
            print("Failed to reload batteries:", e)

    def on_battery_changed(self, idx):
        if idx < 0 or idx >= len(self.battery_list):
            return
            
        self.active_battery = self.battery_list[idx]
        b = self.active_battery
        
        self.txt_cell_type.setText(str(b.get('cell_type', '')))
        self.txt_config.setText(str(b.get('configuration', '')))
        self.txt_nominal_v.setText(str(b.get('nominal_voltage', '')))
        self.txt_capacity.setText(str(b.get('capacity', '')))
        self.txt_chemistry.setText(str(b.get('chemistry', '')))
        self.txt_weight.setText(str(b.get('weight', '')))
        self.txt_part_no.setText(str(b.get('part_number', '')))
        self.txt_serial_no.setText(str(b.get('serial_number', '')))
        date = b.get("mfg_date")
        if date:
            self.test_date.setDate(QDate.fromString(date, "yyyy-MM-dd"))
        
        # Calculate Energy and densities
        self.recalculate_densities()
        
        # Signal change to dashboard/mainwindow
        self.battery_selected.emit(b['id'], b['name'])

    def recalculate_densities(self):
        try:
            volt = float(self.txt_nominal_v.text() or 0.0)
            cap = float(self.txt_capacity.text() or 0.0)
            wh = volt * cap
            self.txt_energy.setText(f"{wh:.1f}")
            
            weight_str = self.txt_weight.text().strip()
            if weight_str:
                wt = float(weight_str)
                if wt > 0:
                    energy_density = wh / wt
                    # Approximate Peak Power at 2C discharge
                    peak_power = volt * cap * 2.0
                    power_density = peak_power / wt
                    self.txt_energy_density.setText(f"{energy_density:.2f}")
                    self.txt_power_density.setText(f"{power_density:.2f}")
                else:
                    self.txt_energy_density.setText("0.00")
                    self.txt_power_density.setText("0.00")
            else:
                self.txt_energy_density.setText("Enter weight...")
                self.txt_power_density.setText("Enter weight...")
        except ValueError:
            self.txt_energy.setText("Error")
            self.txt_energy_density.setText("Error")
            self.txt_power_density.setText("Error")

    def save_new_battery(self):
        name = self.new_name.text().strip()
        volt_str = self.new_volt.text().strip()
        cap_str = self.new_cap.text().strip()
        
        if not name or not volt_str or not cap_str:
            QMessageBox.warning(self, "Validation Error", "Battery Name, Nominal Voltage, and Capacity are required fields.")
            return
            
        try:
            volt = float(volt_str)
            cap = float(cap_str)
            weight = float(self.new_wt.text() or 0.0) if self.new_wt.text().strip() else 0.0
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Nominal Voltage, Capacity, and Weight must be valid numbers.")
            return

        data = {
            'name': name,
            'cell_type': self.new_cell.text().strip(),
            'configuration': self.new_config.text().strip(),
            'nominal_voltage': volt,
            'capacity': cap,
            'chemistry': self.new_chem.text().strip(),
            'weight': weight,
            'part_number': self.new_part.text().strip(),
            'serial_number': self.new_serial.text().strip(),
            'mfg_date': self.new_test_date.date().toString("yyyy-MM-dd")
        }
        
        success = database.add_battery(data)
        if success:
            QMessageBox.information(self, "Success", f"Battery pack '{name}' successfully saved to the database.")
            database.log_audit("user", f"Created new battery configuration: {name}")
            
            # Clear form
            self.new_name.clear()
            self.new_cell.clear()
            self.new_config.clear()
            self.new_volt.clear()
            self.new_cap.clear()
            self.new_wt.clear()
            self.new_part.clear()
            self.new_serial.clear()
            self.new_chem.setText("Li-ion NMC")
            self.new_test_date.setDate(QDate.currentDate())
            
            # Refresh list & select the new pack
            self.reload_batteries()
            cb_idx = self.cb_batteries.findText(name, Qt.MatchContains)
            if cb_idx >= 0:
                self.cb_batteries.setCurrentIndex(cb_idx)
        else:
            QMessageBox.critical(self, "Database Error", f"A battery configuration with the name '{name}' already exists.")
    def toggle_add_form(self):
        expanded = self.btn_expand.isChecked()

        self.form_container.setVisible(expanded)

        if expanded:
            self.btn_expand.setText("▼ Add New Battery Pack Configuration")
        else:
            self.btn_expand.setText("▶ Add New Battery Pack Configuration")

