/*******************************************************************************
 * EEPROMMANAGER.CPP - Persistent Calibration Storage Implementation
 * 
 * Purpose:
 *   Implements saving and loading of complete calibration state for all sensors
 *   (EC low/high, pH, Temperature) to/from Arduino's EEPROM with integrity
 *   checking using CRC16 checksums.
 * 
 * Key Features:
 *   - Saves complete calibration state (182 bytes)
 *   - CRC16 integrity checking
 *   - Magic number validation
 *   - Version compatibility
 *   - Graceful handling of corrupt/empty EEPROM
 * 
 * Author: System Rewrite v1.0 - Complete Edition
 * Date: 2026-02-16
 ******************************************************************************/

#include "EEPROMManager.h"

/*******************************************************************************
 * CONSTRUCTOR
 ******************************************************************************/
EEPROMManager::EEPROMManager() {
  // No initialization needed - EEPROM object is global
}

/*******************************************************************************
 * SAVE CALIBRATION TO EEPROM
 * 
 * Saves complete calibration state for ALL sensors to EEPROM.
 * 
 * Process:
 *   1. Write magic number and version
 *   2. Write calibration modes
 *   3. Write all equations (EC low/high, pH, Temperature)
 *   4. Write all voltages and references
 *   5. Write calibration flags
 *   6. Calculate and write CRC16 checksum
 * 
 * Returns: true if successful, false on error
 ******************************************************************************/
