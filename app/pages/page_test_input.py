from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFileDialog, QLineEdit, QGroupBox, 
                             QFormLayout, QMessageBox, QFrame, QListWidget, 
                             QListWidgetItem, QStackedWidget, QDoubleSpinBox, QScrollArea)
from PySide6.QtCore import Qt, Signal
import os
import json
import pandas as pd
import processor
import database

class PageTestInput(QWidget):
    # Signals completion of data processing
    # (project_id)
    processing_completed = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_id = None
        self.selected_test_ids = []
        self.is_combined = False
        
        self.tses_version_id = None
        
        self.active_test_index = -1
        # Maps test_id -> dict of upload details
        # { 'excel_path': str, 'chamber_temp': float, 'c_rate': float, 
        #   'validation_ok': bool, 'validation_msg': str, 'detected_specs': str }
        self.uploads_map = {}
        
        self.init_ui()

    def set_project_selection(self, project_id, test_ids, is_combined):
        print(">>> set_project_selection called")
        print("Project ID:", project_id)
        print("Test IDs:", test_ids)
        print("Combined:", is_combined)

        self.project_id = project_id
        self.selected_test_ids = test_ids
        self.is_combined = is_combined

        self.uploads_map = {}
        for t_id in self.selected_test_ids:
            self.uploads_map[t_id] = {
                'excel_path': '',
                'chamber_temp': 25.0,
                'ambient_temp': 25.0,
                'c_rate': 1.0,
                'validation_ok': False,
                'validation_msg': 'File not uploaded',
                'detected_specs': 'Pending file upload...'
            }

        print(">>> About to call reload_test_list()")
        self.reload_test_list()
        print(">>> reload_test_list() returned")


    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 1. Left Sidebar: List of Selected Tests
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.StyledPanel)
        left_panel.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #D6D6D6; border-radius: 4px; min-width: 200px; max-width: 250px; }")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        lbl_list = QLabel("Tests Queue")
        lbl_list.setStyleSheet("font-weight: bold; color: #0F4C81; font-size: 14px;")
        left_layout.addWidget(lbl_list)
        
        self.list_tests = QListWidget()
        self.list_tests.itemClicked.connect(self.on_test_item_clicked)
        left_layout.addWidget(self.list_tests)
        layout.addWidget(left_panel)

        # 2. Right Panel: Active Test Upload & Configuration Detail
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setSpacing(15)
        detail_layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
        
        # Test Heading & Description
        self.lbl_test_title = QLabel("Select a test from the queue to configure.")
        self.lbl_test_title.setObjectName("PageHeader")
        self.lbl_test_title.setWordWrap(True)
        detail_layout.addWidget(self.lbl_test_title)
        
        self.lbl_test_desc = QLabel("Objective and details of the test protocol.")
        self.lbl_test_desc.setWordWrap(True)
        self.lbl_test_desc.setStyleSheet("color: #202124; font-size: 14px;")
        detail_layout.addWidget(self.lbl_test_desc)
        
        # Upload Section
        up_group = QGroupBox("Ingest Battery Cycler Telemetry Log (.xlsx, .csv)")
        up_form = QVBoxLayout(up_group)
        
        file_row = QHBoxLayout()
        self.btn_upload = QPushButton("Browse Excel / CSV File")
        self.btn_upload.setObjectName("SecondaryButton")
        self.btn_upload.clicked.connect(self.browse_cycler_file)
        
        self.lbl_uploaded_file = QLabel("No file selected.")
        self.lbl_uploaded_file.setStyleSheet("color: #202124; font-weight: bold;")
        file_row.addWidget(self.btn_upload)
        file_row.addWidget(self.lbl_uploaded_file, 1)
        up_form.addLayout(file_row)
        
        # Live status check indicators
        self.lbl_status_indicator = QLabel("Validation Status: File not uploaded")
        self.lbl_status_indicator.setStyleSheet("font-weight: bold; color: #C00000;")
        up_form.addWidget(self.lbl_status_indicator)
        
        detail_layout.addWidget(up_group)
        
        # Parameter Overrides
        param_group = QGroupBox("Environmental & Load Parameter Overrides")
        param_form = QFormLayout(param_group)
        param_form.setSpacing(8)
        
        self.sb_chamber = QDoubleSpinBox()
        self.sb_chamber.setRange(-40.0, 100.0)
        self.sb_chamber.setValue(25.0)
        self.sb_chamber.setSuffix(" °C")
        self.sb_chamber.valueChanged.connect(self.on_param_changed)
        
        self.sb_ambient = QDoubleSpinBox()
        self.sb_ambient.setRange(-40.0, 100.0)
        self.sb_ambient.setValue(25.0)
        self.sb_ambient.setSuffix(" °C")
        self.sb_ambient.valueChanged.connect(self.on_param_changed)
        
        self.sb_c_rate = QDoubleSpinBox()
        self.sb_c_rate.setRange(0.01, 10.0)
        self.sb_c_rate.setValue(1.0)
        self.sb_c_rate.setSingleStep(0.1)
        self.sb_c_rate.setSuffix(" C")
        self.sb_c_rate.valueChanged.connect(self.on_param_changed)
        
        param_form.addRow("Chamber Temperature:", self.sb_chamber)
        param_form.addRow("Ambient Laboratory Temp:", self.sb_ambient)
        param_form.addRow("Target Discharge C-Rate:", self.sb_c_rate)
        
        detail_layout.addWidget(param_group)
        
        # Smart Data Validation & confirmation
        valid_group = QGroupBox("Smart Validation: Detected Requirements")
        valid_layout = QVBoxLayout(valid_group)
        
        self.lbl_detected = QLabel("Upload a cycler file to auto-detect test run parameters.")
        self.lbl_detected.setWordWrap(True)
        self.lbl_detected.setStyleSheet("color: #333333; font-family: monospace; font-size: 12.5px; line-height: 1.4;")
        valid_layout.addWidget(self.lbl_detected)
        
        # Yes / Modify requirement buttons
        conf_row = QHBoxLayout()
        self.lbl_confirm_txt = QLabel("Are these requirements correct?")
        self.lbl_confirm_txt.setStyleSheet("font-weight: bold; color: #0F4C81;")
        self.btn_confirm_yes = QPushButton("Yes, Confirm")
        self.btn_confirm_yes.setObjectName("PrimaryButton")
        self.btn_confirm_yes.setEnabled(False)
        self.btn_confirm_yes.clicked.connect(self.confirm_detected)
        
        conf_row.addWidget(self.lbl_confirm_txt)
        conf_row.addWidget(self.btn_confirm_yes)
        conf_row.addStretch()
        valid_layout.addLayout(conf_row)
        
        detail_layout.addWidget(valid_group)
        
        # Bottom controls: Next Page trigger
        nav_row = QHBoxLayout()
        self.btn_process = QPushButton("Execute Data Cleaning & Process Telemetry →")
        self.btn_process.setObjectName("PrimaryButton")
        self.btn_process.setStyleSheet("QPushButton { background-color: #0F4C81; color: white; font-weight: bold; padding: 10px 20px; border-radius: 4px; }")
        self.btn_process.clicked.connect(self.process_all_project_files)
        nav_row.addStretch()
        nav_row.addWidget(self.btn_process)
        detail_layout.addLayout(nav_row)
        
        scroll.setWidget(detail_widget)
        right_layout.addWidget(scroll)
        layout.addWidget(right_panel, 1)

    def reload_test_list(self):
        
        print("===================================")
        print("TSES Version ID:", self.tses_version_id)
        print("Selected IDs:", self.selected_test_ids)

        self.list_tests.clear()

        tests = database.get_tests_for_tses(self.tses_version_id)

        print("Tests returned from database:")
        for t in tests:
            print(t)

        for idx, t_id in enumerate(self.selected_test_ids):
            test_row = next((t for t in tests if t['id'] == t_id), None)
            title = test_row['name'] if test_row else "Unknown"

            item = QListWidgetItem(f"[{t_id}] {title[:30]}...")
        self.list_tests.clear()
        for idx, t_id in enumerate(self.selected_test_ids):
            # Fetch title from DB
            tests = database.get_tests_for_tses(self.tses_version_id)
            test_row = next((t for t in tests if t['id'] == t_id), None)
            title = test_row['name'] if test_row else "Unknown"
            
            # Simple item formatting
            item = QListWidgetItem(f"[{t_id}] {title[:30]}...")
            # Check validation status
            is_valid = self.uploads_map[t_id]['validation_ok']
            if is_valid:
                item.setForeground(Qt.darkGreen)
            else:
                item.setForeground(Qt.red)
                
            self.list_tests.addItem(item)
            
        if self.selected_test_ids:
            self.list_tests.setCurrentRow(0)
            self.on_test_item_clicked(self.list_tests.item(0))

    def on_test_item_clicked(self, item):
        idx = self.list_tests.row(item)
        if idx < 0:
            return
            
        self.active_test_index = idx
        t_id = self.selected_test_ids[idx]
        
        # Reload DB details
        tests = database.get_tests_for_tses(self.tses_version_id)
        test_row = next((t for t in tests if t['id'] == t_id), None)
        
        self.lbl_test_title.setText(f"Evaluate Clause {t_id}: {test_row['name'] if test_row else 'Test Data'}")
        self.lbl_test_desc.setText(
            f"<b>Objective:</b> {test_row['description'] if test_row else 'None'}<br/>"
            f"<b>Required Columns:</b> {test_row['required_inputs'] if test_row else 'None'}<br/>"
            f"<b>Criteria:</b> {test_row['acceptance_criteria'] if test_row else 'None'}"
        )
        
        # Load upload details
        up = self.uploads_map[t_id]
        self.lbl_uploaded_file.setText(os.path.basename(up['excel_path']) if up['excel_path'] else "No file selected.")
        
        # Reset override spinners block signals temporarily
        self.sb_chamber.blockSignals(True)
        self.sb_ambient.blockSignals(True)
        self.sb_c_rate.blockSignals(True)
        
        self.sb_chamber.setValue(up['chamber_temp'])
        self.sb_ambient.setValue(up['ambient_temp'])
        self.sb_c_rate.setValue(up['c_rate'])
        
        self.sb_chamber.blockSignals(False)
        self.sb_ambient.blockSignals(False)
        self.sb_c_rate.blockSignals(False)
        
        # Update validation logs & detected requirements
        self.lbl_detected.setText(up['detected_specs'])
        
        if up['validation_ok']:
            self.lbl_status_indicator.setText("Validation Status: Format Validated (OK)")
            self.lbl_status_indicator.setStyleSheet("font-weight: bold; color: green;")
            self.btn_confirm_yes.setEnabled(True)
        else:
            self.lbl_status_indicator.setText(f"Validation Status: {up['validation_msg']}")
            self.lbl_status_indicator.setStyleSheet("font-weight: bold; color: red;")
            self.btn_confirm_yes.setEnabled(False)

    def on_param_changed(self):
        if self.active_test_index < 0:
            return
            
        t_id = self.selected_test_ids[self.active_test_index]
        up = self.uploads_map[t_id]
        
        up['chamber_temp'] = self.sb_chamber.value()
        up['ambient_temp'] = self.sb_ambient.value()
        up['c_rate'] = self.sb_c_rate.value()

    def browse_cycler_file(self):
        if self.active_test_index < 0:
            return
            
        t_id = self.selected_test_ids[self.active_test_index]
        up = self.uploads_map[t_id]
        
        file_path, _ = QFileDialog.getOpenFileName(self, "Upload Cycler Telemetry", "", "Spreadsheets (*.xlsx *.xls *.csv)")
        if not file_path:
            return
            
        up['excel_path'] = file_path
        self.lbl_uploaded_file.setText(os.path.basename(file_path))
        
        # Quick Excel format verification
        try:
            df = processor.detect_and_parse_file(file_path)
            # Normalize and check missing columns
            df_norm = processor.normalize_columns(df)
            
            # Auto-extract parameters
            # Initial temperature
            init_t = float(df_norm['Temperature'].iloc[0]) if 'Temperature' in df_norm.columns else 25.0
            
            # Check C-rate integration approximation
            est_c = 1.0
            if 'Current' in df_norm.columns:
                df_dis = df_norm[df_norm['Current'] < -0.05]
                if not df_dis.empty:
                    dt = df_dis['Time_Sec'].diff().fillna(1.0)
                    dis_cap_ah = float((df_dis['Current'].abs() * dt).sum() / 3600.0)
                    avg_i = float(df_dis['Current'].abs().mean())
                    est_c = avg_i / dis_cap_ah if dis_cap_ah > 0 else 1.0
                
            up['chamber_temp'] = round(init_t, 1)
            up['c_rate'] = round(est_c, 2)
            
            # Trigger updates
            self.sb_chamber.setValue(up['chamber_temp'])
            self.sb_c_rate.setValue(up['c_rate'])
            
            # Format display detected specs
            up['detected_specs'] = (
                f"- Telemetry raw data: {len(df_norm)} rows parsed.\n"
                f"- Auto-detected initial cell temperature: {init_t:.1f}°C.\n"
                f"- Auto-detected discharge load rate: {est_c:.2f}C."
            )
            
            up['validation_ok'] = True
            up['validation_msg'] = "Format Validated"
            
            # Update left list list widget item color
            self.list_tests.item(self.active_test_index).setForeground(Qt.darkGreen)
            
        except Exception as e:
            up['validation_ok'] = False
            up['validation_msg'] = f"Failed to validate file: {str(e)}"
            up['detected_specs'] = f"Failed to read file formatting parameters.\nError log: {str(e)}"
            self.list_tests.item(self.active_test_index).setForeground(Qt.red)
            
        self.on_test_item_clicked(self.list_tests.item(self.active_test_index))

    def confirm_detected(self):
        if self.active_test_index < 0:
            return
            
        t_id = self.selected_test_ids[self.active_test_index]
        QMessageBox.information(self, "Confirmed", f"Detected cycler parameters for test {t_id} locked in successfully.")

    def process_all_project_files(self):
        # Ensure all uploaded files are valid
        for t_id in self.selected_test_ids:
            up = self.uploads_map[t_id]
            if not up['excel_path'] or not up['validation_ok']:
                QMessageBox.warning(self, "Pending Uploads", f"Please upload and validate a cycler telemetry file for test class {t_id} before running the processing engine.")
                return
                
        # Run processing for each test
        try:
            # Query active battery specs to validate limits
            project = database.get_project_details(self.project_id)
            battery_id = project['battery_id']
            # Find matching battery specs
            batteries = database.get_all_batteries()
            battery_spec = next((b for b in batteries if b['id'] == battery_id), None)
            
            for t_id in self.selected_test_ids:
                up = self.uploads_map[t_id]
                
                # Find project test row to get category and required graphs
                pt_row = next((pt for pt in project['tests'] if pt['test_id'] == t_id), None)
                test_category = pt_row.get('category', 'Electrical') if pt_row else 'Electrical'
                
                # Load file again
                df = processor.detect_and_parse_file(up['excel_path'])
                
                # Process data
                diagnostics, ds_df, alerts = processor.run_data_processing(
                    df,
                    expected_temp=up['chamber_temp'],
                    expected_c_rate=up['c_rate'],
                    battery_spec=battery_spec,
                    category=test_category
                )
                
                # Pre-generate required graphs if specified in the database
                req_graphs_str = pt_row.get('required_graphs', '') if pt_row else ''
                custom_graphs = []
                if req_graphs_str:
                    graphs_list = [g.strip() for g in req_graphs_str.split(',') if g.strip()]
                    for g_idx, g_type in enumerate(graphs_list):
                        custom_graph_name = f"_custom_graph_{g_idx+1}.png"
                        graph_path = up['excel_path'].replace(os.path.splitext(up['excel_path'])[1], custom_graph_name)
                        try:
                            reporter.create_matplotlib_graph(ds_df, f"{g_type} Curve", g_type, graph_path)
                            
                            # Parse X/Y parameters
                            y_val = "Voltage"
                            x_val = "Time"
                            if " vs " in g_type:
                                parts = g_type.split(" vs ")
                                y_val = parts[0].strip()
                                x_val = parts[1].strip()
                                
                            custom_graphs.append({
                                "x_axis": x_val,
                                "y1_axis": y_val,
                                "y2_axis": "[None]",
                                "image_path": graph_path
                            })
                        except Exception as e:
                            print(f"Failed to pre-generate required graph {g_type}:", e)
                            
                diagnostics["custom_graphs"] = custom_graphs
                
                # Status evaluation
                status = "Pass"
                observations = "Conforms to specifications."
                if alerts:
                    # Check if critical error
                    if any("CRITICAL" in a or "UNDER-VOLTAGE" in a or "OVER-VOLTAGE" in a or "ABUSE" in a for a in alerts):
                        status = "Fail"
                    else:
                        status = "Review"
                    observations = "Alerts raised during checks:\n" + "\n".join([f"- {a}" for a in alerts])
                    
                # Save generated graph as PNG alongside the raw Excel log
                # For combined reports, we don't draw graphs in final report, but we draw it for dashboard preview
                png_graph_path = up['excel_path'].replace(os.path.splitext(up['excel_path'])[1], "_graph.png")
                # Build Matplotlib image
                reporter.create_matplotlib_graph(ds_df, f"Test Class {t_id} Profile", "Voltage & Current Overlay", png_graph_path)
                
                # Save telemetry outputs as a processed CSV alongside raw log
                csv_path = up['excel_path'].replace(os.path.splitext(up['excel_path'])[1], "_processed.csv")
                ds_df.to_csv(csv_path, index=False)
                
                # Update Project Tests Table in DB
                if pt_row:
                    database.update_project_test(
                        pt_row['id'],
                        status,
                        observations,
                        json.dumps(diagnostics),
                        raw_path=up['excel_path'],
                        proc_path=csv_path # full processed csv used for loading
                    )
                    # Also write excel path in project_tests
                    conn = database.get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE project_tests SET excel_path = ? WHERE id = ?", (up['excel_path'], pt_row['id']))
                    conn.commit()
                    conn.close()

            database.log_audit("user", f"Completed telemetry processing runs for Report ID: {self.project_id}")
            QMessageBox.information(self, "Success", "Telemetry analysis runs completed successfully. Navigating to preview page.")
            
            # Emit completed signal
            self.processing_completed.emit(self.project_id)
            
        except Exception as e:
            QMessageBox.critical(self, "Processing Error", f"Telemetry calculations failed: {e}")
            import traceback
            traceback.print_exc()

# Import reporter inside class/functions to avoid cyclic imports
import reporter
