#!/usr/bin/env python3
"""
Sensor Analysis Module - Part 2A (Features 7-10)
Standalone module for advanced sensor data analysis

This module provides on-demand analysis tools:
  - Feature 7: Rolling Statistics with CV
  - Feature 8: Data Smoothing (3 methods)
  - Feature 9: Correlation Matrix
  - Feature 10: FFT Frequency Analysis

Can be imported into any SensorReader version.

Requires: pip install numpy scipy pandas matplotlib
"""

import numpy as np
import pandas as pd
from scipy import signal
from scipy.fft import fft, fftfreq
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ============================================================================
# FEATURE 7: ROLLING STATISTICS ANALYZER
# ============================================================================

class RollingStatsAnalyzer:
    """Calculate rolling statistics for data quality assessment"""
    
    def __init__(self, window_size=20):
        """
        Initialize analyzer
        
        Args:
            window_size (int): Window size for rolling calculations
        """
        self.window_size = window_size
        
    def calculate(self, data_array):
        """
        Calculate rolling statistics
        
        Args:
            data_array: numpy array or list of values
            
        Returns:
            dict with 'mean', 'std', 'upper', 'lower', 'cv' arrays
            or None if insufficient data
        """
        if len(data_array) < self.window_size:
            return None
            
        try:
            series = pd.Series(data_array)
            rolling_mean = series.rolling(window=self.window_size).mean()
            rolling_std = series.rolling(window=self.window_size).std()
            rolling_cv = (rolling_std / rolling_mean) * 100  # Coefficient of variation %
            
            return {
                'mean': rolling_mean.values,
                'std': rolling_std.values,
                'upper': (rolling_mean + rolling_std).values,
                'lower': (rolling_mean - rolling_std).values,
                'cv': rolling_cv.values
            }
        except Exception as e:
            print(f"Rolling stats error: {e}")
            return None

# ============================================================================
# FEATURE 8: DATA SMOOTHER
# ============================================================================

class DataSmoother:
    """Apply various smoothing filters to noisy sensor data"""
    
    @staticmethod
    def moving_average(data, window=5):
        """
        Simple moving average filter
        
        Args:
            data: array-like data
            window (int): window size
            
        Returns:
            numpy array of smoothed data
        """
        if len(data) < window:
            return np.array(data)
        try:
            return np.convolve(data, np.ones(window)/window, mode='valid')
        except:
            return np.array(data)
        
    @staticmethod
    def savgol_filter(data, window=11, polyorder=3):
        """
        Savitzky-Golay filter (polynomial smoothing)
        
        Args:
            data: array-like data
            window (int): window size (must be odd)
            polyorder (int): polynomial order
            
        Returns:
            numpy array of smoothed data
        """
        if len(data) < window:
            return np.array(data)
        try:
            # Ensure window is odd
            if window % 2 == 0:
                window += 1
            # Ensure window > polyorder
            if window <= polyorder:
                window = polyorder + 2
            return signal.savgol_filter(data, window, polyorder)
        except Exception as e:
            print(f"Savgol filter error: {e}")
            return np.array(data)
            
    @staticmethod
    def median_filter(data, kernel_size=5):
        """
        Median filter (good for spike removal)
        
        Args:
            data: array-like data
            kernel_size (int): kernel size
            
        Returns:
            numpy array of smoothed data
        """
        if len(data) < kernel_size:
            return np.array(data)
        try:
            return signal.medfilt(data, kernel_size)
        except:
            return np.array(data)

# ============================================================================
# FEATURE 9: CORRELATION ANALYZER
# ============================================================================

