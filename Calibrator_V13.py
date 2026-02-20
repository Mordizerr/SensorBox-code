#!/usr/bin/env python3
"""
Multi-Sensor Calibration GUI - UPDATED FOR NEW ARDUINO SYSTEM
Complete integration with Arduino Multi-Sensor Calibration System v1.0

FEATURES:
  ✓ All original Tier 1 features intact
  ✓ 3-tab structure per sensor (Regular/Force/Set Values)
  ✓ Mode selection for EC Low (3/4/5 point)
  ✓ Enhanced calibration plots with real Arduino data
  ✓ Force calibration with manual voltage entry
  ✓ Custom reference value setting
  ✓ Multi-sensor plot visualization

UPDATED COMMANDS:
  ✓ CAL_EC_LOW_1-5, CAL_EC_HIGH_1-2, CAL_PH_1-3, CAL_TEMP_1-3
  ✓ FORCE_EC_LOW_1-5, FORCE_PH_1-3, etc.
  ✓ SET_EC_LOW_1-5, SET_PH_1-3, etc.
  ✓ CALMODE_EC_LOW_3/4/5
  ✓ STATUS_COMPACT (machine-readable status)
  
Requires: pip install PyQt5 pyserial matplotlib numpy
"""

import sys
import os
import csv
import re
import time
import json
import threading
from datetime import datetime, timedelta
from collections import deque
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import serial

# Plotting
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

# ============================================================================
# ENHANCED SERIAL WORKER WITH AUTO-RECONNECT
# ============================================================================

class SerialWorker(QThread):
    """Enhanced serial worker with auto-reconnect and better error handling"""
    dataReceived = pyqtSignal(str)
    connectionStatus = pyqtSignal(bool, str)  # connected, message
    errorOccurred = pyqtSignal(str)
    
    def __init__(self, port, baudrate=115200):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.running = True
        self.serial_port = None
        self.reconnect_delay = 1  # Start with 1 second
        self.max_reconnect_delay = 30
        
    def connect(self):
        """Attempt to connect to serial port"""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
                
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1.0
            )
            time.sleep(0.5)  # Let Arduino stabilize
            self.connectionStatus.emit(True, "Connected")
            self.reconnect_delay = 1  # Reset delay on success
            return True
        except Exception as e:
            self.connectionStatus.emit(False, f"Connection failed: {e}")
            return False
        
    def run(self):
        """Main worker loop with auto-reconnect"""
        while self.running:
            if not self.serial_port or not self.serial_port.is_open:
                if self.connect():
                    continue
                else:
                    # Exponential backoff
                    time.sleep(self.reconnect_delay)
                    self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
                    continue
                    
            try:
                if self.serial_port.in_waiting:
                    line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self.dataReceived.emit(line)
                self.msleep(50)
            except Exception as e:
                self.errorOccurred.emit(f"Read error: {e}")
                if self.serial_port:
                    self.serial_port.close()
                self.connectionStatus.emit(False, "Connection lost")
                
    def send_command(self, cmd):
        """Send command to Arduino"""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.write(f"{cmd}\n".encode())
                return True
        except Exception as e:
            self.errorOccurred.emit(f"Send error: {e}")
            return False
        return False
        
    def stop(self):
        """Stop the worker thread"""
        self.running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()

# ============================================================================
# QUALITY METRICS WIDGET
# ============================================================================

class QualityWidget(QGroupBox):
    """Display calibration quality metrics"""
    
    def __init__(self):
        super().__init__("Quality Metrics")
        self.metrics = {}
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Metric labels
        self.ec_low_label = QLabel("EC Low: --")
        self.ec_high_label = QLabel("EC High: --")
        self.ph_label = QLabel("pH: --")
        self.temp_label = QLabel("Temp: --")
        
        for label in [self.ec_low_label, self.ec_high_label, self.ph_label, self.temp_label]:
            label.setStyleSheet("font-family: monospace; padding: 3px;")
            layout.addWidget(label)
        
        self.setLayout(layout)
        
    def update_from_data(self, data_string):
        """Update quality metrics from Arduino response"""
        # Parse R² values from responses
        if "EC_LOW:" in data_string or "EC Low" in data_string:
            r2_match = re.search(r'R2?[²=]?\s*[=:]?\s*([\d.]+)', data_string)
            if r2_match:
                r2 = float(r2_match.group(1))
                self.ec_low_label.setText(f"EC Low: R²={r2:.4f}")
                
        if "EC_HIGH:" in data_string or "EC High" in data_string:
            r2_match = re.search(r'R2?[²=]?\s*[=:]?\s*([\d.]+)', data_string)
            if r2_match:
                r2 = float(r2_match.group(1))
                self.ec_high_label.setText(f"EC High: R²={r2:.4f}")
                
        if "pH:" in data_string and "R" in data_string:
            r2_match = re.search(r'R2?[²=]?\s*[=:]?\s*([\d.]+)', data_string)
            if r2_match:
                r2 = float(r2_match.group(1))
                self.ph_label.setText(f"pH: R²={r2:.4f}")
                
        if "TEMP:" in data_string or "Temperature" in data_string:
            r2_match = re.search(r'R2?[²=]?\s*[=:]?\s*([\d.]+)', data_string)
            if r2_match:
                r2 = float(r2_match.group(1))
                self.temp_label.setText(f"Temp: R²={r2:.4f}")

