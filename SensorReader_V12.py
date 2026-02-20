#!/usr/bin/env python3
"""
Multi-Sensor Reader - UPDATED FOR NEW ARDUINO SYSTEM
Real-time monitoring with integrated advanced analysis

UPDATED FOR: Arduino Multi-Sensor Calibration System v1.0
- Compatible with new READ command format
- Handles calibrated and uncalibrated sensors
- Supports both compact and verbose output formats

TIER 1 + SEGMENT 1 FEATURES (Built-in):
  ✓ Feature 1-3: CSV/Excel/JSON Export
  ✓ Feature 4: PDF Report Generation
  ✓ Feature 5: Session Save/Load
  ✓ Feature 6: Background CSV Logging
  ✓ Periodic READ command (user-adjustable interval, default 1s)
  ✓ Real-time plotting and statistics

ANALYSIS MODULE 2A FEATURES (On-Demand):
  ✓ Feature 7: Rolling Statistics with CV
  ✓ Feature 8: Data Smoothing (MA, Savitzky-Golay, Median)
  ✓ Feature 9: Correlation Matrix
  ✓ Feature 10: FFT Frequency Analysis

ANALYSIS MODULE 2B FEATURES (On-Demand):
  ✓ Feature 11: Trend Detection with Statistical Significance
  ✓ Feature 12: Anomaly Detection (Z-Score)
  ✓ Feature 13: [Reserved for future expansion]
  ✓ Feature 14: Drift Forecasting (24-hour prediction)

Usage: python SensorReader_V9_NEW.py
Requires: pip install PyQt5 pyserial matplotlib pandas numpy openpyxl reportlab scipy scikit-learn
         SensorAnalysis_Module_2A.py and SensorAnalysis_Module_2B.py must be in same directory
"""

import sys
import os
import csv
import time
import json
import pickle
from datetime import datetime, timedelta
from collections import deque
from pathlib import Path

import numpy as np
from scipy import signal, stats
from scipy.fft import fft, fftfreq
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import serial

# Plotting
import matplotlib
matplotlib.use('Qt5Agg')
# Suppress libpng iCCP warning (known incorrect sRGB profile)
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
matplotlib.rcParams['figure.facecolor'] = 'white'
matplotlib.rcParams['savefig.facecolor'] = 'white'
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Data handling
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Machine Learning (for drift forecasting)
try:
    from sklearn.linear_model import LinearRegression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Analysis Modules (Module 2A & 2B - Features 7-14)
try:
    from SensorAnalysis_Module_2A import (
        AnalysisTab2A, RollingStatsAnalyzer, DataSmoother,
        CorrelationAnalyzer, FFTAnalyzer
    )
    from SensorAnalysis_Module_2B import (
        AnalysisTab2B, TrendDetector, SimpleAnomalyDetector,
        DriftForecaster
    )
    ANALYSIS_MODULES_AVAILABLE = True
except ImportError:
    ANALYSIS_MODULES_AVAILABLE = False
    AnalysisTab2A = None
    AnalysisTab2B = None

# ============================================================================
# CONFIGURATION
# ============================================================================

class SensorConfig:
    """Enhanced configuration with validation thresholds"""
    
    def __init__(self):
        # Serial
        self.uart_port = '/dev/ttyAMA0'
        self.uart_baudrate = 115200
        self.uart_timeout = 1.0
        
        # Measurement
        self.measurement_interval = 3.0
        self.max_plot_points = 500
        
        # Validation ranges
        self.temp_min = -10.0
        self.temp_max = 60.0
        self.ec_min = 0.0
        self.ec_max = 20000.0
        self.ph_min = 0.0
        self.ph_max = 14.0
        
        # Warning thresholds
        self.temp_warn_low = 15.0
        self.temp_warn_high = 35.0
        self.ec_warn_low = 50.0
        self.ec_warn_high = 15000.0
        self.ph_warn_low = 5.0
        self.ph_warn_high = 9.0
        
        # Statistics
        self.rolling_avg_points = 10
        
        # NEW: Background logging
        self.auto_log_enabled = False
        self.log_directory = "sensor_logs"
        
    def save(self, filename='sensor_config.json'):
        """Save configuration"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.__dict__, f, indent=2)
        except Exception as e:
            print(f"Config save error: {e}")
            
    def load(self, filename='sensor_config.json'):
        """Load configuration"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    data = json.load(f)
                    self.__dict__.update(data)
        except Exception as e:
            print(f"Config load error: {e}")

# ============================================================================
# SERIAL WORKER (FROM TIER 1 - UNCHANGED)
# ============================================================================

class SerialWorker(QThread):
    dataReceived = pyqtSignal(str)
    connectionStatus = pyqtSignal(bool, str)
    errorOccurred = pyqtSignal(str)
    
    def __init__(self, port, baudrate=115200):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.running = True
        self.serial_port = None
        self.reconnect_delay = 1
        
    def connect(self):
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.serial_port = serial.Serial(self.port, self.baudrate, timeout=1.0)
            time.sleep(0.5)
            self.connectionStatus.emit(True, "Connected")
            self.reconnect_delay = 1
            return True
        except Exception as e:
            self.connectionStatus.emit(False, f"Failed: {e}")
            return False
            
    def run(self):
        while self.running:
            if not self.serial_port or not self.serial_port.is_open:
                if self.connect():
                    continue
                time.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, 30)
                continue
            try:
                if self.serial_port.in_waiting:
                    line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self.dataReceived.emit(line)
                self.msleep(50)
            except Exception as e:
                self.errorOccurred.emit(str(e))
                if self.serial_port:
                    self.serial_port.close()
                self.connectionStatus.emit(False, "Lost")
                
    def send_command(self, cmd):
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.write(f"{cmd}\n".encode())
                return True
        except:
            pass
        return False
        
    def stop(self):
        self.running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()

