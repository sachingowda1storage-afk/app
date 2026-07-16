import os
import json
import datetime
import pandas as pd
import numpy as np

def clean_time(val):
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, datetime.time):
        return float(val.hour * 3600 + val.minute * 60 + val.second + val.microsecond / 1e6)
    if isinstance(val, datetime.datetime):
        return float(val.hour * 3600 + val.minute * 60 + val.second + val.microsecond / 1e6)
    if isinstance(val, str):
        val = val.strip()
        parts = val.split(':')
        if len(parts) == 3:
            try:
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            except ValueError:
                pass
        elif len(parts) == 2:
            try:
                return float(parts[0]) * 60 + float(parts[1])
            except ValueError:
                pass
        try:
            return float(val)
        except ValueError:
            pass
    return 0.0

def lttb_downsample(x, y, threshold=2000):
    """
    Downsamples x and y values to exactly 'threshold' points using LTTB.
    Returns downsampled numpy arrays.
    """
    n_data = len(x)
    if threshold >= n_data or threshold <= 2:
        return x, y

    # Convert to arrays
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    bucket_size = (n_data - 2) / (threshold - 2)
    keep_indices = np.zeros(threshold, dtype=int)
    keep_indices[0] = 0
    keep_indices[-1] = n_data - 1

    a = 0
    for i in range(threshold - 2):
        # Range of the current bucket
        bin_start = int(np.floor(i * bucket_size) + 1)
        bin_end = int(np.floor((i + 1) * bucket_size) + 1)
        bin_end = min(bin_end, n_data - 1)

        # Average of the next bucket
        next_bin_start = int(np.floor((i + 1) * bucket_size) + 1)
        next_bin_end = int(np.floor((i + 2) * bucket_size) + 1)
        next_bin_end = min(next_bin_end, n_data)

        if next_bin_start < next_bin_end:
            next_avg_x = np.mean(x[next_bin_start:next_bin_end])
            next_avg_y = np.mean(y[next_bin_start:next_bin_end])
        else:
            next_avg_x = x[-1]
            next_avg_y = y[-1]

        # Points in current bucket
        bin_x = x[bin_start:bin_end]
        bin_y = y[bin_start:bin_end]

        x_a, y_a = x[a], y[a]
        x_c, y_c = next_avg_x, next_avg_y

        # Areas of triangles
        areas = 0.5 * np.abs(x_a * (bin_y - y_c) + bin_x * (y_c - y_a) + x_c * (y_a - bin_y))
        
        if len(areas) > 0:
            max_idx = bin_start + np.argmax(areas)
        else:
            max_idx = bin_start
            
        keep_indices[i + 1] = max_idx
        a = max_idx

    return x[keep_indices], y[keep_indices]

def detect_and_parse_file(file_path):
    """
    Detects if the file is excel/csv, parses header row, returns raw dataframe.
    """
    ext = os.path.splitext(file_path)[1].lower()
    sheet_name = None
    header_row = 0
    
    if ext in ['.xlsx', '.xls', '.xlsm']:
        xl = pd.ExcelFile(file_path)
        sheet_name = 'in' if 'in' in xl.sheet_names else xl.sheet_names[0]
        df_preview = xl.parse(sheet_name, nrows=100, header=None)
    else:
        # Delimiter detection
        for sep in [',', ';', '\t']:
            try:
                df_preview = pd.read_csv(file_path, nrows=100, header=None, sep=sep)
                break
            except Exception:
                continue
        else:
            df_preview = pd.read_csv(file_path, nrows=100, header=None)
            sep = ','

    # Find row index containing "current" and "voltage"
    found_header = False
    for idx, row in df_preview.iterrows():
        row_vals = [str(val).lower() for val in row.dropna().tolist()]
        if any('current' in val for val in row_vals) and any('voltage' in val for val in row_vals):
            header_row = idx
            found_header = True
            break
            
    if ext in ['.xlsx', '.xls', '.xlsm']:
        df = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=header_row)
    else:
        df = pd.read_csv(file_path, skiprows=header_row, sep=sep)
        
    return df