bool EEPROMManager::save(Calibration& cal) {
  Serial.println(F("Saving calibration to EEPROM..."));
  
  uint16_t addr = 0;  // Current write address
  
  // === HEADER ===
  // Write magic number (validates this is our data)
  _writeUint16(ADDR_MAGIC, EEPROM_MAGIC);
  
  // Write version (for future compatibility)
  _writeUint8(ADDR_VERSION, EEPROM_VERSION);
  
  // Write calibration modes
  _writeUint8(ADDR_EC_LOW_MODE, (uint8_t)cal.getECLowMode());
  _writeUint8(ADDR_EC_HIGH_MODE, (uint8_t)cal.getECHighMode());
  _writeUint8(ADDR_PH_MODE, (uint8_t)cal.getpHMode());
  _writeUint8(ADDR_TEMP_MODE, (uint8_t)cal.getTempMode());
  
  // === EC LOW RANGE EQUATION ===
  float C, D, R2, RMSE;
  cal.getECLowEquation(C, D, R2, RMSE);
  _writeFloat(ADDR_EC_LOW_EQ_C, C);
  _writeFloat(ADDR_EC_LOW_EQ_D, D);
  _writeFloat(ADDR_EC_LOW_EQ_R2, R2);
  _writeFloat(ADDR_EC_LOW_EQ_RMSE, RMSE);
  
  // === EC HIGH RANGE EQUATION ===
  cal.getECHighEquation(C, D, R2, RMSE);
  _writeFloat(ADDR_EC_HIGH_EQ_C, C);
  _writeFloat(ADDR_EC_HIGH_EQ_D, D);
  _writeFloat(ADDR_EC_HIGH_EQ_R2, R2);
  _writeFloat(ADDR_EC_HIGH_EQ_RMSE, RMSE);
  
  // === pH EQUATION ===
  cal.getpHEquation(C, D, R2, RMSE);
  _writeFloat(ADDR_PH_EQ_C, C);
  _writeFloat(ADDR_PH_EQ_D, D);
  _writeFloat(ADDR_PH_EQ_R2, R2);
  _writeFloat(ADDR_PH_EQ_RMSE, RMSE);
  
  // === TEMPERATURE EQUATION ===
  cal.getTempEquation(C, D, R2, RMSE);
  _writeFloat(ADDR_TEMP_EQ_C, C);
  _writeFloat(ADDR_TEMP_EQ_D, D);
  _writeFloat(ADDR_TEMP_EQ_R2, R2);
  _writeFloat(ADDR_TEMP_EQ_RMSE, RMSE);
  
  // === CALIBRATION DATA (voltages and references) ===
  
  // EC Low Range data
  float volts[EC_LOW_CAL_POINTS];
  float refs[EC_LOW_CAL_POINTS];
  cal.getECLowData(volts, refs);
  addr = ADDR_EC_LOW_VOLTS;
  for (uint8_t i = 0; i < EC_LOW_CAL_POINTS; i++) {
    _writeFloat(addr, volts[i]);
    addr += sizeof(float);
  }
  addr = ADDR_EC_LOW_REFS;
  for (uint8_t i = 0; i < EC_LOW_CAL_POINTS; i++) {
    _writeFloat(addr, refs[i]);
    addr += sizeof(float);
  }
  
  // EC High Range data
  float voltsHigh[EC_HIGH_CAL_POINTS];
  float refsHigh[EC_HIGH_CAL_POINTS];
  cal.getECHighData(voltsHigh, refsHigh);
  addr = ADDR_EC_HIGH_VOLTS;
  for (uint8_t i = 0; i < EC_HIGH_CAL_POINTS; i++) {
    _writeFloat(addr, voltsHigh[i]);
    addr += sizeof(float);
  }
  addr = ADDR_EC_HIGH_REFS;
  for (uint8_t i = 0; i < EC_HIGH_CAL_POINTS; i++) {
    _writeFloat(addr, refsHigh[i]);
    addr += sizeof(float);
  }
  
  // pH data
  float voltspH[PH_CAL_POINTS];
  float refspH[PH_CAL_POINTS];
  cal.getpHData(voltspH, refspH);
  addr = ADDR_PH_VOLTS;
  for (uint8_t i = 0; i < PH_CAL_POINTS; i++) {
    _writeFloat(addr, voltspH[i]);
    addr += sizeof(float);
  }
  addr = ADDR_PH_REFS;
  for (uint8_t i = 0; i < PH_CAL_POINTS; i++) {
    _writeFloat(addr, refspH[i]);
    addr += sizeof(float);
  }
  
  // Temperature data
  float voltsTemp[TEMP_CAL_POINTS];
  float refsTemp[TEMP_CAL_POINTS];
  cal.getTempData(voltsTemp, refsTemp);
  addr = ADDR_TEMP_VOLTS;
  for (uint8_t i = 0; i < TEMP_CAL_POINTS; i++) {
    _writeFloat(addr, voltsTemp[i]);
    addr += sizeof(float);
  }
  addr = ADDR_TEMP_REFS;
  for (uint8_t i = 0; i < TEMP_CAL_POINTS; i++) {
    _writeFloat(addr, refsTemp[i]);
    addr += sizeof(float);
  }
  
  // === CALIBRATION FLAGS ===
  _writeUint8(ADDR_EC_LOW_CAL_FLAG, cal.isECLowCalibrated() ? 1 : 0);
  _writeUint8(ADDR_EC_HIGH_CAL_FLAG, cal.isECHighCalibrated() ? 1 : 0);
  _writeUint8(ADDR_PH_CAL_FLAG, cal.ispHCalibrated() ? 1 : 0);
  _writeUint8(ADDR_TEMP_CAL_FLAG, cal.isTempCalibrated() ? 1 : 0);
  
  // === CALCULATE AND WRITE CHECKSUM ===
  // Calculate CRC16 over all data except checksum itself
  uint16_t checksum = _calculateCRC16(ADDR_MAGIC, ADDR_CHECKSUM - 1);
  _writeUint16(ADDR_CHECKSUM, checksum);
  
  Serial.println(F("EEPROM: Save complete"));
  Serial.print(F("Checksum: 0x"));
  Serial.println(checksum, HEX);
  
  return true;
}

/*******************************************************************************
 * LOAD CALIBRATION FROM EEPROM
 * 
 * Loads and validates calibration state for ALL sensors from EEPROM.
 * 
 * Process:
 *   1. Verify magic number
 *   2. Verify version
 *   3. Verify CRC16 checksum
 *   4. Load all data into Calibration object
 * 
 * Returns: true if successful, false if EEPROM is empty/corrupt
 ******************************************************************************/
