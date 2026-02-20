/*******************************************************************************
 * CALIBRATION.CPP - Complete Calibration Management (ALL SENSORS)
 * 
 * Purpose:
 *   Implements the mathematical foundation for calibration of ALL sensors:
 *   EC (low/high range), pH, and Temperature.
 * 
 * Key Algorithms (shared by all sensors):
 *   - Linear regression (least-squares fitting)
 *   - R² calculation (coefficient of determination)
 *   - RMSE calculation (root mean square error)
 *   - Point validation (separation and span checking)
 * 
 * Implementation Philosophy:
 *   CORRECT: voltage_mV → physical_value (direct mapping for all sensors)
 *   All sensors use: output = C × voltage + D
 * 
 * Author: System Rewrite v1.0 - Complete Edition
 * Date: 2026-02-16
 ******************************************************************************/

#include "Calibration.h"

/*******************************************************************************
 * CONSTRUCTOR
 * 
 * Initializes calibration system for ALL sensors with safe defaults.
 ******************************************************************************/
Calibration::Calibration(SensorReader* sensor)
  : _sensor(sensor),
    // EC calibration
    _ecLowMode(LOW_4PT),
    _ecHighMode(HIGH_2PT),
    _ecLowC(0.0), _ecLowD(0.0),
    _ecHighC(0.0), _ecHighD(0.0),
    _ecLowR2(0.0), _ecLowRMSE(0.0),
    _ecHighR2(0.0), _ecHighRMSE(0.0),
    _isECLowCal(false), _isECHighCal(false),
    _ecLowCount(0), _ecHighCount(0),
    // pH calibration
    _pHMode(PH_3PT),
    _pHC(0.0), _pHD(0.0),
    _pHR2(0.0), _pHRMSE(0.0),
    _ispHCal(false),
    _pHCount(0),
    // Temperature calibration
    _tempMode(TEMP_3PT),
    _tempC(0.0), _tempD(0.0),
    _tempR2(0.0), _tempRMSE(0.0),
    _isTempCal(false),
    _tempCount(0)
{
}

/*******************************************************************************
 * INITIALIZATION
 * 
 * Sets default reference values for ALL sensors.
 ******************************************************************************/
void Calibration::begin() {
  // Initialize EC low range
  for (uint8_t i = 0; i < EC_LOW_CAL_POINTS; i++) {
    _ecLowRef[i] = DEFAULT_EC_LOW_REF[i];
    _ecLowVolts[i] = 0.0;
  }
  
  // Initialize EC high range
  for (uint8_t i = 0; i < EC_HIGH_CAL_POINTS; i++) {
    _ecHighRef[i] = DEFAULT_EC_HIGH_REF[i];
    _ecHighVolts[i] = 0.0;
  }
  
  // Initialize pH
  for (uint8_t i = 0; i < PH_CAL_POINTS; i++) {
    _pHRef[i] = DEFAULT_PH_REF[i];
    _pHVolts[i] = 0.0;
  }
  
  // Initialize Temperature
  for (uint8_t i = 0; i < TEMP_CAL_POINTS; i++) {
    _tempRef[i] = DEFAULT_TEMP_REF[i];
    _tempVolts[i] = 0.0;
  }
  
  Serial.print(F("Cal init: ECL="));
  Serial.print(_ecLowMode);
  Serial.println(F("pt pH=3pt Temp=3pt"));
}

/*******************************************************************************
 * LINEAR REGRESSION - THE MATHEMATICAL HEART (SHARED BY ALL SENSORS)
 * 
 * Calculates best-fit line through calibration points using least-squares method.
 * Used by EC, pH, and Temperature calibration.
 * 
 * Equation: output = C × voltage + D
 * 
 * Mathematical formulas:
 *   C = (n×ΣXY - ΣX×ΣY) / (n×ΣX² - (ΣX)²)
 *   D = (ΣY - C×ΣX) / n
 ******************************************************************************/
void Calibration::_linearRegression(const float x[], const float y[], 
                                    uint8_t count, float& C, float& D) {
  if (count < 2) {
    C = 0.0;
    D = 0.0;
    return;
  }
  
  float sumX = 0.0;
  float sumY = 0.0;
  float sumXY = 0.0;
  float sumX2 = 0.0;
  
  for (uint8_t i = 0; i < count; i++) {
    sumX += x[i];
    sumY += y[i];
    sumXY += x[i] * y[i];
    sumX2 += x[i] * x[i];
  }
  
  float denominator = count * sumX2 - sumX * sumX;
  
  if (abs(denominator) < 0.0001) {
    Serial.println(F("ERROR: Cannot calculate regression (all voltages identical)"));
    C = 0.0;
    D = 0.0;
    return;
  }
  
  C = (count * sumXY - sumX * sumY) / denominator;
  D = (sumY - C * sumX) / count;
}

/*******************************************************************************
 * R² CALCULATION (SHARED BY ALL SENSORS)
 * 
 * Measures how well the calibration line fits the data.
 * R² = 1.0 → perfect fit
 * R² = 0.95 → good fit (our minimum threshold)
 ******************************************************************************/
float Calibration::_calculateR2(const float x[], const float y[], 
                                float C, float D, uint8_t count) {
  if (count < 2) {
    return 0.0;
  }
  
  float meanY = 0.0;
  for (uint8_t i = 0; i < count; i++) {
    meanY += y[i];
  }
  meanY /= count;
  
  float SS_tot = 0.0;
  for (uint8_t i = 0; i < count; i++) {
    float deviation = y[i] - meanY;
    SS_tot += deviation * deviation;
  }
  
  if (SS_tot < 0.0001) {
    return 1.0;
  }
  
  float SS_res = 0.0;
  for (uint8_t i = 0; i < count; i++) {
    float predicted = C * x[i] + D;
    float residual = y[i] - predicted;
    SS_res += residual * residual;
  }
  
  float R2 = 1.0 - (SS_res / SS_tot);
  
  if (R2 < 0.0) R2 = 0.0;
  if (R2 > 1.0) R2 = 1.0;
  
  return R2;
}

/*******************************************************************************
 * RMSE CALCULATION (SHARED BY ALL SENSORS)
 * 
 * Measures average prediction error in same units as data.
 ******************************************************************************/
float Calibration::_calculateRMSE(const float x[], const float y[], 
                                  float C, float D, uint8_t count) {
  if (count < 1) {
    return 0.0;
  }
  
  float sumSquaredError = 0.0;
  
  for (uint8_t i = 0; i < count; i++) {
    float predicted = C * x[i] + D;
    float error = y[i] - predicted;
    sumSquaredError += error * error;
  }
  
  float meanSquaredError = sumSquaredError / count;
  float rmse = sqrt(meanSquaredError);
  
  return rmse;
}

