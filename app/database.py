import sqlite3
import sys
import os
import json
import hashlib
from datetime import datetime

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    RESOURCE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_DIR = BASE_DIR

DB_PATH = os.path.join(BASE_DIR, "data", "battery_processor.db")

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Create Batteries Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS batteries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        cell_type TEXT,
        configuration TEXT,
        nominal_voltage REAL,
        capacity REAL,
        chemistry TEXT,
        weight REAL,
        energy_wh REAL,
        energy_density REAL,
        power_density REAL,
        part_number TEXT,
        serial_number TEXT,
        mfg_date TEXT,
        is_custom INTEGER DEFAULT 0
    )
    """)
    
    # 2. Create TSES Versions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tses_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        version TEXT UNIQUE NOT NULL,
        filename TEXT,
        file_content BLOB,
        compare_notes TEXT,
        uploaded_at TEXT
    )
    """)
    
    # 3. Create Tests Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tests (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        required_inputs TEXT,
        required_excel_format TEXT,
        required_graphs TEXT,
        acceptance_criteria TEXT,
        category TEXT,
        is_custom INTEGER DEFAULT 0,
        tses_version_id INTEGER,
        FOREIGN KEY (tses_version_id) REFERENCES tses_versions(id)
    )
    """)
    
    # 4. Create Projects Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        request_no TEXT,
        battery_id INTEGER,
        tses_version_id INTEGER,
        customer TEXT,
        project_name TEXT,
        engineer TEXT,
        team_members TEXT,
        comments TEXT,
        status TEXT DEFAULT 'Draft',
        created_at TEXT,
        FOREIGN KEY (battery_id) REFERENCES batteries(id),
        FOREIGN KEY (tses_version_id) REFERENCES tses_versions(id)
    )
    """)
    
    # 5. Create Project Tests Table (links tests run in a project)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS project_tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        test_id TEXT,
        excel_path TEXT,
        raw_data_path TEXT,
        processed_data_path TEXT,
        status TEXT DEFAULT 'Pending', -- 'Pending', 'Pass', 'Fail', 'Review'
        observations TEXT,
        results_json TEXT,
        created_at TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id),
        FOREIGN KEY (test_id) REFERENCES tests(id)
    )
    """)
    
    # 6. Create Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL, -- 'Admin', 'Engineer'
        created_at TEXT
    )
    """)
    
    # 7. Create Audit Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        action TEXT NOT NULL,
        timestamp TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    
    conn.commit()
    
    # Seed default values
    seed_default_data(conn)
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def seed_default_data(conn):
    cursor = conn.cursor()
    
    # Seed Users
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        admin_pass = hash_password("admin123")
        eng_pass = hash_password("engineer123")
        now = datetime.now().isoformat()
        cursor.execute("INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                       ("admin", admin_pass, "Admin", now))
        cursor.execute("INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                       ("engineer", eng_pass, "Engineer", now))
    
    # Seed Default Batteries
    cursor.execute("UPDATE batteries SET part_number = 'K2002000-01' WHERE part_number = 'TVS-U701-01'")
    cursor.execute("UPDATE batteries SET part_number = 'K2002000-02' WHERE part_number = 'TVS-U702-01'")
    cursor.execute("UPDATE batteries SET part_number = 'K2002000-03' WHERE part_number = 'TVS-U546-V2'")
    cursor.execute("UPDATE batteries SET part_number = 'K2002000-04' WHERE part_number = 'TVS-U546-V1'")
    cursor.execute("UPDATE batteries SET part_number = 'K2002000-05' WHERE part_number = 'TVS-U829-01'")

    cursor.execute("SELECT COUNT(*) FROM batteries")
    if cursor.fetchone()[0] == 0:
        default_packs = [
            ("U701", "M52V cells", "14s7p", 52.0, 30.2, "Li-ion NMC", 9.2, 1570.4, "K2002000-01", "SN-U701-0001", "2026-01-01"),
            ("U702", "M50L cells", "14s9p", 52.0, 37.0, "Li-ion NMC", 11.5, 1924.0, "K2002000-02", "SN-U702-0001", "2026-01-10"),
            ("U546 V2", "M52V cells", "14s6p", 52.0, 26.0, "Li-ion NMC", 8.0, 1352.0, "K2002000-03", "SN-U546-V2-0001", "2026-02-15"),
            ("U546 V1", "M52V cells", "14s7p", 52.0, 30.2, "Li-ion NMC", 9.2, 1570.4, "K2002000-04", "SN-U546-V1-0001", "2025-06-20"),
            ("U829", "M52V cells", "14s9p", 52.0, 39.0, "Li-ion NMC", 12.0, 2028.0, "K2002000-05", "SN-U829-0001", "2026-03-05")
        ]
        for name, cell, config, volt, cap, chem, wt, wh, part_no, serial_no, mfg_date in default_packs:
            # Densities initially calculated based on weight
            energy_density = wh / wt if wt else 0.0
            # Assume nominal peak power = volt * cap * 2 (2C discharge peak)
            power_density = (volt * cap * 2) / wt if wt else 0.0
            cursor.execute("""
            INSERT INTO batteries (name, cell_type, configuration, nominal_voltage, capacity, chemistry, weight, energy_wh, energy_density, power_density, part_number, serial_number, mfg_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, cell, config, volt, cap, chem, wt, wh, energy_density, power_density, part_no, serial_no, mfg_date))

    # Seed Default TSES Version 8
    cursor.execute("UPDATE tses_versions SET version = 'TSES 799 v8' WHERE version = 'TSES v8'")
    cursor.execute("SELECT id FROM tses_versions WHERE version = 'TSES 799 v8'")
    tses_row = cursor.fetchone()
    if not tses_row:
        now = datetime.now().isoformat()
        cursor.execute("INSERT INTO tses_versions (version, compare_notes, uploaded_at) VALUES (?, ?, ?)",
                       ("TSES 799 v8", "Default system test standard containing 101 predefined verification classes.", now))
        tses_version_id = cursor.lastrowid
    else:
        tses_version_id = tses_row[0]
        
    # Seed 101 Predefined Tests
    # Clear existing predefined tests (is_custom = 0 or NULL) to enforce the new inputs/graphs schemas
    cursor.execute("DELETE FROM tests WHERE is_custom = 0 OR is_custom IS NULL")
    
    json_path = os.path.join(RESOURCE_DIR, "data", "tses_tests.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                tests_data = json.load(f)
            for test_id, data in tests_data.items():
                title = data.get("title", "")
                desc = data.get("purpose", "")
                title_l = title.lower()
                desc_l = desc.lower()
                
                # Dynamic Categorization & Inputs/Graphs mapping based primarily on TITLE
                if any(x in title_l for x in ["vibration", "shock", "drop", "weld", "pull", "mechanical", "crush", "nail", "impact"]):
                    category = "Mechanical"
                    inputs = "Time, Acceleration (g), Frequency (Hz), Pack Voltage (V), Cell Temperatures (°C), CAN Communications Status"
                    excel_fmt = "Vibration / Shock test recorder high-frequency logging (.xlsx, .csv)"
                    graphs = "Acceleration vs Time, Frequency vs Time, Cell Temperature vs Time"
                elif any(x in title_l for x in ["thermal", "dewing", "chamber", "fire", "humidity", "immersion", "heating", "burn", "overtemperature", "undertemperature", "over temperature", "under temperature"]):
                    category = "Thermal / Climatic"
                    inputs = "Time, Ambient Temperature (°C), Cell Temperatures (°C), Pack Voltage (V), Leakage / Venting Flag"
                    excel_fmt = "Chamber logger time-series temperature profile (.xlsx, .csv)"
                    graphs = "Ambient Temperature vs Time, Cell Temperature vs Time, Pack Voltage vs Time"
                elif any(x in title_l for x in ["storage", "self-discharge", "soh", "aging", "life", "cycle"]):
                    category = "Life / Aging"
                    inputs = "Cycle Count, Discharged Capacity (Ah), SOH (%), Retention (%), Temperature (°C)"
                    excel_fmt = "Standard battery cycler life-cycle summary report (.xlsx, .csv)"
                    graphs = "Capacity vs Cycle, SOH vs Cycle, Retention vs Cycle"
                elif any(x in title_l for x in ["can ", "message", "communication", "bms node", "node allocation", "redundancy", "software"]):
                    category = "Functional Safety"
                    inputs = "Time, CAN Message Status, Fault Trigger ID, Alarm Signal Flag, Recovery Duration (s)"
                    excel_fmt = "BMS CAN bus diagnostic log file (.csv, .xlsx, .asc)"
                    graphs = "CAN Message Status vs Time, Fault Flag vs Time"
                elif any(x in title_l for x in ["emc", "emi", "emission", "immunity"]):
                    category = "Electrical"
                    inputs = "Frequency (MHz), Emissions Level (dBμV), Limit Line (dBμV), Test Verdict"
                    excel_fmt = "EMC spectrum analyzer sweep data (.csv, .xlsx)"
                    graphs = "Emissions Level vs Frequency"
                else:
                    # Fallback to description keywords but with strict exclusions
                    if any(x in desc_l for x in ["vibration", "shock", "mechanical crush"]):
                        category = "Mechanical"
                        inputs = "Time, Acceleration (g), Frequency (Hz), Pack Voltage (V), Cell Temperatures (°C), CAN Communications Status"
                        excel_fmt = "Vibration / Shock test recorder high-frequency logging (.xlsx, .csv)"
                        graphs = "Acceleration vs Time, Frequency vs Time, Cell Temperature vs Time"
                    elif any(x in desc_l for x in ["fire exposure", "thermal abuse", "immersion"]):
                        category = "Thermal / Climatic"
                        inputs = "Time, Ambient Temperature (°C), Cell Temperatures (°C), Pack Voltage (V), Leakage / Venting Flag"
                        excel_fmt = "Chamber logger time-series temperature profile (.xlsx, .csv)"
                        graphs = "Ambient Temperature vs Time, Cell Temperature vs Time, Pack Voltage vs Time"
                    else:
                        category = "Electrical"
                        inputs = "Time, Current (A), Pack Voltage (V), Cell Temperatures (°C), Ambient Temperature (°C), SOC (%), Discharged Capacity (Ah), Discharged Energy (Wh)"
                        excel_fmt = "Standard battery cycler time-series log (.xlsx, .csv)"
                        graphs = "Voltage vs Time, Current vs Time, Capacity vs Time"
                
                cursor.execute("""
                INSERT INTO tests (id, name, description, required_inputs, required_excel_format, required_graphs, acceptance_criteria, category, is_custom, tses_version_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """, (test_id, title, desc, inputs, excel_fmt, graphs, data.get("acceptance_criteria"), category, tses_version_id))
        except Exception as e:
            print("Failed to seed tests from JSON:", e)
    
    conn.commit()

# --- DATABASE API FUNCTIONS ---

def get_all_batteries():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM batteries ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_battery(data):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Calculate Wh and densities if valid
        volt = float(data.get('nominal_voltage', 0) or 0)
        cap = float(data.get('capacity', 0) or 0)
        wh = volt * cap
        weight = float(data.get('weight', 0) or 0)
        energy_density = wh / weight if weight else 0.0
        # Peak power approximation (2C discharge)
        power_density = (volt * cap * 2) / weight if weight else 0.0
        
        cursor.execute("""
        INSERT INTO batteries (name, cell_type, configuration, nominal_voltage, capacity, chemistry, weight, energy_wh, energy_density, power_density, part_number, serial_number, mfg_date, is_custom)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (data['name'], data.get('cell_type'), data.get('configuration'), volt, cap, data.get('chemistry'), weight, wh, energy_density, power_density, data.get('part_number'), data.get('serial_number'), data.get('mfg_date')))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def get_all_tses_versions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tses_versions ORDER BY uploaded_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_tses_version(version, filename, content_bytes, compare_notes):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        now = datetime.now().isoformat()
        cursor.execute("""
        INSERT INTO tses_versions (version, filename, file_content, compare_notes, uploaded_at)
        VALUES (?, ?, ?, ?, ?)
        """, (version, filename, sqlite3.Binary(content_bytes) if content_bytes else None, compare_notes, now))
        conn.commit()
        tses_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        tses_id = None
    conn.close()
    return tses_id

def get_tests_for_tses(tses_version_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tests WHERE tses_version_id = ?", (tses_version_id,))
    rows = cursor.fetchall()
    conn.close()
    
    results = [dict(r) for r in rows]
    
    # Natural/numeric sort for clause IDs like "8.1", "8.10", "8.100"
    def parse_clause_key(test):
        test_id = str(test.get('id', ''))
        parts = test_id.split('.')
        try:
            return [int(p) for p in parts if p.strip().isdigit()]
        except ValueError:
            return [9999] # Fallback for non-numeric custom IDs
            
    results.sort(key=parse_clause_key)
    return results

def add_test(test_id, name, description, required_inputs, acceptance_criteria, category, tses_version_id, is_custom=1):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO tests (id, name, description, required_inputs, required_excel_format, required_graphs, acceptance_criteria, category, is_custom, tses_version_id)
        VALUES (?, ?, ?, ?, 'Standard battery cycler time-series log (.xlsx, .csv)', 'Voltage vs Time, Current vs Time', ?, ?, ?, ?)
        """, (test_id, name, description, required_inputs, acceptance_criteria, category, is_custom, tses_version_id))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def create_project(data):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO projects (name, request_no, battery_id, tses_version_id, customer, project_name, engineer, team_members, comments, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (data['name'], data.get('request_no'), data.get('battery_id'), data.get('tses_version_id'), data.get('customer'), data.get('project_name'), data.get('engineer'), data.get('team_members'), data.get('comments'), now))
    conn.commit()
    project_id = cursor.lastrowid
    conn.close()
    return project_id

def get_projects():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.*, b.name as battery_name, t.version as tses_version 
    FROM projects p
    LEFT JOIN batteries b ON p.battery_id = b.id
    LEFT JOIN tses_versions t ON p.tses_version_id = t.id
    ORDER BY p.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_project_details(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.*, b.name as battery_name, b.cell_type, b.configuration, b.nominal_voltage, b.capacity, b.weight, b.chemistry, b.part_number, b.serial_number, b.mfg_date, t.version as tses_version 
    FROM projects p
    LEFT JOIN batteries b ON p.battery_id = b.id
    LEFT JOIN tses_versions t ON p.tses_version_id = t.id
    WHERE p.id = ?
    """, (project_id,))
    project_row = cursor.fetchone()
    if not project_row:
        conn.close()
        return None
        
    project = dict(project_row)
    
    cursor.execute("""
    SELECT pt.*, t.name as test_name, t.description as test_desc, t.acceptance_criteria, t.required_graphs, t.required_inputs, t.category 
    FROM project_tests pt
    LEFT JOIN tests t ON pt.test_id = t.id
    WHERE pt.project_id = ?
    ORDER BY CAST(pt.test_id AS REAL), pt.test_id ASC
    """, (project_id,))
    project['tests'] = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return project

def add_project_test(project_id, test_id, excel_path):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO project_tests (project_id, test_id, excel_path, created_at)
    VALUES (?, ?, ?, ?)
    """, (project_id, test_id, excel_path, now))
    conn.commit()
    pt_id = cursor.lastrowid
    conn.close()
    return pt_id

def update_project_test(pt_id, status, observations, results_json, raw_path="", proc_path=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE project_tests 
    SET status = ?, observations = ?, results_json = ?, raw_data_path = ?, processed_data_path = ?
    WHERE id = ?
    """, (status, observations, results_json, raw_path, proc_path, pt_id))
    conn.commit()
    conn.close()

def log_audit(username, action):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    # Find user_id
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_row = cursor.fetchone()
    user_id = user_row[0] if user_row else None
    
    cursor.execute("""
    INSERT INTO audit_logs (user_id, username, action, timestamp)
    VALUES (?, ?, ?, ?)
    """, (user_id, username, action, now))
    conn.commit()
    conn.close()

def get_audit_logs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 200")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def authenticate_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    h = hash_password(password)
    cursor.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, h))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