bool EEPROMManager::load(Calibration& cal) {
  Serial.println(F("Loading calibration from EEPROM..."));
  
  // === VERIFY MAGIC NUMBER ===
  uint16_t magic = _readUint16(ADDR_MAGIC);
  if (magic != EEPROM_MAGIC) {
    Serial.println(F("INFO: EEPROM empty (first boot)"));
    return false;
  }
  
  // === VERIFY VERSION ===
  uint8_t version = _readUint8(ADDR_VERSION);
  if (version != EEPROM_VERSION) {
    Serial.print(F("ERROR: EEPROM version mismatch (found "));
    Serial.print(version);
    Serial.print(F(", expected "));
    Serial.print(EEPROM_VERSION);
    Serial.println(F(")"));
    return false;
  }
  
  // === VERIFY CHECKSUM ===
  uint16_t storedChecksum = _readUint16(ADDR_CHECKSUM);
  uint16_t calculatedChecksum = _calculateCRC16(ADDR_MAGIC, ADDR_CHECKSUM - 1);
  
  if (storedChecksum != calculatedChecksum) {
    Serial.println(F("ERROR: EEPROM corrupt (bad checksum)"));
    Serial.print(F("  Stored:     0x"));
    Serial.println(storedChecksum, HEX);
    Serial.print(F("  Calculated: 0x"));
    Serial.println(calculatedChecksum, HEX);
    return false;
  }
  
  // === LOAD CALIBRATION MODES ===
  ECLowMode ecLowMode = (ECLowMode)_readUint8(ADDR_EC_LOW_MODE);
  ECHighMode ecHighMode = (ECHighMode)_readUint8(ADDR_EC_HIGH_MODE);
  pHMode pHCalMode = (pHMode)_readUint8(ADDR_PH_MODE);
  TempMode tempCalMode = (TempMode)_readUint8(ADDR_TEMP_MODE);
  
  // Set modes (this will reset calibration data, but we'll restore it)
  cal.setECLowMode(ecLowMode);
  cal.setECHighMode(ecHighMode);
  cal.setpHMode(pHCalMode);
  cal.setTempMode(tempCalMode);
  
  // === LOAD EC LOW RANGE EQUATION ===
  float C = _readFloat(ADDR_EC_LOW_EQ_C);
  float D = _readFloat(ADDR_EC_LOW_EQ_D);
  float R2 = _readFloat(ADDR_EC_LOW_EQ_R2);
  float RMSE = _readFloat(ADDR_EC_LOW_EQ_RMSE);
  cal.setECLowEquation(C, D, R2, RMSE);
  
  // === LOAD EC HIGH RANGE EQUATION ===
  C = _readFloat(ADDR_EC_HIGH_EQ_C);
  D = _readFloat(ADDR_EC_HIGH_EQ_D);
  R2 = _readFloat(ADDR_EC_HIGH_EQ_R2);
  RMSE = _readFloat(ADDR_EC_HIGH_EQ_RMSE);
  cal.setECHighEquation(C, D, R2, RMSE);
  
  // === LOAD pH EQUATION ===
  C = _readFloat(ADDR_PH_EQ_C);
  D = _readFloat(ADDR_PH_EQ_D);
  R2 = _readFloat(ADDR_PH_EQ_R2);
  RMSE = _readFloat(ADDR_PH_EQ_RMSE);
  cal.setpHEquation(C, D, R2, RMSE);
  
  // === LOAD TEMPERATURE EQUATION ===
  C = _readFloat(ADDR_TEMP_EQ_C);
  D = _readFloat(ADDR_TEMP_EQ_D);
  R2 = _readFloat(ADDR_TEMP_EQ_R2);
  RMSE = _readFloat(ADDR_TEMP_EQ_RMSE);
  cal.setTempEquation(C, D, R2, RMSE);
  
  // === LOAD CALIBRATION DATA ===
  
  // EC Low Range data
  float volts[EC_LOW_CAL_POINTS];
  float refs[EC_LOW_CAL_POINTS];
  uint16_t addr = ADDR_EC_LOW_VOLTS;
  for (uint8_t i = 0; i < EC_LOW_CAL_POINTS; i++) {
    volts[i] = _readFloat(addr);
    addr += sizeof(float);
  }
  addr = ADDR_EC_LOW_REFS;
  for (uint8_t i = 0; i < EC_LOW_CAL_POINTS; i++) {
    refs[i] = _readFloat(addr);
    addr += sizeof(float);
  }
  cal.setECLowData(volts, refs);
  
  // EC High Range data
  float voltsHigh[EC_HIGH_CAL_POINTS];
  float refsHigh[EC_HIGH_CAL_POINTS];
  addr = ADDR_EC_HIGH_VOLTS;
  for (uint8_t i = 0; i < EC_HIGH_CAL_POINTS; i++) {
    voltsHigh[i] = _readFloat(addr);
    addr += sizeof(float);
  }
  addr = ADDR_EC_HIGH_REFS;
  for (uint8_t i = 0; i < EC_HIGH_CAL_POINTS; i++) {
    refsHigh[i] = _readFloat(addr);
    addr += sizeof(float);
  }
  cal.setECHighData(voltsHigh, refsHigh);
  
  // pH data
  float voltspH[PH_CAL_POINTS];
  float refspH[PH_CAL_POINTS];
  addr = ADDR_PH_VOLTS;
  for (uint8_t i = 0; i < PH_CAL_POINTS; i++) {
    voltspH[i] = _readFloat(addr);
    addr += sizeof(float);
  }
  addr = ADDR_PH_REFS;
  for (uint8_t i = 0; i < PH_CAL_POINTS; i++) {
    refspH[i] = _readFloat(addr);
    addr += sizeof(float);
  }
  cal.setpHData(voltspH, refspH);
  
  // Temperature data
  float voltsTemp[TEMP_CAL_POINTS];
  float refsTemp[TEMP_CAL_POINTS];
  addr = ADDR_TEMP_VOLTS;
  for (uint8_t i = 0; i < TEMP_CAL_POINTS; i++) {
    voltsTemp[i] = _readFloat(addr);
    addr += sizeof(float);
  }
  addr = ADDR_TEMP_REFS;
  for (uint8_t i = 0; i < TEMP_CAL_POINTS; i++) {
    refsTemp[i] = _readFloat(addr);
    addr += sizeof(float);
  }
  cal.setTempData(voltsTemp, refsTemp);
  
  // === LOAD CALIBRATION FLAGS ===
  bool ecLowCal = (_readUint8(ADDR_EC_LOW_CAL_FLAG) == 1);
  bool ecHighCal = (_readUint8(ADDR_EC_HIGH_CAL_FLAG) == 1);
  bool pHCal = (_readUint8(ADDR_PH_CAL_FLAG) == 1);
  bool tempCal = (_readUint8(ADDR_TEMP_CAL_FLAG) == 1);
  cal.setCalibrationFlags(ecLowCal, ecHighCal, pHCal, tempCal);
  
  Serial.println(F("EEPROM: Load complete"));
  Serial.print(F("Checksum verified: 0x"));
  Serial.println(storedChecksum, HEX);
  
  return true;
}