/*******************************************************************************
 * POINT VALIDATION (SHARED BY ALL SENSORS)
 * 
 * Validates calibration points are suitable for regression.
 * Checks:
 *   1. Point separation >10 mV
 *   2. Voltage span >100 mV
 ******************************************************************************/
bool Calibration::_validatePoints(const float volts[], uint8_t count, 
                                  const char* sensorName) {
  if (count < 2) {
    Serial.print(F("ERR: "));
    Serial.print(sensorName);
    Serial.print(F(" needs 2+ pts (have "));
    Serial.print(count);
    Serial.println(F(")"));
    return false;
  }
  
  // Check point separation
  for (uint8_t i = 0; i < count - 1; i++) {
    for (uint8_t j = i + 1; j < count; j++) {
      float separation = abs(volts[i] - volts[j]);
      
      if (separation < MIN_VOLTAGE_SEPARATION) {
        Serial.print(F("ERR: "));
        Serial.print(sensorName);
        Serial.print(F(" P"));
        Serial.print(i + 1);
        Serial.print(F("-P"));
        Serial.print(j + 1);
        Serial.print(F(" too close ("));
        Serial.print(separation, 1);
        Serial.print(F("mV < "));
        Serial.print(MIN_VOLTAGE_SEPARATION, 1);
        Serial.println(F("mV min) Stabilize!"));
        return false;
      }
    }
  }
  
  // Check voltage span
  float minVolt = volts[0];
  float maxVolt = volts[0];
  
  for (uint8_t i = 1; i < count; i++) {
    if (volts[i] < minVolt) minVolt = volts[i];
    if (volts[i] > maxVolt) maxVolt = volts[i];
  }
  
  float span = maxVolt - minVolt;
  
  if (span < MIN_VOLTAGE_SPAN) {
    Serial.print(F("ERR: "));
    Serial.print(sensorName);
    Serial.print(F(" span "));
    Serial.print(span, 1);
    Serial.print(F("mV < "));
    Serial.print(MIN_VOLTAGE_SPAN, 1);
    Serial.println(F("mV min. Check solutions"));
    return false;
  }
  
  return true;
}

/*******************************************************************************
 * RESET CALIBRATION DATA
 ******************************************************************************/

void Calibration::_resetECLowCalibrationData() {
  for (uint8_t i = 0; i < EC_LOW_CAL_POINTS; i++) {
    _ecLowVolts[i] = 0.0;
  }
  _ecLowC = 0.0;
  _ecLowD = 0.0;
  _ecLowR2 = 0.0;
  _ecLowRMSE = 0.0;
  _isECLowCal = false;
  _ecLowCount = 0;
}

void Calibration::_resetECHighCalibrationData() {
  for (uint8_t i = 0; i < EC_HIGH_CAL_POINTS; i++) {
    _ecHighVolts[i] = 0.0;
  }
  _ecHighC = 0.0;
  _ecHighD = 0.0;
  _ecHighR2 = 0.0;
  _ecHighRMSE = 0.0;
  _isECHighCal = false;
  _ecHighCount = 0;
}

void Calibration::_resetpHCalibrationData() {
  for (uint8_t i = 0; i < PH_CAL_POINTS; i++) {
    _pHVolts[i] = 0.0;
  }
  _pHC = 0.0;
  _pHD = 0.0;
  _pHR2 = 0.0;
  _pHRMSE = 0.0;
  _ispHCal = false;
  _pHCount = 0;
}

void Calibration::_resetTempCalibrationData() {
  for (uint8_t i = 0; i < TEMP_CAL_POINTS; i++) {
    _tempVolts[i] = 0.0;
  }
  _tempC = 0.0;
  _tempD = 0.0;
  _tempR2 = 0.0;
  _tempRMSE = 0.0;
  _isTempCal = false;
  _tempCount = 0;
}

/*******************************************************************************
 * POINT REQUIREMENT HELPERS
 ******************************************************************************/

bool Calibration::_isECLowPointRequired(uint8_t pointIndex) const {
  switch (_ecLowMode) {
    case LOW_3PT:
      return (pointIndex == 0 || pointIndex == 2 || pointIndex == 4);
    case LOW_4PT:
      return (pointIndex <= 2 || pointIndex == 4);
    case LOW_5PT:
      return (pointIndex <= 4);
    default:
      return false;
  }
}

bool Calibration::_isECHighPointRequired(uint8_t pointIndex) const {
  return (pointIndex <= 1);
}

bool Calibration::_ispHPointRequired(uint8_t pointIndex) const {
  return (pointIndex < PH_CAL_POINTS);
}

bool Calibration::_isTempPointRequired(uint8_t pointIndex) const {
  return (pointIndex < TEMP_CAL_POINTS);
}

uint8_t Calibration::_getRequiredECLowPoints() const {
  return (uint8_t)_ecLowMode;
}

uint8_t Calibration::_getRequiredECHighPoints() const {
  return (uint8_t)_ecHighMode;
}

uint8_t Calibration::_getRequiredpHPoints() const {
  return (uint8_t)_pHMode;
}

uint8_t Calibration::_getRequiredTempPoints() const {
  return (uint8_t)_tempMode;
}

/*******************************************************************************
 * STATUS QUERY METHODS
 ******************************************************************************/

bool Calibration::isECLowCalibrated() const {
  return _isECLowCal;
}

bool Calibration::isECHighCalibrated() const {
  return _isECHighCal;
}

bool Calibration::ispHCalibrated() const {
  return _ispHCal;
}

bool Calibration::isTempCalibrated() const {
  return _isTempCal;
}

/*******************************************************************************
 * MODE MANAGEMENT - EC LOW RANGE
 * 
 * Sets the calibration mode for EC low range and resets calibration data.
 ******************************************************************************/
void Calibration::setECLowMode(ECLowMode mode) {
  _ecLowMode = mode;
  _resetECLowCalibrationData();
  
  Serial.print(F("ECL mode: "));
  Serial.print((uint8_t)mode);
  Serial.println(F("pt"));
  
  Serial.print(F("Pts: "));
  for (uint8_t i = 0; i < EC_LOW_CAL_POINTS; i++) {
    if (_isECLowPointRequired(i)) {
      Serial.print(i + 1);
      Serial.print(F("("));
      Serial.print(_ecLowRef[i], 0);
      Serial.print(F(") "));
    }
  }
  Serial.println();
}

/*******************************************************************************
 * MODE MANAGEMENT - EC HIGH RANGE
 ******************************************************************************/
void Calibration::setECHighMode(ECHighMode mode) {
  _ecHighMode = mode;
  _resetECHighCalibrationData();
  
  Serial.print(F("ECH mode: "));
  Serial.print((uint8_t)mode);
  Serial.println(F("pt"));
  Serial.println(F("Pts: 1(1413) 2(12880)"));
}

