#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = "0.1.0"
__description__ = "AT-ENKA (Toolset for Atmel AT-SAM4 Controllers)."
__copyright__ = """
  AT-ENKA (Toolset for Atmel AT-SAM4 Controllers).

  (C) 2015 by Christoph Schueler <https://github.com/christoph2,
                                       cpu12.gems@googlemail.com>

  All Rights Reserved

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along
  with this program; if not, write to the Free Software Foundation, Inc.,
  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

import serial

class TimeoutError(Exception): pass

class Port(object):

    def __init__(self, name):
        self.opened = False
        try:
            self._port = serial.Serial(port = name, baudrate = 115200, bytesize = 8, timeout = 0.0125, writeTimeout = 1.0)
        except serial.SerialException as e:
            print str(e)
            self.opened = False
            raise
        else:
            self.opened = True
            
    def __del__(self):
        self.close()

    def close(self):
        if self.opened:
            self._port.close()
            self.opened = False

    def write(self, data):
        self._port.write(data)
        
    def read(self, length):
        if length == 0:
            return bytearray()
        data = self._port.read(length)
        if len(data) == 0:
            raise TimeoutError("Error on read operation. Requested %d bytes got %d" % (length, len(data)))
        return bytearray(data)
        
    def flush(self):
        #self._port.flush()
        self._port.flushOutput()
        self._port.flushInput()

"""
    cmd = Command(port)
    cmd.nonInteractive()
    data = port.read(32)
    print data.strip()
    cmd.version()
    data = port.read(32)
    print "SAM-BA Ver.  : %s" % data.strip()
    print

    vector = cmd.readLong(0x00000000)
    print "%8x" % vector

    vector = cmd.readLong(0x4004)
    print "%8x" % vector
    
    cinfo = cmd.chipInfo()
    #print cinfo

    print "ChipID       : 0x%08x" % cmd.chipId()
    print "Friendly Name: %s" % cinfo.friendlyName
    print "Architecture : %s" % cinfo.architecture.description
    print "Processor    : %s" % cinfo.processor.description
    print "NVM Type     : %s" % cinfo.nvpType.description
    print "NVM Size0    : %s" % cinfo.nvpSize0.description
    print "NVM Size1    : %s" % cinfo.nvpSize1.description
    print "SRAM Size    : %s" % cinfo.sramSize.description
    print "Version      : %s" % cinfo.version
    if cinfo.ext:
        print "Package      : %s" % cinfo.package
        print "LCD          : %s" % cinfo.lcd
        print "USB          : %s" % cinfo.usb
        print "USB/Full     : %s" % cinfo. usbfull
        print "AES          : %s" % cinfo.aes

    bulk = cmd.read(0x0000, 64 * 1024)
    print "Länge", len(bulk)
    #print bulk
    port.close()
"""