class CorrelationAnalyzer:
    """Calculate sensor correlations to identify relationships"""
    
    @staticmethod
    def calculate_correlation(ec_data, temp_data, ph_data):
        """
        Calculate correlation matrix between sensors
        
        Args:
            ec_data: array-like EC values
            temp_data: array-like temperature values
            ph_data: array-like pH values
            
        Returns:
            tuple: (result_dict, error_message)
            result_dict contains:
                - 'matrix': 3x3 correlation matrix
                - 'ec_temp': EC-Temperature correlation
                - 'ec_ph': EC-pH correlation  
                - 'temp_ph': Temperature-pH correlation
        """
        try:
            # Convert to numpy arrays
            ec = np.array(ec_data)
            temp = np.array(temp_data)
            ph = np.array(ph_data)
            
            # Check for sufficient data
            if len(ec) < 3 or len(temp) < 3 or len(ph) < 3:
                return None, "Need at least 3 data points"
            
            # Stack data
            data = np.column_stack([ec, temp, ph])
            
            # Calculate correlation matrix
            corr_matrix = np.corrcoef(data.T)
            
            return {
                'matrix': corr_matrix,
                'ec_temp': corr_matrix[0, 1],
                'ec_ph': corr_matrix[0, 2],
                'temp_ph': corr_matrix[1, 2]
            }, None
            
        except Exception as e:
            return None, f"Correlation calculation failed: {e}"

# ============================================================================
# FEATURE 10: FFT ANALYZER
# ============================================================================

class FFTAnalyzer:
    """Frequency analysis to detect periodic patterns and noise"""
    
    @staticmethod
    def analyze(data, sampling_rate=0.33):
        """
        Perform FFT analysis on sensor data
        
        Args:
            data: array-like sensor values
            sampling_rate (float): samples per second (default 0.33 = 3s interval)
            
        Returns:
            tuple: (result_dict, error_message)
            result_dict contains:
                - 'frequencies': frequency array (Hz)
                - 'amplitudes': amplitude array
                - 'dominant_freq': top 3 frequencies
                - 'dominant_amp': top 3 amplitudes
                - 'periods': periods corresponding to dominant frequencies (seconds)
        """
        try:
            N = len(data)
            if N < 10:
                return None, "Need at least 10 data points"
            
            # Convert to numpy array
            data_array = np.array(data)
            
            # Remove DC component (mean) for better frequency analysis
            data_centered = data_array - np.mean(data_array)
            
            # Perform FFT
            yf = fft(data_centered)
            xf = fftfreq(N, 1/sampling_rate)
            
            # Get positive frequencies only
            pos_mask = xf > 0
            frequencies = xf[pos_mask]
            amplitudes = np.abs(yf[pos_mask])
            
            if len(amplitudes) == 0:
                return None, "No frequency data available"
            
            # Find top 3 dominant frequencies
            num_peaks = min(3, len(amplitudes))
            top_idx = np.argsort(amplitudes)[-num_peaks:][::-1]
            
            dominant_freq = frequencies[top_idx]
            dominant_amp = amplitudes[top_idx]
            
            # Calculate periods (avoid division by zero)
            periods = np.array([1/f if f > 1e-6 else 0 for f in dominant_freq])
            
            return {
                'frequencies': frequencies,
                'amplitudes': amplitudes,
                'dominant_freq': dominant_freq,
                'dominant_amp': dominant_amp,
                'periods': periods
            }, None
            
        except Exception as e:
            return None, f"FFT analysis failed: {e}"

# ============================================================================
# ANALYSIS TAB WIDGET - INTEGRATES ALL FEATURES
# ============================================================================

