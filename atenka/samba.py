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

from collections import namedtuple
import struct
import logging
from optparse import OptionParser, OptionGroup
import os


MAX_PAYLOAD = 4000  # 4096

CRLF = '\x0d\x0a'
TERM = '#\x0a'

CHIP_ID_ADDR    = 0x400E0740
EX_ID_ADDR      = 0x400E0744
FLASH_USER_PAGE = 0x00800000
SERIAL_NUMBER   = 0x0080020C    # 128bits.
SRAM            = 0x20000000
GPIO            = 0x400E1000

# Base address of Flash Module.
FLASHCALW               = 0x400A0000

# Offsets.
FCR     = 0x00          # Flash Control Register.
FCMD    = 0x04          # Flash Command Register.
FSR     = 0x08          # Flash Status Register.
FPR     = 0x0C          # Flash Parameter Register.
FVR     = 0x10          # Flash Version Register.
FGPFRHI = 0x14          # Flash General Purpose Fuse Register Hi.
FGPFRLO = 0x18          # Flash General Purpose Fuse Register Lo.
CTRL    = 0x408         # PicoCache Control Register.
SR      = 0x40C         # PicoCache Status Register.
MAINT0  = 0x420         # PicoCache Maintenance Register 0.
MAINT1  = 0x424         # PicoCache Maintenance Register 1.
MCFG    = 0x428         # PicoCache Monitor Configuration Register.
MEN     = 0x42C         # PicoCache Monitor Enable Register.
MCTRL   = 0x430         # PicoCache Monitor Control Register.
MSR     = 0x434         # PicoCache Monitor Status Register.
PVR     = 0x4FC         # Version Register.


"""
0x00 Control Register CR Write-only 0x00000000
0x04 Mode Register MR Read-write 0x00000000
0x08 Interrupt Enable Register IER Write-only 0x00000000
0x0C Interrupt Disable Register IDR Write-only 0x00000000
0x010 Interrupt Mask Register IMR Read-only 0x00000000
0x14 Channel Status Register CSR Read-only 0x00000000
0x18 Receiver Holding Register RHR Read-only 0x00000000
0x1C Transmitter Holding Register THR Write-only 0x00000000
0x20 Baud Rate Generator Register BRGR Read-write 0x00000000
0x24 Receiver Time-out Register RTOR Read-write 0x00000000
0x28 Transmitter Timeguard Register TTGR Read-write 0x00000000
0x40 FI DI Ratio Register FIDI Read-write 0x00000174
0x44 Number of Errors Register NER Read-only 0x00000000
0x4C IrDA Filter Register IFR Read-write 0x00000000
0x50 Manchester Configuration Register MAN Read-write 0x30011004
0x54 LIN Mode Register LINMR Read-write 0x00000000
0x58 LIN Identifier Register LINIR Read-write 0x00000000
0x5C LIN Baud Rate Register LINBR Read-only 0x00000000
0xE4 Write Protect Mode Register WPMR Read-write 0x00000000
0xE8 Write Protect Status Register WPSR Read-only 0x00000000
0xFC Version Register VERSION Read-only
"""


Info = namedtuple("Info", "name description")
DeviceCapabilities = namedtuple("DeviceCapabilities", "friendlyName nvpType architecture sramSize nvpSize0 nvpSize1 processor version ext package lcd usb usbfull aes")