/*******************************************************************************
 * MODE MANAGEMENT - pH
 ******************************************************************************/
void Calibration::setpHMode(pHMode mode) {
  _pHMode = mode;
  _resetpHCalibrationData();
  
  Serial.print(F("pH mode: "));
  Serial.print((uint8_t)mode);
  Serial.println(F("pt"));
  Serial.println(F("Pts: 1(4.00) 2(7.00) 3(10.00)"));
}

/*******************************************************************************
 * MODE MANAGEMENT - TEMPERATURE
 ******************************************************************************/
void Calibration::setTempMode(TempMode mode) {
  _tempMode = mode;
  _resetTempCalibrationData();
  
  Serial.print(F("Temp mode: "));
  Serial.print((uint8_t)mode);
  Serial.println(F("pt"));
  Serial.println(F("Pts: 1(25C) 2(32C) 3(40C)"));
}

/*******************************************************************************
 * CALIBRATION POINT CAPTURE - EC LOW RANGE
 * 
 * Captures one EC low range calibration point by reading current sensor voltage.
 ******************************************************************************/
void Calibration::calibrateECLowPoint(uint8_t pointNum) {
  // Validate point number (0-4, but check if required for current mode)
  if (pointNum >= EC_LOW_CAL_POINTS) {
    Serial.println(F("ERR: ECL pt# invalid"));
    return;
  }
  
  if (!_isECLowPointRequired(pointNum)) {
    Serial.print(F("ERR: Pt"));
    Serial.print(pointNum + 1);
    Serial.print(F(" not in "));
    Serial.print((uint8_t)_ecLowMode);
    Serial.println(F("pt mode"));
    return;
  }
  
  // Read current EC voltage
  float voltage = _sensor->readVoltage_EC();
  float temperature = _sensor->readTemperature();
  
  _ecLowVolts[pointNum] = voltage;
  
  bool alreadyCaptured = false;
  for (uint8_t i = 0; i < pointNum; i++) {
    if (_isECLowPointRequired(i) && _ecLowVolts[i] == 0.0) {
      alreadyCaptured = false;
      break;
    }
  }
  
  if (_ecLowVolts[pointNum] > 0.0 && !alreadyCaptured) {
    _ecLowCount = 0;
    for (uint8_t i = 0; i < EC_LOW_CAL_POINTS; i++) {
      if (_isECLowPointRequired(i) && _ecLowVolts[i] > 0.0) {
        _ecLowCount++;
      }
    }
  }
  
  Serial.print(F("ECL P"));
  Serial.print(pointNum + 1);
  Serial.print(F(": Vmv="));
  Serial.print(voltage, 1);
  Serial.print(F(" T="));
  Serial.print(temperature, 1);
  Serial.print(F("C Ref="));
  Serial.print(_ecLowRef[pointNum], 1);
  Serial.print(F("uS L"));
  Serial.print(pointNum + 1);
  Serial.print(F(":"));
  Serial.print(_ecLowCount);
  Serial.print(F("/"));
  Serial.println(_getRequiredECLowPoints());
  
  if (_ecLowCount == _getRequiredECLowPoints()) {
    Serial.println(F("ECL: calc..."));
    _calculateECLowEquation();
  }
}

/*******************************************************************************
 * CALIBRATION POINT CAPTURE - EC HIGH RANGE
 ******************************************************************************/
void Calibration::calibrateECHighPoint(uint8_t pointNum) {
  if (pointNum >= EC_HIGH_CAL_POINTS) {
    Serial.println(F("ERR: ECH pt# invalid"));
    return;
  }
  
  float voltage = _sensor->readVoltage_EC();
  float temperature = _sensor->readTemperature();
  
  _ecHighVolts[pointNum] = voltage;
  
  _ecHighCount = 0;
  for (uint8_t i = 0; i < EC_HIGH_CAL_POINTS; i++) {
    if (_ecHighVolts[i] > 0.0) {
      _ecHighCount++;
    }
  }
  
  Serial.print(F("ECH P"));
  Serial.print(pointNum + 1);
  Serial.print(F(": Vmv="));
  Serial.print(voltage, 1);
  Serial.print(F(" T="));
  Serial.print(temperature, 1);
  Serial.print(F("C Ref="));
  Serial.print(_ecHighRef[pointNum], 1);
  Serial.print(F("uS H"));
  Serial.print(pointNum + 1);
  Serial.print(F(":"));
  Serial.print(_ecHighCount);
  Serial.print(F("/"));
  Serial.println(_getRequiredECHighPoints());
  
  if (_ecHighCount == _getRequiredECHighPoints()) {
    Serial.println(F("ECH: calc..."));
    _calculateECHighEquation();
  }
}

/*******************************************************************************
 * CALIBRATION POINT CAPTURE - pH
 ******************************************************************************/
void Calibration::calibratepHPoint(uint8_t pointNum) {
  if (pointNum >= PH_CAL_POINTS) {
    Serial.println(F("ERR: pH pt# invalid"));
    return;
  }
  
  float voltage = _sensor->readVoltage_pH();
  float temperature = _sensor->readTemperature();
  
  _pHVolts[pointNum] = voltage;
  
  _pHCount = 0;
  for (uint8_t i = 0; i < PH_CAL_POINTS; i++) {
    if (_pHVolts[i] > 0.0) {
      _pHCount++;
    }
  }
  
  Serial.print(F("pH P"));
  Serial.print(pointNum + 1);
  Serial.print(F(": Vmv="));
  Serial.print(voltage, 1);
  Serial.print(F(" T="));
  Serial.print(temperature, 1);
  Serial.print(F("C Ref="));
  Serial.print(_pHRef[pointNum], 2);
  Serial.print(F("pH P"));
  Serial.print(pointNum + 1);
  Serial.print(F(":"));
  Serial.print(_pHCount);
  Serial.print(F("/"));
  Serial.println(_getRequiredpHPoints());
  
  if (_pHCount == _getRequiredpHPoints()) {
    Serial.println(F("pH: calc..."));
    _calculatepHEquation();
  }
}

/*******************************************************************************
 * CALIBRATION POINT CAPTURE - TEMPERATURE
 ******************************************************************************/
void Calibration::calibrateTempPoint(uint8_t pointNum) {
  if (pointNum >= TEMP_CAL_POINTS) {
    Serial.println(F("ERR: Temp pt# invalid"));
    return;
  }
  
  float voltage = _sensor->readVoltage_Temp();
  
  _tempVolts[pointNum] = voltage;
  
  _tempCount = 0;
  for (uint8_t i = 0; i < TEMP_CAL_POINTS; i++) {
    if (_tempVolts[i] > 0.0) {
      _tempCount++;
    }
  }
  
  Serial.print(F("Temp P"));
  Serial.print(pointNum + 1);
  Serial.print(F(": Vmv="));
  Serial.print(voltage, 1);
  Serial.print(F(" Ref="));
  Serial.print(_tempRef[pointNum], 1);
  Serial.print(F("C T"));
  Serial.print(pointNum + 1);
  Serial.print(F(":"));
  Serial.print(_tempCount);
  Serial.print(F("/"));
  Serial.println(_getRequiredTempPoints());
  
  if (_tempCount == _getRequiredTempPoints()) {
    Serial.println(F("Temp: calc..."));
    _calculateTempEquation();
  }
}