class AnalysisTab2A(QWidget):
    """
    Qt Widget providing Analysis Tab with Features 7-10
    
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
        self.rolling_stats = RollingStatsAnalyzer(window_size=20)
        self.smoother = DataSmoother()
        self.correlation = CorrelationAnalyzer()
        self.fft = FFTAnalyzer()
        
        self.initUI()
        
    def initUI(self):
        """Initialize user interface"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("📊 Advanced Analysis (On-Demand)")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #228be6; padding: 5px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Analysis buttons
        btn_group = QGroupBox("Analysis Tools")
        btn_layout = QGridLayout()
        
        # Feature 7 button
        self.rolling_btn = QPushButton("📈 Rolling Statistics")
        self.rolling_btn.clicked.connect(self.show_rolling_stats)
        self.rolling_btn.setStyleSheet(
            "QPushButton { padding: 10px; font-weight: bold; background-color: #e7f5ff; }"
            "QPushButton:hover { background-color: #d0ebff; }"
        )
        self.rolling_btn.setToolTip("Calculate rolling mean, std dev, and coefficient of variation")
        btn_layout.addWidget(self.rolling_btn, 0, 0)
        
        # Feature 8 button
        self.smooth_btn = QPushButton("🌊 Data Smoothing")
        self.smooth_btn.clicked.connect(self.show_smoothing)
        self.smooth_btn.setStyleSheet(
            "QPushButton { padding: 10px; font-weight: bold; background-color: #e7f5ff; }"
            "QPushButton:hover { background-color: #d0ebff; }"
        )
        self.smooth_btn.setToolTip("Apply smoothing filters: MA, Savitzky-Golay, Median")
        btn_layout.addWidget(self.smooth_btn, 0, 1)
        
        # Feature 9 button
        self.corr_btn = QPushButton("🔗 Correlation Matrix")
        self.corr_btn.clicked.connect(self.show_correlation)
        self.corr_btn.setStyleSheet(
            "QPushButton { padding: 10px; font-weight: bold; background-color: #e7f5ff; }"
            "QPushButton:hover { background-color: #d0ebff; }"
        )
        self.corr_btn.setToolTip("Calculate sensor correlations and relationships")
        btn_layout.addWidget(self.corr_btn, 1, 0)
        
        # Feature 10 button
        self.fft_btn = QPushButton("📊 FFT Analysis")
        self.fft_btn.clicked.connect(self.show_fft)
        self.fft_btn.setStyleSheet(
            "QPushButton { padding: 10px; font-weight: bold; background-color: #e7f5ff; }"
            "QPushButton:hover { background-color: #d0ebff; }"
        )
        self.fft_btn.setToolTip("Frequency analysis to detect periodic patterns")
        btn_layout.addWidget(self.fft_btn, 1, 1)
        
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
        
    def show_rolling_stats(self):
        """Feature 7: Display rolling statistics analysis"""
        data = self.get_parent_data()
        
        if not data or len(data['ec']) < 20:
            QMessageBox.information(
                self, "Insufficient Data",
                "Need at least 20 data points for rolling statistics.\n"
                "Current points: {}".format(len(data['ec']) if data else 0)
            )
            return
            
        self.results_text.clear()
        self.results_text.append("=" * 50)
        self.results_text.append("📈 ROLLING STATISTICS ANALYSIS")
        self.results_text.append("=" * 50)
        self.results_text.append(f"Window Size: {self.rolling_stats.window_size} points\n")
        
        # Calculate rolling stats for EC
        ec_array = np.array(data['ec'])
        ec_stats = self.rolling_stats.calculate(ec_array)
        
        if ec_stats is None:
            self.results_text.append("Error: Could not calculate statistics")
            return
            
        # Plot
        self.analysis_figure.clear()
        ax = self.analysis_figure.add_subplot(111)
        
        times = np.array(data['time'])
        
        # Raw data (faded)
        ax.plot(times, ec_array, 'o', alpha=0.3, markersize=3,
               label='Raw Data', color='#228be6', zorder=1)
        
        # Rolling mean (bold)
        ax.plot(times, ec_stats['mean'], '-', linewidth=2.5,
               label=f'Rolling Mean ({self.rolling_stats.window_size}pt)',
               color='#fa5252', zorder=3)
        
        # ±1 std dev bands
        ax.fill_between(times, ec_stats['lower'], ec_stats['upper'],
                       alpha=0.25, color='#fa5252',
                       label='±1 Std Dev', zorder=2)
        
        ax.set_xlabel('Time (s)', fontweight='bold', fontsize=11)
        ax.set_ylabel('EC (µS/cm)', fontweight='bold', fontsize=11)
        ax.set_title('Rolling Statistics - EC Signal', fontweight='bold', fontsize=13)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        self.analysis_figure.tight_layout()
        self.analysis_canvas.draw()
        
        # Statistics summary
        valid_cv = ec_stats['cv'][~np.isnan(ec_stats['cv'])]
        valid_mean = ec_stats['mean'][~np.isnan(ec_stats['mean'])]
        valid_std = ec_stats['std'][~np.isnan(ec_stats['std'])]
        
        if len(valid_cv) > 0:
            self.results_text.append(f"Overall Mean CV: {np.mean(valid_cv):.2f}%")
            self.results_text.append(f"Current CV: {valid_cv[-1]:.2f}%")
            self.results_text.append(f"Mean Value: {valid_mean[-1]:.2f} µS/cm")
            self.results_text.append(f"Std Deviation: {valid_std[-1]:.2f} µS/cm")
            self.results_text.append(f"\n{'='*50}")
            self.results_text.append("INTERPRETATION:")
            self.results_text.append("="*50)
            
            current_cv = valid_cv[-1]
            if current_cv < 2:
                self.results_text.append("✓ Very Stable (CV < 2%)")
                self.results_text.append("  → Excellent measurement stability")
                self.results_text.append("  → Suitable for precise measurements")
            elif current_cv < 5:
                self.results_text.append("○ Moderately Stable (CV < 5%)")
                self.results_text.append("  → Acceptable stability for most applications")
                self.results_text.append("  → Consider checking for noise sources")
            else:
                self.results_text.append("⚠ Variable (CV > 5%)")
                self.results_text.append("  → High variability detected")
                self.results_text.append("  → Check sensor stability and environment")
                self.results_text.append("  → May need calibration or troubleshooting")
        
    def show_smoothing(self):
        """Feature 8: Display smoothed data comparison"""
        data = self.get_parent_data()
        
        if not data or len(data['ec']) < 10:
            QMessageBox.information(
                self, "Insufficient Data",
                "Need at least 10 data points for smoothing.\n"
                "Current points: {}".format(len(data['ec']) if data else 0)
            )
            return
            
        self.results_text.clear()
        self.results_text.append("=" * 50)
        self.results_text.append("🌊 DATA SMOOTHING ANALYSIS")
        self.results_text.append("=" * 50)
        
        ec_array = np.array(data['ec'])
        
        # Apply smoothing methods
        ma_smoothed = self.smoother.moving_average(ec_array, window=5)
        sg_smoothed = self.smoother.savgol_filter(ec_array, window=11, polyorder=3)
        median_smoothed = self.smoother.median_filter(ec_array, kernel_size=5)
        
        # Plot
        self.analysis_figure.clear()
        ax = self.analysis_figure.add_subplot(111)
        
        times = np.array(data['time'])
        
        # Raw data
        ax.plot(times, ec_array, 'o', alpha=0.3, markersize=3,
               label='Raw Data', color='gray', zorder=1)
        
        # Smoothed versions
        if len(ma_smoothed) > 0:
            # Align time axis
            ma_times = times[len(times)-len(ma_smoothed):]
            ax.plot(ma_times, ma_smoothed, '-', linewidth=2,
                   label='Moving Average (5pt)', color='#228be6', zorder=2)
        
        if len(sg_smoothed) > 0:
            ax.plot(times, sg_smoothed, '-', linewidth=2,
                   label='Savitzky-Golay (11pt)', color='#fa5252', zorder=3)
        
        if len(median_smoothed) > 0:
            ax.plot(times, median_smoothed, '-', linewidth=2,
                   label='Median Filter (5pt)', color='#51cf66', zorder=4)
        
        ax.set_xlabel('Time (s)', fontweight='bold', fontsize=11)
        ax.set_ylabel('EC (µS/cm)', fontweight='bold', fontsize=11)
        ax.set_title('Data Smoothing Comparison', fontweight='bold', fontsize=13)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        self.analysis_figure.tight_layout()
        self.analysis_canvas.draw()
        
        # Calculate noise reduction
        original_std = np.std(ec_array)
        
        results = []
        if len(ma_smoothed) > 0:
            ma_std = np.std(ma_smoothed)
            ma_reduction = ((original_std - ma_std) / original_std * 100)
            results.append(("Moving Average", ma_std, ma_reduction))
        
        if len(sg_smoothed) > 0:
            sg_std = np.std(sg_smoothed)
            sg_reduction = ((original_std - sg_std) / original_std * 100)
            results.append(("Savitzky-Golay", sg_std, sg_reduction))
        
        if len(median_smoothed) > 0:
            med_std = np.std(median_smoothed)
            med_reduction = ((original_std - med_std) / original_std * 100)
            results.append(("Median Filter", med_std, med_reduction))
        
        # Display results
        self.results_text.append(f"Original Signal:")
        self.results_text.append(f"  Std Deviation: {original_std:.2f} µS/cm")
        self.results_text.append(f"\nSmoothing Results:")
        self.results_text.append("-" * 50)
        
        for method, std, reduction in results:
            self.results_text.append(f"\n{method}:")
            self.results_text.append(f"  Std Deviation: {std:.2f} µS/cm")
            self.results_text.append(f"  Noise Reduction: {reduction:.1f}%")
        
        self.results_text.append(f"\n{'='*50}")
        self.results_text.append("RECOMMENDATION:")
        self.results_text.append("="*50)
        self.results_text.append("• Moving Average: Best for general smoothing")
        self.results_text.append("• Savitzky-Golay: Preserves peaks/features")
        self.results_text.append("• Median Filter: Best for spike removal")
        
    def show_correlation(self):
        """Feature 9: Display correlation matrix"""
        data = self.get_parent_data()
        
        if not data or len(data['ec']) < 10:
            QMessageBox.information(
                self, "Insufficient Data",
                "Need at least 10 data points for correlation analysis.\n"
                "Current points: {}".format(len(data['ec']) if data else 0)
            )
            return
            
        self.results_text.clear()
        self.results_text.append("=" * 50)
        self.results_text.append("🔗 CORRELATION ANALYSIS")
        self.results_text.append("=" * 50)
        
        result, error = self.correlation.calculate_correlation(
            data['ec'], data['temp'], data['ph']
        )
        
        if error:
            self.results_text.append(f"Error: {error}")
            return
        
        # Plot correlation matrix heatmap
        self.analysis_figure.clear()
        ax = self.analysis_figure.add_subplot(111)
        
        im = ax.imshow(result['matrix'], cmap='coolwarm', vmin=-1, vmax=1,
                      aspect='auto', interpolation='nearest')
        
        # Colorbar
        cbar = self.analysis_figure.colorbar(im, ax=ax)
        cbar.set_label('Correlation Coefficient', rotation=270, labelpad=20, fontweight='bold')
        
        # Labels
        labels = ['EC', 'Temperature', 'pH']
        ax.set_xticks([0, 1, 2])
        ax.set_yticks([0, 1, 2])
        ax.set_xticklabels(labels, fontweight='bold')
        ax.set_yticklabels(labels, fontweight='bold')
        
        # Add correlation values as text
        for i in range(3):
            for j in range(3):
                value = result['matrix'][i, j]
                text_color = 'white' if abs(value) > 0.5 else 'black'
                ax.text(j, i, f'{value:.3f}',
                       ha="center", va="center",
                       color=text_color, fontweight='bold', fontsize=12)
        
        ax.set_title("Sensor Correlation Matrix", fontweight='bold', fontsize=13, pad=15)
        
        self.analysis_figure.tight_layout()
        self.analysis_canvas.draw()
        
        # Text results
        self.results_text.append("Correlation Coefficients:")
        self.results_text.append("-" * 50)
        self.results_text.append(f"EC - Temperature:   {result['ec_temp']:+.4f}")
        self.results_text.append(f"EC - pH:            {result['ec_ph']:+.4f}")
        self.results_text.append(f"Temperature - pH:   {result['temp_ph']:+.4f}")
        
        self.results_text.append(f"\n{'='*50}")
        self.results_text.append("INTERPRETATION:")
        self.results_text.append("="*50)
        
        # EC-Temperature correlation
        ec_temp_corr = abs(result['ec_temp'])
        self.results_text.append(f"\nEC-Temperature Correlation: {result['ec_temp']:+.3f}")
        if ec_temp_corr > 0.7:
            self.results_text.append("  ⚠ Strong correlation detected!")
            self.results_text.append("  → Temperature significantly affects EC readings")
            self.results_text.append("  → Recommendation: Enable temperature compensation")
        elif ec_temp_corr > 0.3:
            self.results_text.append("  ○ Moderate correlation")
            self.results_text.append("  → Some temperature influence present")
            self.results_text.append("  → Consider temperature compensation")
        else:
            self.results_text.append("  ✓ Weak correlation")
            self.results_text.append("  → Temperature compensation working well")
            self.results_text.append("  → Or minimal temperature effect")
        
        # EC-pH correlation
        ec_ph_corr = abs(result['ec_ph'])
        self.results_text.append(f"\nEC-pH Correlation: {result['ec_ph']:+.3f}")
        if ec_ph_corr > 0.5:
            self.results_text.append("  → EC and pH are related (expected in some solutions)")
        else:
            self.results_text.append("  → EC and pH are independent")
        
    def show_fft(self):
        """Feature 10: Display FFT frequency analysis"""
        data = self.get_parent_data()
        
        if not data or len(data['ec']) < 20:
            QMessageBox.information(
                self, "Insufficient Data",
                "Need at least 20 data points for FFT analysis.\n"
                "Current points: {}".format(len(data['ec']) if data else 0)
            )
            return
            
        self.results_text.clear()
        self.results_text.append("=" * 50)
        self.results_text.append("📊 FFT FREQUENCY ANALYSIS")
        self.results_text.append("=" * 50)
        
        # Calculate sampling rate from time data
        times = np.array(data['time'])
        if len(times) > 1:
            time_diffs = np.diff(times)
            avg_interval = np.mean(time_diffs)
            sampling_rate = 1.0 / avg_interval if avg_interval > 0 else 0.33
        else:
            sampling_rate = 0.33
        
        self.results_text.append(f"Sampling Rate: {sampling_rate:.3f} Hz")
        self.results_text.append(f"Sampling Interval: {1/sampling_rate:.1f} s\n")
        
        # Perform FFT
        result, error = self.fft.analyze(data['ec'], sampling_rate)
        
        if error:
            self.results_text.append(f"Error: {error}")
            return
        
        # Plot frequency spectrum
        self.analysis_figure.clear()
        ax = self.analysis_figure.add_subplot(111)
        
        ax.plot(result['frequencies'], result['amplitudes'],
               'b-', linewidth=2, label='Frequency Spectrum')
        
        # Mark dominant frequencies
        for i, (freq, amp) in enumerate(zip(result['dominant_freq'], result['dominant_amp'])):
            ax.axvline(freq, color='r', linestyle='--', alpha=0.5, linewidth=1.5)
            period = result['periods'][i]
            label_text = f'{freq:.4f} Hz\n({period:.1f}s)' if period > 0 else f'{freq:.4f} Hz'
            ax.text(freq, amp, label_text,
                   rotation=0, fontsize=9, ha='left', va='bottom',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
        
        ax.set_xlabel('Frequency (Hz)', fontweight='bold', fontsize=11)
        ax.set_ylabel('Amplitude', fontweight='bold', fontsize=11)
        ax.set_title('FFT Spectrum - EC Signal', fontweight='bold', fontsize=13)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='best')
        
        self.analysis_figure.tight_layout()
        self.analysis_canvas.draw()
        
        # Text results
        self.results_text.append("Dominant Frequencies:")
        self.results_text.append("-" * 50)
        
        for i, (freq, period, amp) in enumerate(zip(result['dominant_freq'], 
                                                     result['periods'],
                                                     result['dominant_amp']), 1):
            self.results_text.append(f"\n{i}. Frequency: {freq:.5f} Hz")
            self.results_text.append(f"   Period: {period:.1f} seconds")
            self.results_text.append(f"   Amplitude: {amp:.2f}")
        
        self.results_text.append(f"\n{'='*50}")
        self.results_text.append("INTERPRETATION:")
        self.results_text.append("="*50)
        
        # Interpret results
        if len(result['dominant_freq']) > 0:
            highest_freq = result['dominant_freq'][0]
            highest_period = result['periods'][0]
            
            if highest_period > 0:
                if 55 < highest_period < 65:
                    self.results_text.append("\n⚠ ~60s period detected:")
                    self.results_text.append("  → Likely AC line noise (60Hz electrical)")
                    self.results_text.append("  → Check grounding and shielding")
                elif 45 < highest_period < 55:
                    self.results_text.append("\n⚠ ~50s period detected:")
                    self.results_text.append("  → Likely 50Hz electrical interference")
                    self.results_text.append("  → Check power supply and cables")
                elif highest_period > 100:
                    self.results_text.append(f"\n○ Long period detected (~{highest_period:.0f}s):")
                    self.results_text.append("  → Possible environmental cycling")
                    self.results_text.append("  → Check temperature/airflow variations")
                else:
                    self.results_text.append(f"\n○ Period: {highest_period:.1f}s")
                    self.results_text.append("  → Check for periodic disturbances")
            
            if highest_freq < 0.01:
                self.results_text.append("\n✓ No significant high-frequency noise")
                self.results_text.append("  → Signal quality is good")
        else:
            self.results_text.append("\n✓ No dominant frequencies detected")
            self.results_text.append("  → Random noise only (expected)")

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
    window.setWindowTitle("Analysis Module 2A - Test")
    window.setGeometry(100, 100, 1200, 800)
    
    # Create the analysis tab
    analysis_tab = AnalysisTab2A()
    window.setCentralWidget(analysis_tab)
    
    # Create some test data (simulating parent's plot_widget)
    class MockPlotWidget:
        def __init__(self):
            t = np.linspace(0, 300, 100)
            self.time_data = t.tolist()
            # EC with some noise and trend
            self.ec_data = (1000 + 50*np.sin(0.1*t) + 10*np.random.randn(100)).tolist()
            # Temperature with slow drift
            self.temp_data = (25 + 0.01*t + 0.5*np.random.randn(100)).tolist()
            # pH relatively stable
            self.ph_data = (7.0 + 0.1*np.random.randn(100)).tolist()
    
    # Attach mock data to window
    window.plot_widget = MockPlotWidget()
    
    window.show()
    
    print("=" * 60)
    print("SENSOR ANALYSIS MODULE 2A - STANDALONE TEST")
    print("=" * 60)
    print("\nThis module provides 4 analysis tools:")
    print("  1. Rolling Statistics - assess stability")
    print("  2. Data Smoothing - compare filters")
    print("  3. Correlation Matrix - sensor relationships")
    print("  4. FFT Analysis - detect periodic patterns")
    print("\nClick the buttons to test each analysis!")
    print("=" * 60)
    
    sys.exit(app.exec_())

