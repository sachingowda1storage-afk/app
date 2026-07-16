from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QGroupBox, QFormLayout, QLineEdit, QTextEdit, 
                             QComboBox, QMessageBox, QFileDialog, QTabWidget, QFrame, QScrollArea, QGridLayout, QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt
import os
import json
from datetime import datetime
import database
import reporter
import pandas as pd
import pandas as pd

# Matplotlib embedding
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.fig.tight_layout()

class PageReportPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_id = None
        self.project_data = None
        self.init_ui()

    def set_project(self, project_id):
        self.project_id = project_id
        self.reload_project_data()

    def init_ui(self):
        # Allow scrolling of content
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        main_content = QWidget()
        layout = QHBoxLayout(main_content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.setSizeConstraint(QHBoxLayout.SetMinimumSize)

        # 1. Left Panel: Project Info, Signatures & Export
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.StyledPanel)
        left_panel.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #D6D6D6; border-radius: 4px; }")
        left_panel.setMinimumWidth(420)
        left_panel.setMaximumWidth(450)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(15, 15, 15, 15)
        
        lbl_left = QLabel("Report Settings & Export")
        lbl_left.setStyleSheet("font-weight: bold; color: #0F4C81; font-size: 15px;")
        left_layout.addWidget(lbl_left)
        
        # ------------------------------
        # Project Details Form Layout
        # ------------------------------
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        self.txt_ref_no = QLineEdit()
        self.txt_customer = QLineEdit()
        self.txt_project_name = QLineEdit()
        self.txt_engineer = QLineEdit()
        self.txt_team = QLineEdit()
        self.txt_conclusion = QTextEdit()

        self.txt_conclusion.setMaximumHeight(90)
        self.txt_conclusion.setPlaceholderText(
            "Final summary statement or declarations about validation results..."
        )

        # Make all text boxes the same height
        for widget in [
            self.txt_ref_no,
            self.txt_customer,
            self.txt_project_name,
            self.txt_engineer,
            self.txt_team,
        ]:
            widget.setMinimumHeight(34)

        labels = [
            "Report Reference No",
            "Customer Name",
            "Report Name",
            "Testing Engineer",
            "Team Members",
            "Final Conclusion"
        ]

        widgets = [
            self.txt_ref_no,
            self.txt_customer,
            self.txt_project_name,
            self.txt_engineer,
            self.txt_team,
            self.txt_conclusion
        ]

        for text, widget in zip(labels, widgets):
            lbl = QLabel(text + " :")
            lbl.setStyleSheet("font-weight: bold; color: #202124;")
            form.addRow(lbl, widget)

        left_layout.addLayout(form)
        
        # Save Metadata Button
        btn_save_meta = QPushButton("Update Report Details")
        btn_save_meta.setObjectName("SecondaryButton")
        btn_save_meta.clicked.connect(self.save_project_metadata)
        left_layout.addWidget(btn_save_meta)
        
        left_layout.addSpacing(15)
        
        # Export Actions Group
        exp_group = QGroupBox("Generate Validation Reports")
        exp_layout = QVBoxLayout(exp_group)
        exp_layout.setSpacing(8)
        
        self.btn_export_pdf = QPushButton("Export PDF Document")
        self.btn_export_pdf.setObjectName("PrimaryButton")
        self.btn_export_pdf.setStyleSheet("QPushButton { background-color: #0F4C81; color: white; font-weight: bold; padding: 8px; border-radius: 4px; }")
        self.btn_export_pdf.clicked.connect(self.export_pdf)
        
        self.btn_export_docx = QPushButton("Export Word (DOCX)")
        self.btn_export_docx.setObjectName("SecondaryButton")
        self.btn_export_docx.clicked.connect(self.export_docx)
        
        self.btn_export_csv = QPushButton("Export CSV Table")
        self.btn_export_csv.setObjectName("SecondaryButton")
        self.btn_export_csv.clicked.connect(self.export_csv)
        
        exp_layout.addWidget(self.btn_export_pdf)
        exp_layout.addWidget(self.btn_export_docx)
        exp_layout.addWidget(self.btn_export_csv)
        
        left_layout.addWidget(exp_group)
        layout.addWidget(left_panel, 0)
       

        # 2. Right Panel: Tabbed Review (Summary vs Graphs Preview)
        right_tabs = QTabWidget()
        right_tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #D6D6D6; background: white; }")
        layout.addWidget(right_tabs, 1)
        # Tab 1: Executive Table
        self.tab_table = QWidget()
        tab_t_layout = QVBoxLayout(self.tab_table)
        tab_t_layout.setContentsMargins(10, 10, 10, 10)
        
        lbl_tbl = QLabel("Review Test Observations & Override Verdicts")
        lbl_tbl.setStyleSheet("font-weight: bold; color: #202124; font-size: 14px;")
        tab_t_layout.addWidget(lbl_tbl)
         
        
        # Results table (interactive cell editing)
        self.table_results = QTableWidget(0, 5)
        self.table_results.setHorizontalHeaderLabels(["Class", "Test Name", "Requirements", "Observations (Double click to edit)", "Verdict"])
        self.table_results.setWordWrap(True)
        self.table_results.setTextElideMode(Qt.ElideNone)
        self.table_results.setAlternatingRowColors(True)
        self.table_results.setShowGrid(True)
        self.table_results.verticalHeader().setVisible(False)
        self.table_results.verticalHeader().setDefaultSectionSize(90)
        header = self.table_results.horizontalHeader()

        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        self.table_results.setColumnWidth(0, 90)
        self.table_results.setColumnWidth(4, 120)
        header.setStretchLastSection(False)
        self.table_results.cellChanged.connect(self.on_table_cell_changed)
        tab_t_layout.addWidget(self.table_results)
        
        right_tabs.addTab(self.tab_table, "Executive Summary Table")
        
        # Tab 2: Telemetry Curves Canvas
        self.tab_curves = QWidget()
        tab_c_layout = QVBoxLayout(self.tab_curves)
        tab_c_layout.setContentsMargins(10, 10, 10, 10)
        
        top_c_row = QHBoxLayout()
        top_c_row.addWidget(QLabel("Select Test to Preview Telemetry Curve:"))
        self.cb_preview_tests = QComboBox()
        self.cb_preview_tests.currentIndexChanged.connect(self.on_preview_test_changed)
        top_c_row.addWidget(self.cb_preview_tests, 1)
        tab_c_layout.addLayout(top_c_row)
        
        # Dynamic axis configuration row
        axes_row = QHBoxLayout()
        axes_row.addWidget(QLabel("X-Axis:"))
        self.cb_plot_x = QComboBox()
        self.cb_plot_x.currentIndexChanged.connect(self.update_canvas_plot)
        axes_row.addWidget(self.cb_plot_x, 1)
        
        axes_row.addWidget(QLabel("Y1-Axis:"))
        self.cb_plot_y = QComboBox()
        self.cb_plot_y.currentIndexChanged.connect(self.update_canvas_plot)
        axes_row.addWidget(self.cb_plot_y, 1)
        
        axes_row.addWidget(QLabel("Y2-Axis (Optional):"))
        self.cb_plot_y2 = QComboBox()
        self.cb_plot_y2.currentIndexChanged.connect(self.update_canvas_plot)
        axes_row.addWidget(self.cb_plot_y2, 1)
        
        tab_c_layout.addLayout(axes_row)
        
        # Save graph row
        save_row = QHBoxLayout()
        self.btn_save_graph = QPushButton("Add Current Graph to Report")
        self.btn_save_graph.setObjectName("SecondaryButton")
        self.btn_save_graph.setStyleSheet("QPushButton { border: 1px solid #0F4C81; color: #0F4C81; font-weight: bold; border-radius: 4px; padding: 6px 12px; }")
        self.btn_save_graph.clicked.connect(self.save_custom_graph)
        save_row.addWidget(self.btn_save_graph)
        
        self.btn_remove_graph = QPushButton("Remove Selected Graph")
        self.btn_remove_graph.setStyleSheet("QPushButton { border: 1px solid #D93025; color: #D93025; font-weight: bold; border-radius: 4px; padding: 6px 12px; }")
        self.btn_remove_graph.clicked.connect(self.remove_selected_graph)
        save_row.addWidget(self.btn_remove_graph)
        
        tab_c_layout.addLayout(save_row)
        
        # Saved report graphs interactive preview list
        tab_c_layout.addWidget(QLabel("<b>Saved Report Graphs (Click to Preview / Verify):</b>"))
        self.list_saved_graphs = QListWidget()
        self.list_saved_graphs.setFixedHeight(75)
        self.list_saved_graphs.itemClicked.connect(self.on_saved_graph_clicked)
        tab_c_layout.addWidget(self.list_saved_graphs)
        
        # Embedded Matplotlib canvas
        self.canvas = MplCanvas(self, width=6, height=4, dpi=100)
        tab_c_layout.addWidget(self.canvas)
        
        right_tabs.addTab(self.tab_curves, "Curves Graphical Preview")
        
        scroll.setWidget(main_content)
        # Outer layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        

    def reload_project_data(self):
        if not self.project_id:
            return
            
        try:
            self.project_data = database.get_project_details(self.project_id)
            p = self.project_data
            
            # Fill inputs
            self.txt_ref_no.setText(str(p.get('request_no', '')))
            self.txt_customer.setText(str(p.get('customer', '')))
            self.txt_project_name.setText(str(p.get('project_name', '')))
            self.txt_engineer.setText(str(p.get('engineer', '')))
            self.txt_team.setText(str(p.get('team_members', '')))
            self.txt_conclusion.setText(str(p.get('comments', '')))
            
            # Populate results table
            self.table_results.blockSignals(True)
            self.table_results.setRowCount(0)
            
            self.cb_preview_tests.blockSignals(True)
            self.cb_preview_tests.clear()
            
            for idx, pt in enumerate(p.get('tests', [])):
                self.table_results.insertRow(idx)
                
                # Class
                self.table_results.setItem(idx, 0, QTableWidgetItem(pt['test_id']))
                self.table_results.item(idx, 0).setFlags(Qt.ItemIsEnabled)
                # Name
                self.table_results.setItem(idx, 1, QTableWidgetItem(pt['test_name']))
                self.table_results.item(idx, 1).setFlags(Qt.ItemIsEnabled)
                # Requirements
                self.table_results.setItem(idx, 2, QTableWidgetItem(pt.get('acceptance_criteria', 'N/A')))
                self.table_results.item(idx, 2).setFlags(Qt.ItemIsEnabled)
                
                # Observations (Editable)
                obs_item = QTableWidgetItem(pt.get('observations', ''))
                self.table_results.setItem(idx, 3, obs_item)
                
                # Verdict override dropdown widget
                cb_verdict = QComboBox()
                cb_verdict.addItems(["Pending", "Pass", "Fail", "Review"])
                cb_verdict.setCurrentText(pt.get('status', 'Pending'))
                # Store pt_id in property
                cb_verdict.setProperty("pt_id", pt['id'])
                cb_verdict.currentTextChanged.connect(self.on_verdict_combo_changed)
                self.table_results.setCellWidget(idx, 4, cb_verdict)
                
                # Add to graphs preview cb if data path is valid
                if pt.get('processed_data_path') and os.path.exists(pt['processed_data_path']):
                    self.cb_preview_tests.addItem(f"[{pt['test_id']}] {pt['test_name'][:30]}...", pt)
                    
            self.table_results.resizeRowsToContents()
            
            self.table_results.blockSignals(False)
            self.cb_preview_tests.blockSignals(False)
            
            if self.cb_preview_tests.count() > 0:
                self.cb_preview_tests.setCurrentIndex(0)
                self.on_preview_test_changed(0)
            else:
                self.canvas.ax.clear()
                self.canvas.ax.text(0.5, 0.5, "No processed curve data available.", ha='center', va='center')
                self.canvas.draw()
        except Exception as e:
            print("Failed to reload project data:", e)

    def on_table_cell_changed(self, row, col):
        if col != 3:
            return
            
        obs_text = self.table_results.item(row, col).text()
        pt_id = self.project_data['tests'][row]['id']
        status = self.project_data['tests'][row]['status']
        results_json = self.project_data['tests'][row]['results_json']
        raw = self.project_data['tests'][row]['excel_path']
        proc = self.project_data['tests'][row]['processed_data_path']
        
        # Save to DB
        try:
            database.update_project_test(pt_id, status, obs_text, results_json, raw, proc)
            # Update local cache
            self.project_data['tests'][row]['observations'] = obs_text
        except Exception as e:
            print("Failed to update test observations:", e)

    def on_verdict_combo_changed(self, text):
        cb = self.sender()
        if not cb:
            return
        pt_id = cb.property("pt_id")
        
        # Find local index
        pt_row = next(((idx, pt) for idx, pt in enumerate(self.project_data['tests']) if pt['id'] == pt_id), None)
        if pt_row:
            idx, pt = pt_row
            pt['status'] = text
            # Save to DB
            try:
                database.update_project_test(pt_id, text, pt['observations'], pt['results_json'], pt['excel_path'], pt['processed_data_path'])
            except Exception as e:
                print("Failed to update test status:", e)

    def on_preview_test_changed(self, idx):
        if idx < 0:
            return
            
        pt = self.cb_preview_tests.itemData(idx)
        if not pt:
            return
        csv_path = pt.get('processed_data_path')
        if not csv_path or not os.path.exists(csv_path):
            return
            
        self.update_saved_graphs_list(pt)
            
        try:
            df = pd.read_csv(csv_path)
            
            # Block signals to prevent multiple triggers during population
            self.cb_plot_x.blockSignals(True)
            self.cb_plot_y.blockSignals(True)
            self.cb_plot_y2.blockSignals(True)
            
            self.cb_plot_x.clear()
            self.cb_plot_y.clear()
            self.cb_plot_y2.clear()
            
            self.cb_plot_y2.addItem("[None]")
            
            cols = list(df.columns)
            self.cb_plot_x.addItems(cols)
            self.cb_plot_y.addItems(cols)
            self.cb_plot_y2.addItems(cols)
            
            # Search for sensible defaults
            x_default = 0
            y_default = 0
            y2_default = 0 # [None]
            
            for i, col in enumerate(cols):
                c_low = col.lower().strip()
                if c_low in ['time_sec', 'time', 'elapsed time', 'frequency', 'freq']:
                    x_default = i
                    break
            
            for i, col in enumerate(cols):
                c_low = col.lower().strip()
                if c_low in ['voltage', 'acceleration', 'emissions level', 'pressure', 'can message status']:
                    y_default = i
                    break
                elif c_low in ['current', 'temperature', 'frequency', 'fault flag']:
                    y_default = i
            
            for i, col in enumerate(cols):
                c_low = col.lower().strip()
                if c_low in ['current', 'temperature'] and i != y_default:
                    y2_default = i + 1 # offset by 1 because [None] is at 0
                    break
            
            self.cb_plot_x.setCurrentIndex(x_default)
            self.cb_plot_y.setCurrentIndex(y_default)
            self.cb_plot_y2.setCurrentIndex(y2_default)
            
            self.cb_plot_x.blockSignals(False)
            self.cb_plot_y.blockSignals(False)
            self.cb_plot_y2.blockSignals(False)
            
            self.update_canvas_plot()
        except Exception as e:
            print("Failed to populate axis options:", e)

    def update_canvas_plot(self):
        idx = self.cb_preview_tests.currentIndex()
        if idx < 0:
            return
        pt = self.cb_preview_tests.itemData(idx)
        if not pt:
            return
        csv_path = pt.get('processed_data_path')
        if not csv_path or not os.path.exists(csv_path):
            return
            
        try:
            df = pd.read_csv(csv_path)
            self.canvas.ax.clear()
            
            # Remove any twin axes created in previous plots
            for extra_ax in getattr(self, '_extra_axes', []):
                try:
                    extra_ax.remove()
                except Exception:
                    pass
            self._extra_axes = []
            
            x_col = self.cb_plot_x.currentText()
            y_col = self.cb_plot_y.currentText()
            y2_col = self.cb_plot_y2.currentText()
            
            if not x_col or not y_col:
                return
                
            x_data = df[x_col].copy()
            y_data = df[y_col].copy()
            
            # Use Time_Sec under the hood if they chose Time to prevent string plotting errors
            if x_col == "Time" and "Time_Sec" in df.columns:
                x_data = df["Time_Sec"].copy()
                x_label = "Time"
            else:
                x_label = x_col
                
            # If the selected column is not numeric, parse/coerce it
            if x_data.dtype == object:
                try:
                    x_data = x_data.apply(processor.clean_time)
                except Exception:
                    x_data = pd.to_numeric(x_data, errors='coerce').fillna(0.0)
            
            if y_data.dtype == object:
                y_data = pd.to_numeric(y_data, errors='coerce').fillna(0.0)
            
            # Auto-scale time axis to hours if it spans long intervals
            if ('time_sec' in x_label.lower() or x_label.lower() == 'time') and x_data.max() > 300:
                x_data = x_data / 3600.0
                x_axis_label = f"{x_col} (hours)"
            else:
                x_axis_label = x_col
                
            self.canvas.ax.plot(x_data, y_data, color='#0F4C81', label=y_col)
            self.canvas.ax.set_xlabel(x_axis_label, fontweight='bold')
            self.canvas.ax.set_ylabel(y_col, color='#0F4C81', fontweight='bold')
            self.canvas.ax.tick_params(axis='y', labelcolor='#0F4C81')
            
            # Render optional secondary Y axis
            if y2_col and y2_col != "[None]" and y2_col in df.columns:
                y2_data = df[y2_col].copy()
                if y2_data.dtype == object:
                    y2_data = pd.to_numeric(y2_data, errors='coerce').fillna(0.0)
                ax2 = self.canvas.ax.twinx()
                ax2.plot(x_data, y2_data, color='#FF6B6B', label=y2_col, alpha=0.7)
                ax2.set_ylabel(y2_col, color='#FF6B6B', fontweight='bold')
                ax2.tick_params(axis='y', labelcolor='#FF6B6B')
                ax2.grid(False)
                self._extra_axes.append(ax2)
                
            self.canvas.ax.set_title(f"{y_col} vs {x_col}", fontsize=11, fontweight='bold', pad=10)
            self.canvas.fig.tight_layout()
            self.canvas.draw()
        except Exception as e:
            print("Canvas drawing error:", e)

    def save_project_metadata(self):
        if not self.project_id:
            return
            
        conn = database.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            UPDATE projects 
            SET request_no = ?, customer = ?, project_name = ?, engineer = ?, team_members = ?, comments = ?
            WHERE id = ?
            """, (
                self.txt_ref_no.text().strip(),
                self.txt_customer.text().strip(),
                self.txt_project_name.text().strip(),
                self.txt_engineer.text().strip(),
                self.txt_team.text().strip(),
                self.txt_conclusion.toPlainText().strip(),
                self.project_id
            ))
            conn.commit()
            QMessageBox.information(self, "Success", "Report metadata updated successfully.")
            database.log_audit("user", f"Updated report metadata for report: {self.project_id}")
            self.reload_project_data()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to update report metadata: {e}")
        finally:
            conn.close()

    def export_pdf(self):
        if not self.project_id:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Export PDF Report", f"Battery_Validation_Report_{self.project_id}.pdf", "PDF Files (*.pdf)")
        if not file_path:
            return
            
        try:
            # Sync fresh data
            self.reload_project_data()
            reporter.export_to_pdf(self.project_data, file_path)
            QMessageBox.information(self, "Export Complete", f"PDF report successfully exported to:\n{file_path}")
            database.log_audit("user", f"Exported project {self.project_id} validation report to PDF: {os.path.basename(file_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to generate PDF document: {e}")

    def export_docx(self):
        if not self.project_id:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Word Report", f"Battery_Validation_Report_{self.project_id}.docx", "Word Documents (*.docx)")
        if not file_path:
            return
            
        try:
            self.reload_project_data()
            reporter.export_to_docx(self.project_data, file_path)
            QMessageBox.information(self, "Export Complete", f"Word document successfully exported to:\n{file_path}")
            database.log_audit("user", f"Exported project {self.project_id} validation report to DOCX: {os.path.basename(file_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to generate DOCX document: {e}")

    def export_csv(self):
        if not self.project_id:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Export CSV Summary", f"Battery_Validation_Summary_{self.project_id}.csv", "CSV Files (*.csv)")
        if not file_path:
            return
            
        try:
            self.reload_project_data()
            reporter.export_to_csv(self.project_data, file_path)
            QMessageBox.information(self, "Export Complete", f"Summary data successfully exported to:\n{file_path}")
            database.log_audit("user", f"Exported project {self.project_id} summary to CSV: {os.path.basename(file_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to generate CSV: {e}")

    def update_saved_graphs_list(self, pt):
        self.list_saved_graphs.clear()
        if not pt or not pt.get('results_json'):
            return
            
        try:
            results = json.loads(pt['results_json'])
            graphs = results.get("custom_graphs", [])
            for idx, g in enumerate(graphs):
                y1 = g.get('y1_axis', '')
                x = g.get('x_axis', '')
                y2 = g.get('y2_axis', '')
                y2_str = f" & {y2}" if y2 and y2 != "[None]" else ""
                item_text = f"Graph {idx+1}: {y1}{y2_str} vs {x}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, g)
                self.list_saved_graphs.addItem(item)
        except Exception as e:
            print("Failed to update saved graphs list:", e)

    def on_saved_graph_clicked(self, item):
        g = item.data(Qt.UserRole)
        if not g:
            return
            
        self.cb_plot_x.blockSignals(True)
        self.cb_plot_y.blockSignals(True)
        self.cb_plot_y2.blockSignals(True)
        
        self.cb_plot_x.setCurrentText(g.get('x_axis', ''))
        self.cb_plot_y.setCurrentText(g.get('y1_axis', ''))
        self.cb_plot_y2.setCurrentText(g.get('y2_axis') or "[None]")
        
        self.cb_plot_x.blockSignals(False)
        self.cb_plot_y.blockSignals(False)
        self.cb_plot_y2.blockSignals(False)
        
        self.update_canvas_plot()

    def remove_selected_graph(self):
        list_idx = self.list_saved_graphs.currentRow()
        if list_idx < 0:
            QMessageBox.warning(self, "No Selection", "Please select a graph from the list to remove.")
            return
            
        idx = self.cb_preview_tests.currentIndex()
        if idx < 0:
            return
        pt = self.cb_preview_tests.itemData(idx)
        if not pt:
            return
            
        try:
            results = json.loads(pt['results_json'])
            graphs = results.get("custom_graphs", [])
            if 0 <= list_idx < len(graphs):
                g = graphs.pop(list_idx)
                # Delete image file
                img_path = g.get('image_path')
                if img_path and os.path.exists(img_path):
                    try:
                        os.remove(img_path)
                    except Exception:
                        pass
                
                results["custom_graphs"] = graphs
                results_str = json.dumps(results)
                
                database.update_project_test(
                    pt['id'],
                    pt['status'],
                    pt['observations'],
                    results_str,
                    pt['excel_path'],
                    pt['processed_data_path']
                )
                
                pt['results_json'] = results_str
                self.update_saved_graphs_list(pt)
                QMessageBox.information(self, "Success", "Selected custom graph removed from report.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to remove graph: {e}")

    def save_custom_graph(self):
        idx = self.cb_preview_tests.currentIndex()
        if idx < 0:
            return
        pt = self.cb_preview_tests.itemData(idx)
        if not pt:
            return
            
        csv_path = pt.get('processed_data_path')
        if not csv_path or not os.path.exists(csv_path):
            return
            
        x_col = self.cb_plot_x.currentText()
        y_col = self.cb_plot_y.currentText()
        y2_col = self.cb_plot_y2.currentText()
        
        if not x_col or not y_col:
            QMessageBox.warning(self, "Invalid Selection", "Please select valid X and Y1 axes columns before saving.")
            return
            
        try:
            results = {}
            if pt.get('results_json'):
                try:
                    results = json.loads(pt['results_json'])
                except Exception:
                    results = {}
                    
            if "custom_graphs" not in results:
                results["custom_graphs"] = []
                
            graph_index = len(results["custom_graphs"]) + 1
            custom_graph_name = f"_custom_graph_{graph_index}.png"
            graph_path = csv_path.replace(".csv", custom_graph_name)
            
            df = pd.read_csv(csv_path)
            
            x_data = df[x_col].copy()
            y_data = df[y_col].copy()
            if x_col == "Time" and "Time_Sec" in df.columns:
                x_data = df["Time_Sec"].copy()
                x_label = "Time"
            else:
                x_label = x_col
                
            if x_data.dtype == object:
                try:
                    x_data = x_data.apply(processor.clean_time)
                except Exception:
                    x_data = pd.to_numeric(x_data, errors='coerce').fillna(0.0)
            if y_data.dtype == object:
                y_data = pd.to_numeric(y_data, errors='coerce').fillna(0.0)
                
            title = f"Custom Graph: {y_col} vs {x_col}"
            if y2_col and y2_col != "[None]":
                title += f" & {y2_col}"
                
            reporter.create_matplotlib_graph(df, title, f"{y_col} vs {x_col}", graph_path)
            
            # If y2 is selected, we want to regenerate it with y2 overlay
            if y2_col and y2_col != "[None]" and y2_col in df.columns:
                import matplotlib.pyplot as plt
                plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
                fig, ax = plt.subplots(figsize=(6, 3.5), dpi=150)
                
                x_axis_data = x_data.copy()
                if ('time_sec' in x_label.lower() or x_label.lower() == 'time') and x_axis_data.max() > 300:
                    x_axis_data = x_axis_data / 3600.0
                    x_axis_label = f"{x_col} (hours)"
                else:
                    x_axis_label = x_col
                    
                ax.plot(x_axis_data, y_data, color='#0F4C81', label=y_col)
                ax.set_xlabel(x_axis_label, fontweight='bold')
                ax.set_ylabel(y_col, color='#0F4C81', fontweight='bold')
                ax.tick_params(axis='y', labelcolor='#0F4C81')
                
                y2_data = df[y2_col].copy()
                if y2_data.dtype == object:
                    y2_data = pd.to_numeric(y2_data, errors='coerce').fillna(0.0)
                    
                ax2 = ax.twinx()
                ax2.plot(x_axis_data, y2_data, color='#FF6B6B', label=y2_col, alpha=0.7)
                ax2.set_ylabel(y2_col, color='#FF6B6B', fontweight='bold')
                ax2.tick_params(axis='y', labelcolor='#FF6B6B')
                ax2.grid(False)
                
                ax.set_title(title, fontsize=11, fontweight='bold', pad=10)
                ax.grid(True, linestyle='--', color='#E5E5E5')
                for spine in ax.spines.values():
                    spine.set_color('#CCCCCC')
                plt.tight_layout()
                plt.savefig(graph_path, bbox_inches='tight')
                plt.close()

            results["custom_graphs"].append({
                "x_axis": x_col,
                "y1_axis": y_col,
                "y2_axis": y2_col,
                "image_path": graph_path
            })
            
            results_str = json.dumps(results)
            database.update_project_test(
                pt['id'],
                pt['status'],
                pt['observations'],
                results_str,
                pt['excel_path'],
                pt['processed_data_path']
            )
            
            pt['results_json'] = results_str
            self.update_saved_graphs_list(pt)
            QMessageBox.information(self, "Success", f"Custom graph ({y_col} vs {x_col}) saved successfully and added to the report.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save custom graph: {e}")