/*******************************************************************************
 * FORCE CALIBRATION - EC LOW RANGE
 * 
 * Force calibration with manual voltage entry (when solution no longer available)
 ******************************************************************************/
void Calibration::forceECLowPoint(uint8_t pointNum, float voltage_mV) {
  if (pointNum >= EC_LOW_CAL_POINTS) {
    Serial.println(F("ERR: ECL pt# invalid"));
    return;
  }
  
  if (!_isECLowPointRequired(pointNum)) {
    Serial.print(F("ERR: Pt"));
    Serial.print(pointNum + 1);
    Serial.print(F(" not in "));
    Serial.print((uint8_t)_ecLowMode);
    Serial.println(F("pt mode"));
    return;
  }
  
  _ecLowVolts[pointNum] = voltage_mV;
  
  _ecLowCount = 0;
  for (uint8_t i = 0; i < EC_LOW_CAL_POINTS; i++) {
    if (_isECLowPointRequired(i) && _ecLowVolts[i] > 0.0) {
      _ecLowCount++;
    }
  }
  
  Serial.print(F("F-ECL P"));
  Serial.print(pointNum + 1);
  Serial.print(F(": Vmv="));
  Serial.print(voltage_mV, 1);
  Serial.print(F(" Ref="));
  Serial.print(_ecLowRef[pointNum], 1);
  Serial.print(F("uS L"));
  Serial.print(pointNum + 1);
  Serial.print(F(":"));
  Serial.print(_ecLowCount);
  Serial.print(F("/"));
  Serial.println(_getRequiredECLowPoints());
  
  if (_ecLowCount == _getRequiredECLowPoints()) {
    Serial.println(F("ECL: calc..."));
    _calculateECLowEquation();
  }
}

/*******************************************************************************
 * FORCE CALIBRATION - EC HIGH RANGE
 ******************************************************************************/
void Calibration::forceECHighPoint(uint8_t pointNum, float voltage_mV) {
  if (pointNum >= EC_HIGH_CAL_POINTS) {
    Serial.println(F("ERR: ECH pt# invalid"));
    return;
  }
  
  _ecHighVolts[pointNum] = voltage_mV;
  
  _ecHighCount = 0;
  for (uint8_t i = 0; i < EC_HIGH_CAL_POINTS; i++) {
    if (_ecHighVolts[i] > 0.0) _ecHighCount++;
  }
  
  Serial.print(F("F-ECH P"));
  Serial.print(pointNum + 1);
  Serial.print(F(": Vmv="));
  Serial.print(voltage_mV, 1);
  Serial.print(F(" Ref="));
  Serial.print(_ecHighRef[pointNum], 1);
  Serial.print(F("uS H"));
  Serial.print(pointNum + 1);
  Serial.print(F(":"));
  Serial.print(_ecHighCount);
  Serial.print(F("/"));
  Serial.println(_getRequiredECHighPoints());
  
  if (_ecHighCount == _getRequiredECHighPoints()) {
    Serial.println(F("ECH: calc..."));
    _calculateECHighEquation();
  }
}

/*******************************************************************************
 * FORCE CALIBRATION - pH
 ******************************************************************************/
void Calibration::forcepHPoint(uint8_t pointNum, float voltage_mV) {
  if (pointNum >= PH_CAL_POINTS) {
    Serial.println(F("ERR: pH pt# invalid"));
    return;
  }
  
  _pHVolts[pointNum] = voltage_mV;
  
  _pHCount = 0;
  for (uint8_t i = 0; i < PH_CAL_POINTS; i++) {
    if (_pHVolts[i] > 0.0) _pHCount++;
  }
  
  Serial.print(F("F-pH P"));
  Serial.print(pointNum + 1);
  Serial.print(F(": Vmv="));
  Serial.print(voltage_mV, 1);
  Serial.print(F(" Ref="));
  Serial.print(_pHRef[pointNum], 2);
  Serial.print(F("pH P"));
  Serial.print(pointNum + 1);
  Serial.print(F(":"));
  Serial.print(_pHCount);
  Serial.print(F("/"));
  Serial.println(_getRequiredpHPoints());
  
  if (_pHCount == _getRequiredpHPoints()) {
    Serial.println(F("pH: calc..."));
    _calculatepHEquation();
  }
}

/*******************************************************************************
 * FORCE CALIBRATION - TEMPERATURE
 ******************************************************************************/
void Calibration::forceTempPoint(uint8_t pointNum, float voltage_mV) {
  if (pointNum >= TEMP_CAL_POINTS) {
    Serial.println(F("ERR: Temp pt# invalid"));
    return;
  }
  
  _tempVolts[pointNum] = voltage_mV;
  
  _tempCount = 0;
  for (uint8_t i = 0; i < TEMP_CAL_POINTS; i++) {
    if (_tempVolts[i] > 0.0) _tempCount++;
  }
  
  Serial.print(F("F-Temp P"));
  Serial.print(pointNum + 1);
  Serial.print(F(": Vmv="));
  Serial.print(voltage_mV, 1);
  Serial.print(F(" Ref="));
  Serial.print(_tempRef[pointNum], 1);
  Serial.print(F("C T"));
  Serial.print(pointNum + 1);
  Serial.print(F(":"));
  Serial.print(_tempCount);
  Serial.print(F("/"));
  Serial.println(_getRequiredTempPoints());
  
  if (_tempCount == _getRequiredTempPoints()) {
    Serial.println(F("Temp: calc..."));
    _calculateTempEquation();
  }
}

/*******************************************************************************
 * REFERENCE VALUE MANAGEMENT - EC
 ******************************************************************************/
void Calibration::setECLowRef(uint8_t pointNum, float value) {
  if (pointNum >= EC_LOW_CAL_POINTS) {
    Serial.println(F("ERR: Invalid pt#"));
    return;
  }
  _ecLowRef[pointNum] = value;
  Serial.print(F("ECL P"));
  Serial.print(pointNum + 1);
  Serial.print(F(" ref="));
  Serial.print(value, 1);
  Serial.println(F("uS"));
}

void Calibration::setECHighRef(uint8_t pointNum, float value) {
  if (pointNum >= EC_HIGH_CAL_POINTS) {
    Serial.println(F("ERR: Invalid pt#"));
    return;
  }
  _ecHighRef[pointNum] = value;
  Serial.print(F("ECH P"));
  Serial.print(pointNum + 1);
  Serial.print(F(" ref="));
  Serial.print(value, 1);
  Serial.println(F("uS"));
}