/*******************************************************************************
 * VERIFY EEPROM INTEGRITY
 * 
 * Checks if EEPROM contains valid calibration data without loading it.
 * Useful for diagnostics.
 * 
 * Returns: true if EEPROM has valid data
 ******************************************************************************/
bool EEPROMManager::verify() {
  // Check magic number
  uint16_t magic = _readUint16(ADDR_MAGIC);
  if (magic != EEPROM_MAGIC) {
    return false;
  }
  
  // Check version
  uint8_t version = _readUint8(ADDR_VERSION);
  if (version != EEPROM_VERSION) {
    return false;
  }
  
  // Check checksum
  uint16_t storedChecksum = _readUint16(ADDR_CHECKSUM);
  uint16_t calculatedChecksum = _calculateCRC16(ADDR_MAGIC, ADDR_CHECKSUM - 1);
  
  return (storedChecksum == calculatedChecksum);
}

/*******************************************************************************
 * PRIVATE METHODS - LOW-LEVEL EEPROM ACCESS
 ******************************************************************************/

/*
 * Read a float from EEPROM (4 bytes)
 */
float EEPROMManager::_readFloat(uint16_t address) {
  float value;
  EEPROM.get(address, value);
  return value;
}

/*
 * Write a float to EEPROM (4 bytes)
 */
