#include "DFRobot_ECPRO.h"

// Define the EC, Temperature, and pH analog pins
#define EC_PIN A1
#define TE_PIN A2
#define SensorPin A3  // pH meter Analog output

// pH meter settings
#define Offset 0.00         // Deviation compensate
#define LED 13
#define ArrayLenth 40       // Number of samples for pH averaging

DFRobot_ECPRO ec;
DFRobot_ECPRO_PT1000 ecpt;

uint16_t InputVoltage, TempVoltage;
float Conductivity, Temperature;
int pHArray[ArrayLenth];    // Store pH sensor feedback values
int pHArrayIndex = 0;       // Index for storing pH values
String inputString = "";    // String to hold incoming data from Serial Monitor
static float pHValue, voltage;  // To store the latest pH value and voltage

void setup() {
  Serial.begin(115200);

  // Conductivity sensor initialization
  ec.setCalibration(1);  // Replace with your specific calibration value
  Serial.println("Sensors Initialized");

  // pH sensor initialization
  pinMode(LED, OUTPUT);
  Serial.println("pH Sensor setup completed.");
}

void loop() {
  // Only proceed if a command is received over Serial
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    // Check if the command is "READ" to gather sensor readings
    if (command.equalsIgnoreCase("READ")) {
      
      // 1. Read EC and Temperature sensor voltages
      InputVoltage = (uint32_t)analogRead(EC_PIN) * 5000 / 1024;
      TempVoltage = (uint32_t)analogRead(TE_PIN) * 5000 / 1024;

      // Convert Temp voltage to Celsius
      Temperature = ecpt.convVoltagetoTemperature_C((float)TempVoltage / 1000);

      // Calculate conductivity using the EC input voltage and temperature
      Conductivity = ec.getEC_us_cm(InputVoltage, Temperature);

      // 2. Read pH sensor data only when READ command is received
      // Collect 40 samples of pH readings
      for (int i = 0; i < ArrayLenth; i++) {
        pHArray[i] = analogRead(SensorPin);
        delay(20);  // Sampling interval (20ms)
      }

      // Calculate pH voltage and value
      voltage = avergearray(pHArray, ArrayLenth) * 5.0 / 1024;
      pHValue = 3.5 * voltage + Offset;

      // 3. Output all sensor readings over Serial
      Serial.print("InputVoltage: ");
      Serial.print(InputVoltage);
      Serial.print(" mV\t");

      Serial.print("Conductivity: ");
      Serial.print(Conductivity);
      Serial.print(" us/cm\t");

      Serial.print("TempVoltage: ");
      Serial.print(TempVoltage);
      Serial.print(" mV\t");

      Serial.print("Temperature: ");
      Serial.print(Temperature);
      Serial.print(" ℃\t");

      Serial.print("pH Voltage: ");
      Serial.print(voltage, 2);
      Serial.print(" V\t");

      Serial.print("pH Value: ");
      Serial.println(pHValue, 2);

      // Toggle the LED to indicate a measurement was taken
      digitalWrite(LED, digitalRead(LED) ^ 1);
    }
  }
}

double avergearray(int* arr, int number) {
  int i;
  int max, min;
  double avg;
  long amount = 0;

  if (number <= 0) {
    Serial.println("Error: invalid array length for averaging!");
    return 0;
  }

  if (number < 5) {   // Less than 5, calculate directly
    for (i = 0; i < number; i++) {
      amount += arr[i];
    }
    avg = amount / number;
    return avg;
  } else {
    // Handle outliers
    if (arr[0] < arr[1]) {
      min = arr[0];
      max = arr[1];
    } else {
      min = arr[1];
      max = arr[0];
    }

    for (i = 2; i < number; i++) {
      if (arr[i] < min) {
        amount += min;
        min = arr[i];
      } else if (arr[i] > max) {
        amount += max;
        max = arr[i];
      } else {
        amount += arr[i];
      }
    }
    avg = (double)amount / (number - 2);
  }
  return avg;
}