# ============================================================================
# FEATURE 1-3: DATA EXPORTER (CSV/EXCEL/JSON)
# ============================================================================

class DataExporter:
    """Export collected data in multiple formats"""
    
    def __init__(self):
        self.exports_dir = "sensor_exports"
        os.makedirs(self.exports_dir, exist_ok=True)
        
    def export_to_csv(self, data_list):
        """Export to CSV"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.exports_dir, f"sensor_data_{timestamp}.csv")
        
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Elapsed (s)', 'EC (µS/cm)', 'Temperature (°C)', 'pH'])
                for item in data_list:
                    writer.writerow([
                        item.get('timestamp', ''),
                        item.get('elapsed', 0),
                        item.get('ec', 0),
                        item.get('temp', 0),
                        item.get('ph', 0)
                    ])
            return filename, None
        except Exception as e:
            return None, str(e)
            
    def export_to_excel(self, data_list):
        """Export to Excel with formatting"""
        if not PANDAS_AVAILABLE:
            return None, "pandas not installed"
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.exports_dir, f"sensor_data_{timestamp}.xlsx")
        
        try:
            df = pd.DataFrame(data_list)
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Sensor Data', index=False)
            return filename, None
        except Exception as e:
            return None, str(e)
            
    def export_to_json(self, data_list):
        """Export to JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.exports_dir, f"sensor_data_{timestamp}.json")
        
        try:
            with open(filename, 'w') as f:
                json.dump(data_list, f, indent=2, default=str)
            return filename, None
        except Exception as e:
            return None, str(e)

# ============================================================================
# FEATURE 4: PDF REPORT GENERATOR
# ============================================================================

class ReportGenerator:
    """Generate PDF reports from collected data"""
    
    def __init__(self):
        self.reports_dir = "sensor_reports"
        os.makedirs(self.reports_dir, exist_ok=True)
        
    def generate_report(self, statistics, plot_image=None):
        """Generate PDF report"""
        if not REPORTLAB_AVAILABLE:
            return None, "reportlab not installed"
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.reports_dir, f"sensor_report_{timestamp}.pdf")
        
        try:
            doc = SimpleDocTemplate(filename, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            story.append(Paragraph("Sensor Monitoring Report", styles['Title']))
            story.append(Spacer(1, 0.3*inch))
            
            # Metadata
            meta_data = [
                ['Generated:', datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                ['Duration:', f"{statistics.get('duration', 0):.1f} seconds"],
                ['Data Points:', str(statistics.get('count', 0))],
            ]
            meta_table = Table(meta_data)
            meta_table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 1, colors.grey),
                ('BACKGROUND', (0,0), (0,-1), colors.lightgrey)
            ]))
            story.append(meta_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Statistics
            story.append(Paragraph("Statistics Summary", styles['Heading2']))
            stats_data = [
                ['Parameter', 'Mean', 'Std Dev', 'Min', 'Max'],
                ['EC (µS/cm)', 
                 f"{statistics.get('ec_mean', 0):.1f}",
                 f"{statistics.get('ec_std', 0):.2f}",
                 f"{statistics.get('ec_min', 0):.1f}",
                 f"{statistics.get('ec_max', 0):.1f}"],
                ['Temperature (°C)',
                 f"{statistics.get('temp_mean', 0):.2f}",
                 f"{statistics.get('temp_std', 0):.2f}",
                 f"{statistics.get('temp_min', 0):.2f}",
                 f"{statistics.get('temp_max', 0):.2f}"],
                ['pH',
                 f"{statistics.get('ph_mean', 0):.3f}",
                 f"{statistics.get('ph_std', 0):.3f}",
                 f"{statistics.get('ph_min', 0):.3f}",
                 f"{statistics.get('ph_max', 0):.3f}"],
            ]
            stats_table = Table(stats_data)
            stats_table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 1, colors.grey),
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#228be6')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke)
            ]))
            story.append(stats_table)
            
            # Add plot if provided
            if plot_image and os.path.exists(plot_image):
                story.append(Spacer(1, 0.3*inch))
                story.append(Paragraph("Data Visualization", styles['Heading2']))
                from reportlab.platypus import Image as RLImage
                img = RLImage(plot_image, width=6*inch, height=4*inch)
                story.append(img)
                
            doc.build(story)
            return filename, None
        except Exception as e:
            return None, str(e)

# ============================================================================
# FEATURE 5: SESSION MANAGER (SAVE/LOAD)
# ============================================================================

class SessionManager:
    """Manage monitoring sessions"""
    
    def __init__(self):
        self.sessions_dir = "sensor_sessions"
        os.makedirs(self.sessions_dir, exist_ok=True)
        
    def save_session(self, data_list, name=None):
        """Save current session"""
        if not name:
            name = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        filename = os.path.join(self.sessions_dir, f"{name}.pkl")
        
        try:
            session_data = {
                'name': name,
                'timestamp': datetime.now(),
                'data': data_list
            }
            with open(filename, 'wb') as f:
                pickle.dump(session_data, f)
            return filename, None
        except Exception as e:
            return None, str(e)
            
    def load_session(self, filename):
        """Load session"""
        try:
            with open(filename, 'rb') as f:
                session = pickle.load(f)
            return session, None
        except Exception as e:
            return None, str(e)
            
    def list_sessions(self):
        """List available sessions"""
        try:
            sessions = []
            for file in Path(self.sessions_dir).glob("*.pkl"):
                sessions.append(str(file))
            return sessions
        except:
            return []

# ============================================================================
# FEATURE 6: BACKGROUND CSV LOGGER
# ============================================================================