def normalize_columns(df):
    """
    Maps telemetry column headers to unified keywords:
    Time, Step, Current, Voltage, Temperature, SOC, Cycle, Capacity, Energy
    """
    df = df.copy()
    columns = [str(c).strip() for c in df.columns]
    
    target_patterns = {
        'Time': [
            lambda c: c == 'total time, (h:m:s)',
            lambda c: c == 'total time',
            lambda c: 'total time' in c,
            lambda c: c == 'time',
            lambda c: 'time' in c and 'step' not in c
        ],
        'Step': [
            lambda c: c == 'step',
            lambda c: 'step' in c and 'time' not in c
        ],
        'Current': [
            lambda c: c == 'current, a',
            lambda c: c == 'current(a)',
            lambda c: c == 'current',
            lambda c: 'current' in c and not any(x in c for x in ['fault', 'limit', 'sensor', 'continuous', 'peak'])
        ],
        'Voltage': [
            lambda c: c == 'voltage, v',
            lambda c: c == 'voltage(v)',
            lambda c: c == 'voltage',
            lambda c: 'voltage' in c and not any(x in c for x in ['fault', 'limit', 'sensor', 'cell', 'pack'])
        ],
        'BMS_Pack_Voltage': [
            lambda c: 'pack_voltage' in c or 'pack voltage' in c or c == 'bms_pack_voltage'
        ],
        'Capacity': [
            lambda c: c == 'amp-hours, ah',
            lambda c: c == 'amp-hours',
            lambda c: c == 'ah' or c == 'capacity' or 'capacity_discharge' in c or 'amp-hours discharge' in c
        ],
        'Energy': [
            lambda c: c == 'watt-hours, wh',
            lambda c: c == 'watt-hours',
            lambda c: c == 'wh' or c == 'energy' or 'energy_discharge' in c
        ],
        'Temperature': [
            lambda c: 'maxcell_temp' in c or 'maxcell_temperature' in c or 'cell_temp' in c or c == 'bms_maxcell_temp' or c == 'temp' or c == 'temperature'
        ],
        'SOC': [
            lambda c: 'soc' in c or c == 'bms_soc'
        ],
        'Cycle': [
            lambda c: 'cycle' in c
        ]
    }
    
    col_mapping = {}
    assigned = set()
    for target, patterns in target_patterns.items():
        for pattern in patterns:
            matched = None
            for col in df.columns:
                if col in assigned:
                    continue
                c_low = str(col).lower().strip()
                if pattern(c_low):
                    matched = col
                    break
            if matched is not None:
                col_mapping[matched] = target
                assigned.add(matched)
                break
                
    df = df.rename(columns=col_mapping)
    
    # Inject defaults
    if 'Time' not in df.columns:
        df['Time'] = range(len(df))
    if 'Temperature' not in df.columns:
        # Search for other temp tags
        other_temps = [c for c in df.columns if 'temp' in str(c).lower()]
        if other_temps:
            df['Temperature'] = df[other_temps[0]]
        else:
            df['Temperature'] = 25.0 # Ambient default
        
    # Clean types for existing mapped columns
    for col in ['Current', 'Voltage', 'Temperature', 'SOC', 'Step', 'Cycle', 'Capacity', 'Energy']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
    df['Time_Sec'] = df['Time'].apply(clean_time)
    df = df.sort_values(by='Time_Sec').reset_index(drop=True)
    
    # DO NOT drop rows with NaNs as requested by manager to avoid losing important data
    
    return df

