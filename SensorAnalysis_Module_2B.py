#!/usr/bin/env python3
"""
Sensor Analysis Module - Part 2B (Features 11-14)
Standalone module for advanced predictive and detection analysis

This module provides on-demand analysis tools:
  - Feature 11: Trend Detection with Statistical Significance
  - Feature 12: Simple Anomaly Detection (Z-Score)
  - Feature 14: Drift Forecasting (24-hour prediction)

Can be imported into any SensorReader version.

Requires: pip install numpy scipy pandas matplotlib scikit-learn
"""

import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime, timedelta
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Optional: scikit-learn for advanced regression
try:
    from sklearn.linear_model import LinearRegression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# ============================================================================
# FEATURE 11: TREND DETECTOR
# ============================================================================

class TrendDetector:
    """Detect and test statistical significance of trends in sensor data"""
    
    @staticmethod
    def analyze_trend(data, times=None):
        """
        Detect trend and test statistical significance
        
        Args:
            data: array-like sensor values
            times: array-like time values (optional, uses indices if None)
            
        Returns:
            tuple: (result_dict, error_message)
            result_dict contains:
                - 'slope': trend slope (per time unit)
                - 'intercept': y-intercept
                - 'r_squared': coefficient of determination
                - 'p_value': statistical significance
                - 'is_significant': True if p < 0.05
                - 'direction': 'increasing', 'decreasing', or 'stable'
                - 'rate_per_hour': change rate per hour (if times provided)
        """
        try:
            data_array = np.array(data)
            n = len(data_array)
            
            if n < 3:
                return None, "Need at least 3 data points"
            
            # Use provided times or create index
            if times is not None:
                x = np.array(times)
            else:
                x = np.arange(n)
            
            # Reshape for sklearn or use numpy polyfit
            X = x.reshape(-1, 1)
            y = data_array
            
            # Fit linear regression
            if SKLEARN_AVAILABLE:
                model = LinearRegression()
                model.fit(X, y)
                slope = model.coef_[0]
                intercept = model.intercept_
                y_pred = model.predict(X)
                r_squared = model.score(X, y)
            else:
                # Fallback to numpy
                coeffs = np.polyfit(x, y, 1)
                slope = coeffs[0]
                intercept = coeffs[1]
                y_pred = slope * x + intercept
                
                # Calculate R²
                ss_tot = np.sum((y - np.mean(y))**2)
                ss_res = np.sum((y - y_pred)**2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            # Calculate statistical significance
            residuals = y - y_pred
            mse = np.mean(residuals**2)
            
            # Standard error of slope
            x_mean = np.mean(x)
            x_var = np.sum((x - x_mean)**2)
            se_slope = np.sqrt(mse / x_var) if x_var > 0 else 0
            
            # T-statistic and p-value
            t_stat = slope / se_slope if se_slope > 0 else 0
            df = n - 2  # degrees of freedom
            p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df))
            
            # Determine significance
            is_significant = p_value < 0.05
            
            # Determine direction
            if is_significant:
                direction = 'increasing' if slope > 0 else 'decreasing'
            else:
                direction = 'stable'
            
            # Calculate rate per hour if times provided
            rate_per_hour = None
            if times is not None and len(times) > 1:
                time_span = times[-1] - times[0]
                if time_span > 0:
                    # Assume times are in seconds
                    rate_per_hour = slope * 3600  # convert to per hour
            
            return {
                'slope': slope,
                'intercept': intercept,
                'r_squared': r_squared,
                'p_value': p_value,
                'is_significant': is_significant,
                'direction': direction,
                'rate_per_hour': rate_per_hour,
                'y_pred': y_pred
            }, None
            
        except Exception as e:
            return None, f"Trend analysis failed: {e}"

# ============================================================================
# FEATURE 12: ANOMALY DETECTOR (Z-SCORE METHOD)
# ============================================================================

