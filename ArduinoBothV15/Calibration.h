/*******************************************************************************
 * CALIBRATION.H - Complete Calibration Management (ALL SENSORS)
 * 
 * Purpose:
 *   Manages all calibration data and operations for EC, pH, and Temperature sensors.
 *   Handles calibration point capture, linear regression, quality metrics,
 *   and provides calibrated sensor readings for all three sensors.
 * 
 * Calibration Approach (ALL SENSORS):
 *   Maps sensor voltages directly to physical values using linear regression.
 *   
 *   EC:          voltage_mV → EC_µS/cm
 *   pH:          voltage_mV → pH_units
 *   Temperature: voltage_mV → temperature_°C
 *   
 *   All use equation: output = C × voltage_mV + D
 * 
 * Calibration Modes:
 *   EC Low Range:   3, 4, or 5 point calibration
 *   EC High Range:  2 point calibration ONLY
 *   pH:             3 point calibration
 *   Temperature:    3 point calibration
 * 
 * Author: System Rewrite v1.0 - Complete Edition
 * Date: 2026-02-16
 ******************************************************************************/

#ifndef CALIBRATION_H
#define CALIBRATION_H

#include <Arduino.h>
#include "Config.h"
#include "SensorReader.h"

/*******************************************************************************
 * CALIBRATION DATA STRUCTURES (for Python integration and plotting)
 ******************************************************************************/
struct CalibrationData {
  float voltages[5];   // Max 5 points (EC low has most)
  float references[5];
};

struct CalibrationEquation {
  float C;
  float D;
  float R2;
  float RMSE;
};

/*******************************************************************************
 * CLASS: Calibration
 * 
 * Manages calibration for ALL sensors: EC (low/high), pH, and Temperature.
 * Each sensor has its own calibration mode, data, and equation.
 ******************************************************************************/
class Calibration {
public:
  /***************************************************************************
   * CONSTRUCTOR & INITIALIZATION
   ***************************************************************************/
  Calibration(SensorReader* sensor);
  void begin();
  
  /***************************************************************************
   * EC CALIBRATION - MODE MANAGEMENT
   ***************************************************************************/
  void setECLowMode(ECLowMode mode);
  void setECHighMode(ECHighMode mode);
  
  /***************************************************************************
   * pH CALIBRATION - MODE MANAGEMENT
   ***************************************************************************/
  void setpHMode(pHMode mode);
  
  /***************************************************************************
   * TEMPERATURE CALIBRATION - MODE MANAGEMENT
   ***************************************************************************/
  void setTempMode(TempMode mode);
  
  /***************************************************************************
   * EC CALIBRATION - POINT CAPTURE
   ***************************************************************************/
  void calibrateECLowPoint(uint8_t pointNum);
  void calibrateECHighPoint(uint8_t pointNum);
  
  /***************************************************************************
   * pH CALIBRATION - POINT CAPTURE
   ***************************************************************************/
  void calibratepHPoint(uint8_t pointNum);
  
  /***************************************************************************
   * TEMPERATURE CALIBRATION - POINT CAPTURE
   ***************************************************************************/
  void calibrateTempPoint(uint8_t pointNum);
  
  /***************************************************************************
   * FORCE CALIBRATION - MANUAL VOLTAGE ENTRY
   * Use when you have recorded voltage data but no calibration solutions
   ***************************************************************************/
  void forceECLowPoint(uint8_t pointNum, float voltage_mV);
  void forceECHighPoint(uint8_t pointNum, float voltage_mV);
  void forcepHPoint(uint8_t pointNum, float voltage_mV);
  void forceTempPoint(uint8_t pointNum, float voltage_mV);
  
  /***************************************************************************
   * EC REFERENCE VALUE MANAGEMENT
   ***************************************************************************/
  void setECLowRef(uint8_t pointNum, float value);
  void setECHighRef(uint8_t pointNum, float value);
  
  /***************************************************************************
   * pH REFERENCE VALUE MANAGEMENT
   ***************************************************************************/
  void setpHRef(uint8_t pointNum, float value);
  
  /***************************************************************************
   * TEMPERATURE REFERENCE VALUE MANAGEMENT
   ***************************************************************************/
  void setTempRef(uint8_t pointNum, float value);
  
  /***************************************************************************
   * CALIBRATED READINGS
   ***************************************************************************/
  float getCalibratedEC();
  float getCalibratedpH();
  float getCalibratedTemperature();
  
  /***************************************************************************
   * STATUS & INFORMATION DISPLAY
   ***************************************************************************/
  void showEquations();
  void showStatus();
  void showQuality();
  
  /***************************************************************************
   * CALIBRATION STATUS QUERIES
   ***************************************************************************/
  bool isECLowCalibrated() const;
  bool isECHighCalibrated() const;
  bool ispHCalibrated() const;
  bool isTempCalibrated() const;
  
  /***************************************************************************
   * SIMPLE GETTERS (for Python integration and plotting)
   ***************************************************************************/
  uint8_t getECLowPointCount() const { return _ecLowCount; }
  uint8_t getECHighPointCount() const { return _ecHighCount; }
  uint8_t getpHPointCount() const { return _pHCount; }
  uint8_t getTempPointCount() const { return _tempCount; }
  
  float getECLowR2() const { return _ecLowR2; }
  float getECHighR2() const { return _ecHighR2; }
  float getpHR2() const { return _pHR2; }
  float getTempR2() const { return _tempR2; }
  
