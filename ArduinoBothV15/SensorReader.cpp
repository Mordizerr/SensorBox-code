/*******************************************************************************
 * SENSORREADER.CPP - Sensor Hardware Interface (ALL SENSORS)
 * 
 * Purpose:
 *   Implements clean interface to read all analog sensors:
 *   EC, Temperature, and pH.
 * 
 * Key Features:
 *   - Direct ADC reading from Arduino's 10-bit ADC
 *   - Accurate voltage conversion
 *   - Noise reduction through averaging
 *   - Optional exponential filtering
 *   - Temperature conversion (uncalibrated)
 *   - pH conversion (uncalibrated)
 * 
 * Author: System Rewrite v1.0 - Complete Edition
 * Date: 2026-02-16
 ******************************************************************************/

#include "SensorReader.h"

/*******************************************************************************
 * CONSTRUCTOR
 ******************************************************************************/
SensorReader::SensorReader(uint8_t ecPin, uint8_t tempPin, uint8_t pHPin)
  : _ecPin(ecPin),
    _tempPin(tempPin),
    _pHPin(pHPin),
    _lastEC(0.0),
    _lastTemp(0.0),
    _lastpH(0.0)
{
}

/*******************************************************************************
 * INITIALIZATION
 ******************************************************************************/
void SensorReader::begin() {
  pinMode(_ecPin, INPUT);
  pinMode(_tempPin, INPUT);
  pinMode(_pHPin, INPUT);
  
  // Seed filters with initial readings
  _lastEC = _adcToMillivolts(analogRead(_ecPin));
  
  float tempVoltage = _adcToMillivolts(analogRead(_tempPin));
  _lastTemp = (tempVoltage / 1000.0 - TEMP_OFFSET_V) * TEMP_SCALE;
  
  _lastpH = _adcToMillivolts(analogRead(_pHPin));
  
  delay(100);
}

/*******************************************************************************
 * RAW ADC READING METHODS
 ******************************************************************************/

uint16_t SensorReader::readRawADC_EC() {
  return analogRead(_ecPin);
}

uint16_t SensorReader::readRawADC_Temp() {
  return analogRead(_tempPin);
}

uint16_t SensorReader::readRawADC_pH() {
  return analogRead(_pHPin);
}

/*******************************************************************************
 * VOLTAGE READING METHODS
 ******************************************************************************/

float SensorReader::readVoltage_EC() {
  float sum = 0.0;
  
  for (uint8_t i = 0; i < EC_SAMPLE_COUNT; i++) {
    uint16_t adcValue = analogRead(_ecPin);
    sum += _adcToMillivolts(adcValue);
    if (i < EC_SAMPLE_COUNT - 1) {
      delay(1);
    }
  }
  
  float voltage = sum / EC_SAMPLE_COUNT;
  voltage = _applyFilter(voltage, _lastEC);
  _lastEC = voltage;
  
  return voltage;
}

float SensorReader::readVoltage_Temp() {
  float sum = 0.0;
  
  for (uint8_t i = 0; i < TEMP_SAMPLE_COUNT; i++) {
    uint16_t adcValue = analogRead(_tempPin);
    sum += _adcToMillivolts(adcValue);
    if (i < TEMP_SAMPLE_COUNT - 1) {
      delay(1);
    }
  }
  
  return sum / TEMP_SAMPLE_COUNT;
}

float SensorReader::readVoltage_pH() {
  float sum = 0.0;
  
  for (uint8_t i = 0; i < PH_SAMPLE_COUNT; i++) {
    uint16_t adcValue = analogRead(_pHPin);
    sum += _adcToMillivolts(adcValue);
    if (i < PH_SAMPLE_COUNT - 1) {
      delay(PH_SAMPLE_DELAY_MS);
    }
  }
  
  float voltage = sum / PH_SAMPLE_COUNT;
  voltage = _applyFilter(voltage, _lastpH);
  _lastpH = voltage;
  
  return voltage;
}

/*******************************************************************************
 * UNCALIBRATED TEMPERATURE READING
 ******************************************************************************/

float SensorReader::readTemperature() {
  float voltageMillivolts = readVoltage_Temp();
  float voltageVolts = voltageMillivolts / 1000.0;
  float temperature = (voltageVolts - TEMP_OFFSET_V) * TEMP_SCALE;
  
  temperature = _applyFilter(temperature, _lastTemp);
  _lastTemp = temperature;
  
  return temperature;
}

/*******************************************************************************
 * UNCALIBRATED pH READING
 * 
 * Converts pH electrode voltage to pH value using Nernstian response.
 * 
 * Theory:
 *   pH electrodes follow Nernst equation: E = E₀ + (RT/nF) × ln([H⁺])
 *   At 25°C, this simplifies to: ~59.16 mV change per pH unit
 *   
 *   Typical pH electrode:
 *   - pH 7 (neutral) → ~2500 mV (mid-scale of 0-5V range)
 *   - pH decreases → voltage increases (acidic = higher voltage)
 *   - pH increases → voltage decreases (alkaline = lower voltage)
 * 
 * Formula:
 *   pH = 7.0 + (V_mV - PH_NEUTRAL_MV) / PH_MV_PER_UNIT
 *   pH = 7.0 + (V_mV - 2500) / -59.16
 * 
 * Example:
 *   V = 2500 mV → pH = 7.0 + (2500-2500)/-59.16 = 7.0 (neutral)
 *   V = 2200 mV → pH = 7.0 + (2200-2500)/-59.16 = 12.07 (alkaline)
 *   V = 2800 mV → pH = 7.0 + (2800-2500)/-59.16 = 1.93 (acidic)
 * 
 * Note: This is uncalibrated! Calibration will provide accurate readings.
 ******************************************************************************/
float SensorReader::readpH() {
  float voltageMillivolts = readVoltage_pH();
  
  // Apply Nernstian response formula
  // pH = 7.0 + (V - V_neutral) / slope
  // where slope is typically -59.16 mV/pH at 25°C
  float pH = 7.0 + (voltageMillivolts - PH_NEUTRAL_MV) / PH_MV_PER_UNIT;
  
  // Clamp to valid pH range (0-14)
  if (pH < 0.0) pH = 0.0;
  if (pH > 14.0) pH = 14.0;
  
  return pH;
}

/*******************************************************************************
 * PRIVATE HELPER METHODS
 ******************************************************************************/

float SensorReader::_adcToMillivolts(uint16_t adcValue) {
  return adcValue * ADC_TO_MV_FACTOR;
}

float SensorReader::_applyFilter(float newValue, float oldValue) {
  return FILTER_ALPHA * newValue + (1.0 - FILTER_ALPHA) * oldValue;
}

/*******************************************************************************
 * END OF SENSORREADER IMPLEMENTATION
 * 
 * All sensors now supported:
 *   ✓ EC - voltage reading
 *   ✓ Temperature - voltage and °C conversion
 *   ✓ pH - voltage and pH conversion
 * 
 * Next: Calibration implementation for all three sensors
 ******************************************************************************/