class BackgroundLogger:
    """Continuously log data to CSV"""
    
    def __init__(self, config):
        self.config = config
        self.log_file = None
        self.csv_writer = None
        self.is_logging = False
        
    def start_logging(self):
        """Start background logging"""
        if self.is_logging:
            return True, "Already logging"
            
        try:
            os.makedirs(self.config.log_directory, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.config.log_directory, f"log_{timestamp}.csv")
            
            self.log_file = open(filename, 'w', newline='')
            self.csv_writer = csv.writer(self.log_file)
            self.csv_writer.writerow(['Timestamp', 'Elapsed (s)', 'EC (µS/cm)', 'Temperature (°C)', 'pH'])
            self.log_file.flush()
            
            self.is_logging = True
            return True, f"Logging to: {filename}"
        except Exception as e:
            return False, str(e)
            
    def log_data(self, elapsed, ec, temp, ph):
        """Log a data point"""
        if not self.is_logging or not self.csv_writer:
            return
            
        try:
            self.csv_writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                elapsed,
                ec,
                temp,
                ph
            ])
            self.log_file.flush()
        except:
            pass
            
    def stop_logging(self):
        """Stop logging"""
        if self.log_file:
            self.log_file.close()
        self.is_logging = False
        return "Logging stopped"

# ============================================================================
# HEALTH MONITORING WIDGET (FROM TIER 1 - UNCHANGED)
# ============================================================================

class HealthMonitorWidget(QGroupBox):
    """Widget to display system health"""
    
    def __init__(self):
        super().__init__("System Health")
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        self.health_indicator = QLabel("●")
        self.health_indicator.setStyleSheet("font-size: 48px; color: gray;")
        self.health_indicator.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.health_indicator)
        
        self.health_status = QLabel("Status: Unknown")
        self.health_status.setAlignment(Qt.AlignCenter)
        self.health_status.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.health_status)
        
        layout.addWidget(QLabel(""))
        
        self.cal_age = QLabel("Cal Age: ---")
        self.drift_status = QLabel("Drift: ---")
        self.temp_coeff = QLabel("Temp Coeff: ---")
        
        for label in [self.cal_age, self.drift_status, self.temp_coeff]:
            label.setStyleSheet("padding: 3px; font-family: monospace; font-size: 10px;")
            layout.addWidget(label)
            
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.request_refresh)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
        self.setLayout(layout)
        
    def request_refresh(self):
        parent = self.parent()
        while parent and not hasattr(parent, 'send_command'):
            parent = parent.parent()
        if parent:
            parent.send_command("DIAG")
            
    def update_health(self, data):
        """Parse maintenance data"""
        import re
        
        if "Cal age:" in data:
            age_match = re.search(r'(\d+)\s*d', data)
            if age_match:
                days = int(age_match.group(1))
                self.cal_age.setText(f"Cal Age: {days}d")
                if days > 30:
                    self.cal_age.setStyleSheet("color: red; font-weight: bold; font-family: monospace;")
                elif days > 21:
                    self.cal_age.setStyleSheet("color: orange; font-family: monospace;")
                else:
                    self.cal_age.setStyleSheet("color: green; font-family: monospace;")
                    
        if "Drift:" in data:
            if "Stable" in data:
                self.drift_status.setText("Drift: Stable ✓")
                self.drift_status.setStyleSheet("color: green; font-family: monospace;")
            elif "DRIFTING" in data:
                self.drift_status.setText("Drift: Warning ⚠")
                self.drift_status.setStyleSheet("color: red; font-weight: bold; font-family: monospace;")
                
        if "System healthy" in data:
            self.health_indicator.setStyleSheet("font-size: 48px; color: green;")
            self.health_status.setText("Status: Healthy ✓")
        elif "ACTION" in data:
            self.health_indicator.setStyleSheet("font-size: 48px; color: red;")
            self.health_status.setText("Status: Action Required")

# ============================================================================
# ENHANCED PLOT WIDGET (FROM TIER 1 + PLOT EXPORT)
# ============================================================================