class SimpleAnomalyDetector:
    """Detect anomalies using Z-score method"""
    
    def __init__(self, threshold=3.0):
        """
        Initialize detector
        
        Args:
            threshold (float): Z-score threshold for anomaly (default 3.0 = 99.7%)
        """
        self.threshold = threshold
        
    def detect_anomalies(self, data):
        """
        Detect anomalies using Z-score method
        
        Args:
            data: array-like sensor values
            
        Returns:
            tuple: (result_dict, error_message)
            result_dict contains:
                - 'z_scores': Z-score for each point
                - 'is_anomaly': boolean array marking anomalies
                - 'anomaly_indices': indices of anomalous points
                - 'anomaly_values': values of anomalous points
                - 'num_anomalies': count of anomalies
                - 'percentage': percentage of anomalies
        """
        try:
            data_array = np.array(data)
            
            if len(data_array) < 3:
                return None, "Need at least 3 data points"
            
            # Calculate mean and std
            mean = np.mean(data_array)
            std = np.std(data_array)
            
            if std == 0:
                return None, "Zero standard deviation - all values identical"
            
            # Calculate Z-scores
            z_scores = np.abs((data_array - mean) / std)
            
            # Identify anomalies
            is_anomaly = z_scores > self.threshold
            anomaly_indices = np.where(is_anomaly)[0]
            anomaly_values = data_array[anomaly_indices]
            
            num_anomalies = len(anomaly_indices)
            percentage = (num_anomalies / len(data_array)) * 100
            
            return {
                'z_scores': z_scores,
                'is_anomaly': is_anomaly,
                'anomaly_indices': anomaly_indices,
                'anomaly_values': anomaly_values,
                'num_anomalies': num_anomalies,
                'percentage': percentage,
                'mean': mean,
                'std': std,
                'threshold': self.threshold
            }, None
            
        except Exception as e:
            return None, f"Anomaly detection failed: {e}"

# ============================================================================
# FEATURE 14: DRIFT FORECASTER
# ============================================================================

