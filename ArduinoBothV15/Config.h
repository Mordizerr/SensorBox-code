/*******************************************************************************
 * CONFIG.H - System Configuration & Constants (COMPLETE - ALL SENSORS)
 * 
 * Purpose:
 *   Central configuration file for the Multi-Sensor Calibration System.
 *   Contains all constants, enumerations, pin assignments, and default values
 *   for EC, pH, AND Temperature sensors.
 * 
 * Author: System Rewrite v1.0 - Complete Edition
 * Date: 2026-02-16
 * 
 * Hardware:
 *   - Arduino Uno (ATmega328P)
 *   - EC Sensor on A1 (0-5V analog output)
 *   - Temperature Sensor on A2 (0-5V analog output)
 *   - pH Sensor on A3 (0-5V analog output)
 ******************************************************************************/

#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

/*******************************************************************************
 * HARDWARE PIN ASSIGNMENTS
 ******************************************************************************/

// Analog sensor pins
const uint8_t PIN_EC_SENSOR        = A1;  // EC (Electrical Conductivity) sensor
const uint8_t PIN_TEMP_SENSOR      = A2;  // Temperature sensor
const uint8_t PIN_PH_SENSOR        = A3;  // pH sensor

/*******************************************************************************
 * EC CALIBRATION MODES
 * 
 * EC Low Range Modes:
 *   - LOW_3PT: Uses 3 calibration points (65.3, 500, 1413 µS/cm)
 *   - LOW_4PT: Uses 4 calibration points (65.3, 200, 500, 1413 µS/cm)
 *   - LOW_5PT: Uses 5 calibration points (65.3, 200, 500, 1413, 2000 µS/cm)
 * 
 * EC High Range Mode:
 *   - HIGH_2PT: Uses 2 calibration points (1413, 12880 µS/cm) - ONLY option
 ******************************************************************************/

enum ECLowMode {
  LOW_3PT = 3,  // 3-point calibration
  LOW_4PT = 4,  // 4-point calibration
  LOW_5PT = 5   // 5-point calibration
};

enum ECHighMode {
  HIGH_2PT = 2  // 2-point calibration (only mode available)
};

/*******************************************************************************
 * pH CALIBRATION MODES
 * 
 * pH calibration uses standard buffer solutions.
 * Linear regression maps voltage to pH value.
 * 
 * pH Modes:
 *   - PH_3PT: Uses 3 calibration points (pH 4.00, 7.00, 10.00) - Standard
 ******************************************************************************/

enum pHMode {
  PH_3PT = 3   // 3-point calibration (standard for pH)
};

/*******************************************************************************
 * TEMPERATURE CALIBRATION MODES
 * 
 * Temperature calibration uses known temperature references.
 * Linear regression maps voltage to temperature.
 * 
 * Temperature Modes:
 *   - TEMP_3PT: Uses 3 calibration points (0°C, 25°C, 50°C) - Standard
 ******************************************************************************/

enum TempMode {
  TEMP_3PT = 3  // 3-point calibration (standard for temperature)
};

/*******************************************************************************
 * CALIBRATION POINT LIMITS
 ******************************************************************************/

const uint8_t EC_LOW_CAL_POINTS    = 5;   // Maximum EC low range points
const uint8_t EC_HIGH_CAL_POINTS   = 2;   // Maximum EC high range points
const uint8_t PH_CAL_POINTS        = 3;   // pH calibration points
const uint8_t TEMP_CAL_POINTS      = 3;   // Temperature calibration points

/*******************************************************************************
 * DEFAULT EC CALIBRATION REFERENCE VALUES (µS/cm)
 * 
 * Standard EC values for calibration solutions.
 * Users can change these with SET_EC_LOW_x and SET_EC_HIGH_x commands.
 * 
 * EC Low Range Calibration Solutions:
 *   Point 0: 65.0 µS/cm   (Ultra-low conductivity)
 *   Point 1: 200.0 µS/cm  (Low conductivity)
 *   Point 2: 500.0 µS/cm  (Medium-low conductivity)
 *   Point 3: 1000.0 µS/cm (Medium conductivity)
 *   Point 4: 1413.0 µS/cm (Standard calibration solution)
 * 
 * EC High Range Calibration Solutions:
 *   Point 0: 1413.0 µS/cm  (Overlap with low range)
 *   Point 1: 12880.0 µS/cm (High conductivity)
 ******************************************************************************/

const float DEFAULT_EC_LOW_REF[EC_LOW_CAL_POINTS] = {
  65.0,    // Point 0
  200.0,   // Point 1
  500.0,   // Point 2
  1000.0,  // Point 3
  1413.0   // Point 4
};