def run_data_processing(df, expected_temp=None, expected_c_rate=None, battery_spec=None, category='Electrical'):
    """
    Cleans, extracts stats, detects anomalies, calculates DC IR, and downsamples.
    Returns: (diagnostics_dict, downsampled_df, alerts_list)
    """
    alerts = []
    
    # 1. Basic Stats
    df = normalize_columns(df)
    
    is_cycler = 'Current' in df.columns and 'Voltage' in df.columns
    
    df['dt'] = df['Time_Sec'].diff().fillna(1.0)
    df.loc[df['dt'] > 600.0, 'dt'] = 1.0 # filter massive gap anomalies
    
    charge_stats = None
    if is_cycler:
        # Identify charging
        df_charge = df[df['Current'] > 0.05]
        if not df_charge.empty:
            v_max = float(df_charge['Voltage'].max())
            cv_mask = (df_charge['Voltage'] >= v_max - 0.02)
            cc_time = float(df_charge[~cv_mask]['dt'].sum())
            cv_time = float(df_charge[cv_mask]['dt'].sum())
            total_chg = cc_time + cv_time
            
            charge_stats = {
                'max_voltage': v_max,
                'cc_time_sec': cc_time,
                'cv_time_sec': cv_time,
                'cc_pct': (cc_time / total_chg * 100.0) if total_chg > 0 else 0.0,
                'cv_pct': (cv_time / total_chg * 100.0) if total_chg > 0 else 0.0
            }
        
    discharge_stats = None
    if is_cycler:
        # Identify discharging
        df_discharge = df[df['Current'] < -0.05]
        if not df_discharge.empty:
            # Dynamic Capacity calculation via integration
            dis_cap_ah = float((df_discharge['Current'].abs() * df_discharge['dt']).sum() / 3600.0)
            # Check if telemetry column already had capacity
            if 'Capacity' in df_discharge.columns:
                cap_col_max = float(df_discharge['Capacity'].max())
                if cap_col_max > 0.1:
                    dis_cap_ah = cap_col_max
                
            dis_eng_wh = float(((df_discharge['Current'] * df_discharge['Voltage']).abs() * df_discharge['dt']).sum() / 3600.0)
            if 'Energy' in df_discharge.columns:
                eng_col_max = float(df_discharge['Energy'].max())
                if eng_col_max > 0.1:
                    dis_eng_wh = eng_col_max
                
            avg_v = float(df_discharge['Voltage'].mean())
            avg_i = float(df_discharge['Current'].abs().mean())
            active_c_rate = avg_i / dis_cap_ah if dis_cap_ah > 0 else 0.0
            
            discharge_stats = {
                'capacity_ah': dis_cap_ah,
                'energy_wh': dis_eng_wh,
                'avg_voltage': avg_v,
                'avg_current': avg_i,
                'c_rate': active_c_rate
            }
        
    # 2. DC Internal Resistance (Ohmic Drop)
    # Transitions from Rest (abs(I) <= 0.05) to Discharge (I < -0.05)
    dc_ir_list = []
    if is_cycler:
        for i in range(1, len(df)):
            curr_prev = df.iloc[i-1]['Current']
            curr_curr = df.iloc[i]['Current']
            if abs(curr_prev) <= 0.05 and curr_curr < -0.5:
                # Transition found
                v_ocv = df.iloc[i-1]['Voltage']
                v_dis = df.iloc[i]['Voltage']
                i_dis = abs(curr_curr)
                sag = v_ocv - v_dis
                dc_ir = (sag / i_dis) * 1000.0 # mOhm
                
                dc_ir_list.append({
                    'time_sec': float(df.iloc[i]['Time_Sec']),
                    'soc': float(df.iloc[i]['SOC']) if 'SOC' in df.columns else 50.0,
                    'v_ocv': float(v_ocv),
                    'v_discharge': float(v_dis),
                    'i_discharge': float(i_dis),
                    'sag': float(sag),
                    'dc_ir': float(dc_ir)
                })
            
    # 3. Peak temperature rise estimation
    thermal_stats = None
    if 'Temperature' in df.columns:
        t_max = float(df['Temperature'].max())
        t_min = float(df['Temperature'].min())
        thermal_stats = {
            't_max': t_max,
            't_min': t_min,
            't_rise': max(0.0, t_max - t_min)
        }
        
    # 4. Configured Validation Limits & Discrepancies
    if category == 'Electrical':
        if expected_temp is not None and 'Temperature' in df.columns:
            if not df.empty:
                t_start = float(df['Temperature'].iloc[0])
                try:
                    exp_t = float(expected_temp)
                    if abs(t_start - exp_t) > 5.0:
                        alerts.append(f"CHAMBER DEVIATION: Initial temperature ({t_start:.1f}°C) differs from expected chamber setpoint ({exp_t:.1f}°C) by >5°C.")
                except ValueError:
                    pass
                 
        if expected_c_rate is not None and discharge_stats is not None:
            try:
                exp_c = float(expected_c_rate)
                active_c = discharge_stats['c_rate']
                if abs(active_c - exp_c) > 0.15:
                    alerts.append(f"C-RATE DISCREPANCY: Active discharge rate is {active_c:.2f}C, while configured rate was {exp_c:.2f}C.")
            except ValueError:
                pass
                
        # Check physical battery limits if spec provided and voltage is available
        if battery_spec is not None and 'Voltage' in df.columns:
            nom_v = float(battery_spec.get('nominal_voltage', 52.0) or 52.0)
            v_min_limit = (nom_v / 52.0) * 35.0
            v_max_limit = (nom_v / 52.0) * 59.5
            v_min_obs = float(df['Voltage'].min())
            v_max_obs = float(df['Voltage'].max())
            
            if v_min_obs < v_min_limit:
                alerts.append(f"BATTERY UNDER-VOLTAGE: Terminal voltage dropped to {v_min_obs:.2f}V (Below safe discharge limit of {v_min_limit:.1f}V)")
            if v_max_obs > v_max_limit:
                alerts.append(f"BATTERY OVER-VOLTAGE: Terminal voltage peaked at {v_max_obs:.2f}V (Above safe charging limit of {v_max_limit:.1f}V)")
                
            # Capacity check
            spec_cap = float(battery_spec.get('capacity', 30.0) or 30.0)
            if discharge_stats is not None:
                retrieved_cap = discharge_stats['capacity_ah']
                retrieved_pct = (retrieved_cap / spec_cap) * 100.0
                if retrieved_pct < 85.0:
                    alerts.append(f"CAPACITY DEGRADATION: Measured discharge capacity ({retrieved_cap:.2f} Ah) is only {retrieved_pct:.1f}% of nominal pack rating ({spec_cap} Ah)")
                elif retrieved_pct > 115.0:
                    alerts.append(f"CAPACITY EXCEEDS NOMINAL: Measured capacity ({retrieved_cap:.2f} Ah) is {retrieved_pct:.1f}% of nominal. Check sensor calibration.")
                    
    elif category == 'Thermal / Climatic':
        # Check cell over-temperature boundary
        if 'Temperature' in df.columns:
            t_max = float(df['Temperature'].max())
            if t_max > 60.0:
                alerts.append(f"THERMAL ABUSE: Cell temperature reached {t_max:.1f}°C (Exceeds maximum safe thermal boundary of 60°C)")
            elif t_max > 55.0:
                alerts.append(f"THERMAL WARNING: Cell temperature rose to {t_max:.1f}°C")
                
    elif category == 'Mechanical':
        # Check acceleration levels if available
        acc_col = next((c for c in df.columns if 'acceleration' in c.lower()), None)
        if acc_col:
            acc_max = float(df[acc_col].max())
            if acc_max > 15.0:
                alerts.append(f"MECHANICAL SHOCK DETECTED: Peak acceleration reached {acc_max:.1f}g (Vibration profile anomaly)")
                
    elif category == 'EMC':
        # Check emissions levels vs limit lines
        em_col = next((c for c in df.columns if 'emission' in c.lower()), None)
        lim_col = next((c for c in df.columns if 'limit' in c.lower()), None)
        if em_col and lim_col:
            excess = df[df[em_col] > df[lim_col]]
            if not excess.empty:
                alerts.append(f"EMC LIMIT EXCEEDED: Emissions level exceeded the standard limit line at {len(excess)} frequency points.")
                
    elif category == 'Functional Safety':
        # Check fault alarms or alarm signal state
        fault_col = next((c for c in df.columns if 'fault' in c.lower() or 'alarm' in c.lower()), None)
        if fault_col:
            faults = df[df[fault_col] > 0]
            if not faults.empty:
                alerts.append(f"BMS FAULT TRIGGERED: Active fault flag alarms detected in CAN log.")

    # 5. Keep full telemetry data
    downsampled_data = df.copy()
        
    diagnostics = {
        'charge': charge_stats,
        'discharge': discharge_stats,
        'transitions': dc_ir_list,
        'thermal': thermal_stats
    }
    
    return diagnostics, downsampled_data, alerts
