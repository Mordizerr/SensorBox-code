file:///home/raspberry/Downloads/Sensor_Reader_v6.py {"mtime":1741392085212,"ctime":1731081160780,"size":22007,"etag":"3drgmjqsamrs","orphaned":false,"typeId":""}
#!/usr/bin/python3

import sys
import time
import os
import glob
import csv
import serial
import matplotlib
matplotlib.use('Qt5Agg')  # Set the backend to Qt5Agg for compatibility with PyQt5
from PyQt5.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget, QApplication, QGroupBox, QHBoxLayout, QLineEdit, QPushButton
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QTimer
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from DFRobot_ADS1115 import ADS1115
from DFRobot_PH import DFRobot_PH
import threading
from datetime import datetime

class UARTCommunication:
    def __init__(self, port='/dev/ttyAMA0', baudrate=115200):
        # Set up the port, baudrate, and initial values
        self.port = port 
        self.baudrate = baudrate
        self.conductivity = None  # To store the latest conductivity value
        self.temperature = None    # To store the latest temperature value
        self.ph_value = None       # To store the latest pH value
        self.lock = threading.Lock()  # Lock for thread safety
        self.running = True  # Flag to control the read thread

        # Initialize UART communication and handle potential errors
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            if not self.ser.is_open:
                self.ser.open()
            time.sleep(1)  # Wait for serial connection to initialize
        except (serial.SerialException, TypeError) as e:
            print(f"Error opening serial port: {e}")
            self.ser = None  # Set ser to None if initialization fails

        # Start a thread for reading from UART if initialization succeeded
        if self.ser:
            self.read_thread = threading.Thread(target=self.read_uart)
            self.read_thread.daemon = True  # Daemonize thread to close with main program
            self.read_thread.start()

    def send_command(self, command):
        # Send a command over UART, ensuring the serial connection is open
        if self.ser and self.ser.is_open:
            self.ser.write(command.encode('utf-8'))
        else:
            print("Serial connection not open. Cannot send command.")

    def get_conductivity(self):
        # Safely return the stored conductivity value
        with self.lock:
            return self.conductivity
        
    def get_temperature(self):
        # Safely return the stored temperature value
        with self.lock:
            return self.temperature
    
    def get_ph_value(self):
        # Safely return the stored pH value
        with self.lock:
            return self.ph_value

    def process_response(self, response):
        # Extract and store the conductivity, temperature, and pH value if present in the response
        with self.lock:  # Lock when modifying shared resource
            try:
                if "Conductivity:" in response:
                    # Extract conductivity value from the response string
                    conductivity_value = float(response.split("Conductivity: ")[1].split(" us/cm")[0])
                    self.conductivity = conductivity_value  # Store conductivity value
    
                if "Temperature:" in response:
                    # Extract temperature value from the response string
                    temp_str = response.split("Temperature: ")[1].split(" ")[0]
                    # Clean the temperature string by replacing invalid characters
                    temp_str = temp_str.replace('�', '').replace('�', '')  # Adjust this as necessary for specific characters
                    temperature_value = float(temp_str)
                    self.temperature = temperature_value  # Store temperature value

                if "pH Value:" in response:
                    # Extract pH value from the response string
                    ph_value = float(response.split("pH Value: ")[1].split(" ")[0])
                    self.ph_value = ph_value  # Store pH value
    
            except (ValueError, IndexError) as e:
                print(f"Error processing response: {response}, Error: {e}")

    def read_uart(self):
        # Continuously read from UART and process responses without sending "READ" automatically
        while self.running:
            # Check if data is available and read it
            if self.ser and self.ser.is_open and self.ser.in_waiting > 0:
                try:
                    response = self.ser.readline().decode('utf-8').strip()  # Read response
                    self.process_response(response)  # Process the response
                except Exception as e:
                    print(f"Error reading from UART: {e}")
            time.sleep(1)  # Sleep to prevent tight loop and CPU overload

    def close(self):
        # Close the serial connection and stop the read thread when done
        self.running = False  # Stop the read thread
        if self.ser and self.ser.is_open:
            self.ser.close()
        print("Serial connection closed.")