const float DEFAULT_EC_HIGH_REF[EC_HIGH_CAL_POINTS] = {
  1413.0,  // Point 0 (overlaps with low range point 3)
  12880.0  // Point 1
};

/*******************************************************************************
 * DEFAULT pH CALIBRATION REFERENCE VALUES
 * 
 * Standard pH buffer solution values.
 * Users can change these with SET_PH_x commands.
 * 
 * pH Buffer Solutions:
 *   Point 0: 4.00 pH  (Acidic buffer - typically orange/red)
 *   Point 1: 7.00 pH  (Neutral buffer - typically yellow)
 *   Point 2: 10.00 pH (Alkaline buffer - typically blue)
 * 
 * These are the most common pH calibration buffers worldwide.
 ******************************************************************************/

const float DEFAULT_PH_REF[PH_CAL_POINTS] = {
  4.00,   // Point 0 - Acidic buffer
  7.00,   // Point 1 - Neutral buffer
  10.00   // Point 2 - Alkaline buffer
};

/*******************************************************************************
 * DEFAULT TEMPERATURE CALIBRATION REFERENCE VALUES (°C)
 * 
 * Standard temperature reference points.
 * Users can change these with SET_TEMP_x commands.
 * 
 * Temperature Reference Points:
 *   Point 0: 25.0°C  (Room temperature - reference standard)
 *   Point 1: 32.0°C  (Moderate warm temperature)
 *   Point 2: 40.0°C  (Warm water bath)
 * 
 * These cover a practical range for hydroponic/agricultural monitoring.
 ******************************************************************************/

const float DEFAULT_TEMP_REF[TEMP_CAL_POINTS] = {
  25.0,   // Point 0 - Room temperature
  32.0,   // Point 1 - Moderate warm
  40.0    // Point 2 - Warm water
};

/*******************************************************************************
 * EC VOLTAGE RANGE THRESHOLD
 * 
 * The voltage threshold that determines which EC calibration equation to use:
 *   - Voltage < 980 mV  → Use LOW range equation
 *   - Voltage ≥ 980 mV  → Use HIGH range equation
 ******************************************************************************/

const float EC_RANGE_THRESHOLD_MV  = 980.0;  // Millivolts

/*******************************************************************************
 * ADC & VOLTAGE CONVERSION CONSTANTS
 * 
 * Arduino Uno ADC specifications:
 *   - Resolution: 10-bit (0-1023)
 *   - Reference voltage: 5.0V
 *   - Conversion formula: V_mV = ADC × 5000 / 1024
 ******************************************************************************/

const uint16_t ADC_MAX             = 1023;    // 10-bit ADC maximum value
const float    ADC_REFERENCE_MV    = 5000.0;  // 5V reference in millivolts
const float    ADC_TO_MV_FACTOR    = ADC_REFERENCE_MV / 1024.0;  // 4.8828 mV per count

/*******************************************************************************
 * TEMPERATURE SENSOR CONVERSION CONSTANTS (UNCALIBRATED)
 * 
 * Temperature sensor uncalibrated conversion formula:
 *   T_celsius = (V_volts - TEMP_OFFSET) × TEMP_SCALE
 *   T_celsius = (V_volts - 0.176) × 39.93
 * 
 * This provides a baseline reading. Calibration will refine this.
 ******************************************************************************/

const float TEMP_OFFSET_V          = 0.176;   // Voltage offset in volts
const float TEMP_SCALE             = 39.93;   // Temperature scale factor

/*******************************************************************************
 * pH SENSOR CONVERSION CONSTANTS (UNCALIBRATED)
 * 
 * pH sensor uncalibrated conversion formula:
 *   pH = (V_mV - PH_NEUTRAL_MV) × PH_SLOPE + 7.0
 * 
 * This assumes:
 *   - pH 7 (neutral) is at ~2500 mV (mid-scale)
 *   - Typical pH electrode slope: ~59 mV/pH (Nernstian response)
 * 
 * Calibration will replace this with accurate equation.
 ******************************************************************************/

const float PH_NEUTRAL_MV          = 2500.0;  // Voltage at pH 7 (typical)
const float PH_MV_PER_UNIT         = -59.16;  // mV change per pH unit (negative for standard electrode)

/*******************************************************************************
 * CALIBRATION VALIDATION THRESHOLDS
 * 
 * These thresholds ensure calibration quality for all sensors.
 ******************************************************************************/

const float MIN_VOLTAGE_SEPARATION = 10.0;    // Minimum mV between points
const float MIN_VOLTAGE_SPAN       = 100.0;   // Minimum mV range (max - min)
const float MIN_R_SQUARED          = 0.95;    // Minimum acceptable R²

/*******************************************************************************
 * SENSOR READING PARAMETERS
 ******************************************************************************/