class Samba(object):
    """Interface to ATMEL SAM-BA bootloaders.
    """
    INTERACTIVE = 'T'
    NON_INTERACTIVE = 'N'
    VERSION  = 'V'
    WRITE_WORD = 'W'
    READ_WORD = 'w'
    WRITE_HALF_WORD = 'H'
    READ_HALF_WORD = 'h'
    WRITE_OCTET = 'O'
    READ_OCTET = 'o'
    WRITE = 'S'
    READ = 'R'
    GO = 'G'

    def __init__(self, port):
        self._port = port
        self._interactive = None
        self._port.flush()

    def __del__(self):
        self._port.close()

    def writeCmd(self, cmd):
        self._port.write("%s%s" % (cmd, TERM))

    def _readUnit(self, cmd, addr, dlen):
        self._port.write("%s%08X,%u%s" % (cmd, addr, dlen, TERM))
        data = self._port.read(dlen)
        return int(struct.unpack("<L" if dlen == 4 else "H" if dlen == 2 else "B" if dlen == 1 else None, ''.join([chr(x) for x in data]))[0])

    def _writeUnit(self, cmd, addr, value, dlen):
        MASKS = {
            1: (0x000000ff, "%02X"),
            2: (0x0000ffff, "%04X"),
            4: (0xffffffff, "%08X"),
        }
        data = ("%s" % MASKS[dlen][1]) % (value & MASKS[dlen][0])
        #print("%s%08X,%s%s" % (cmd, addr, data, TERM))
        self._port.write("%s%08X,%s%s" % (cmd, addr, data, TERM))

    def writeCmdParams(self, cmd, *params):
        self._port.write("%s%s" % (cmd, TERM))
        for param in params:
            pass

    def interactive(self):
        self.writeCmd(Samba.INTERACTIVE)
        self._interactive = True

    def nonInteractive(self):
        self.writeCmd(Samba.NON_INTERACTIVE)
        self._interactive = False

    def version(self):
        self.writeCmd(Samba.VERSION)

    def writeLong(self, addr, l):
        self._writeUnit(Samba.WRITE_WORD, addr, l, 4)

    def readLong(self, addr):
        return self._readUnit(self.READ_WORD, addr, 4)

    def writeWord(self, addr, w):
        self._writeUnit(Samba.WRITE_HALF_WORD, addr, w, 2)

    def readWord(self, addr):
        return self._readUnit(self.READ_HALF_WORD, addr, 2)

    def writeByte(self, addr, b):
        self._writeUnit(Samba.WRITE_OCTET, addr, b, 1)

    def readByte(self, addr):
        return self._readUnit(self.READ_OCTET, addr, 1)

    def _write(self, addr, length, data):
        print "Writing {0} bytes...".format(length)
        self._port.write("%s%08X,%08X%s" % (Samba.WRITE, addr, length, TERM))
        self._port.flush()
        self._port.write(data)
        self._port.flush()

    def sendFile(self, addr, data):
        """
        // The SAM firmware has a bug that if the command and binary data
        // are received in the same USB data packet, then the firmware
        // gets confused.  Even though the writes are sperated in the code,
        // USB drivers often do write combining which can put them together
        // in the same USB data packet.  To avoid this, we call the serial
        // port object's flush method before writing the data.
        """
        length = len(data)
        loops = length / MAX_PAYLOAD
        bytesRemaining = length % MAX_PAYLOAD
        addrOffset = addr
        dataOffsetFrom = 0
        dataOffsetTo = MAX_PAYLOAD
        for l in range(loops):
            dslice = data[dataOffsetFrom : dataOffsetTo]

            self._write(addrOffset, MAX_PAYLOAD, dslice)
            #self._port.write("%s%08X,%08X%s" % (Samba.WRITE, addrOffset, MAX_PAYLOAD, TERM))
            #self._port.write(bytearray(dslice))
            #print "addr", addrOffset

            addrOffset += MAX_PAYLOAD
            dataOffsetFrom = dataOffsetTo
            dataOffsetTo = dataOffsetFrom + MAX_PAYLOAD
        if bytesRemaining:
            dslice = data[dataOffsetFrom: dataOffsetFrom + bytesRemaining]

            self._write(addrOffset, bytesRemaining, dslice)
            #self._port.write("%s%08X,%08X%s" % (Samba.WRITE, addrOffset, bytesRemaining, TERM))
            #self._port.write(dslice)
            #print ("%s%08X,%08X%s" % (Samba.WRITE, addrOffset, bytesRemaining, TERM))
            #self._port.write(bytearray(dslice))
            #print "addr", addrOffset

    def receiveFile(self, addr, length):
        loops = length / MAX_PAYLOAD
        bytesRemaining = length % MAX_PAYLOAD
        offset = addr
        result = bytearray()
        for l in range(loops):
            self._port.write("%s%08X,%08X%s" % (Samba.READ, offset, MAX_PAYLOAD, TERM))
            data = self._port.read(length)
            result.extend(data)
            offset += MAX_PAYLOAD
        if bytesRemaining:
            self._port.write("%s%08X,%08X%s" % (Samba.READ, offset, bytesRemaining, TERM))
            data = self._port.read(bytesRemaining)
            result.extend(data)
        return result

    def go(self, addr):
        self._port.write("%s%08X" % (Samba.GO, addr))
        self._port.flush()

    def chipId(self):
        return self.readLong(CHIP_ID_ADDR)

    def exId(self):
        return self.readLong(EX_ID_ADDR)

    def chipInfo(self):
        EXT     = 0x80000000
        NVPTYP  = 0x70000000
        ARCH    = 0x0ff00000
        SRAMSIZ = 0x000f0000
        NVPSIZ2  =0x0000f000
        NVPSIZ  = 0x00000f00
        EPROC   = 0x000000e0
        VERSION = 0x0000001f

        PACKAGE = 0x07000000
        LCD     = 0x00000008
        USBFULL = 0x00000004
        USB     = 0x00000002
        AES     = 0x00000001

        chipId = self.chipId()

        FriendlyNames = {
            0xAB0B0AE0: "ATSAM4LC8C",
            0xAB0A09E0: "ATSAM4LC4C",
            0xAB0A07E0: "ATSAM4LC2C",
            0xAB0B0AE0: "ATSAM4LC8B",
            0xAB0A09E0: "ATSAM4LC4B",
            0xAB0A07E0: "ATSAM4LC2B",
            0xAB0B0AE0: "ATSAM4LC8A",
            0xAB0A09E0: "ATSAM4LC4A",
            0xAB0A07E0: "ATSAM4LC2A",
            0xAB0B0AE0: "ATSAM4LS8C",
            0xAB0A09E0: "ATSAM4LS4C",
            0xAB0A07E0: "ATSAM4LS2C",
            0xAB0B0AE0: "ATSAM4LS8B",
            0xAB0A09E0: "ATSAM4LS4B",
            0xAB0A07E0: "ATSAM4LS2B",
            0xAB0B0AE0: "ATSAM4LS8A",
            0xAB0A09E0: "ATSAM4LS4A",
            0xAB0A07E0: "ATSAM4LS2A",
        }


        NvpTypes = {
            0: Info("ROM", "ROM"),
            1: Info("ROMLESS", "ROMless or on-chip Flash"),
            4: Info("SRAM", "SRAM emulating ROM"),
            2: Info("FLASH", "Embedded Flash Memory"),
            3: Info("ROM_FLASH", "ROM and Embedded Flash Memory"),   ## NVPSIZ is ROM size, NVPSIZ2 is Flash size
        }

        Archs = {
            0x19: Info("AT91SAM9xx", "AT91SAM9xx Series"),
            0x29: Info("AT91SAM9XExx", "AT91SAM9XExx Series"),
            0x34: Info("AT91x34", "AT91x34 Series"),
            0x37: Info("CAP7", "CAP7 Series"),
            0x39: Info("CAP9", "CAP9 Series"),
            0x3B: Info("CAP11", "CAP11 Series"),
            0x40: Info("AT91x40", "AT91x40 Series"),
            0x42: Info("AT91x42", "AT91x42 Series"),
            0x55: Info("AT91x55", "AT91x55 Series"),
            0x60: Info("AT91SAM7Axx", "AT91SAM7Axx Series"),
            0x61: Info("AT91SAM7AQxx", "AT91SAM7AQxx Series"),
            0x63: Info("AT91x63", "AT91x63 Series"),
            0x70: Info("AT91SAM7Sxx", "AT91SAM7Sxx Series"),
            0x71: Info("AT91SAM7XCxx", "AT91SAM7XCxx Series"),
            0x72: Info("AT91SAM7SExx", "AT91SAM7SExx Series"),
            0x73: Info("AT91SAM7Lxx", "AT91SAM7Lxx Series"),
            0x75: Info("AT91SAM7Xxx", "AT91SAM7Xxx Series"),
            0x76: Info("AT91SAM7SLxx", "AT91SAM7SLxx Series"),
            0x80: Info("SAM3UxC", "SAM3UxC Series (100-pin version)"),
            0x81: Info("SAM3UxE", "SAM3UxE Series (144-pin version)"),
            0x83: Info("SAM3AxC/SAM4AxC", "SAM3AxC/SAM4AxC Series (100-pin version)"),
            0x84: Info("SAM3XxC/SAM4XxC", "SAM3XxC/SAM4XxC Series (100-pin version)"),
            0x85: Info("SAM3XxE/SAM4XxE", "SAM3XxE/SAM4XxE Series (144-pin version)"),
            0x86: Info("SAM3XxG/SAM4XxG", "SAM3XxG/SAM4XxG Series (208/217-pin version)"),
            0x88: Info("SAM3SxA/SAM4SxA", "SAM3SxA/SAM4SxA Series (48-pin version)"),
            0x89: Info("SAM3SxB/SAM4SxB", "SAM3SxB/SAM4SxB Series (64-pin version)"),
            0x8A: Info("SAM3SxC/SAM4SxC", "SAM3SxC/SAM4SxC Series (100-pin version)"),
            0x92: Info("AT91x92", "AT91x92 Series"),
            0x93: Info("SAM3NxA", "SAM3NxA Series (48-pin version)"),
            0x94: Info("SAM3NxB", "SAM3NxB Series (64-pin version)"),
            0x95: Info("SAM3NxC", "SAM3NxC Series (100-pin version)"),
            0x99: Info("SAM3SDxB", "SAM3SDxB Series (64-pin version)"),
            0x9A: Info("SAM3SDxC", "SAM3SDxC Series (100-pin version)"),
            0xA5: Info("SAM5A", "SAM5A"),
            0xB0: Info("SAM4L", "SAM4Lxx Series"),
            0xF0: Info("AT75Cxx", "AT75Cxx Series"),
        }

        SRamSizes = {
            0:  Info("48K", "48K bytes"),
            1:  Info("1K", "1K bytes"),
            2:  Info("2K", "2K bytes"),
            3:  Info("6K", "6K bytes"),
            4:  Info("24K", "24K bytes"),
            5:  Info("4K", "4K bytes"),
            6:  Info("80K", "80K bytes"),
            7:  Info("160K", "160K bytes"),
            8:  Info("8K", "8K bytes"),
            9:  Info("16K", "16K bytes"),
            10: Info("32K", "32K bytes"),
            11: Info("64K", "64K bytes"),
            12: Info("128K", "128K bytes"),
            13: Info("256K", "256K bytes"),
            14: Info("96K", "96K bytes"),
            15: Info("512K", "512K bytes"),
        }

        NvpSiz2s = {
            0:  Info("None", "None"),
            1:  Info("8K", "8K bytes"),
            2:  Info("16K", "16K bytes"),
            3:  Info("32K", "32K bytes"),
            4:  Info("Reserved", "Reserved"),
            5:  Info("64K", "64K bytes"),
            6:  Info("Reserved", "Reserved"),
            7:  Info("128K", "128K bytes"),
            8:  Info("Reserved", "Reserved"),
            9:  Info("256K", "56K bytes"),
            10: Info("512K", "512K bytes"),
            11: Info("Reserved", "Reserved"),
            12: Info("1024K", "1024K bytes"),
            13: Info("Reserved", "Reserved"),
            14: Info("2048K", "2048K bytes"),
            15: Info("Reserved", "Reserved"),
        }

        EProcs = {
            1: Info("ARM946ES", "ARM946ES"),
            2: Info("ARM7TDMI", "ARM7TDMI"),
            3: Info("CM3", "Cortex-M3"),
            4: Info("ARM920T", "ARM920T"),
            5: Info("ARM926EJS", "ARM926EJS"),
            6: Info("CA5", "Cortex-A5"),
            7: Info("CM4", "Cortex-M4"),
        }

        NvpSizes = {
            0:  Info("NONE", "None"),
            1:  Info("8K", "8K bytes"),
            2:  Info("16K", "16K bytes"),
            3:  Info("32K", "32K bytes"),
            4:  Info("Reserved", "Reserved"),
            5:  Info("64K", "64K bytes"),
            6:  Info("Reserved", "Reserved"),
            7:  Info("128K", "128K bytes"),
            8:  Info("Reserved", "Reserved"),
            9:  Info("256K", "256K bytes"),
            10: Info("512K", "512K bytes"),
            11: Info("Reserved", "Reserved"),
            12: Info("1024K", "1024K bytes"),
            13: Info("Reserved", "Reserved"),
            14: Info("2048K", "2048K bytes"),
            15: Info("Reserved", "Reserved"),
        }

        Packages =  {
            0: "24-pin",
            1: "32-pin",
            2: "48-pin",
            3: "64-pin",
            4: "100-pi",
            5: "144-pin",
        }

        friendlyName = FriendlyNames.get(chipId, "*** Unknown ***")
        ext = (chipId & EXT) == EXT
        nvptyp = (chipId & NVPTYP) >> 28
        arch = (chipId & ARCH) >> 20
        sramsiz = (chipId & SRAMSIZ) >> 16
        nvpsiz2 = (chipId & NVPSIZ2) >> 12
        nvpsiz = (chipId & NVPSIZ) >> 8
        eproc = (chipId & EPROC) >> 5
        version = (chipId & VERSION)

        if ext:
            exid = self.exId()
            package = (exid & PACKAGE) >> 24
            lcd     = (exid & LCD) == LCD
            usbfull = (exid & USBFULL) == USBFULL
            usb     = (exid & USB) == USB
            aes     = (exid & AES) == AES
        else:
            package = "*** Unknown ***"
            lcd = False
            usb = False
            usbfull = False
            aes = False


        return DeviceCapabilities(friendlyName, NvpTypes.get(nvptyp, "*** Unknown ***"), Archs.get(arch, "*** Unknown ***"),
            SRamSizes.get(sramsiz, "*** Unknown ***"), NvpSizes.get(nvpsiz, "*** Unknown ***"), NvpSiz2s.get(nvpsiz2, "*** Unknown ***"),
            EProcs.get(eproc, "*** Unknown ***"), version, ext, Packages.get(package, "*** Reserved ***"), lcd, usb, usbfull, aes
        )