/*******************************************************************************
 * REFERENCE VALUE MANAGEMENT - pH
 ******************************************************************************/
void Calibration::setpHRef(uint8_t pointNum, float value) {
  if (pointNum >= PH_CAL_POINTS) {
    Serial.println(F("ERR: Invalid pt#"));
    return;
  }
  _pHRef[pointNum] = value;
  Serial.print(F("pH P"));
  Serial.print(pointNum + 1);
  Serial.print(F(" ref="));
  Serial.print(value, 2);
  Serial.println(F("pH"));
}

/*******************************************************************************
 * REFERENCE VALUE MANAGEMENT - TEMPERATURE
 ******************************************************************************/
void Calibration::setTempRef(uint8_t pointNum, float value) {
  if (pointNum >= TEMP_CAL_POINTS) {
    Serial.println(F("ERR: Invalid pt#"));
    return;
  }
  _tempRef[pointNum] = value;
  Serial.print(F("Temp P"));
  Serial.print(pointNum + 1);
  Serial.print(F(" ref="));
  Serial.print(value, 1);
  Serial.println(F("C"));
}

/*******************************************************************************
 * EQUATION CALCULATION - EC LOW RANGE
 * 
 * Calculates calibration equation after all points are captured.
 ******************************************************************************/
void Calibration::_calculateECLowEquation() {
  uint8_t requiredPoints = _getRequiredECLowPoints();
  
  // Collect only the points required for current mode
  float volts[5];
  float refs[5];
  uint8_t count = 0;
  
  for (uint8_t i = 0; i < EC_LOW_CAL_POINTS; i++) {
    if (_isECLowPointRequired(i)) {
      volts[count] = _ecLowVolts[i];
      refs[count] = _ecLowRef[i];
      count++;
    }
  }
  
  // Validate points
  if (!_validatePoints(volts, count, "EC Low")) {
    return;
  }
  
  // Calculate equation using linear regression
  _linearRegression(volts, refs, count, _ecLowC, _ecLowD);
  
  // Calculate quality metrics
  _ecLowR2 = _calculateR2(volts, refs, _ecLowC, _ecLowD, count);
  _ecLowRMSE = _calculateRMSE(volts, refs, _ecLowC, _ecLowD, count);
  
  // Mark as calibrated
  _isECLowCal = true;
  
  // Print results
  Serial.print(F("EC_LOW: C="));
  Serial.print(_ecLowC, 6);
  Serial.print(F(" D="));
  Serial.print(_ecLowD, 2);
  Serial.print(F(" R2="));
  Serial.print(_ecLowR2, 4);
  Serial.print(F(" RMSE="));
  Serial.println(_ecLowRMSE, 2);
  
  if (_ecLowR2 < MIN_R_SQUARED) {
    Serial.print(F("WARN: Low R2="));
    Serial.println(_ecLowR2, 4);
  }
}

/*******************************************************************************
 * EQUATION CALCULATION - EC HIGH RANGE
 ******************************************************************************/
void Calibration::_calculateECHighEquation() {
  // Validate points
  if (!_validatePoints(_ecHighVolts, EC_HIGH_CAL_POINTS, "EC High")) {
    return;
  }
  
  // Calculate equation
  _linearRegression(_ecHighVolts, _ecHighRef, EC_HIGH_CAL_POINTS, _ecHighC, _ecHighD);
  
  // Calculate quality metrics
  _ecHighR2 = _calculateR2(_ecHighVolts, _ecHighRef, _ecHighC, _ecHighD, EC_HIGH_CAL_POINTS);
  _ecHighRMSE = _calculateRMSE(_ecHighVolts, _ecHighRef, _ecHighC, _ecHighD, EC_HIGH_CAL_POINTS);
  
  // Mark as calibrated
  _isECHighCal = true;
  
  // Print results
  Serial.print(F("EC_HIGH: C="));
  Serial.print(_ecHighC, 6);
  Serial.print(F(" D="));
  Serial.print(_ecHighD, 2);
  Serial.print(F(" R2="));
  Serial.print(_ecHighR2, 4);
  Serial.print(F(" RMSE="));
  Serial.println(_ecHighRMSE, 2);
  
  if (_ecHighR2 < MIN_R_SQUARED) {
    Serial.print(F("WARN: Low R2="));
    Serial.println(_ecHighR2, 4);
  }
}

/*******************************************************************************
 * EQUATION CALCULATION - pH
 ******************************************************************************/
void Calibration::_calculatepHEquation() {
  // Validate points
  if (!_validatePoints(_pHVolts, PH_CAL_POINTS, "pH")) {
    return;
  }
  
  // Calculate equation
  _linearRegression(_pHVolts, _pHRef, PH_CAL_POINTS, _pHC, _pHD);
  
  // Calculate quality metrics
  _pHR2 = _calculateR2(_pHVolts, _pHRef, _pHC, _pHD, PH_CAL_POINTS);
  _pHRMSE = _calculateRMSE(_pHVolts, _pHRef, _pHC, _pHD, PH_CAL_POINTS);
  
  // Mark as calibrated
  _ispHCal = true;
  
  // Print results
  Serial.print(F("pH: C="));
  Serial.print(_pHC, 6);
  Serial.print(F(" D="));
  Serial.print(_pHD, 2);
  Serial.print(F(" R2="));
  Serial.print(_pHR2, 4);
  Serial.print(F(" RMSE="));
  Serial.println(_pHRMSE, 3);
  
  if (_pHR2 < MIN_R_SQUARED) {
    Serial.print(F("WARN: Low R2="));
    Serial.println(_pHR2, 4);
  }
}

/*******************************************************************************
 * EQUATION CALCULATION - TEMPERATURE
 ******************************************************************************/
void Calibration::_calculateTempEquation() {
  // Validate points
  if (!_validatePoints(_tempVolts, TEMP_CAL_POINTS, "Temperature")) {
    return;
  }
  
  // Calculate equation
  _linearRegression(_tempVolts, _tempRef, TEMP_CAL_POINTS, _tempC, _tempD);
  
  // Calculate quality metrics
  _tempR2 = _calculateR2(_tempVolts, _tempRef, _tempC, _tempD, TEMP_CAL_POINTS);
  _tempRMSE = _calculateRMSE(_tempVolts, _tempRef, _tempC, _tempD, TEMP_CAL_POINTS);
  
  // Mark as calibrated
  _isTempCal = true;
  
  // Print results
  Serial.print(F("TEMP: C="));
  Serial.print(_tempC, 6);
  Serial.print(F(" D="));
  Serial.print(_tempD, 2);
  Serial.print(F(" R2="));
  Serial.print(_tempR2, 4);
  Serial.print(F(" RMSE="));
  Serial.println(_tempRMSE, 2);
  
  if (_tempR2 < MIN_R_SQUARED) {
    Serial.print(F("WARN: Low R2="));
    Serial.println(_tempR2, 4);
  }
}

