/*******************************************************************************
 * SENSORREADER.H - Sensor Hardware Interface (ALL SENSORS)
 * 
 * Purpose:
 *   Provides clean interface to read analog sensors (EC, Temperature, pH).
 *   Handles ADC reading, voltage conversion, averaging, and optional filtering.
 * 
 * Responsibilities:
 *   - Read raw ADC values from sensor pins
 *   - Convert ADC counts to millivolts
 *   - Apply averaging to reduce noise
 *   - Apply optional exponential filtering
 *   - Convert temperature voltage to Celsius
 *   - Convert pH voltage to pH units (uncalibrated)
 * 
 * Does NOT handle:
 *   - Calibration (that's Calibration class's job)
 *   - EEPROM storage
 *   - Serial communication
 * 
 * Author: System Rewrite v1.0 - Complete Edition
 * Date: 2026-02-16
 ******************************************************************************/

#ifndef SENSORREADER_H
#define SENSORREADER_H

#include <Arduino.h>
#include "Config.h"

/*******************************************************************************
 * CLASS: SensorReader
 * 
 * Simple, focused class for reading sensor voltages and converting to
 * physical units. Provides both raw and uncalibrated readings for all sensors.
 ******************************************************************************/
class SensorReader {
public:
  /***************************************************************************
   * CONSTRUCTOR
   ***************************************************************************/
  SensorReader(uint8_t ecPin, uint8_t tempPin, uint8_t pHPin);
  
  /***************************************************************************
   * INITIALIZATION
   ***************************************************************************/
  void begin();
  
  /***************************************************************************
   * RAW ADC READING METHODS
   * 
   * Returns raw 10-bit ADC value (0-1023) for diagnostics.
   ***************************************************************************/
  uint16_t readRawADC_EC();
  uint16_t readRawADC_Temp();
  uint16_t readRawADC_pH();
  
  /***************************************************************************
   * VOLTAGE READING METHODS
   * 
   * Returns sensor voltage in millivolts (0-5000 mV) with averaging.
   ***************************************************************************/
  float readVoltage_EC();
  float readVoltage_Temp();
  float readVoltage_pH();
  
  /***************************************************************************
   * UNCALIBRATED READING METHODS
   * 
   * These methods convert voltage to physical units using default formulas.
   * Calibration class will provide calibrated readings.
   ***************************************************************************/
  
  /*
   * Read temperature in degrees Celsius (uncalibrated)
   * 
   * Uses formula: T = (V - 0.176) × 39.93
   * Calibration will refine this reading.
   */
  float readTemperature();
  
  /*
   * Read pH value (uncalibrated)
   * 
   * Uses formula: pH = 7.0 + (V_mV - 2500) / -59.16
   * This assumes Nernstian response: ~59 mV/pH unit
   * pH 7 (neutral) should read ~2500 mV (mid-scale)
   * 
   * Calibration will provide accurate pH readings.
   */
  float readpH();

private:
  /***************************************************************************
   * PRIVATE MEMBER VARIABLES
   ***************************************************************************/
  uint8_t _ecPin;
  uint8_t _tempPin;
  uint8_t _pHPin;
  
  // Exponential filter state
  float _lastEC;
  float _lastTemp;
  float _lastpH;
  
  /***************************************************************************
   * PRIVATE HELPER METHODS
   ***************************************************************************/
  float _adcToMillivolts(uint16_t adcValue);
  float _applyFilter(float newValue, float oldValue);
};

#endif // SENSORREADER_H