const uint8_t EC_SAMPLE_COUNT      = 3;       // EC samples to average
const uint8_t TEMP_SAMPLE_COUNT    = 3;       // Temperature samples to average
const uint8_t PH_SAMPLE_COUNT      = 10;      // pH samples to average
const uint8_t PH_SAMPLE_DELAY_MS   = 20;      // Delay between pH samples (ms)

/*******************************************************************************
 * OPTIONAL FILTERING
 ******************************************************************************/

const float FILTER_ALPHA           = 0.3;     // Exponential filter coefficient

/*******************************************************************************
 * EEPROM STORAGE STRUCTURE
 * 
 * Memory layout for persistent calibration storage (ALL SENSORS):
 * 
 * Offset  Size  Content
 * ------  ----  -------------------------------------------------------
 *      0     2  Magic number (0xEC57)
 *      2     1  Version (1)
 *      3     1  EC low calibration mode (3, 4, or 5)
 *      4     1  EC high calibration mode (2)
 *      5     1  pH calibration mode (3)
 *      6     1  Temperature calibration mode (3)
 *      7     1  (padding)
 *      
 *      8     4  EC Low equation C (float)
 *     12     4  EC Low equation D (float)
 *     16     4  EC Low equation R² (float)
 *     20     4  EC Low equation RMSE (float)
 *     
 *     24     4  EC High equation C (float)
 *     28     4  EC High equation D (float)
 *     32     4  EC High equation R² (float)
 *     36     4  EC High equation RMSE (float)
 *     
 *     40     4  pH equation C (float)
 *     44     4  pH equation D (float)
 *     48     4  pH equation R² (float)
 *     52     4  pH equation RMSE (float)
 *     
 *     56     4  Temp equation C (float)
 *     60     4  Temp equation D (float)
 *     64     4  Temp equation R² (float)
 *     68     4  Temp equation RMSE (float)
 *     
 *     72    20  EC Low voltages[5] (5 × 4-byte floats)
 *     92     8  EC High voltages[2] (2 × 4-byte floats)
 *    100    12  pH voltages[3] (3 × 4-byte floats)
 *    112    12  Temp voltages[3] (3 × 4-byte floats)
 *    
 *    124    20  EC Low reference values[5]
 *    144     8  EC High reference values[2]
 *    152    12  pH reference values[3]
 *    164    12  Temp reference values[3]
 *    
 *    176     1  Flag: isECLowCalibrated
 *    177     1  Flag: isECHighCalibrated
 *    178     1  Flag: ispHCalibrated
 *    179     1  Flag: isTempCalibrated
 *    
 *    180     2  CRC16 checksum
 * 
 * Total: 182 bytes
 ******************************************************************************/

const uint16_t EEPROM_MAGIC        = 0xEC57;  // Magic number
const uint8_t  EEPROM_VERSION      = 1;       // Storage format version

// EEPROM address offsets
const uint16_t ADDR_MAGIC          = 0;
const uint16_t ADDR_VERSION        = 2;
const uint16_t ADDR_EC_LOW_MODE    = 3;
const uint16_t ADDR_EC_HIGH_MODE   = 4;
const uint16_t ADDR_PH_MODE        = 5;
const uint16_t ADDR_TEMP_MODE      = 6;

const uint16_t ADDR_EC_LOW_EQ_C    = 8;
const uint16_t ADDR_EC_LOW_EQ_D    = 12;
const uint16_t ADDR_EC_LOW_EQ_R2   = 16;
const uint16_t ADDR_EC_LOW_EQ_RMSE = 20;

const uint16_t ADDR_EC_HIGH_EQ_C   = 24;
const uint16_t ADDR_EC_HIGH_EQ_D   = 28;
const uint16_t ADDR_EC_HIGH_EQ_R2  = 32;
const uint16_t ADDR_EC_HIGH_EQ_RMSE= 36;

const uint16_t ADDR_PH_EQ_C        = 40;
const uint16_t ADDR_PH_EQ_D        = 44;
const uint16_t ADDR_PH_EQ_R2       = 48;
const uint16_t ADDR_PH_EQ_RMSE     = 52;

const uint16_t ADDR_TEMP_EQ_C      = 56;
const uint16_t ADDR_TEMP_EQ_D      = 60;
const uint16_t ADDR_TEMP_EQ_R2     = 64;
const uint16_t ADDR_TEMP_EQ_RMSE   = 68;

const uint16_t ADDR_EC_LOW_VOLTS   = 72;
const uint16_t ADDR_EC_HIGH_VOLTS  = 92;
const uint16_t ADDR_PH_VOLTS       = 100;
const uint16_t ADDR_TEMP_VOLTS     = 112;

const uint16_t ADDR_EC_LOW_REFS    = 124;
const uint16_t ADDR_EC_HIGH_REFS   = 144;
const uint16_t ADDR_PH_REFS        = 152;
const uint16_t ADDR_TEMP_REFS      = 164;

