/*******************************************************************************
 * EEPROMMANAGER.H - Persistent Calibration Storage (ALL SENSORS)
 * 
 * Purpose:
 *   Manages saving and loading calibration data to/from Arduino's EEPROM
 *   for EC, pH, and Temperature sensors.
 *   Ensures data integrity using CRC16 checksums and magic numbers.
 * 
 * Responsibilities:
 *   - Save complete calibration state for all sensors to EEPROM
 *   - Load calibration state from EEPROM
 *   - Verify data integrity (magic number, version, checksum)
 *   - Handle version migration if needed
 * 
 * EEPROM Structure (182 bytes total):
 *   See Config.h for detailed memory layout
 * 
 * Safety Features:
 *   - Magic number (0xEC57) validates this is our data
 *   - Version number enables future compatibility
 *   - CRC16 checksum detects corruption
 *   - Graceful handling of empty/corrupt EEPROM
 * 
 * Author: System Rewrite v1.0 - Complete Edition
 * Date: 2026-02-16
 ******************************************************************************/

#ifndef EEPROMMANAGER_H
#define EEPROMMANAGER_H

#include <Arduino.h>
#include <EEPROM.h>
#include "Config.h"
#include "Calibration.h"

/*******************************************************************************
 * CLASS: EEPROMManager
 * 
 * Simple, reliable EEPROM storage manager for all sensor calibration data.
 * Uses CRC16 for integrity checking.
 ******************************************************************************/
class EEPROMManager {
public:
  /***************************************************************************
   * CONSTRUCTOR
   ***************************************************************************/
  EEPROMManager();
  
  /***************************************************************************
   * SAVE CALIBRATION TO EEPROM
   * 
   * Saves complete calibration state for ALL sensors to EEPROM with
   * integrity checking.
   ***************************************************************************/
  bool save(Calibration& cal);
  
  /***************************************************************************
   * LOAD CALIBRATION FROM EEPROM
   * 
   * Loads calibration state for ALL sensors from EEPROM with validation.
   ***************************************************************************/
  bool load(Calibration& cal);
  
  /***************************************************************************
   * VERIFY EEPROM INTEGRITY
   * 
   * Checks if EEPROM contains valid calibration data without loading it.
   ***************************************************************************/
  bool verify();

private:
  /***************************************************************************
   * PRIVATE METHODS - Low-level EEPROM Access
   ***************************************************************************/
  float _readFloat(uint16_t address);
  void _writeFloat(uint16_t address, float value);
  uint16_t _readUint16(uint16_t address);
  void _writeUint16(uint16_t address, uint16_t value);
  uint8_t _readUint8(uint16_t address);
  void _writeUint8(uint16_t address, uint8_t value);
  
  /***************************************************************************
   * PRIVATE METHODS - Checksum Calculation
   ***************************************************************************/
  uint16_t _calculateCRC16(uint16_t startAddr, uint16_t endAddr);
  uint16_t _updateCRC16(uint16_t crc, uint8_t data);
};

#endif // EEPROMMANAGER_H