  // Simple returns for plot data (structs defined above)
  CalibrationData getECLowData() const;
  CalibrationData getECHighData() const;
  CalibrationData getpHData() const;
  CalibrationData getTempData() const;
  
  CalibrationEquation getECLowEquation() const;
  CalibrationEquation getECHighEquation() const;
  CalibrationEquation getpHEquation() const;
  CalibrationEquation getTempEquation() const;
  
  /***************************************************************************
   * DATA ACCESS (for EEPROM storage)
   ***************************************************************************/
  
  // Get current modes
  ECLowMode getECLowMode() const { return _ecLowMode; }
  ECHighMode getECHighMode() const { return _ecHighMode; }
  pHMode getpHMode() const { return _pHMode; }
  TempMode getTempMode() const { return _tempMode; }
  
  // Get EC calibration data
  void getECLowEquation(float& C, float& D, float& R2, float& RMSE) const;
  void getECHighEquation(float& C, float& D, float& R2, float& RMSE) const;
  void getECLowData(float volts[], float refs[]) const;
  void getECHighData(float volts[], float refs[]) const;
  
  // Get pH calibration data
  void getpHEquation(float& C, float& D, float& R2, float& RMSE) const;
  void getpHData(float volts[], float refs[]) const;
  
  // Get Temperature calibration data
  void getTempEquation(float& C, float& D, float& R2, float& RMSE) const;
  void getTempData(float volts[], float refs[]) const;
  
  // Set calibration data (used when loading from EEPROM)
  void setECLowEquation(float C, float D, float R2, float RMSE);
  void setECHighEquation(float C, float D, float R2, float RMSE);
  void setpHEquation(float C, float D, float R2, float RMSE);
  void setTempEquation(float C, float D, float R2, float RMSE);
  
  void setECLowData(const float volts[], const float refs[]);
  void setECHighData(const float volts[], const float refs[]);
  void setpHData(const float volts[], const float refs[]);
  void setTempData(const float volts[], const float refs[]);
  
  void setCalibrationFlags(bool ecLowCal, bool ecHighCal, bool pHCal, bool tempCal);

private:
  /***************************************************************************
   * PRIVATE MEMBER VARIABLES
   ***************************************************************************/
  
  SensorReader* _sensor;
  
  // === EC CALIBRATION DATA ===
  ECLowMode  _ecLowMode;
  ECHighMode _ecHighMode;
  
  float _ecLowRef[EC_LOW_CAL_POINTS];
  float _ecHighRef[EC_HIGH_CAL_POINTS];
  float _ecLowVolts[EC_LOW_CAL_POINTS];
  float _ecHighVolts[EC_HIGH_CAL_POINTS];
  
  float _ecLowC, _ecLowD;
  float _ecHighC, _ecHighD;
  float _ecLowR2, _ecLowRMSE;
  float _ecHighR2, _ecHighRMSE;
  
  bool _isECLowCal;
  bool _isECHighCal;
  uint8_t _ecLowCount;
  uint8_t _ecHighCount;
  
  // === pH CALIBRATION DATA ===
  pHMode _pHMode;
  
  float _pHRef[PH_CAL_POINTS];
  float _pHVolts[PH_CAL_POINTS];
  
  float _pHC, _pHD;
  float _pHR2, _pHRMSE;
  
  bool _ispHCal;
  uint8_t _pHCount;
  
  // === TEMPERATURE CALIBRATION DATA ===
  TempMode _tempMode;
  
  float _tempRef[TEMP_CAL_POINTS];
  float _tempVolts[TEMP_CAL_POINTS];
  
  float _tempC, _tempD;
  float _tempR2, _tempRMSE;
  
  bool _isTempCal;
  uint8_t _tempCount;
  
  /***************************************************************************
   * PRIVATE METHODS - Calibration Calculation
   ***************************************************************************/
  void _calculateECLowEquation();
  void _calculateECHighEquation();
  void _calculatepHEquation();
  void _calculateTempEquation();
  
  /***************************************************************************
   * PRIVATE METHODS - Core Math (shared by all sensors)
   ***************************************************************************/
  void _linearRegression(const float x[], const float y[], uint8_t count, 
                        float& C, float& D);
  float _calculateR2(const float x[], const float y[], float C, float D, uint8_t count);
  float _calculateRMSE(const float x[], const float y[], float C, float D, uint8_t count);
  
  /***************************************************************************
   * PRIVATE METHODS - Validation
   ***************************************************************************/
  bool _validatePoints(const float volts[], uint8_t count, const char* sensorName);
  
  /***************************************************************************
   * PRIVATE METHODS - Utilities
   ***************************************************************************/
  void _resetECLowCalibrationData();
  void _resetECHighCalibrationData();
  void _resetpHCalibrationData();
  void _resetTempCalibrationData();
  
  bool _isECLowPointRequired(uint8_t pointIndex) const;
  bool _isECHighPointRequired(uint8_t pointIndex) const;
  bool _ispHPointRequired(uint8_t pointIndex) const;
  bool _isTempPointRequired(uint8_t pointIndex) const;
  
  uint8_t _getRequiredECLowPoints() const;
  uint8_t _getRequiredECHighPoints() const;
  uint8_t _getRequiredpHPoints() const;
  uint8_t _getRequiredTempPoints() const;
};

#endif // CALIBRATION_H