/*******************************************************************************
 * CALIBRATED READINGS - EC
 * 
 * Returns calibrated EC value using stored calibration equations.
 * Automatically selects low or high range based on voltage.
 ******************************************************************************/
float Calibration::getCalibratedEC() {
  // Read current EC voltage
  float voltage = _sensor->readVoltage_EC();
  
  // Determine which range to use based on voltage threshold
  if (voltage < EC_RANGE_THRESHOLD_MV) {
    // Use LOW range equation
    if (!_isECLowCal) {
      // Not calibrated - return -1.0 to indicate error
      return -1.0;
    }
    
    // Apply low range equation: EC = C × voltage + D
    float ec = _ecLowC * voltage + _ecLowD;
    
    // Ensure non-negative (EC can't be negative)
    if (ec < 0.0) ec = 0.0;
    
    return ec;
    
  } else {
    // Use HIGH range equation
    if (!_isECHighCal) {
      // Not calibrated - return -1.0 to indicate error
      return -1.0;
    }
    
    // Apply high range equation: EC = C × voltage + D
    float ec = _ecHighC * voltage + _ecHighD;
    
    // Ensure non-negative
    if (ec < 0.0) ec = 0.0;
    
    return ec;
  }
}

/*******************************************************************************
 * CALIBRATED READINGS - pH
 * 
 * Returns calibrated pH value using stored calibration equation.
 ******************************************************************************/
float Calibration::getCalibratedpH() {
  // Check if calibrated
  if (!_ispHCal) {
    return -1.0;  // Error indicator
  }
  
  // Read current pH voltage
  float voltage = _sensor->readVoltage_pH();
  
  // Apply calibration equation: pH = C × voltage + D
  float pH = _pHC * voltage + _pHD;
  
  // Clamp to valid pH range (0-14)
  if (pH < 0.0) pH = 0.0;
  if (pH > 14.0) pH = 14.0;
  
  return pH;
}

/*******************************************************************************
 * CALIBRATED READINGS - TEMPERATURE
 * 
 * Returns calibrated temperature value using stored calibration equation.
 ******************************************************************************/
float Calibration::getCalibratedTemperature() {
  // Check if calibrated
  if (!_isTempCal) {
    // If not calibrated, return uncalibrated reading from sensor
    // This allows temperature to work even without calibration
    return _sensor->readTemperature();
  }
  
  // Read current temperature voltage
  float voltage = _sensor->readVoltage_Temp();
  
  // Apply calibration equation: T = C × voltage + D
  float temperature = _tempC * voltage + _tempD;
  
  return temperature;
}

/*******************************************************************************
 * STATUS DISPLAY - SHOW ALL CALIBRATION EQUATIONS
 * 
 * Displays detailed calibration information for all sensors.
 ******************************************************************************/
void Calibration::showEquations() {
  Serial.println(F("CALIBRATION EQUATIONS"));
  Serial.println();
  
  // === EC LOW RANGE ===
  Serial.println(F("--- EC LOW RANGE ---"));
  if (_isECLowCal) {
    Serial.print(F("Equation: EC = "));
    Serial.print(_ecLowC, 6);
    Serial.print(F(" * V_mV + "));
    Serial.println(_ecLowD, 2);
    
    Serial.println(F("Calibration Points:"));
    for (uint8_t i = 0; i < EC_LOW_CAL_POINTS; i++) {
      if (_isECLowPointRequired(i) && _ecLowVolts[i] > 0.0) {
        Serial.print(F("  P"));
        Serial.print(i + 1);
        Serial.print(F(": "));
        Serial.print(_ecLowVolts[i], 1);
        Serial.print(F("mV -> "));
        Serial.print(_ecLowRef[i], 1);
        Serial.println(F("uS/cm"));
      }
    }
    
    Serial.print(F("Quality: R2="));
    Serial.print(_ecLowR2, 4);
    Serial.print(F(" RMSE="));
    Serial.print(_ecLowRMSE, 2);
    Serial.println(F(" uS/cm"));
  } else {
    Serial.println(F("NOT CALIBRATED"));
  }
  Serial.println();
  
  // === EC HIGH RANGE ===
  Serial.println(F("--- EC HIGH RANGE ---"));
  if (_isECHighCal) {
    Serial.print(F("Equation: EC = "));
    Serial.print(_ecHighC, 6);
    Serial.print(F(" * V_mV + "));
    Serial.println(_ecHighD, 2);
    
    Serial.println(F("Calibration Points:"));
    for (uint8_t i = 0; i < EC_HIGH_CAL_POINTS; i++) {
      if (_ecHighVolts[i] > 0.0) {
        Serial.print(F("  P"));
        Serial.print(i + 1);
        Serial.print(F(": "));
        Serial.print(_ecHighVolts[i], 1);
        Serial.print(F("mV -> "));
        Serial.print(_ecHighRef[i], 1);
        Serial.println(F("uS/cm"));
      }
    }
    
    Serial.print(F("Quality: R2="));
    Serial.print(_ecHighR2, 4);
    Serial.print(F(" RMSE="));
    Serial.print(_ecHighRMSE, 2);
    Serial.println(F(" uS/cm"));
  } else {
    Serial.println(F("NOT CALIBRATED"));
  }
  Serial.println();
  
  // === pH ===
  Serial.println(F("--- pH ---"));
  if (_ispHCal) {
    Serial.print(F("Equation: pH = "));
    Serial.print(_pHC, 6);
    Serial.print(F(" * V_mV + "));
    Serial.println(_pHD, 2);
    
    Serial.println(F("Calibration Points:"));
    for (uint8_t i = 0; i < PH_CAL_POINTS; i++) {
      if (_pHVolts[i] > 0.0) {
        Serial.print(F("  P"));
        Serial.print(i + 1);
        Serial.print(F(": "));
        Serial.print(_pHVolts[i], 1);
        Serial.print(F("mV -> "));
        Serial.print(_pHRef[i], 2);
        Serial.println(F("pH"));
      }
    }
    
    Serial.print(F("Quality: R2="));
    Serial.print(_pHR2, 4);
    Serial.print(F(" RMSE="));
    Serial.print(_pHRMSE, 3);
    Serial.println(F(" pH"));
  } else {
    Serial.println(F("NOT CALIBRATED"));
  }
  Serial.println();
  
  // === TEMPERATURE ===
  Serial.println(F("--- TEMPERATURE ---"));
  if (_isTempCal) {
    Serial.print(F("Equation: T = "));
    Serial.print(_tempC, 6);
    Serial.print(F(" * V_mV + "));
    Serial.println(_tempD, 2);
    
    Serial.println(F("Calibration Points:"));
    for (uint8_t i = 0; i < TEMP_CAL_POINTS; i++) {
      if (_tempVolts[i] > 0.0) {
        Serial.print(F("  P"));
        Serial.print(i + 1);
        Serial.print(F(": "));
        Serial.print(_tempVolts[i], 1);
        Serial.print(F("mV -> "));
        Serial.print(_tempRef[i], 1);
        Serial.println(F("C"));
      }
    }
    
    Serial.print(F("Quality: R2="));
    Serial.print(_tempR2, 4);
    Serial.print(F(" RMSE="));
    Serial.print(_tempRMSE, 2);
    Serial.println(F(" C"));
  } else {
    Serial.println(F("NOT CALIBRATED"));
  }
}