# Data Logger Class
class DataLogger:
    def __init__(self):
        # Ensure the directory exists
        self.directory = "logs"
        os.makedirs(self.directory, exist_ok=True)

        # Create a unique filename based on the current date and time
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        self.filename = os.path.join(self.directory, f"sensor_data_{timestamp}.csv")

        # Define the fieldnames for the CSV file
        self.fieldnames = ["Timestamp", "Elapsed Time", "Temperature", "EC (us/cm)", "pH Value"]

        # Create the CSV file and write the header if it doesn't exist
        if not os.path.isfile(self.filename):
            with open(self.filename, mode='w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=self.fieldnames)
                writer.writeheader()

    def log_data(self, elapsed_time, temp2, ec, ph_value):
        """Log a new row of data to the CSV file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_row = {
            "Timestamp": timestamp,
            "Elapsed Time": elapsed_time,
            "Temperature": temp2,
            "EC (us/cm)": ec,
            "pH Value": ph_value  # Log pH value
        }

        # Append the data to the CSV file
        with open(self.filename, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=self.fieldnames)
            writer.writerow(data_row)


class DataPlotter(QWidget):
    def __init__(self, max_points=50):
        super().__init__()

        # Create a figure and a canvas to plot on
        self.figure = plt.figure(figsize=(8, 10))

        # Create the main vertical layout for the DataPlotter
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)  # Set spacing to zero
        self.main_layout.setContentsMargins(0, 0, 0, 0)  # Set margins to zero
        self.setLayout(self.main_layout)

        # Initialize data lists
        self.time_data = []
        self.temp_uart_data = []  # New data for UART temperature
        self.ec2_data = []  # Data for second conductivity
        self.ph_data = []

        # Set the maximum number of points to display
        self.max_points = max_points

        # Create separate widgets for each graph
        self.temp2_widget = QWidget(self)
        self.ec2_widget = QWidget(self)
        self.ph_widget = QWidget(self)

        # Create canvases for each graph
        self.canvas_temp2 = FigureCanvas(plt.figure())
        self.canvas_ec2 = FigureCanvas(plt.figure())
        self.canvas_ph = FigureCanvas(plt.figure())

        # Set up the layout for each widget
        temp2_layout = QVBoxLayout()
        temp2_layout.addWidget(self.canvas_temp2)
        temp2_layout.setSpacing(0)  # Set spacing to zero for temperature 2
        temp2_layout.setContentsMargins(0, 0, 0, 0)  # Set margins to zero
        self.temp2_widget.setLayout(temp2_layout)

        ec2_layout = QVBoxLayout()
        ec2_layout.addWidget(self.canvas_ec2)
        ec2_layout.setSpacing(0)  # Set spacing to zero for EC 2
        ec2_layout.setContentsMargins(0, 0, 0, 0)  # Set margins to zero
        self.ec2_widget.setLayout(ec2_layout)

        ph_layout = QVBoxLayout()
        ph_layout.addWidget(self.canvas_ph)
        ph_layout.setSpacing(0)  # Set spacing to zero for pH
        ph_layout.setContentsMargins(0, 0, 0, 0)  # Set margins to zero
        self.ph_widget.setLayout(ph_layout)

        # Add widgets to the main layout
        self.main_layout.addWidget(self.temp2_widget)
        self.main_layout.addWidget(self.ec2_widget)
        self.main_layout.addWidget(self.ph_widget)

        self.ax_temp2 = self.canvas_temp2.figure.add_subplot(111)
        self.ax_temp2.set_title('Temperature (C)')
        self.ax_temp2.set_xlabel('Time (s)')
        self.ax_temp2.set_ylabel('Temperature (C)')

        self.ax_ec2 = self.canvas_ec2.figure.add_subplot(111)
        self.ax_ec2.set_title('EC (us/cm)')
        self.ax_ec2.set_xlabel('Time (s)')
        self.ax_ec2.set_ylabel('EC (us/cm)')

        self.ax_ph = self.canvas_ph.figure.add_subplot(111)
        self.ax_ph.set_title('pH Level')
        self.ax_ph.set_xlabel('Time (s)')
        self.ax_ph.set_ylabel('pH')

        # Adjust layout to prevent overlap
        self.figure.tight_layout()

    def update_plot(self, elapsed_time, temp_uart, ec2, ph):
        # Append new data
        self.time_data.append(elapsed_time)
        self.temp_uart_data.append(temp_uart)
        self.ec2_data.append(ec2)
        self.ph_data.append(ph)
    
        # Limit the number of points to the maximum defined
        if len(self.time_data) > self.max_points:
            self.time_data = self.time_data[-self.max_points:]
            self.temp_uart_data = self.temp_uart_data[-self.max_points:]
            self.ec2_data = self.ec2_data[-self.max_points:]
            self.ph_data = self.ph_data[-self.max_points:]
    
        # Clear previous plots
        self.ax_temp2.clear()
        self.ax_ec2.clear()
        self.ax_ph.clear()
    
        # Plot the data
        self.ax_temp2.plot(self.time_data, self.temp_uart_data, label='Temperature', color='purple')
        self.ax_ec2.plot(self.time_data, self.ec2_data, label='EC', color='blue')
        self.ax_ph.plot(self.time_data, self.ph_data, label='pH', color='orange')
    
        self.ax_temp2.set_title('Temperature (C)')
        self.ax_temp2.set_xlabel('Time (s)')
        self.ax_temp2.set_ylabel('Temperature (C)')
    
        self.ax_ec2.set_title('EC (us/cm)')
        self.ax_ec2.set_xlabel('Time (s)')
        self.ax_ec2.set_ylabel('EC (us/cm)')
    
        self.ax_ph.set_title('pH Level')
        self.ax_ph.set_xlabel('Time (s)')
        self.ax_ph.set_ylabel('pH')
    
        # Set y-axis limits with fixed values for temperatures and pH, and dynamic padding for EC2
        fixed_padding = 4  # Fixed padding for the max of Temperature and pH
    
        if self.temp_uart_data:
            y_max_temp2 = max(self.temp_uart_data) + fixed_padding
            self.ax_temp2.set_ylim(bottom=18, top=y_max_temp2)  # Fixed minimum of 15 for Temperature 2
    
        if self.ec2_data:
            y_min_ec2 = min(self.ec2_data)
            y_max_ec2 = max(self.ec2_data) + fixed_padding
            self.ax_ec2.set_ylim(bottom=y_min_ec2, top=y_max_ec2)  # Dynamic minimum for EC2
    
        if self.ph_data:
            y_max_ph = max(self.ph_data) + fixed_padding
            self.ax_ph.set_ylim(bottom=0, top=y_max_ph)  # Fixed minimum of 0 for pH
    
        # Refresh the canvases
        self.canvas_temp2.draw()
        self.canvas_ec2.draw()
        self.canvas_ph.draw()


class SensorReader:
    def __init__(self):

        # Temperature sensor initialization
        os.system('modprobe w1-gpio')
        os.system('modprobe w1-therm')
        #self.device_folder = glob.glob('/sys/bus/w1/devices/' + '28*')[0]
        #self.device_file = self.device_folder + '/w1_slave'

#    def read_temp_raw(self):
#        with open(self.device_file, 'r') as f:
#            lines = f.readlines()
#        return lines
#
#    def read_temp(self):
#        lines = self.read_temp_raw()
#        while 'YES' not in lines[0]:
#            time.sleep(0.2)
#            lines = self.read_temp_raw()
#        equals_pos = lines[1].find('t=')
#        if equals_pos != -1:
#            temp_string = lines[1][equals_pos+2:]
#            temp_c = float(temp_string) / 1000.0
#            return temp_c
#        return None

    def read_temp(self):
        return 25

class SensorWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.average_points = 1
        self.conductivity_buffer = []
        self.temperature_uart_buffer = []
        self.ph_value_buffer = []

        self.setWindowTitle("Sensor Data Monitoring")

        # Create central widget
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        # Create a horizontal layout to hold both text and graph side by side
        self.main_layout = QHBoxLayout(self.central_widget)

        # Create an instance of SensorReader
        self.sensor_reader = SensorReader()

        # Create an instance of UARTCommunication
        self.uart_communication = UARTCommunication()

        # Create a QGroupBox to hold the text labels (vertically)
        self.label_group_box = QGroupBox("Sensor Data", self)
        self.label_layout = QVBoxLayout()  # Vertically place the labels

        # Create labels for displaying data
        self.labels = {
            "Elapsed Time": QLabel("Elapsed Time: 0 sec"),
            "Temperature": QLabel("Temperature: "),  # New label for UART temperature
            "EC": QLabel("EC: "),  # Second conductivity label
            "pH Value": QLabel("pH Value: ")  # New label for pH value
        }

        # Adjust font size and style for the labels
        font = QFont("Arial", 20)  # Set the font to Arial and size 20
        for label in self.labels.values():
            label.setFont(font)

        # Add labels to the label layout
        for label in self.labels.values():
            self.label_layout.addWidget(label)

        # Create buttons for changing average_points
        self.average_buttons = QHBoxLayout()
        self.average_1_button = QPushButton("1")
        self.average_3_button = QPushButton("3")
        self.average_5_button = QPushButton("5")
        self.average_buttons.addWidget(self.average_1_button)
        self.average_buttons.addWidget(self.average_3_button)
        self.average_buttons.addWidget(self.average_5_button)

        # Connect buttons to functions
        self.average_1_button.clicked.connect(lambda: self.set_average_points(1, self.average_1_button))
        self.average_3_button.clicked.connect(lambda: self.set_average_points(3, self.average_3_button))
        self.average_5_button.clicked.connect(lambda: self.set_average_points(5, self.average_5_button))

        # Create buttons for changing measurement_interval
        self.interval_buttons = QHBoxLayout()
        self.interval_3_button = QPushButton("3s")
        self.interval_5_button = QPushButton("5s")
        self.interval_10_button = QPushButton("10s")
        self.interval_buttons.addWidget(self.interval_3_button)
        self.interval_buttons.addWidget(self.interval_5_button)
        self.interval_buttons.addWidget(self.interval_10_button)

        # Connect buttons to functions
        self.interval_3_button.clicked.connect(lambda: self.set_measurement_interval(3, self.interval_3_button))
        self.interval_5_button.clicked.connect(lambda: self.set_measurement_interval(5, self.interval_5_button))
        self.interval_10_button.clicked.connect(lambda: self.set_measurement_interval(10, self.interval_10_button))

        # Add button layouts to the label layout
        self.label_layout.addLayout(self.average_buttons)
        self.label_layout.addLayout(self.interval_buttons)

        # Set the layout for the label group box
        self.label_group_box.setLayout(self.label_layout)

        # Add the QGroupBox to the main layout (left side)
        self.main_layout.addWidget(self.label_group_box)

        # Create an instance of DataPlotter and add it to the main layout (right side)
        self.data_plotter = DataPlotter()
        self.main_layout.addWidget(self.data_plotter)

        # Set stretch factors for the main layout
        self.main_layout.setStretch(0, 3)  # Left layout (30%)
        self.main_layout.setStretch(1, 7)  # Right layout (70%)

        # Create an instance of DataLogger
        self.data_logger = DataLogger()

        # Create a variable for the measurement interval (in seconds)
        self.measurement_interval = 3  # Default value
        self.elapsed_time = 0  # Initialize elapsed time

        # Create a timer to update sensor data
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_sensor_data)
        print(f"Measurement Interval: {self.measurement_interval} seconds")
        self.timer.start(int(self.measurement_interval * 1000))  # Convert to milliseconds

        # Create a separate timer for UART communication (READ command)
        self.uart_timer = QTimer()
        self.uart_timer.timeout.connect(self.send_read_command)
        self.uart_timer.start(self.measurement_interval * 1000)  # 1-second interval for UART communication

        # Track the last pressed buttons
        self.last_pressed_average_button = None
        self.last_pressed_interval_button = None

    def reset_average_buttons(self):
        self.average_1_button.setStyleSheet("")
        self.average_3_button.setStyleSheet("")
        self.average_5_button.setStyleSheet("")

    def reset_interval_buttons(self):
        self.interval_3_button.setStyleSheet("")
        self.interval_5_button.setStyleSheet("")
        self.interval_10_button.setStyleSheet("")

    def set_average_points(self, points, button):
        print(f"Setting average points to {points}")
        self.average_points = points
        self.reset_average_buttons()
        button.setStyleSheet("background-color: yellow; border: 1px solid black;")
        self.last_pressed_average_button = button
        print(f"Average points set to: {self.average_points}")

    def set_measurement_interval(self, interval, button):
        print(f"Setting measurement interval to {interval} seconds")
        self.measurement_interval = interval
        self.reset_interval_buttons()
        button.setStyleSheet("background-color: yellow; border: 1px solid black;")
        self.last_pressed_interval_button = button
        self.timer.start(int(self.measurement_interval * 1000))
        self.uart_timer.start(self.measurement_interval * 1000)
        print(f"Measurement interval set to: {self.measurement_interval} seconds")

    def update_sensor_data(self):
        print(f"update_sensor_data() called at: {time.time()}")  # Debug print
        self.read_and_update()  # Call directly, not in a new thread

    def read_and_update(self):
        # Get the conductivity (EC 2) from UART communication
        conductivity = self.uart_communication.get_conductivity()
        temperature_uart = self.uart_communication.get_temperature()
        ph_value = self.uart_communication.get_ph_value()  # Get the pH value from UART

        # Ensure all data was read correctly before updating
        if conductivity is not None and temperature_uart is not None and ph_value is not None:
            # Append data to buffers
            self.conductivity_buffer.append(conductivity)
            self.temperature_uart_buffer.append(temperature_uart)
            self.ph_value_buffer.append(ph_value)

            # Check if we have enough data points to average
            if len(self.conductivity_buffer) >= self.average_points:
                avg_conductivity = sum(self.conductivity_buffer) / len(self.conductivity_buffer)
                avg_temperature_uart = sum(self.temperature_uart_buffer) / len(self.temperature_uart_buffer)
                avg_ph_value = sum(self.ph_value_buffer) / len(self.ph_value_buffer)

                # Clear buffers
                self.conductivity_buffer.clear()
                self.temperature_uart_buffer.clear()
                self.ph_value_buffer.clear()

                # Increment elapsed time
                self.elapsed_time += self.measurement_interval * self.average_points  # Increment by the total interval

                # Update labels with new values
                self.labels["Temperature"].setText(f"Temperature: {avg_temperature_uart:.2f} C")
                self.labels["EC"].setText(f"EC: {avg_conductivity:.2f} us/cm")  # EC from UART
                self.labels["pH Value"].setText(f"pH Value: {avg_ph_value:.2f}")  # Update pH value label

                # Update the elapsed time label
                self.labels["Elapsed Time"].setText(f"Elapsed Time: {self.elapsed_time:.2f}s")

                # Log the data, including pH value
                self.data_logger.log_data(self.elapsed_time, avg_temperature_uart, avg_conductivity, avg_ph_value)

                # Update the plot with all parameters, including UART temperature and pH value
                self.data_plotter.update_plot(self.elapsed_time, avg_temperature_uart, avg_conductivity, avg_ph_value)  # Pass pH value

    def send_read_command(self):
        # Send the READ command periodically
        command = "READ\n"
        print(f"[{time.strftime('%H:%M:%S')}] Sending UART command: {command.strip()}")
        self.uart_communication.send_command(command)

    def closeEvent(self, event):
        self.uart_communication.close()  # Close UART communication on exit
        event.accept()  # Accept the close event


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SensorWindow()
    window.showMaximized()
    sys.exit(app.exec_())