const uint16_t ADDR_EC_LOW_CAL_FLAG = 176;
const uint16_t ADDR_EC_HIGH_CAL_FLAG= 177;
const uint16_t ADDR_PH_CAL_FLAG    = 178;
const uint16_t ADDR_TEMP_CAL_FLAG  = 179;

const uint16_t ADDR_CHECKSUM       = 180;

/*******************************************************************************
 * SERIAL COMMUNICATION SETTINGS
 ******************************************************************************/

const uint32_t SERIAL_BAUD_RATE    = 115200;

/*******************************************************************************
 * COMMAND STRINGS - EC CALIBRATION
 ******************************************************************************/

// EC calibration mode commands
const char CMD_CALMODE_EC_LOW_3[]  = "CALMODE_EC_LOW_3";
const char CMD_CALMODE_EC_LOW_4[]  = "CALMODE_EC_LOW_4";
const char CMD_CALMODE_EC_LOW_5[]  = "CALMODE_EC_LOW_5";
const char CMD_CALMODE_EC_HIGH_2[] = "CALMODE_EC_HIGH_2";

// EC low range calibration commands
const char CMD_CAL_EC_LOW_1[]      = "CAL_EC_LOW_1";
const char CMD_CAL_EC_LOW_2[]      = "CAL_EC_LOW_2";
const char CMD_CAL_EC_LOW_3[]      = "CAL_EC_LOW_3";
const char CMD_CAL_EC_LOW_4[]      = "CAL_EC_LOW_4";
const char CMD_CAL_EC_LOW_5[]      = "CAL_EC_LOW_5";

// EC high range calibration commands
const char CMD_CAL_EC_HIGH_1[]     = "CAL_EC_HIGH_1";
const char CMD_CAL_EC_HIGH_2[]     = "CAL_EC_HIGH_2";

// EC reference value commands
const char CMD_SET_EC_LOW_1[]      = "SET_EC_LOW_1";
const char CMD_SET_EC_LOW_2[]      = "SET_EC_LOW_2";
const char CMD_SET_EC_LOW_3[]      = "SET_EC_LOW_3";
const char CMD_SET_EC_LOW_4[]      = "SET_EC_LOW_4";
const char CMD_SET_EC_LOW_5[]      = "SET_EC_LOW_5";
const char CMD_SET_EC_HIGH_1[]     = "SET_EC_HIGH_1";
const char CMD_SET_EC_HIGH_2[]     = "SET_EC_HIGH_2";

/*******************************************************************************
 * COMMAND STRINGS - pH CALIBRATION
 ******************************************************************************/

// pH calibration mode commands
const char CMD_CALMODE_PH_3[]      = "CALMODE_PH_3";

// pH calibration commands
const char CMD_CAL_PH_1[]          = "CAL_PH_1";
const char CMD_CAL_PH_2[]          = "CAL_PH_2";
const char CMD_CAL_PH_3[]          = "CAL_PH_3";

// pH reference value commands
const char CMD_SET_PH_1[]          = "SET_PH_1";
const char CMD_SET_PH_2[]          = "SET_PH_2";
const char CMD_SET_PH_3[]          = "SET_PH_3";

/*******************************************************************************
 * COMMAND STRINGS - TEMPERATURE CALIBRATION
 ******************************************************************************/

// Temperature calibration mode commands
const char CMD_CALMODE_TEMP_3[]    = "CALMODE_TEMP_3";

// Temperature calibration commands
const char CMD_CAL_TEMP_1[]        = "CAL_TEMP_1";
const char CMD_CAL_TEMP_2[]        = "CAL_TEMP_2";
const char CMD_CAL_TEMP_3[]        = "CAL_TEMP_3";

// Temperature reference value commands
const char CMD_SET_TEMP_1[]        = "SET_TEMP_1";
const char CMD_SET_TEMP_2[]        = "SET_TEMP_2";
const char CMD_SET_TEMP_3[]        = "SET_TEMP_3";

/*******************************************************************************
 * COMMAND STRINGS - READING & STATUS
 ******************************************************************************/

// Reading commands
const char CMD_READ[]              = "READ";
const char CMD_DIAG[]              = "DIAG";

// Status commands
const char CMD_EQUATIONS[]         = "EQUATIONS";
const char CMD_STATUS[]            = "STATUS";
const char CMD_QUALITY[]           = "QUALITY";

// Management commands
const char CMD_CLEAR[]             = "CLEAR";
const char CMD_SAVE[]              = "SAVE";
const char CMD_LOAD[]              = "LOAD";

// Help command
const char CMD_HELP[]              = "HELP";

#endif // CONFIG_H