/*******************************************************************************
 * STATUS DISPLAY - SHOW CALIBRATION STATUS
 * 
 * Displays summary of calibration status for all sensors.
 ******************************************************************************/
void Calibration::showStatus() {
  Serial.println(F("CALIBRATION STATUS"));
  
  // EC Low Range
  Serial.print(F("EC Low Range:  "));
  if (_isECLowCal) {
    Serial.print(F("CALIBRATED ("));
    Serial.print(_getRequiredECLowPoints());
    Serial.print(F(" points, R2="));
    Serial.print(_ecLowR2, 4);
    Serial.println(F(")"));
  } else {
    Serial.print(F("NOT CALIBRATED ("));
    Serial.print(_ecLowCount);
    Serial.print(F("/"));
    Serial.print(_getRequiredECLowPoints());
    Serial.println(F(" points captured)"));
  }
  
  // EC High Range
  Serial.print(F("EC High Range: "));
  if (_isECHighCal) {
    Serial.print(F("CALIBRATED ("));
    Serial.print(_getRequiredECHighPoints());
    Serial.print(F(" points, R2="));
    Serial.print(_ecHighR2, 4);
    Serial.println(F(")"));
  } else {
    Serial.print(F("NOT CALIBRATED ("));
    Serial.print(_ecHighCount);
    Serial.print(F("/"));
    Serial.print(_getRequiredECHighPoints());
    Serial.println(F(" points captured)"));
  }
  
  // pH
  Serial.print(F("pH:            "));
  if (_ispHCal) {
    Serial.print(F("CALIBRATED ("));
    Serial.print(_getRequiredpHPoints());
    Serial.print(F(" points, R2="));
    Serial.print(_pHR2, 4);
    Serial.println(F(")"));
  } else {
    Serial.print(F("NOT CALIBRATED ("));
    Serial.print(_pHCount);
    Serial.print(F("/"));
    Serial.print(_getRequiredpHPoints());
    Serial.println(F(" points captured)"));
  }
  
  // Temperature
  Serial.print(F("Temperature:   "));
  if (_isTempCal) {
    Serial.print(F("CALIBRATED ("));
    Serial.print(_getRequiredTempPoints());
    Serial.print(F(" points, R2="));
    Serial.print(_tempR2, 4);
    Serial.println(F(")"));
  } else {
    Serial.print(F("NOT CALIBRATED ("));
    Serial.print(_tempCount);
    Serial.print(F("/"));
    Serial.print(_getRequiredTempPoints());
    Serial.println(F(" points captured)"));
  }
}

/*******************************************************************************
 * STATUS DISPLAY - SHOW QUALITY METRICS
 * 
 * Displays quality metrics (R² and RMSE) for all calibrated sensors.
 ******************************************************************************/
void Calibration::showQuality() {
  Serial.println(F("CALIBRATION QUALITY METRICS"));
  
  Serial.print(F("EC Low:  R2="));
  if (_isECLowCal) {
    Serial.print(_ecLowR2, 4);
    Serial.print(F(" RMSE="));
    Serial.print(_ecLowRMSE, 2);
    Serial.println(F(" uS/cm"));
  } else {
    Serial.println(F("N/A"));
  }
  
  Serial.print(F("EC High: R2="));
  if (_isECHighCal) {
    Serial.print(_ecHighR2, 4);
    Serial.print(F(" RMSE="));
    Serial.print(_ecHighRMSE, 2);
    Serial.println(F(" uS/cm"));
  } else {
    Serial.println(F("N/A"));
  }
  
  Serial.print(F("pH:      R2="));
  if (_ispHCal) {
    Serial.print(_pHR2, 4);
    Serial.print(F(" RMSE="));
    Serial.print(_pHRMSE, 3);
    Serial.println(F(" pH"));
  } else {
    Serial.println(F("N/A"));
  }
  
  Serial.print(F("Temp:    R2="));
  if (_isTempCal) {
    Serial.print(_tempR2, 4);
    Serial.print(F(" RMSE="));
    Serial.print(_tempRMSE, 2);
    Serial.println(F(" C"));
  } else {
    Serial.println(F("N/A"));
  }
  
  Serial.println();
  Serial.println(F("R2 > 0.95 is good, closer to 1.0 is better"));
  Serial.println(F("RMSE: Lower is better (average error magnitude)"));
}

/*******************************************************************************
 * DATA ACCESS METHODS - FOR EEPROM STORAGE
 * 
 * These methods allow EEPROMManager to save and load calibration data.
 ******************************************************************************/

// Get EC calibration equations
void Calibration::getECLowEquation(float& C, float& D, float& R2, float& RMSE) const {
  C = _ecLowC;
  D = _ecLowD;
  R2 = _ecLowR2;
  RMSE = _ecLowRMSE;
}

void Calibration::getECHighEquation(float& C, float& D, float& R2, float& RMSE) const {
  C = _ecHighC;
  D = _ecHighD;
  R2 = _ecHighR2;
  RMSE = _ecHighRMSE;
}

// Get pH calibration equation
void Calibration::getpHEquation(float& C, float& D, float& R2, float& RMSE) const {
  C = _pHC;
  D = _pHD;
  R2 = _pHR2;
  RMSE = _pHRMSE;
}

// Get Temperature calibration equation
void Calibration::getTempEquation(float& C, float& D, float& R2, float& RMSE) const {
  C = _tempC;
  D = _tempD;
  R2 = _tempR2;
  RMSE = _tempRMSE;
}

// Get EC calibration data (voltages and references)
void Calibration::getECLowData(float volts[], float refs[]) const {
  for (uint8_t i = 0; i < EC_LOW_CAL_POINTS; i++) {
    volts[i] = _ecLowVolts[i];
    refs[i] = _ecLowRef[i];
  }
}

void Calibration::getECHighData(float volts[], float refs[]) const {
  for (uint8_t i = 0; i < EC_HIGH_CAL_POINTS; i++) {
    volts[i] = _ecHighVolts[i];
    refs[i] = _ecHighRef[i];
  }
}