class EnhancedPlotWidget(QWidget):
    """Enhanced plot with export capability"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.time_data = deque(maxlen=500)
        self.ec_data = deque(maxlen=500)
        self.temp_data = deque(maxlen=500)
        self.ph_data = deque(maxlen=500)
        
        self.show_ec = True
        self.show_temp = True
        self.show_ph = True
        
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # Controls
        controls = QHBoxLayout()
        
        self.ec_check = QCheckBox("EC")
        self.ec_check.setChecked(True)
        self.ec_check.toggled.connect(self.update_plot)
        controls.addWidget(self.ec_check)
        
        self.temp_check = QCheckBox("Temperature")
        self.temp_check.setChecked(True)
        self.temp_check.toggled.connect(self.update_plot)
        controls.addWidget(self.temp_check)
        
        self.ph_check = QCheckBox("pH")
        self.ph_check.setChecked(True)
        self.ph_check.toggled.connect(self.update_plot)
        controls.addWidget(self.ph_check)
        
        controls.addWidget(QLabel("|"))
        
        grid_check = QCheckBox("Grid")
        grid_check.setChecked(True)
        grid_check.toggled.connect(self.update_plot)
        controls.addWidget(grid_check)
        self.show_grid = True
        grid_check.toggled.connect(lambda c: setattr(self, 'show_grid', c))
        
        controls.addStretch()
        
        # NEW: Export plot button
        export_btn = QPushButton("Export Plot")
        export_btn.clicked.connect(self.export_plot)
        controls.addWidget(export_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_data)
        controls.addWidget(clear_btn)
        
        layout.addLayout(controls)
        self.setLayout(layout)
        
    def add_data(self, timestamp, ec, temp, ph):
        """Add data point"""
        self.time_data.append(timestamp)
        self.ec_data.append(ec)
        self.temp_data.append(temp)
        self.ph_data.append(ph)
        self.update_plot()
        
    def update_plot(self):
        """Update plot"""
        self.figure.clear()
        
        if len(self.time_data) == 0:
            self.canvas.draw()
            return
            
        num_plots = sum([self.ec_check.isChecked(), 
                        self.temp_check.isChecked(), 
                        self.ph_check.isChecked()])
        
        if num_plots == 0:
            self.canvas.draw()
            return
            
        plot_idx = 1
        times = list(self.time_data)
        
        if self.ec_check.isChecked():
            ax = self.figure.add_subplot(num_plots, 1, plot_idx)
            ax.plot(times, list(self.ec_data), 'o-', color='#228be6', linewidth=2, markersize=3)
            ax.set_ylabel('EC (µS/cm)', fontweight='bold')
            if self.show_grid:
                ax.grid(True, alpha=0.3)
            plot_idx += 1
            
        if self.temp_check.isChecked():
            ax = self.figure.add_subplot(num_plots, 1, plot_idx)
            ax.plot(times, list(self.temp_data), 'o-', color='#fa5252', linewidth=2, markersize=3)
            ax.set_ylabel('Temperature (°C)', fontweight='bold')
            if self.show_grid:
                ax.grid(True, alpha=0.3)
            plot_idx += 1
            
        if self.ph_check.isChecked():
            ax = self.figure.add_subplot(num_plots, 1, plot_idx)
            ax.plot(times, list(self.ph_data), 'o-', color='#51cf66', linewidth=2, markersize=3)
            ax.set_ylabel('pH', fontweight='bold')
            ax.set_xlabel('Time (s)', fontweight='bold')
            if self.show_grid:
                ax.grid(True, alpha=0.3)
                
        self.figure.tight_layout()
        self.canvas.draw()
        
    def export_plot(self):
        """Export plot to file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Plot",
            f"plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            "PNG Files (*.png);;PDF Files (*.pdf)"
        )
        
        if filename:
            self.figure.savefig(filename, dpi=300, bbox_inches='tight', pil_kwargs={'optimize': False})
            QMessageBox.information(self, "Success", f"Plot exported to:\n{filename}")
            
    def get_temp_plot_file(self):
        """Get temporary plot file for reports"""
        temp_file = f"temp_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        self.figure.savefig(temp_file, dpi=200, bbox_inches='tight', pil_kwargs={'optimize': False})
        return temp_file
        
    def clear_data(self):
        """Clear all data"""
        self.time_data.clear()
        self.ec_data.clear()
        self.temp_data.clear()
        self.ph_data.clear()
        self.update_plot()

# ============================================================================
# STATISTICS WIDGET (FROM TIER 1 - UNCHANGED)
# ============================================================================

class StatisticsWidget(QGroupBox):
    """Display statistics"""
    
    def __init__(self):
        super().__init__("Statistics")
        self.initUI()
        
        self.ec_history = deque(maxlen=500)
        self.temp_history = deque(maxlen=500)
        self.ph_history = deque(maxlen=500)
        
    def initUI(self):
        layout = QVBoxLayout()
        
        self.stats_table = QTableWidget(3, 6)
        self.stats_table.setHorizontalHeaderLabels([
            'Sensor', 'Current', 'Mean', 'Std Dev', 'Min', 'Max'
        ])
        self.stats_table.setVerticalHeaderLabels(['EC', 'Temp', 'pH'])
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.stats_table.setMaximumHeight(150)
        
        layout.addWidget(self.stats_table)
        self.setLayout(layout)
        
    def update_statistics(self, ec, temp, ph):
        """Update statistics"""
        self.ec_history.append(ec)
        self.temp_history.append(temp)
        self.ph_history.append(ph)
        
        self._update_row(0, ec, self.ec_history, "µS/cm")
        self._update_row(1, temp, self.temp_history, "°C")
        self._update_row(2, ph, self.ph_history, "")
        
    def _update_row(self, row, current, history, unit):
        """Update table row"""
        if len(history) == 0:
            return
            
        data_array = np.array(list(history))
        
        self.stats_table.setItem(row, 1, QTableWidgetItem(f"{current:.2f} {unit}"))
        
        mean = np.mean(data_array)
        self.stats_table.setItem(row, 2, QTableWidgetItem(f"{mean:.2f} {unit}"))
        
        std = np.std(data_array)
        self.stats_table.setItem(row, 3, QTableWidgetItem(f"{std:.2f} {unit}"))
        
        min_val = np.min(data_array)
        self.stats_table.setItem(row, 4, QTableWidgetItem(f"{min_val:.2f} {unit}"))
        
        max_val = np.max(data_array)
        self.stats_table.setItem(row, 5, QTableWidgetItem(f"{max_val:.2f} {unit}"))
        
    def get_statistics_dict(self):
        """Get statistics as dictionary for reports"""
        stats = {}
        if len(self.ec_history) > 0:
            ec_data = np.array(list(self.ec_history))
            temp_data = np.array(list(self.temp_history))
            ph_data = np.array(list(self.ph_history))
            
            stats = {
                'count': len(self.ec_history),
                'duration': self.ec_history[-1] if len(self.ec_history) > 0 else 0,
                'ec_mean': np.mean(ec_data),
                'ec_std': np.std(ec_data),
                'ec_min': np.min(ec_data),
                'ec_max': np.max(ec_data),
                'temp_mean': np.mean(temp_data),
                'temp_std': np.std(temp_data),
                'temp_min': np.min(temp_data),
                'temp_max': np.max(temp_data),
                'ph_mean': np.mean(ph_data),
                'ph_std': np.std(ph_data),
                'ph_min': np.min(ph_data),
                'ph_max': np.max(ph_data),
            }
        return stats