class DriftForecaster:
    """Forecast sensor drift and predict future values"""
    
    @staticmethod
    def forecast(data, times, hours_ahead=24):
        """
        Predict sensor value at future time based on current trend
        
        Args:
            data: array-like sensor values
            times: array-like time values (in seconds)
            hours_ahead (int): hours into future to predict
            
        Returns:
            tuple: (result_dict, error_message)
            result_dict contains:
                - 'current_value': most recent value
                - 'predicted_value': predicted value at hours_ahead
                - 'drift_rate_per_hour': rate of change per hour
                - 'confidence_interval': 95% confidence interval (±)
                - 'r_squared': fit quality
                - 'hours_ahead': hours into future
                - 'prediction_time': predicted timestamp
        """
        try:
            data_array = np.array(data)
            times_array = np.array(times)
            
            if len(data_array) < 10:
                return None, "Need at least 10 data points for reliable forecasting"
            
            # Fit linear regression
            X = times_array.reshape(-1, 1)
            y = data_array
            
            if SKLEARN_AVAILABLE:
                model = LinearRegression()
                model.fit(X, y)
                
                # Current value
                current_value = data_array[-1]
                
                # Predict future
                last_time = times_array[-1]
                future_time = last_time + hours_ahead * 3600  # convert hours to seconds
                predicted_value = model.predict([[future_time]])[0]
                
                # Calculate drift rate per hour
                drift_rate = model.coef_[0] * 3600  # per hour
                
                # Calculate R²
                r_squared = model.score(X, y)
                
                # Calculate confidence interval
                y_pred = model.predict(X)
                residuals = y - y_pred
                std_error = np.std(residuals)
                confidence_interval = 1.96 * std_error  # 95% CI
                
            else:
                # Fallback to numpy
                coeffs = np.polyfit(times_array, data_array, 1)
                slope = coeffs[0]
                intercept = coeffs[1]
                
                current_value = data_array[-1]
                
                last_time = times_array[-1]
                future_time = last_time + hours_ahead * 3600
                predicted_value = slope * future_time + intercept
                
                drift_rate = slope * 3600
                
                # Calculate R²
                y_pred = slope * times_array + intercept
                ss_tot = np.sum((data_array - np.mean(data_array))**2)
                ss_res = np.sum((data_array - y_pred)**2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                
                residuals = data_array - y_pred
                std_error = np.std(residuals)
                confidence_interval = 1.96 * std_error
            
            # Calculate prediction time
            start_time = datetime.now()
            prediction_time = start_time + timedelta(hours=hours_ahead)
            
            return {
                'current_value': current_value,
                'predicted_value': predicted_value,
                'drift_rate_per_hour': drift_rate,
                'confidence_interval': confidence_interval,
                'r_squared': r_squared,
                'hours_ahead': hours_ahead,
                'prediction_time': prediction_time.strftime("%Y-%m-%d %H:%M:%S")
            }, None
            
        except Exception as e:
            return None, f"Drift forecasting failed: {e}"

# ============================================================================
# ANALYSIS TAB WIDGET - INTEGRATES ALL FEATURES
# ============================================================================

class AnalysisTab2B(QWidget):
    """
    Qt Widget providing Analysis Tab with Features 11-14
    
    This widget can be added as a tab to any Qt application.
    It expects the parent to have a 'plot_widget' attribute with:
        - time_data (deque or list)
        - ec_data (deque or list)
        - temp_data (deque or list)
        - ph_data (deque or list)
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create analyzers
        self.trend_detector = TrendDetector()
        self.anomaly_detector = SimpleAnomalyDetector(threshold=3.0)
        self.drift_forecaster = DriftForecaster()
        
        self.initUI()
        
    def initUI(self):
        """Initialize user interface"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("🔮 Predictive Analysis (On-Demand)")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #fa5252; padding: 5px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Analysis buttons
        btn_group = QGroupBox("Analysis Tools")
        btn_layout = QGridLayout()
        
        # Feature 11: Trend Detection
        self.trend_btn = QPushButton("📈 Trend Detection")
        self.trend_btn.clicked.connect(self.show_trend_analysis)
        self.trend_btn.setStyleSheet(
            "QPushButton { padding: 10px; font-weight: bold; background-color: #fff5f5; }"
            "QPushButton:hover { background-color: #ffe3e3; }"
        )
        self.trend_btn.setToolTip("Detect trends with statistical significance testing")
        btn_layout.addWidget(self.trend_btn, 0, 0)
        
        # Feature 12: Anomaly Detection
        self.anomaly_btn = QPushButton("🚨 Anomaly Detection")
        self.anomaly_btn.clicked.connect(self.show_anomaly_detection)
        self.anomaly_btn.setStyleSheet(
            "QPushButton { padding: 10px; font-weight: bold; background-color: #fff5f5; }"
            "QPushButton:hover { background-color: #ffe3e3; }"
        )
        self.anomaly_btn.setToolTip("Detect outliers using Z-score method")
        btn_layout.addWidget(self.anomaly_btn, 0, 1)
        
        # Feature 14: Drift Forecasting
        self.forecast_btn = QPushButton("🔮 Drift Forecasting")
        self.forecast_btn.clicked.connect(self.show_drift_forecast)
        self.forecast_btn.setStyleSheet(
            "QPushButton { padding: 10px; font-weight: bold; background-color: #fff5f5; }"
            "QPushButton:hover { background-color: #ffe3e3; }"
        )
        self.forecast_btn.setToolTip("Predict sensor values 24 hours ahead")
        btn_layout.addWidget(self.forecast_btn, 1, 0, 1, 2)  # Span 2 columns
        
        btn_group.setLayout(btn_layout)
        layout.addWidget(btn_group)
        
        # Results display area
        results_group = QGroupBox("Analysis Results")
        results_layout = QVBoxLayout()
        
        # Matplotlib plot area
        self.analysis_figure = Figure(figsize=(10, 6))
        self.analysis_canvas = FigureCanvas(self.analysis_figure)
        results_layout.addWidget(self.analysis_canvas)
        
        # Text results
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(150)
        self.results_text.setStyleSheet(
            "font-family: monospace; font-size: 11px; "
            "background-color: #f8f9fa; padding: 5px;"
        )
        results_layout.addWidget(self.results_text)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        self.setLayout(layout)
        
    def get_parent_data(self):
        """
        Get sensor data from parent widget
        
        Returns:
            dict with 'time', 'ec', 'temp', 'ph' lists or None if unavailable
        """
        parent = self.parent()
        
        # Walk up the widget hierarchy to find plot_widget
        while parent and not hasattr(parent, 'plot_widget'):
            parent = parent.parent()
            
        if parent and hasattr(parent, 'plot_widget'):
            plot_widget = parent.plot_widget
            return {
                'time': list(plot_widget.time_data),
                'ec': list(plot_widget.ec_data),
                'temp': list(plot_widget.temp_data),
                'ph': list(plot_widget.ph_data)
            }
        
        return None
        
    def show_trend_analysis(self):
        """Feature 11: Display trend detection analysis"""
        data = self.get_parent_data()
        
        if not data or len(data['ec']) < 3:
            QMessageBox.information(
                self, "Insufficient Data",
                "Need at least 3 data points for trend analysis.\n"
                "Current points: {}".format(len(data['ec']) if data else 0)
            )
            return
            
        self.results_text.clear()
        self.results_text.append("=" * 50)
        self.results_text.append("📈 TREND DETECTION ANALYSIS")
        self.results_text.append("=" * 50)
        
        # Analyze EC trend
        ec_array = np.array(data['ec'])
        times_array = np.array(data['time'])
        
        result, error = self.trend_detector.analyze_trend(ec_array, times_array)
        
        if error:
            self.results_text.append(f"Error: {error}")
            return
        
        # Plot
        self.analysis_figure.clear()
        ax = self.analysis_figure.add_subplot(111)
        
        # Raw data
        ax.plot(times_array, ec_array, 'o', alpha=0.5, markersize=5,
               label='Measured Data', color='#228be6', zorder=2)
        
        # Trend line
        ax.plot(times_array, result['y_pred'], '-', linewidth=3,
               label=f'Trend Line (R²={result["r_squared"]:.4f})',
               color='#fa5252', zorder=3)
        
        # Add confidence band if significant
        if result['is_significant']:
            # Simple confidence band (not exact, but illustrative)
            residuals = ec_array - result['y_pred']
            std_residuals = np.std(residuals)
            ax.fill_between(times_array,
                           result['y_pred'] - 2*std_residuals,
                           result['y_pred'] + 2*std_residuals,
                           alpha=0.2, color='#fa5252',
                           label='±2σ Confidence Band', zorder=1)
        
        ax.set_xlabel('Time (s)', fontweight='bold', fontsize=11)
        ax.set_ylabel('EC (µS/cm)', fontweight='bold', fontsize=11)
        ax.set_title('Trend Analysis - EC Signal', fontweight='bold', fontsize=13)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        self.analysis_figure.tight_layout()
        self.analysis_canvas.draw()
        
        # Text results
        self.results_text.append(f"\nTrend Parameters:")
        self.results_text.append("-" * 50)
        self.results_text.append(f"Slope: {result['slope']:.4f} µS/cm per second")
        if result['rate_per_hour'] is not None:
            self.results_text.append(f"Rate: {result['rate_per_hour']:.2f} µS/cm per hour")
        self.results_text.append(f"R² (fit quality): {result['r_squared']:.4f}")
        self.results_text.append(f"P-value: {result['p_value']:.6f}")
        
        self.results_text.append(f"\n{'='*50}")
        self.results_text.append("STATISTICAL SIGNIFICANCE:")
        self.results_text.append("="*50)
        
        if result['is_significant']:
            self.results_text.append(f"✓ Significant trend detected (p < 0.05)")
            self.results_text.append(f"  Direction: {result['direction'].upper()}")
            
            if result['direction'] == 'increasing':
                self.results_text.append(f"  → EC is steadily increasing")
                if result['rate_per_hour'] and result['rate_per_hour'] > 10:
                    self.results_text.append(f"  ⚠ Rapid increase detected!")
                    self.results_text.append(f"     → Check for drift or calibration issues")
            else:
                self.results_text.append(f"  → EC is steadily decreasing")
                if result['rate_per_hour'] and abs(result['rate_per_hour']) > 10:
                    self.results_text.append(f"  ⚠ Rapid decrease detected!")
                    self.results_text.append(f"     → Check sensor or solution")
        else:
            self.results_text.append(f"○ No significant trend (p > 0.05)")
            self.results_text.append(f"  → Measurements appear stable")
            self.results_text.append(f"  → Random fluctuations only")
        
        self.results_text.append(f"\nFit Quality:")
        if result['r_squared'] > 0.9:
            self.results_text.append(f"  ✓ Excellent fit (R² > 0.9)")
        elif result['r_squared'] > 0.7:
            self.results_text.append(f"  ○ Good fit (R² > 0.7)")
        else:
            self.results_text.append(f"  ⚠ Poor fit (R² < 0.7)")
            self.results_text.append(f"     → Data may be too noisy for trend")
        
    def show_anomaly_detection(self):
        """Feature 12: Display anomaly detection results"""
        data = self.get_parent_data()
        
        if not data or len(data['ec']) < 3:
            QMessageBox.information(
                self, "Insufficient Data",
                "Need at least 3 data points for anomaly detection.\n"
                "Current points: {}".format(len(data['ec']) if data else 0)
            )
            return
            
        self.results_text.clear()
        self.results_text.append("=" * 50)
        self.results_text.append("🚨 ANOMALY DETECTION ANALYSIS")
        self.results_text.append("=" * 50)
        self.results_text.append(f"Method: Z-Score (threshold = {self.anomaly_detector.threshold}σ)\n")
        
        # Detect anomalies in EC
        ec_array = np.array(data['ec'])
        times_array = np.array(data['time'])
        
        result, error = self.anomaly_detector.detect_anomalies(ec_array)
        
        if error:
            self.results_text.append(f"Error: {error}")
            return
        
        # Plot
        self.analysis_figure.clear()
        ax = self.analysis_figure.add_subplot(111)
        
        # Normal points
        normal_mask = ~result['is_anomaly']
        ax.plot(times_array[normal_mask], ec_array[normal_mask],
               'o', markersize=5, label='Normal', color='#51cf66', zorder=2)
        
        # Anomalous points
        if result['num_anomalies'] > 0:
            ax.plot(times_array[result['is_anomaly']], result['anomaly_values'],
                   'X', markersize=10, label='Anomaly', color='#fa5252',
                   markeredgewidth=2, zorder=3)
        
        # Mean line
        ax.axhline(result['mean'], color='gray', linestyle='--',
                  linewidth=2, label=f'Mean ({result["mean"]:.1f})', zorder=1)
        
        # Threshold lines
        upper_threshold = result['mean'] + self.anomaly_detector.threshold * result['std']
        lower_threshold = result['mean'] - self.anomaly_detector.threshold * result['std']
        
        ax.axhline(upper_threshold, color='orange', linestyle=':',
                  linewidth=1.5, label=f'+{self.anomaly_detector.threshold}σ', alpha=0.7)
        ax.axhline(lower_threshold, color='orange', linestyle=':',
                  linewidth=1.5, label=f'-{self.anomaly_detector.threshold}σ', alpha=0.7)
        
        # Shaded acceptable range
        ax.fill_between(times_array, lower_threshold, upper_threshold,
                       alpha=0.1, color='green', zorder=0)
        
        ax.set_xlabel('Time (s)', fontweight='bold', fontsize=11)
        ax.set_ylabel('EC (µS/cm)', fontweight='bold', fontsize=11)
        ax.set_title('Anomaly Detection - EC Signal', fontweight='bold', fontsize=13)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        self.analysis_figure.tight_layout()
        self.analysis_canvas.draw()
        
        # Text results
        self.results_text.append(f"Statistics:")
        self.results_text.append("-" * 50)
        self.results_text.append(f"Mean: {result['mean']:.2f} µS/cm")
        self.results_text.append(f"Std Dev: {result['std']:.2f} µS/cm")
        self.results_text.append(f"Threshold: ±{self.anomaly_detector.threshold}σ")
        self.results_text.append(f"Acceptable Range: {lower_threshold:.1f} - {upper_threshold:.1f} µS/cm")
        
        self.results_text.append(f"\n{'='*50}")
        self.results_text.append("ANOMALY RESULTS:")
        self.results_text.append("="*50)
        self.results_text.append(f"Total Points: {len(ec_array)}")
        self.results_text.append(f"Anomalies Found: {result['num_anomalies']}")
        self.results_text.append(f"Percentage: {result['percentage']:.1f}%")
        
        if result['num_anomalies'] > 0:
            self.results_text.append(f"\n⚠ ANOMALIES DETECTED:")
            self.results_text.append("-" * 50)
            for idx, val in zip(result['anomaly_indices'], result['anomaly_values']):
                z_score = result['z_scores'][idx]
                time_val = times_array[idx]
                self.results_text.append(
                    f"  Point {idx}: {val:.1f} µS/cm (t={time_val:.1f}s, Z={z_score:.2f})"
                )
            
            self.results_text.append(f"\nPossible Causes:")
            self.results_text.append("  • Sensor malfunction or disconnection")
            self.results_text.append("  • Solution contamination")
            self.results_text.append("  • Measurement interference")
            self.results_text.append("  • Data transmission error")
        else:
            self.results_text.append(f"\n✓ NO ANOMALIES DETECTED")
            self.results_text.append(f"  → All measurements within normal range")
            self.results_text.append(f"  → System operating normally")
        
        # Quality assessment
        self.results_text.append(f"\nData Quality Assessment:")
        if result['percentage'] < 1:
            self.results_text.append(f"  ✓ Excellent (<1% anomalies)")
        elif result['percentage'] < 5:
            self.results_text.append(f"  ○ Good (<5% anomalies)")
        else:
            self.results_text.append(f"  ⚠ Poor (>{result['percentage']:.0f}% anomalies)")
            self.results_text.append(f"     → Investigate measurement system")
        
    def show_drift_forecast(self):
        """Feature 14: Display drift forecasting"""
        data = self.get_parent_data()
        
        if not data or len(data['ec']) < 10:
            QMessageBox.information(
                self, "Insufficient Data",
                "Need at least 10 data points for reliable forecasting.\n"
                "Current points: {}".format(len(data['ec']) if data else 0)
            )
            return
            
        self.results_text.clear()
        self.results_text.append("=" * 50)
        self.results_text.append("🔮 DRIFT FORECASTING ANALYSIS")
        self.results_text.append("=" * 50)
        
        # Forecast EC drift
        ec_array = np.array(data['ec'])
        times_array = np.array(data['time'])
        
        result, error = self.drift_forecaster.forecast(ec_array, times_array, hours_ahead=24)
        
        if error:
            self.results_text.append(f"Error: {error}")
            return
        
        # Plot
        self.analysis_figure.clear()
        ax = self.analysis_figure.add_subplot(111)
        
        # Historical data
        ax.plot(times_array, ec_array, 'o-', markersize=5,
               label='Historical Data', color='#228be6', linewidth=2, zorder=2)
        
        # Trend line through historical data
        if SKLEARN_AVAILABLE:
            model = LinearRegression()
            model.fit(times_array.reshape(-1, 1), ec_array)
            trend_line = model.predict(times_array.reshape(-1, 1))
        else:
            coeffs = np.polyfit(times_array, ec_array, 1)
            trend_line = coeffs[0] * times_array + coeffs[1]
        
        ax.plot(times_array, trend_line, '--', linewidth=2,
               label='Current Trend', color='gray', alpha=0.7, zorder=1)
        
        # Forecast point
        forecast_time = times_array[-1] + 24 * 3600  # 24 hours in seconds
        ax.plot(forecast_time, result['predicted_value'],
               '*', markersize=20, label='24h Forecast',
               color='#fa5252', markeredgecolor='black',
               markeredgewidth=2, zorder=4)
        
        # Confidence interval for forecast
        ci = result['confidence_interval']
        ax.errorbar(forecast_time, result['predicted_value'],
                   yerr=ci, fmt='none', ecolor='#fa5252',
                   elinewidth=2, capsize=10, capthick=2,
                   label=f'95% CI (±{ci:.1f})', zorder=3)
        
        # Extended trend line to forecast
        extended_times = np.array([times_array[-1], forecast_time])
        extended_values = np.array([ec_array[-1], result['predicted_value']])
        ax.plot(extended_times, extended_values, ':', linewidth=2,
               color='#fa5252', alpha=0.5, zorder=1)
        
        ax.set_xlabel('Time (s)', fontweight='bold', fontsize=11)
        ax.set_ylabel('EC (µS/cm)', fontweight='bold', fontsize=11)
        ax.set_title('Drift Forecasting - 24 Hour Prediction', fontweight='bold', fontsize=13)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Add vertical line at forecast time
        ax.axvline(times_array[-1], color='green', linestyle='--',
                  alpha=0.5, label='Now')
        
        self.analysis_figure.tight_layout()
        self.analysis_canvas.draw()
        
        # Text results
        self.results_text.append(f"Current Status:")
        self.results_text.append("-" * 50)
        self.results_text.append(f"Current Value: {result['current_value']:.2f} µS/cm")
        self.results_text.append(f"Drift Rate: {result['drift_rate_per_hour']:.3f} µS/cm per hour")
        self.results_text.append(f"Trend Quality (R²): {result['r_squared']:.4f}")
        
        self.results_text.append(f"\n{'='*50}")
        self.results_text.append("24-HOUR FORECAST:")
        self.results_text.append("="*50)
        self.results_text.append(f"Predicted Value: {result['predicted_value']:.2f} µS/cm")
        self.results_text.append(f"Prediction Time: {result['prediction_time']}")
        self.results_text.append(f"95% Confidence: ±{result['confidence_interval']:.2f} µS/cm")
        self.results_text.append(f"Predicted Range: {result['predicted_value']-result['confidence_interval']:.1f} - {result['predicted_value']+result['confidence_interval']:.1f} µS/cm")
        
        # Calculate change
        change = result['predicted_value'] - result['current_value']
        change_pct = (change / result['current_value'] * 100) if result['current_value'] != 0 else 0
        
        self.results_text.append(f"\nExpected Change:")
        self.results_text.append(f"  Absolute: {change:+.2f} µS/cm")
        self.results_text.append(f"  Relative: {change_pct:+.2f}%")
        
        self.results_text.append(f"\n{'='*50}")
        self.results_text.append("INTERPRETATION:")
        self.results_text.append("="*50)
        
        # Forecast quality
        if result['r_squared'] > 0.8:
            self.results_text.append(f"✓ High confidence forecast (R² > 0.8)")
            self.results_text.append(f"  → Trend is well-established")
        elif result['r_squared'] > 0.5:
            self.results_text.append(f"○ Moderate confidence (R² > 0.5)")
            self.results_text.append(f"  → Use with caution")
        else:
            self.results_text.append(f"⚠ Low confidence (R² < 0.5)")
            self.results_text.append(f"  → Trend not reliable for prediction")
            self.results_text.append(f"  → Data may be too variable")
        
        # Drift assessment
        abs_drift_rate = abs(result['drift_rate_per_hour'])
        if abs_drift_rate > 10:
            self.results_text.append(f"\n⚠ SIGNIFICANT DRIFT DETECTED:")
            self.results_text.append(f"  Rate: {abs_drift_rate:.2f} µS/cm/hour")
            self.results_text.append(f"  → Consider recalibration soon")
        elif abs_drift_rate > 5:
            self.results_text.append(f"\n○ Moderate drift ({abs_drift_rate:.2f} µS/cm/hour)")
            self.results_text.append(f"  → Monitor and plan calibration")
        else:
            self.results_text.append(f"\n✓ Minimal drift ({abs_drift_rate:.2f} µS/cm/hour)")
            self.results_text.append(f"  → Sensor stable")

# ============================================================================
# EXAMPLE USAGE AND TESTING
# ============================================================================

if __name__ == "__main__":
    """
    Example of how to use this module standalone for testing
    """
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Create a test window
    window = QMainWindow()
    window.setWindowTitle("Analysis Module 2B - Test")
    window.setGeometry(100, 100, 1200, 800)
    
    # Create the analysis tab
    analysis_tab = AnalysisTab2B()
    window.setCentralWidget(analysis_tab)
    
    # Create some test data (simulating parent's plot_widget)
    class MockPlotWidget:
        def __init__(self):
            t = np.linspace(0, 3600, 100)  # 1 hour of data
            self.time_data = t.tolist()
            
            # EC with upward drift + noise + occasional spikes
            base_drift = 1000 + 0.05*t  # 50 µS/cm per hour drift
            noise = 10*np.random.randn(100)
            spikes = np.zeros(100)
            spikes[[20, 45, 78]] = [100, -80, 120]  # Add some anomalies
            self.ec_data = (base_drift + noise + spikes).tolist()
            
            # Temperature with slight increase
            self.temp_data = (25 + 0.001*t + 0.3*np.random.randn(100)).tolist()
            
            # pH relatively stable
            self.ph_data = (7.0 + 0.05*np.random.randn(100)).tolist()
    
    # Attach mock data to window
    window.plot_widget = MockPlotWidget()
    
    window.show()
    
    print("=" * 60)
    print("SENSOR ANALYSIS MODULE 2B - STANDALONE TEST")
    print("=" * 60)
    print("\nThis module provides 3 predictive analysis tools:")
    print("  1. Trend Detection - statistical significance")
    print("  2. Anomaly Detection - Z-score outlier detection")
    print("  3. Drift Forecasting - 24h predictions")
    print("\nTest data includes:")
    print("  • Upward drift (~50 µS/cm per hour)")
    print("  • Random noise")
    print("  • 3 anomalous spikes")
    print("\nClick the buttons to test each analysis!")
    print("=" * 60)
    
    sys.exit(app.exec_())