// Get pH calibration data
void Calibration::getpHData(float volts[], float refs[]) const {
  for (uint8_t i = 0; i < PH_CAL_POINTS; i++) {
    volts[i] = _pHVolts[i];
    refs[i] = _pHRef[i];
  }
}

// Get Temperature calibration data
void Calibration::getTempData(float volts[], float refs[]) const {
  for (uint8_t i = 0; i < TEMP_CAL_POINTS; i++) {
    volts[i] = _tempVolts[i];
    refs[i] = _tempRef[i];
  }
}

// Set EC calibration equations (used when loading from EEPROM)
void Calibration::setECLowEquation(float C, float D, float R2, float RMSE) {
  _ecLowC = C;
  _ecLowD = D;
  _ecLowR2 = R2;
  _ecLowRMSE = RMSE;
}

void Calibration::setECHighEquation(float C, float D, float R2, float RMSE) {
  _ecHighC = C;
  _ecHighD = D;
  _ecHighR2 = R2;
  _ecHighRMSE = RMSE;
}

// Set pH calibration equation
void Calibration::setpHEquation(float C, float D, float R2, float RMSE) {
  _pHC = C;
  _pHD = D;
  _pHR2 = R2;
  _pHRMSE = RMSE;
}

// Set Temperature calibration equation
void Calibration::setTempEquation(float C, float D, float R2, float RMSE) {
  _tempC = C;
  _tempD = D;
  _tempR2 = R2;
  _tempRMSE = RMSE;
}

// Set EC calibration data
void Calibration::setECLowData(const float volts[], const float refs[]) {
  for (uint8_t i = 0; i < EC_LOW_CAL_POINTS; i++) {
    _ecLowVolts[i] = volts[i];
    _ecLowRef[i] = refs[i];
  }
}

void Calibration::setECHighData(const float volts[], const float refs[]) {
  for (uint8_t i = 0; i < EC_HIGH_CAL_POINTS; i++) {
    _ecHighVolts[i] = volts[i];
    _ecHighRef[i] = refs[i];
  }
}

// Set pH calibration data
void Calibration::setpHData(const float volts[], const float refs[]) {
  for (uint8_t i = 0; i < PH_CAL_POINTS; i++) {
    _pHVolts[i] = volts[i];
    _pHRef[i] = refs[i];
  }
}

// Set Temperature calibration data
void Calibration::setTempData(const float volts[], const float refs[]) {
  for (uint8_t i = 0; i < TEMP_CAL_POINTS; i++) {
    _tempVolts[i] = volts[i];
    _tempRef[i] = refs[i];
  }
}

// Set calibration flags (used when loading from EEPROM)
void Calibration::setCalibrationFlags(bool ecLowCal, bool ecHighCal, 
                                      bool pHCal, bool tempCal) {
  _isECLowCal = ecLowCal;
  _isECHighCal = ecHighCal;
  _ispHCal = pHCal;
  _isTempCal = tempCal;
  
  // Update point counts based on flags
  if (_isECLowCal) {
    _ecLowCount = _getRequiredECLowPoints();
  }
  if (_isECHighCal) {
    _ecHighCount = _getRequiredECHighPoints();
  }
  if (_ispHCal) {
    _pHCount = _getRequiredpHPoints();
  }
  if (_isTempCal) {
    _tempCount = _getRequiredTempPoints();
  }
}

/*******************************************************************************
 * SIMPLE GETTERS FOR PYTHON INTEGRATION AND PLOTTING
 ******************************************************************************/

CalibrationData Calibration::getECLowData() const {
  CalibrationData data = {{0}, {0}};
  for (uint8_t i = 0; i < EC_LOW_CAL_POINTS; i++) {
    data.voltages[i] = _ecLowVolts[i];
    data.references[i] = _ecLowRef[i];
  }
  return data;
}

CalibrationData Calibration::getECHighData() const {
  CalibrationData data = {{0}, {0}};
  for (uint8_t i = 0; i < EC_HIGH_CAL_POINTS; i++) {
    data.voltages[i] = _ecHighVolts[i];
    data.references[i] = _ecHighRef[i];
  }
  return data;
}

CalibrationData Calibration::getpHData() const {
  CalibrationData data = {{0}, {0}};
  for (uint8_t i = 0; i < PH_CAL_POINTS; i++) {
    data.voltages[i] = _pHVolts[i];
    data.references[i] = _pHRef[i];
  }
  return data;
}

CalibrationData Calibration::getTempData() const {
  CalibrationData data = {{0}, {0}};
  for (uint8_t i = 0; i < TEMP_CAL_POINTS; i++) {
    data.voltages[i] = _tempVolts[i];
    data.references[i] = _tempRef[i];
  }
  return data;
}

CalibrationEquation Calibration::getECLowEquation() const {
  CalibrationEquation eq;
  eq.C = _ecLowC;
  eq.D = _ecLowD;
  eq.R2 = _ecLowR2;
  eq.RMSE = _ecLowRMSE;
  return eq;
}

CalibrationEquation Calibration::getECHighEquation() const {
  CalibrationEquation eq;
  eq.C = _ecHighC;
  eq.D = _ecHighD;
  eq.R2 = _ecHighR2;
  eq.RMSE = _ecHighRMSE;
  return eq;
}

CalibrationEquation Calibration::getpHEquation() const {
  CalibrationEquation eq;
  eq.C = _pHC;
  eq.D = _pHD;
  eq.R2 = _pHR2;
  eq.RMSE = _pHRMSE;
  return eq;
}

CalibrationEquation Calibration::getTempEquation() const {
  CalibrationEquation eq;
  eq.C = _tempC;
  eq.D = _tempD;
  eq.R2 = _tempR2;
  eq.RMSE = _tempRMSE;
  return eq;
}

/*******************************************************************************
 * END OF CALIBRATION.CPP - COMPLETE IMPLEMENTATION
 * 
 * All features implemented:
 *   ✓ Constructor & initialization
 *   ✓ Linear regression (shared by all sensors)
 *   ✓ R² and RMSE calculation (shared by all)
 *   ✓ Point validation (shared by all)
 *   ✓ Mode management (EC, pH, Temperature)
 *   ✓ Point capture (all sensors)
 *   ✓ Reference value management (all sensors)
 *   ✓ Automatic equation calculation (all sensors)
 *   ✓ Calibrated readings (all sensors)
 *   ✓ Status display (equations, status, quality)
 *   ✓ EEPROM data access (get/set methods)
 *   ✓ Helper methods and utilities
 *   ✓ Simple getters for Python integration and plotting
 * 
 * Calibration system is now COMPLETE for EC, pH, and Temperature!
 * 
 * Next: Chunk 6 - EEPROM storage implementation
 ******************************************************************************/