void EEPROMManager::_writeFloat(uint16_t address, float value) {
  EEPROM.put(address, value);
}

/*
 * Read a uint16_t from EEPROM (2 bytes)
 */
uint16_t EEPROMManager::_readUint16(uint16_t address) {
  uint16_t value;
  EEPROM.get(address, value);
  return value;
}

/*
 * Write a uint16_t to EEPROM (2 bytes)
 */
void EEPROMManager::_writeUint16(uint16_t address, uint16_t value) {
  EEPROM.put(address, value);
}

/*
 * Read a uint8_t from EEPROM (1 byte)
 */
uint8_t EEPROMManager::_readUint8(uint16_t address) {
  return EEPROM.read(address);
}

/*
 * Write a uint8_t to EEPROM (1 byte)
 */
void EEPROMManager::_writeUint8(uint16_t address, uint8_t value) {
  EEPROM.write(address, value);
}

/*******************************************************************************
 * PRIVATE METHODS - CRC16 CHECKSUM CALCULATION
 * 
 * CRC-16-CCITT algorithm (polynomial 0x1021)
 * This is a standard, well-tested checksum algorithm.
 ******************************************************************************/

/*
 * Calculate CRC16 checksum over a range of EEPROM addresses
 * 
 * Parameters:
 *   startAddr - First address to include in checksum
 *   endAddr   - Last address to include in checksum (inclusive)
 * 
 * Returns:
 *   uint16_t - CRC16 checksum value
 */
uint16_t EEPROMManager::_calculateCRC16(uint16_t startAddr, uint16_t endAddr) {
  uint16_t crc = 0xFFFF;  // Initial value
  
  // Process each byte in the range
  for (uint16_t addr = startAddr; addr <= endAddr; addr++) {
    uint8_t data = EEPROM.read(addr);
    crc = _updateCRC16(crc, data);
  }
  
  return crc;
}

/*
 * Update CRC16 with one byte
 * 
 * This is the core CRC16 calculation using the CCITT polynomial (0x1021).
 * 
 * Parameters:
 *   crc  - Current CRC value
 *   data - Byte to add to CRC
 * 
 * Returns:
 *   uint16_t - Updated CRC value
 * 
 * Algorithm:
 *   The CRC is calculated by XORing the data byte into the high byte of the
 *   CRC, then processing each bit. If the MSB is 1, XOR with the polynomial.
 */
uint16_t EEPROMManager::_updateCRC16(uint16_t crc, uint8_t data) {
  crc ^= ((uint16_t)data << 8);  // XOR data into high byte of CRC
  
  // Process each bit (8 bits per byte)
  for (uint8_t i = 0; i < 8; i++) {
    if (crc & 0x8000) {
      // MSB is 1: shift left and XOR with polynomial
      crc = (crc << 1) ^ 0x1021;
    } else {
      // MSB is 0: just shift left
      crc = crc << 1;
    }
  }
  
  return crc;
}

/*******************************************************************************
 * END OF EEPROMMANAGER IMPLEMENTATION
 * 
 * EEPROM storage is now complete:
 *   ✓ Save complete calibration state (all sensors)
 *   ✓ Load complete calibration state (all sensors)
 *   ✓ CRC16 integrity checking
 *   ✓ Magic number validation
 *   ✓ Version checking
 *   ✓ Graceful error handling
 * 
 * Calibration now persists across power cycles!
 * 
 * Next: Chunk 7 - Command parser and serial interface
 ******************************************************************************/