# ============================================================================
# ENHANCED CALIBRATION PLOT WIDGET
# ============================================================================

class CalibrationPlotWidget(QGroupBox):
    """Visual display of calibration points and fitted line with real Arduino data"""
    
    def __init__(self):
        super().__init__("📊 Calibration Visualization")
        self.sensor_data = {}  # Store data for all sensors
        self.current_sensor = "ECL"  # Which sensor to display
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Sensor selector
        sensor_layout = QHBoxLayout()
        sensor_layout.addWidget(QLabel("Display:"))
        self.sensor_combo = QComboBox()
        self.sensor_combo.addItems(["EC Low", "EC High", "pH", "Temperature"])
        self.sensor_combo.currentIndexChanged.connect(self.on_sensor_changed)
        sensor_layout.addWidget(self.sensor_combo)
        sensor_layout.addStretch()
        layout.addLayout(sensor_layout)
        
        # Matplotlib figure
        self.figure = Figure(figsize=(6, 3.5))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # Info text showing equation and R²
        self.info_text = QLabel("No calibration data")
        self.info_text.setWordWrap(True)
        self.info_text.setStyleSheet(
            "padding: 5px; background-color: #e7f5ff; "
            "border-radius: 3px; font-family: monospace; font-size: 10px;"
        )
        layout.addWidget(self.info_text)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh Plot")
        refresh_btn.clicked.connect(self.request_plot_update)
        layout.addWidget(refresh_btn)
        
        self.setLayout(layout)
        
    def request_plot_update(self):
        """Request calibration data from Arduino via EQUATIONS command"""
        parent = self
        while parent and not hasattr(parent, 'send_command'):
            parent = parent.parent()
        if parent:
            parent.send_command("EQUATIONS")
            
    def update_from_equations(self, full_response):
        """
        Parse multi-line EQUATIONS response from Arduino.

        Format per sensor block:
          --- EC LOW RANGE ---
          Equation: EC = 1.234567 * V_mV + -123.45
          Calibration Points:
            P1: 450.3mV -> 65.0uS/cm
            P2: 673.8mV -> 200.0uS/cm
          Quality: R2=0.9987 RMSE=2.30 uS/cm
        """
        try:
            section_map = {
                '--- EC LOW RANGE ---':  'ECL',
                '--- EC HIGH RANGE ---': 'ECH',
                '--- pH ---':            'PH',
                '--- TEMPERATURE ---':   'T',
            }

            current_sensor = None
            points = []
            C = D = R2 = 0.0

            for raw_line in full_response.split('\n'):
                line = raw_line.strip()

                # Detect section header
                if line in section_map:
                    if current_sensor and points:
                        self.sensor_data[current_sensor] = {
                            'points': points, 'C': C, 'D': D, 'R2': R2
                        }
                    current_sensor = section_map[line]
                    points = []
                    C = D = R2 = 0.0
                    continue

                if current_sensor is None:
                    continue

                # Equation line: "Equation: EC = 1.234567 * V_mV + -123.45"
                if line.startswith('Equation:'):
                    m = re.search(
                        r'=\s*([-\d.]+)\s*\*\s*V_mV\s*\+\s*([-\d.]+)', line)
                    if m:
                        C = float(m.group(1))
                        D = float(m.group(2))

                # Point line: "P1: 450.3mV -> 65.0uS/cm"
                elif re.match(r'P\d+:', line):
                    m = re.search(r'P\d+:\s*([\d.]+)mV\s*->\s*([\d.]+)', line)
                    if m:
                        points.append((float(m.group(1)), float(m.group(2))))

                # Quality line: "Quality: R2=0.9987 RMSE=..."
                elif line.startswith('Quality:'):
                    m = re.search(r'R2=([\d.]+)', line)
                    if m:
                        R2 = float(m.group(1))

            # Save the last sensor block
            if current_sensor and points:
                self.sensor_data[current_sensor] = {
                    'points': points, 'C': C, 'D': D, 'R2': R2
                }

            self.plot_current_sensor()

        except Exception as e:
            self.info_text.setText(f"Error parsing EQUATIONS: {e}")
    
    def on_sensor_changed(self, index):
        """Change displayed sensor"""
        sensor_map = {0: 'ECL', 1: 'ECH', 2: 'PH', 3: 'T'}
        self.current_sensor = sensor_map[index]
        self.plot_current_sensor()
    
    def plot_current_sensor(self):
        """Plot calibration for currently selected sensor"""
        if self.current_sensor not in self.sensor_data:
            self.figure.clear()
            self.canvas.draw()
            self.info_text.setText("No calibration data for this sensor")
            return
        
        data = self.sensor_data[self.current_sensor]
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Plot calibration points
        voltages = [p[0] for p in data['points']]
        refs = [p[1] for p in data['points']]
        
        ax.scatter(voltages, refs, s=100, c='#228be6', 
                  label='Calibration Points', zorder=5, edgecolors='black', linewidths=1.5)
        
        # Plot fitted line
        if len(voltages) >= 2:
            v_min, v_max = min(voltages), max(voltages)
            v_range = np.linspace(v_min - (v_max-v_min)*0.1, v_max + (v_max-v_min)*0.1, 100)
            fitted = data['C'] * v_range + data['D']
            ax.plot(v_range, fitted, '--', color='#fa5252', 
                   label=f"y = {data['C']:.6f}x + {data['D']:.2f}", linewidth=2)
        
        # Annotate points
        for v, r in zip(voltages, refs):
            ax.annotate(f'{r:.1f}', xy=(v, r), xytext=(5, 5),
                       textcoords='offset points', fontsize=8, color='#228be6')
        
        # Labels and styling
        sensor_units = {'ECL': 'µS/cm', 'ECH': 'µS/cm', 'PH': 'pH', 'T': '°C'}
        sensor_names = {'ECL': 'EC Low', 'ECH': 'EC High', 'PH': 'pH', 'T': 'Temperature'}
        unit = sensor_units.get(self.current_sensor, '')
        name = sensor_names.get(self.current_sensor, self.current_sensor)
        
        ax.set_xlabel('Voltage (mV)', fontsize=10, fontweight='bold')
        ax.set_ylabel(f'Reference Value ({unit})', fontsize=10, fontweight='bold')
        ax.set_title(f'Calibration: {name}', fontsize=12, fontweight='bold')
        ax.legend(loc='best', fontsize=9, framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        self.canvas.draw()
        
        # Update info text
        self.info_text.setText(
            f"Equation: y = {data['C']:.6f}x + {data['D']:.2f}  |  "
            f"R² = {data['R2']:.4f}  |  "
            f"Points: {len(data['points'])}"
        )

# ============================================================================
# MAIN CALIBRATION WINDOW
# ============================================================================

class CalibrationWindow(QMainWindow):
    """Main calibration GUI window - ENHANCED with new Arduino integration"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Sensor Calibration - Arduino Integration v1.0")
        self.setGeometry(100, 100, 1400, 900)
        
        # State
        self.worker = None
        self.is_connected = False
        self.current_calibration = None
        self._equations_buffer = []   # accumulates lines of EQUATIONS response
        self._in_equations = False    # True while reading EQUATIONS block
        
        # Storage for mode selections
        self.ec_low_mode = 4  # Default 4-point
        
        self.initUI()
        
    def initUI(self):
        """Setup the user interface"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        
        # ====== LEFT PANEL ======
        left_panel = QVBoxLayout()
        
        # Connection controls
        conn_group = QGroupBox("Connection")
        conn_layout = QVBoxLayout(conn_group)
        
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_input = QLineEdit("/dev/ttyAMA0")
        port_layout.addWidget(self.port_input)
        conn_layout.addLayout(port_layout)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        conn_layout.addWidget(self.connect_btn)
        
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet(
            "color: #fa5252; font-weight: bold; padding: 5px; "
            "border: 2px solid #fa5252; border-radius: 3px;"
        )
        self.status_label.setAlignment(Qt.AlignCenter)
        conn_layout.addWidget(self.status_label)
        
        left_panel.addWidget(conn_group)
        
        # Sensor readings
        readings_group = QGroupBox("Current Readings")
        readings_layout = QVBoxLayout(readings_group)
        
        self.ec_reading = QLabel("EC: --- µS/cm")
        self.temp_reading = QLabel("Temp: --- °C")
        self.ph_reading = QLabel("pH: ---")
        
        for label in [self.ec_reading, self.temp_reading, self.ph_reading]:
            label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
            readings_layout.addWidget(label)
        
        left_panel.addWidget(readings_group)
        
        # Quality metrics
        self.quality_widget = QualityWidget()
        left_panel.addWidget(self.quality_widget)
        
        left_panel.addStretch()
        main_layout.addLayout(left_panel, 1)
        
        # ====== MIDDLE PANEL ======
        middle_panel = QVBoxLayout()
        
        # Quick commands
        cmd_group = QGroupBox("Quick Commands")
        cmd_layout = QGridLayout(cmd_group)
        
        quick_commands = [
            ("Status", "STATUS_COMPACT"),
            ("Quality", "QUALITY"),
            ("Equations", "EQUATIONS"),
            ("Diagnostics", "DIAG"),
            ("Save EEPROM", "SAVE"),
            ("Load EEPROM", "LOAD"),
        ]
        
        for i, (text, cmd) in enumerate(quick_commands):
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked, c=cmd: self.send_command(c))
            cmd_layout.addWidget(btn, i // 2, i % 2)
            
        middle_panel.addWidget(cmd_group)
        
        # Calibration tabs
        cal_group = QGroupBox("Calibration")
        cal_layout = QVBoxLayout(cal_group)
        
        self.cal_tabs = QTabWidget()
        
        # Create calibration tabs with enhanced 3-tab structure
        self.create_ec_low_tab()
        self.create_ec_high_tab()
        self.create_ph_tab()
        self.create_temp_tab()
        
        cal_layout.addWidget(self.cal_tabs)
        
        # Calibration status
        self.cal_status = QLabel("Ready")
        self.cal_status.setStyleSheet(
            "color: #228be6; font-weight: bold; font-size: 14px; "
            "padding: 5px; border: 2px solid #228be6; border-radius: 3px;"
        )
        self.cal_status.setAlignment(Qt.AlignCenter)
        cal_layout.addWidget(self.cal_status)
        
        # Repeats
        repeats_layout = QHBoxLayout()
        repeats_layout.addWidget(QLabel("Repeats:"))
        self.repeats_spin = QSpinBox()
        self.repeats_spin.setRange(1, 20)
        self.repeats_spin.setValue(3)
        repeats_layout.addWidget(self.repeats_spin)
        repeats_layout.addStretch()
        cal_layout.addLayout(repeats_layout)
        
        middle_panel.addWidget(cal_group)
        
        # Calibration plot visualization
        self.plot_widget = CalibrationPlotWidget()
        middle_panel.addWidget(self.plot_widget)
        
        main_layout.addLayout(middle_panel, 2)
        
        # ====== RIGHT PANEL ======
        right_panel = QVBoxLayout()
        
        # Profile management
        profile_group = QGroupBox("Profile Management")
        profile_layout = QVBoxLayout(profile_group)
        
        profile_btn_layout = QHBoxLayout()
        
        export_btn = QPushButton("Export Profile")
        export_btn.clicked.connect(self.export_calibration)
        profile_btn_layout.addWidget(export_btn)
        
        import_btn = QPushButton("Import Profile")
        import_btn.clicked.connect(self.import_calibration)
        profile_btn_layout.addWidget(import_btn)
        
        profile_layout.addLayout(profile_btn_layout)
        
        profile_layout.addWidget(QLabel("Recent Profiles:"))
        self.profile_list = QListWidget()
        self.profile_list.setMaximumHeight(100)
        profile_layout.addWidget(self.profile_list)
        
        right_panel.addWidget(profile_group)
        
        # Console
        console_group = QGroupBox("Console")
        console_layout = QVBoxLayout(console_group)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("font-family: monospace; font-size: 10px;")
        console_layout.addWidget(self.console)
        
        # Manual command
        cmd_input_layout = QHBoxLayout()
        cmd_input_layout.addWidget(QLabel("Command:"))
        self.cmd_input = QLineEdit()
        self.cmd_input.returnPressed.connect(self.send_manual_command)
        cmd_input_layout.addWidget(self.cmd_input)
        
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_manual_command)
        cmd_input_layout.addWidget(send_btn)
        
        console_layout.addLayout(cmd_input_layout)
        
        right_panel.addWidget(console_group)
        
        main_layout.addLayout(right_panel, 1)
    
    def create_ec_low_tab(self):
        """Create EC Low calibration tab with 3 sub-tabs (Regular/Force/Set Values)"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        
        # Mode selector at top
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        self.ec_low_mode_combo = QComboBox()
        self.ec_low_mode_combo.addItems(["3-point", "4-point", "5-point"])
        self.ec_low_mode_combo.setCurrentIndex(1)  # Default 4-point
        self.ec_low_mode_combo.currentIndexChanged.connect(self.on_ec_low_mode_changed)
        mode_layout.addWidget(self.ec_low_mode_combo)
        mode_layout.addStretch()
        main_layout.addLayout(mode_layout)
        
        # Create sub-tabs
        sub_tabs = QTabWidget()
        
        # Tab 1: Regular calibration
        regular_tab = QWidget()
        regular_layout = QVBoxLayout(regular_tab)
        regular_layout.addWidget(QLabel("EC Low Range Calibration"))
        
        points = [
            ("L1 (65µS)", "CAL_EC_LOW_1", "EC Low L1"),
            ("L2 (200µS)", "CAL_EC_LOW_2", "EC Low L2"),
            ("L3 (500µS)", "CAL_EC_LOW_3", "EC Low L3"),
            ("L4 (1000µS)", "CAL_EC_LOW_4", "EC Low L4"),
            ("L5 (1413µS)", "CAL_EC_LOW_5", "EC Low L5"),
        ]
        
        for text, cmd, desc in points:
            btn = QPushButton(f"Calibrate {text}")
            btn.clicked.connect(lambda checked, c=cmd, d=desc: self.start_calibration(c, d))
            regular_layout.addWidget(btn)
        
        regular_layout.addStretch()
        sub_tabs.addTab(regular_tab, "Regular")
        
        # Tab 2: Force calibration
        force_tab = self.create_force_tab([
            ("Point 1 (65µS)", "FORCE_EC_LOW_1"),
            ("Point 2 (200µS)", "FORCE_EC_LOW_2"),
            ("Point 3 (500µS)", "FORCE_EC_LOW_3"),
            ("Point 4 (1000µS)", "FORCE_EC_LOW_4"),
            ("Point 5 (1413µS)", "FORCE_EC_LOW_5"),
        ])
        sub_tabs.addTab(force_tab, "Force")
        
        # Tab 3: Set values
        set_tab = self.create_set_values_tab([
            ("Point 1", "SET_EC_LOW_1", "65"),
            ("Point 2", "SET_EC_LOW_2", "200"),
            ("Point 3", "SET_EC_LOW_3", "500"),
            ("Point 4", "SET_EC_LOW_4", "1000"),
            ("Point 5", "SET_EC_LOW_5", "1413"),
        ])
        sub_tabs.addTab(set_tab, "Set Values")
        
        main_layout.addWidget(sub_tabs)
        self.cal_tabs.addTab(tab, "EC Low")
    
    def create_ec_high_tab(self):
        """Create EC High calibration tab with 3 sub-tabs"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        
        # Create sub-tabs
        sub_tabs = QTabWidget()
        
        # Tab 1: Regular calibration
        regular_tab = QWidget()
        regular_layout = QVBoxLayout(regular_tab)
        regular_layout.addWidget(QLabel("EC High Range (2-point)"))
        
        points = [
            ("H1 (1413µS)", "CAL_EC_HIGH_1", "EC High H1"),
            ("H2 (12.88mS)", "CAL_EC_HIGH_2", "EC High H2"),
        ]
        
        for text, cmd, desc in points:
            btn = QPushButton(f"Calibrate {text}")
            btn.clicked.connect(lambda checked, c=cmd, d=desc: self.start_calibration(c, d))
            regular_layout.addWidget(btn)
        
        regular_layout.addStretch()
        sub_tabs.addTab(regular_tab, "Regular")
        
        # Tab 2: Force calibration
        force_tab = self.create_force_tab([
            ("Point 1 (1413µS)", "FORCE_EC_HIGH_1"),
            ("Point 2 (12.88mS)", "FORCE_EC_HIGH_2"),
        ])
        sub_tabs.addTab(force_tab, "Force")
        
        # Tab 3: Set values
        set_tab = self.create_set_values_tab([
            ("Point 1", "SET_EC_HIGH_1", "1413"),
            ("Point 2", "SET_EC_HIGH_2", "12880"),
        ])
        sub_tabs.addTab(set_tab, "Set Values")
        
        main_layout.addWidget(sub_tabs)
        self.cal_tabs.addTab(tab, "EC High")
    
    def create_ph_tab(self):
        """Create pH calibration tab with 3 sub-tabs"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        
        # Create sub-tabs
        sub_tabs = QTabWidget()
        
        # Tab 1: Regular calibration
        regular_tab = QWidget()
        regular_layout = QVBoxLayout(regular_tab)
        regular_layout.addWidget(QLabel("pH Calibration (3-point)"))
        
        points = [
            ("pH 4.0", "CAL_PH_1", "pH 4.0"),
            ("pH 7.0", "CAL_PH_2", "pH 7.0"),
            ("pH 10.0", "CAL_PH_3", "pH 10.0"),
        ]
        
        for text, cmd, desc in points:
            btn = QPushButton(f"Calibrate {text}")
            btn.clicked.connect(lambda checked, c=cmd, d=desc: self.start_calibration(c, d))
            regular_layout.addWidget(btn)
        
        regular_layout.addStretch()
        sub_tabs.addTab(regular_tab, "Regular")
        
        # Tab 2: Force calibration
        force_tab = self.create_force_tab([
            ("Point 1 (pH 4.0)", "FORCE_PH_1"),
            ("Point 2 (pH 7.0)", "FORCE_PH_2"),
            ("Point 3 (pH 10.0)", "FORCE_PH_3"),
        ])
        sub_tabs.addTab(force_tab, "Force")
        
        # Tab 3: Set values
        set_tab = self.create_set_values_tab([
            ("Point 1", "SET_PH_1", "4.0"),
            ("Point 2", "SET_PH_2", "7.0"),
            ("Point 3", "SET_PH_3", "10.0"),
        ])
        sub_tabs.addTab(set_tab, "Set Values")
        
        main_layout.addWidget(sub_tabs)
        self.cal_tabs.addTab(tab, "pH")
    
    def create_temp_tab(self):
        """Create temperature calibration tab with 3 sub-tabs"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        
        # Create sub-tabs
        sub_tabs = QTabWidget()
        
        # Tab 1: Regular calibration
        regular_tab = QWidget()
        regular_layout = QVBoxLayout(regular_tab)
        regular_layout.addWidget(QLabel("Temperature Calibration (3-point)"))
        
        points = [
            ("25°C", "CAL_TEMP_1", "Temp 25°C"),
            ("32°C", "CAL_TEMP_2", "Temp 32°C"),
            ("40°C", "CAL_TEMP_3", "Temp 40°C"),
        ]
        
        for text, cmd, desc in points:
            btn = QPushButton(f"Calibrate {text}")
            btn.clicked.connect(lambda checked, c=cmd, d=desc: self.start_calibration(c, d))
            regular_layout.addWidget(btn)
        
        regular_layout.addStretch()
        sub_tabs.addTab(regular_tab, "Regular")
        
        # Tab 2: Force calibration
        force_tab = self.create_force_tab([
            ("Point 1 (25°C)", "FORCE_TEMP_1"),
            ("Point 2 (32°C)", "FORCE_TEMP_2"),
            ("Point 3 (40°C)", "FORCE_TEMP_3"),
        ])
        sub_tabs.addTab(force_tab, "Force")
        
        # Tab 3: Set values
        set_tab = self.create_set_values_tab([
            ("Point 1", "SET_TEMP_1", "25"),
            ("Point 2", "SET_TEMP_2", "32"),
            ("Point 3", "SET_TEMP_3", "40"),
        ])
        sub_tabs.addTab(set_tab, "Set Values")
        
        main_layout.addWidget(sub_tabs)
        self.cal_tabs.addTab(tab, "Temperature")
    
    def create_force_tab(self, points):
        """Generic force calibration tab creator"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        layout.addWidget(QLabel("Force Calibration (Manual Voltage Entry)"))
        
        for text, cmd_base in points:
            row = QHBoxLayout()
            label = QLabel(text)
            label.setMinimumWidth(120)
            row.addWidget(label)
            
            input_field = QLineEdit()
            input_field.setPlaceholderText("Voltage (mV)")
            input_field.setMaximumWidth(100)
            row.addWidget(input_field)
            
            btn = QPushButton("Force")
            btn.setMaximumWidth(80)
            btn.clicked.connect(lambda checked, c=cmd_base, i=input_field: 
                              self.send_force_calibration(c, i))
            row.addWidget(btn)
            row.addStretch()
            
            layout.addLayout(row)
        
        layout.addStretch()
        return tab
    
    def create_set_values_tab(self, points):
        """Generic set values tab creator"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        layout.addWidget(QLabel("Set Reference Values"))
        
        for text, cmd_base, default in points:
            row = QHBoxLayout()
            label = QLabel(text)
            label.setMinimumWidth(120)
            row.addWidget(label)
            
            input_field = QLineEdit()
            input_field.setText(default)
            input_field.setPlaceholderText("Reference value")
            input_field.setMaximumWidth(100)
            row.addWidget(input_field)
            
            btn = QPushButton("Set")
            btn.setMaximumWidth(80)
            btn.clicked.connect(lambda checked, c=cmd_base, i=input_field: 
                              self.send_set_value(c, i))
            row.addWidget(btn)
            row.addStretch()
            
            layout.addLayout(row)
        
        layout.addStretch()
        return tab
    
    def on_ec_low_mode_changed(self, index):
        """Handle EC Low mode change"""
        mode_num = index + 3  # 0→3, 1→4, 2→5
        self.ec_low_mode = mode_num
        self.send_command(f"CALMODE_EC_LOW_{mode_num}")
        self.log(f"EC Low mode set to {mode_num}-point")
    
    def send_force_calibration(self, cmd_base, input_field):
        """Send force calibration command with voltage"""
        try:
            voltage = float(input_field.text())
            self.send_command(f"{cmd_base} {voltage}")
            self.log(f"Force calibration: {cmd_base} {voltage} mV")
        except ValueError:
            self.log("ERROR: Invalid voltage value")
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid voltage value (mV)")
    
    def send_set_value(self, cmd_base, input_field):
        """Send set value command"""
        try:
            value = float(input_field.text())
            self.send_command(f"{cmd_base} {value}")
            self.log(f"Set reference: {cmd_base} {value}")
        except ValueError:
            self.log("ERROR: Invalid reference value")
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid reference value")
    
    def toggle_connection(self):
        """Toggle serial connection"""
        if self.is_connected:
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        """Connect to Arduino"""
        port = self.port_input.text().strip()
        
        try:
            self.worker = SerialWorker(port)
            self.worker.dataReceived.connect(self.handle_data)
            self.worker.connectionStatus.connect(self.update_connection_status)
            self.worker.errorOccurred.connect(self.log)
            self.worker.start()
            
            self.is_connected = True
            self.connect_btn.setText("Disconnect")
            self.log(f"Connecting to {port}...")
            
        except Exception as e:
            self.log(f"Connection error: {e}")
            QMessageBox.critical(self, "Connection Error", str(e))
    
    def disconnect(self):
        """Disconnect from Arduino"""
        if self.worker:
            self.worker.stop()
            self.worker.wait()
            self.worker = None
        
        self.is_connected = False
        self.connect_btn.setText("Connect")
        self.status_label.setText("Disconnected")
        self.status_label.setStyleSheet(
            "color: #fa5252; font-weight: bold; padding: 5px; "
            "border: 2px solid #fa5252; border-radius: 3px;"
        )
        self.log("Disconnected")
    
    def update_connection_status(self, connected, message):
        """Update connection status display"""
        if connected:
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet(
                "color: #51cf66; font-weight: bold; padding: 5px; "
                "border: 2px solid #51cf66; border-radius: 3px;"
            )
        else:
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet(
                "color: #fa5252; font-weight: bold; padding: 5px; "
                "border: 2px solid #fa5252; border-radius: 3px;"
            )
        self.log(message)
    
    def handle_data(self, data):
        """Handle incoming serial data from Arduino"""
        self.log(f"← {data}")

        # ── EQUATIONS multi-line buffering ───────────────────────────────────
        # The EQUATIONS command outputs many lines.  We collect them from the
        # opening header "CALIBRATION EQUATIONS" until we see the blank line
        # after the last sensor block (Arduino prints Serial.println() at end
        # of each block, and the command ends there).
        # We detect the end by a blank line AFTER we've already seen all 4
        # section headers, or by the next unrelated command starting.

        if data.strip() == "CALIBRATION EQUATIONS":
            self._in_equations = True
            self._equations_buffer = [data]
            return

        if self._in_equations:
            # Collect EQUATIONS multi-line output until we detect a logical end.
            self._equations_buffer.append(data)
            joined = '\n'.join(self._equations_buffer)

            # If we've received the TEMPERATURE section header and then the
            # Quality line for that section, assume the EQUATIONS block is complete
            # and flush the buffer into the plot parser.
            if '--- TEMPERATURE ---' in joined and data.strip().startswith('Quality:'):
                self._in_equations = False
                try:
                    self.plot_widget.update_from_equations(joined)
                except Exception as e:
                    self.log(f"Error updating plot from EQUATIONS: {e}")
                self._equations_buffer = []
                return

            # Fallback: if Arduino emits a blank line after the block, flush.
            if data.strip() == "" and '---' in joined:
                self._in_equations = False
                try:
                    self.plot_widget.update_from_equations(joined)
                except Exception as e:
                    self.log(f"Error updating plot from EQUATIONS: {e}")
                self._equations_buffer = []
                return

            # Otherwise keep collecting lines
            return
        # ─────────────────────────────────────────────────────────────────────

        # Parse STATUS_COMPACT
        if data.startswith("STATUS_COMPACT:"):
            self.parse_status_compact(data)

        # Parse sensor readings from READ command
        elif "EC:" in data and ("T:" in data or "Temp:" in data):
            self.parse_sensor_reading(data)

        # Parse quality metrics / calibration complete lines
        elif "EC_LOW:" in data or "EC_HIGH:" in data or "PH:" in data or "TEMP:" in data:
            self.quality_widget.update_from_data(data)
            if "R2=" in data:
                self.cal_status.setText("Calibration Complete!")
                # Auto-refresh plot after calibration
                #QTimer.singleShot(800, self.plot_widget.request_plot_update)
    
    def parse_status_compact(self, data):
        """
        Parse STATUS_COMPACT response
        Format: STATUS_COMPACT:ECL:1,4,0.9987|ECH:0,0,0.0000|PH:1,3,0.9995|T:1,3,0.9998
        """
        try:
            status_str = data.split(':', 1)[1]
            sensors = status_str.split('|')
            
            for sensor_data in sensors:
                parts = sensor_data.split(':')
                if len(parts) >= 2:
                    sensor = parts[0]
                    values = parts[1].split(',')
                    if len(values) >= 3:
                        is_cal = values[0]
                        points = values[1]
                        r2 = values[2]
                        
                        status_msg = "CALIBRATED" if is_cal == "1" else "NOT CALIBRATED"
                        self.log(f"{sensor}: {status_msg} ({points} points, R²={r2})")
        except Exception as e:
            self.log(f"Error parsing STATUS_COMPACT: {e}")
    
    def parse_sensor_reading(self, data):
        """Parse sensor readings from READ command"""
        try:
            # Try compact format first: EC:1205.3 T:25.2 pH:6.85
            ec_match = re.search(r'EC:\s*([\d.]+|N/A)', data)
            temp_match = re.search(r'(?:T|Temp):\s*([\d.]+)', data)
            ph_match = re.search(r'pH:\s*([\d.]+|N/A)', data)
            
            if ec_match:
                ec_val = ec_match.group(1)
                if ec_val != "N/A":
                    self.ec_reading.setText(f"EC: {ec_val} µS/cm")
                else:
                    self.ec_reading.setText("EC: NOT CALIBRATED")
            
            if temp_match:
                temp_val = temp_match.group(1)
                self.temp_reading.setText(f"Temp: {temp_val} °C")
            
            if ph_match:
                ph_val = ph_match.group(1)
                if ph_val != "N/A":
                    self.ph_reading.setText(f"pH: {ph_val}")
                else:
                    self.ph_reading.setText("pH: NOT CALIBRATED")
                    
        except Exception as e:
            self.log(f"Error parsing sensor reading: {e}")
    
    def start_calibration(self, cmd, desc):
        """Start a calibration sequence"""
        repeats = self.repeats_spin.value()
        self.current_calibration = desc
        self.cal_status.setText(f"Calibrating {desc}... (1/{repeats})")
        
        # Send calibration command
        for i in range(repeats):
            QTimer.singleShot(i * 1000, lambda c=cmd: self.send_command(c))
        
        # Auto-request plot data after calibration completes
        #QTimer.singleShot((repeats + 1) * 1000, self.plot_widget.request_plot_update)
    
    def send_command(self, cmd):
        """Send command to Arduino"""
        if self.worker:
            self.worker.send_command(cmd)
            self.log(f"→ {cmd}")
        else:
            self.log("ERROR: Not connected")
    
    def send_manual_command(self):
        """Send manual command from input field"""
        cmd = self.cmd_input.text().strip()
        if cmd:
            self.send_command(cmd)
            self.cmd_input.clear()
    
    def log(self, message):
        """Log message to console"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console.append(f"[{timestamp}] {message}")
        # Auto-scroll to bottom
        self.console.verticalScrollBar().setValue(
            self.console.verticalScrollBar().maximum()
        )
    
    def export_calibration(self):
        """Export calibration profile to file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Calibration", "", "JSON Files (*.json)"
        )
        if filename:
            try:
                # Request current calibration data
                self.send_command("EQUATIONS")
                self.send_command("STATUS_COMPACT")
                
                # In a real implementation, we'd wait for responses and save them
                # For now, just acknowledge
                self.log(f"Calibration data requested for export to {filename}")
                QMessageBox.information(self, "Export", "Calibration export initiated")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))
    
    def import_calibration(self):
        """Import calibration profile from file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Calibration", "", "JSON Files (*.json)"
        )
        if filename:
            try:
                # In a real implementation, we'd parse the file and send SET commands
                self.log(f"Import calibration from {filename}")
                QMessageBox.information(self, "Import", "Calibration import feature in development")
            except Exception as e:
                QMessageBox.critical(self, "Import Error", str(e))
    
    def closeEvent(self, event):
        """Handle window close"""
        if self.is_connected:
            self.disconnect()
        event.accept()

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Custom color palette (optional - keeping original clean look)
    palette = app.palette()
    app.setPalette(palette)
    
    window = CalibrationWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()