# ============================================================================
# MAIN GUI WITH SEGMENT 1 FEATURES
# ============================================================================

class SensorReaderSegment1(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sensor Reader - TIER 1 + SEGMENT 1 (Features 1-6)")
        self.setGeometry(50, 50, 1600, 900)
        
        # Configuration
        self.config = SensorConfig()
        self.config.load()
        
        # Serial worker
        self.worker = None
        self.is_connected = False
        
        # NEW: Segment 1 components
        self.data_exporter = DataExporter()
        self.report_generator = ReportGenerator()
        self.session_manager = SessionManager()
        self.background_logger = BackgroundLogger(self.config)
        
        # Data collection for export/session
        self.collected_data = []

        # Measurement averaging buffer
        self._avg_buffer = []   # accumulates raw readings until avg_spin count reached
        self._avg_count = 1     # mirrors avg_spin value, updated via on_avg_changed()
        
        # Timers
        self.measurement_timer = QTimer()
        self.measurement_timer.timeout.connect(self.request_measurement)
        
        self.start_time = time.time()
        
        self.setupUI()
        
    def setupUI(self):
        """Setup UI with tabbed interface for monitoring and analysis"""
        # Create main widget and layout
        central = QWidget()
        main_layout = QHBoxLayout(central)
        
        # Wrap central widget in scroll area for scrolling functionality
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(central)
        self.setCentralWidget(scroll_area)
        
        # Left panel
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)
        
        # Middle panel - Tabbed interface with Monitoring + Analysis modules
        self.tabs = QTabWidget()
        
        # TAB 1: Real-Time Monitoring
        monitoring_tab = QWidget()
        mon_layout = QVBoxLayout()
        
        title = QLabel("Real-Time Sensor Monitoring")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #228be6;")
        title.setAlignment(Qt.AlignCenter)
        mon_layout.addWidget(title)
        
        self.plot_widget = EnhancedPlotWidget()
        mon_layout.addWidget(self.plot_widget)
        
        monitoring_tab.setLayout(mon_layout)
        self.tabs.addTab(monitoring_tab, "📊 Monitoring")
        
        # TAB 2: Analysis Module 2A (Features 7-10) - if available
        if ANALYSIS_MODULES_AVAILABLE and AnalysisTab2A:
            self.analysis_tab_2a = AnalysisTab2A(self)
            self.tabs.addTab(self.analysis_tab_2a, "🔬 Analysis 1")
        else:
            placeholder_2a = QWidget()
            placeholder_layout = QVBoxLayout()
            msg = QLabel("⚠️ Analysis Module 2A not available\n\nMake sure SensorAnalysis_Module_2A.py is in the same directory")
            msg.setAlignment(Qt.AlignCenter)
            msg.setStyleSheet("color: #fa5252; font-weight: bold;")
            placeholder_layout.addWidget(msg)
            placeholder_2a.setLayout(placeholder_layout)
            self.tabs.addTab(placeholder_2a, "🔬 Analysis 1")
        
        # TAB 3: Analysis Module 2B (Features 11-14) - if available
        if ANALYSIS_MODULES_AVAILABLE and AnalysisTab2B:
            self.analysis_tab_2b = AnalysisTab2B(self)
            self.tabs.addTab(self.analysis_tab_2b, "🔮 Analysis 2")
        else:
            placeholder_2b = QWidget()
            placeholder_layout = QVBoxLayout()
            msg = QLabel("⚠️ Analysis Module 2B not available\n\nMake sure SensorAnalysis_Module_2B.py is in the same directory")
            msg.setAlignment(Qt.AlignCenter)
            msg.setStyleSheet("color: #fa5252; font-weight: bold;")
            placeholder_layout.addWidget(msg)
            placeholder_2b.setLayout(placeholder_layout)
            self.tabs.addTab(placeholder_2b, "🔮 Analysis 2")
        
        main_layout.addWidget(self.tabs, 2)
        
        # Right panel - Current readings, statistics, console
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 1)
        
        # Status bar
        status_msg = "Ready - Segment 1 with Features 1-6"
        if ANALYSIS_MODULES_AVAILABLE:
            status_msg += " + Analysis Modules (Features 7-14)"
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(status_msg)
        
        # Toolbar
        self.create_toolbar()
        
    def create_toolbar(self):
        """Create toolbar with export/session actions"""
        toolbar = self.addToolBar("Actions")
        toolbar.setIconSize(QSize(24, 24))
        
        # Export actions
        export_csv = QAction("💾 CSV", self)
        export_csv.triggered.connect(lambda: self.export_data('csv'))
        export_csv.setStatusTip("Export data to CSV")
        toolbar.addAction(export_csv)
        
        export_excel = QAction("📊 Excel", self)
        export_excel.triggered.connect(lambda: self.export_data('excel'))
        export_excel.setStatusTip("Export data to Excel")
        toolbar.addAction(export_excel)
        
        export_json = QAction("📋 JSON", self)
        export_json.triggered.connect(lambda: self.export_data('json'))
        export_json.setStatusTip("Export data to JSON")
        toolbar.addAction(export_json)
        
        toolbar.addSeparator()
        
        # Report action
        report_action = QAction("📄 Report", self)
        report_action.triggered.connect(self.generate_report)
        report_action.setStatusTip("Generate PDF report")
        toolbar.addAction(report_action)
        
        toolbar.addSeparator()
        
        # Session actions
        save_session = QAction("💿 Save", self)
        save_session.triggered.connect(self.save_session)
        save_session.setStatusTip("Save current session")
        toolbar.addAction(save_session)
        
        load_session = QAction("📂 Load", self)
        load_session.triggered.connect(self.load_session)
        load_session.setStatusTip("Load previous session")
        toolbar.addAction(load_session)
        
    def create_left_panel(self):
        """Create left control panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # Connection
        conn_group = QGroupBox("Connection")
        conn_layout = QVBoxLayout()
        
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_input = QLineEdit(self.config.uart_port)
        port_layout.addWidget(self.port_input)
        conn_layout.addLayout(port_layout)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setStyleSheet("background-color: #51cf66; font-weight: bold; padding: 8px;")
        conn_layout.addWidget(self.connect_btn)
        
        self.status_label = QLabel("● Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        conn_layout.addWidget(self.status_label)
        
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)
        
        # Measurement control
        meas_group = QGroupBox("Measurement")
        meas_layout = QVBoxLayout()
        
        avg_layout = QHBoxLayout()
        avg_layout.addWidget(QLabel("Averaging:"))
        self.avg_spin = QSpinBox()
        self.avg_spin.setRange(1, 100)
        self.avg_spin.setValue(1)
        self.avg_spin.setToolTip("Number of readings to average before displaying/saving (1 = no averaging)")
        self.avg_spin.valueChanged.connect(self.on_avg_changed)
        avg_layout.addWidget(self.avg_spin)
        meas_layout.addLayout(avg_layout)

        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Interval (s):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(int(self.config.measurement_interval))
        interval_layout.addWidget(self.interval_spin)
        meas_layout.addLayout(interval_layout)
        
        self.start_btn = QPushButton("Start Measurements")
        self.start_btn.clicked.connect(self.toggle_measurements)
        meas_layout.addWidget(self.start_btn)
        
        # NEW: Background logging control
        self.log_btn = QPushButton("Start Logging")
        self.log_btn.clicked.connect(self.toggle_logging)
        self.log_btn.setStyleSheet("background-color: #339af0; color: white; font-weight: bold;")
        meas_layout.addWidget(self.log_btn)
        
        meas_group.setLayout(meas_layout)
        layout.addWidget(meas_group)
        
        # Health monitor
        self.health_widget = HealthMonitorWidget()
        layout.addWidget(self.health_widget)
        
        layout.addStretch()
        panel.setLayout(layout)
        return panel
        
    def create_right_panel(self):
        """Create right panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # Current readings
        readings_group = QGroupBox("Current Readings")
        readings_layout = QVBoxLayout()
        
        self.ec_label = QLabel("EC: ---")
        self.ec_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #228be6;")
        readings_layout.addWidget(self.ec_label)
        
        self.temp_label = QLabel("Temp: ---")
        self.temp_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #fa5252;")
        readings_layout.addWidget(self.temp_label)
        
        self.ph_label = QLabel("pH: ---")
        self.ph_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #51cf66;")
        readings_layout.addWidget(self.ph_label)
        
        readings_group.setLayout(readings_layout)
        layout.addWidget(readings_group)
        
        # Statistics
        self.stats_widget = StatisticsWidget()
        layout.addWidget(self.stats_widget)
        
        # Console
        console_group = QGroupBox("Console")
        console_layout = QVBoxLayout()
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("font-family: monospace; font-size: 10px;")
        console_layout.addWidget(self.console)
        
        console_group.setLayout(console_layout)
        layout.addWidget(console_group)
        
        panel.setLayout(layout)
        return panel
        
    def toggle_connection(self):
        """Toggle connection"""
        if self.is_connected:
            self.disconnect()
        else:
            self.connect()
            
    def connect(self):
        """Connect to Arduino"""
        port = self.port_input.text()
        
        try:
            self.worker = SerialWorker(port, self.config.uart_baudrate)
            self.worker.dataReceived.connect(self.handle_data)
            self.worker.connectionStatus.connect(self.handle_connection_status)
            self.worker.errorOccurred.connect(self.handle_error)
            self.worker.start()
            
            self.is_connected = True
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet("background-color: #ff6b6b; font-weight: bold; padding: 8px;")
            self.log("Connecting...")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Connection failed: {e}")
            
    def disconnect(self):
        """Disconnect"""
        if self.worker:
            self.worker.stop()
            self.worker.wait()
            
        self.is_connected = False
        self.connect_btn.setText("Connect")
        self.connect_btn.setStyleSheet("background-color: #51cf66; font-weight: bold; padding: 8px;")
        self.status_label.setText("● Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        self.log("Disconnected")
        
        # Stop logging if active
        if self.background_logger.is_logging:
            self.toggle_logging()
            
    def handle_connection_status(self, connected, message):
        """Handle connection status"""
        if connected:
            self.status_label.setText("● Connected")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.log(f"✓ {message}")
            QTimer.singleShot(1000, lambda: self.send_command("DIAG"))
        else:
            self.status_label.setText("● Reconnecting...")
            self.status_label.setStyleSheet("color: orange; font-weight: bold;")
            
    def handle_error(self, error):
        """Handle error"""
        self.log(f"✗ ERROR: {error}")
        
    def handle_data(self, data):
        """Handle incoming data - FULLY INTEGRATED"""
        self.log(f"← {data}")

        # SENSOR READINGS multi-line buffer.
        # Arduino sends READ response as 4 separate lines:
        #   "SENSOR READINGS" / "EC:   0.0 uS/cm" / "Temp: 22.1 C" / "pH:   5.24"
        # We collect them into a dict before calling parse_sensor_readings().

        if data.strip() == "SENSOR READINGS":
            self._reading_buffer = {}
            return

        if getattr(self, "_reading_buffer", None) is not None:
            import re
            ec_m   = re.search(r"EC:\s*([-\d.]+|NOT CALIBRATED)", data, re.IGNORECASE)
            temp_m = re.search(r"(?:Temp|T):\s*([-\d.]+)", data)
            ph_m   = re.search(r"pH:\s*([-\d.]+|NOT CALIBRATED)",  data, re.IGNORECASE)

            if ec_m:
                self._reading_buffer["ec"]   = ec_m.group(1)
            if temp_m:
                self._reading_buffer["temp"] = temp_m.group(1)
            if ph_m:
                self._reading_buffer["ph"]   = ph_m.group(1)

            if all(k in self._reading_buffer for k in ("ec", "temp", "ph")):
                buf = self._reading_buffer
                self._reading_buffer = None
                self.parse_sensor_readings(buf)
            return

        # Parse health data (DIAG command)
        if "DIAG" in data or "ADC:" in data or "mV:" in data:
            self.health_widget.update_health(data)
    
    def parse_sensor_readings(self, buf):
        """
        Parse sensor readings from buffered dict.
        buf = {'ec': '0.0', 'temp': '22.1', 'ph': '5.24'}
        Values may be numeric strings or 'NOT CALIBRATED'.
        """
        try:
            ec_str   = buf.get('ec',   'NOT CALIBRATED')
            temp_str = buf.get('temp', '0.0')
            ph_str   = buf.get('ph',   'NOT CALIBRATED')

            # Parse EC (handle NOT CALIBRATED)
            if 'NOT' in ec_str.upper():
                ec = None
                ec_display = "EC: NOT CALIBRATED"
            else:
                ec = float(ec_str)
                ec_display = f"EC: {ec:.1f} µS/cm"

            # Temperature always has a value
            temp = float(temp_str)
            temp_display = f"Temp: {temp:.1f} °C"

            # Parse pH (handle NOT CALIBRATED)
            if 'NOT' in ph_str.upper():
                ph = None
                ph_display = "pH: NOT CALIBRATED"
            else:
                ph = float(ph_str)
                ph_display = f"pH: {ph:.2f}"
            
            # Always update live display labels immediately
            self.ec_label.setText(ec_display)
            self.temp_label.setText(temp_display)
            self.ph_label.setText(ph_display)

            # Only average/log/plot if all sensors calibrated
            if ec is not None and ph is not None:
                if self.validate_reading(ec, temp, ph):
                    # Add raw reading to averaging buffer
                    self._avg_buffer.append((ec, temp, ph))

                    n = self._avg_count  # target average window
                    buf_len = len(self._avg_buffer)

                    # Show progress in label when averaging > 1
                    if n > 1:
                        self.ec_label.setText(f"{ec_display}  [{buf_len}/{n}]")

                    if buf_len >= n:
                        # Compute averages
                        avg_ec   = sum(r[0] for r in self._avg_buffer) / buf_len
                        avg_temp = sum(r[1] for r in self._avg_buffer) / buf_len
                        avg_ph   = sum(r[2] for r in self._avg_buffer) / buf_len
                        self._avg_buffer = []  # reset buffer

                        # Update display with averaged values
                        self.ec_label.setText(f"EC: {avg_ec:.1f} µS/cm" + (f" (avg {n})" if n > 1 else ""))
                        self.temp_label.setText(f"Temp: {avg_temp:.1f} °C" + (f" (avg {n})" if n > 1 else ""))
                        self.ph_label.setText(f"pH: {avg_ph:.2f}" + (f" (avg {n})" if n > 1 else ""))

                        # Update plot, stats, export with averaged value
                        elapsed = time.time() - self.start_time
                        self.plot_widget.add_data(elapsed, avg_ec, avg_temp, avg_ph)
                        self.stats_widget.update_statistics(avg_ec, avg_temp, avg_ph)

                        self.collected_data.append({
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'elapsed':   elapsed,
                            'ec':        avg_ec,
                            'temp':      avg_temp,
                            'ph':        avg_ph
                        })

                        if self.background_logger.is_logging:
                            self.background_logger.log_data(elapsed, avg_ec, avg_temp, avg_ph)
            else:
                # Some sensors not calibrated - show warning once
                if not hasattr(self, '_uncalibrated_warning_shown'):
                    self.log("⚠ Some sensors not calibrated - data logging paused")
                    self.log("  Calibrate sensors using Calibrator GUI, then data logging will resume")
                    self._uncalibrated_warning_shown = True
                    
        except Exception as e:
            self.log(f"Parse error: {e}")
            
    def validate_reading(self, ec, temp, ph):
        """Validate readings"""
        if not (self.config.ec_min <= ec <= self.config.ec_max):
            self.log(f"⚠ EC out of range: {ec}")
            return False
        if not (self.config.temp_min <= temp <= self.config.temp_max):
            self.log(f"⚠ Temperature out of range: {temp}")
            return False
        if not (self.config.ph_min <= ph <= self.config.ph_max):
            self.log(f"⚠ pH out of range: {ph}")
            return False
        return True
        
    def on_avg_changed(self, value):
        """Reset averaging buffer when window size changes"""
        self._avg_count = value
        self._avg_buffer = []
        if value == 1:
            self.log("Averaging: disabled (every reading shown)")
        else:
            self.log(f"Averaging: {value} readings per data point")

    def toggle_measurements(self):
        """Toggle measurements"""
        if self.measurement_timer.isActive():
            self.measurement_timer.stop()
            self.start_btn.setText("Start Measurements")
            self.log("Measurements stopped")
        else:
            # Reset averaging buffer on fresh start
            self._avg_buffer = []
            self._avg_count = self.avg_spin.value()
            interval = self.interval_spin.value() * 1000
            self.measurement_timer.start(interval)
            self.start_btn.setText("Stop Measurements")
            avg_info = f", averaging {self._avg_count}" if self._avg_count > 1 else ""
            self.log(f"Measurements started ({self.interval_spin.value()}s interval{avg_info})")
            self.request_measurement()
            
    def toggle_logging(self):
        """Toggle background logging"""
        if self.background_logger.is_logging:
            message = self.background_logger.stop_logging()
            self.log_btn.setText("Start Logging")
            self.log_btn.setStyleSheet("background-color: #339af0; color: white; font-weight: bold;")
            self.log(f"✓ {message}")
        else:
            success, message = self.background_logger.start_logging()
            if success:
                self.log_btn.setText("Stop Logging")
                self.log_btn.setStyleSheet("background-color: #ff6b6b; color: white; font-weight: bold;")
                self.log(f"✓ {message}")
            else:
                QMessageBox.warning(self, "Error", message)
                self.log(f"✗ {message}")
                
    def request_measurement(self):
        """Request measurement"""
        self.send_command("READ")
        
    def send_command(self, cmd):
        """Send command"""
        if self.worker and self.is_connected:
            self.worker.send_command(cmd)
            self.log(f"→ {cmd}")
            
    def export_data(self, format_type):
        """Export collected data"""
        if len(self.collected_data) == 0:
            QMessageBox.information(self, "No Data", "No data to export. Start measurements first!")
            return
            
        self.log(f"💾 Exporting {len(self.collected_data)} points as {format_type.upper()}...")
        
        if format_type == 'csv':
            filename, error = self.data_exporter.export_to_csv(self.collected_data)
        elif format_type == 'excel':
            filename, error = self.data_exporter.export_to_excel(self.collected_data)
        elif format_type == 'json':
            filename, error = self.data_exporter.export_to_json(self.collected_data)
        else:
            return
            
        if error:
            QMessageBox.warning(self, "Error", error)
            self.log(f"✗ Export failed: {error}")
        else:
            QMessageBox.information(self, "Success", f"✓ Exported to:\n{filename}")
            self.log(f"✓ Export complete: {filename}")
            
    def generate_report(self):
        """Generate PDF report"""
        if len(self.collected_data) == 0:
            QMessageBox.information(self, "No Data", "No data for report. Start measurements first!")
            return
            
        self.log("📄 Generating PDF report...")
        
        # Get statistics
        statistics = self.stats_widget.get_statistics_dict()
        
        # Get plot image
        plot_image = self.plot_widget.get_temp_plot_file()
        
        # Generate report
        filename, error = self.report_generator.generate_report(statistics, plot_image)
        
        # Clean up temp plot
        if os.path.exists(plot_image):
            os.remove(plot_image)
            
        if error:
            QMessageBox.warning(self, "Error", error)
            self.log(f"✗ Report failed: {error}")
        else:
            reply = QMessageBox.question(
                self, "Success",
                f"✓ Report generated:\n{filename}\n\nOpen it?",
                QMessageBox.Yes | QMessageBox.No
            )
            self.log(f"✓ Report complete: {filename}")
            
            if reply == QMessageBox.Yes:
                import subprocess
                subprocess.run(['xdg-open', filename])
                
    def save_session(self):
        """Save current session"""
        if len(self.collected_data) == 0:
            QMessageBox.information(self, "No Data", "No data to save. Start measurements first!")
            return
            
        name, ok = QInputDialog.getText(self, "Save Session", "Session name:")
        if ok and name:
            filename, error = self.session_manager.save_session(self.collected_data, name)
            
            if error:
                QMessageBox.warning(self, "Error", error)
                self.log(f"✗ Save failed: {error}")
            else:
                QMessageBox.information(self, "Success", f"✓ Session saved!")
                self.log(f"✓ Session saved: {name}")
                
    def load_session(self):
        """Load previous session"""
        sessions = self.session_manager.list_sessions()
        
        if not sessions:
            QMessageBox.information(self, "No Sessions", "No saved sessions found")
            return
            
        # Show file dialog
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Session",
            self.session_manager.sessions_dir,
            "Session Files (*.pkl)"
        )
        
        if filename:
            session, error = self.session_manager.load_session(filename)
            
            if error:
                QMessageBox.warning(self, "Error", error)
                self.log(f"✗ Load failed: {error}")
            else:
                # Clear current data
                self.plot_widget.clear_data()
                self.collected_data.clear()
                
                # Load session data
                loaded_data = session['data']
                for item in loaded_data:
                    self.plot_widget.add_data(
                        item['elapsed'],
                        item['ec'],
                        item['temp'],
                        item['ph']
                    )
                    
                self.collected_data = loaded_data
                
                QMessageBox.information(self, "Success", 
                    f"✓ Loaded session: {session['name']}\n"
                    f"Data points: {len(loaded_data)}")
                self.log(f"✓ Session loaded: {session['name']}")
                
    def log(self, message):
        """Log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console.append(f"[{timestamp}] {message}")
        self.console.verticalScrollBar().setValue(
            self.console.verticalScrollBar().maximum()
        )
    
    def scroll_to_top(self):
        """Scroll window to top"""
        scroll_area = self.centralWidget()
        if isinstance(scroll_area, QScrollArea):
            scroll_area.verticalScrollBar().setValue(0)
            
    def scroll_to_bottom(self):
        """Scroll window to bottom"""
        scroll_area = self.centralWidget()
        if isinstance(scroll_area, QScrollArea):
            scroll_area.verticalScrollBar().setValue(
                scroll_area.verticalScrollBar().maximum()
            )
    
    def scroll_by(self, pixels):
        """Scroll by specified pixels (positive = down, negative = up)"""
        scroll_area = self.centralWidget()
        if isinstance(scroll_area, QScrollArea):
            current = scroll_area.verticalScrollBar().value()
            scroll_area.verticalScrollBar().setValue(current + pixels)
        
    def closeEvent(self, event):
        """Handle close"""
        if self.is_connected:
            self.disconnect()
        self.config.save()
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = SensorReaderSegment1()
    window.show()
    
    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        window.close()

if __name__ == "__main__":
    main()
