#!/usr/bin/env python
# -*- coding: utf-8 -*-


__version__ = "0.1.0"
__description__ = "AT-ENKA (Toolset for Atmel AT-SAM4 Controllers)"
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

"""
Access to first flash region of SAM4Lx8
Every SAM4L devices are shipped with flash region 0 locked, on SAM4Lx8 (512kB) devices, this region also includes the start of the applicative area (0x4000 – 0x8000).
When a write or erase of this particular area is requested, SAM-BA application will temporarily unlock the region 0, access the area and finally relock the region.

Enable Security Bit         Set the security bit to secure the device (refer to the device datasheet in the FLASHCALW chapter for more information)
Read Security Bit           Give the current security state
Erase application area      Erase all application code (SAM-BA part won’t be erased)
Invalidate application      Erase first page of application
Read Fuses                  Returns the values of the flash fuses
Read Locks                  Returns the current lock bits value
Read Unique Serial Number   Returns the unique serial number of the Atmel ATSAM4L device (refer to the device datasheet in the FLASHCALW chapter for more information)
Set Lock Bit [0..15]        Set the specified lock bit to prevent any erasure of a flash memory region. (refer to the device datasheet in the FLASHCALW chapter for more information)
Unlock All                  Unlock every flash memory sections
"""

from collections import namedtuple, OrderedDict

import logging
from optparse import OptionParser, OptionGroup
import os
import sys
import threading
import serial.serialutil as serialutil
from atenka.port import Port
from atenka.samba import Samba

SRAM            = 0x20000000

APPLET_ADDR     = 0x20002000
APPLET_MAILBOX_ADDR = 0x20002040


GPIO            = 0x400E1000
FLASHCALW       = 0x400A0000

logger = logging.getLogger("atenka")
logger.setLevel(logging.WARN)

COMMANDS = {    # a.k.a builtin plugins.
    'info': None,
    'dump': None,


    'del-plugin': None,
    'ls-plugins': None,
}

ACC_RW  = 0 # Read/Write access.
ACC_RO  = 1 # Read-only access.
ACC_WO  = 2 # Write-only access.

Register = namedtuple('Register', 'offset description decoder')
GPIORegister = namedtuple('Register', 'offset description decoder access extInterface')


"""
Use-cases:
---
Testing stuff
Cost-effective automated testing.
Low-cost automated testing.
Remote-control of your board.
Curiosity
Fun-stuff.
"""

class InterfaceNotSupportedError(Exception): pass
class RegisterNotDefinedError(Exception): pass
class ModuleInstanceNotAvailable(Exception): pass


class SingletonBase(object):
    _lock = threading.Lock()

    def __new__(cls, *args, **kws):
        # Double-Checked Locking
        if not hasattr(cls, '_instance'):
            try:
                cls._lock.acquire()
                if not hasattr(cls, '_instance'):
                    cls._instance = super(SingletonBase, cls).__new__(cls)
            finally:
                cls._lock.release()
        return cls._instance


class Module(SingletonBase):
    NAME = None
    EXTRAS = []

    def __init__(self, samba):
        self.samba = samba


class ModGPIO(Module):

    NAME                = "GPIO"
    BASE_ADDRESS        = 0x400E1000

    PA                  = 0
    PB                  = 1
    PC                  = 2

    REGISTER_BLOCK_SIZE = 0x0200

    SET_OFFSET          = 0x04
    CLEAR_OFFSET        = 0x08
    TOGGLE_OFFSET       = 0xc

    REGISTERS = {
        "GPER":       GPIORegister(0x000, "GPIO Enable Register",                   None, ACC_RW, True),
        "PMR0":       GPIORegister(0x010, "Peripheral Mux Register 0",              None, ACC_RW, True),
        "PMR1":       GPIORegister(0x020, "Peripheral Mux Register 1",              None, ACC_RW, True),
        "PMR2":       GPIORegister(0x030, "Peripheral Mux Register 2",              None, ACC_RW, True),
        "ODER":       GPIORegister(0x040, "Output Driver Enable Register",          None, ACC_RW, True),
        "OVR":        GPIORegister(0x050, "Output Value Register",                  None, ACC_RW, True),
        "PVR":        GPIORegister(0x060, "Pin Value Register",                     None, ACC_RO, False),
        "PUER":       GPIORegister(0x070, "Pull-up Enable Register",                None, ACC_RW, True),
        "PDER":       GPIORegister(0x080, "Pull-down Enable Register",              None, ACC_RW, True),
        "IER":        GPIORegister(0x090, "Interrupt Enable Register",              None, ACC_RW, True),
        "IMR0":       GPIORegister(0x0A0, "Interrupt Mode Register 0",              None, ACC_RW, True),
        "IMR1":       GPIORegister(0x0B0, "Interrupt Mode Register 1",              None, ACC_RW, True),
        "GFER":       GPIORegister(0x0C0, "Glitch Filter Enable Register",          None, ACC_RW, True),
        "IFR":        GPIORegister(0x0D0, "Interrupt Flag Register",                None, ACC_RO, True),
        "ODCR0":      GPIORegister(0x100, "Output Driving Capability Register 0",   None, ACC_RW, True),
        "ODCR1":      GPIORegister(0x110, "Output Driving Capability Register 1",   None, ACC_RW, True),
        "OSRR0":      GPIORegister(0x130, "Output Slew Rate Register 0",            None, ACC_RW, True),
        "OSRR0T":     GPIORegister(0x13C, "Output Slew Rate Register 0",            None, ACC_WO, True),
        "STER":       GPIORegister(0x160, "Schmitt Trigger Enable Register",        None, ACC_RW, True),
        "EVER":       GPIORegister(0x180, "Event Enable Register",                  None, ACC_RW, True),
        "PARAMETER":  GPIORegister(0x1F8, "Parameter Register",                     None, ACC_RO, False),
        "VERSION":    GPIORegister(0x1FC, "Version Register",                       None, ACC_RO, False),
    }

    #def __init__(self):
    #    pass

    def _baseAddress(self, instance):
        return ModGPIO.BASE_ADDRESS + (instance * ModGPIO.REGISTER_BLOCK_SIZE)

    def _namecheck(self, reg):
        if reg not in ModGPIO.REGISTERS:
            raise RegisterNotDefinedError("Register '%s' does not exist." % reg)

    def _extInterfaceCheck(self, reg):
        if not ModGPIO.REGISTERS[reg].extInterface:
            raise InterfaceNotSupportedError("Interface not supported by '%s'." % reg)

    def read(self, inst, reg):
        self._namecheck(reg)
        baseAddr = self._baseAddress(inst) + ModGPIO.REGISTERS[reg].offset
        return self.samba.readLong(baseAddr)

    def write(self, inst, reg, value):
        self._namecheck(reg)
        baseAddr = self._baseAddress(inst)

    def set(self, inst, reg, mask):
        self._namecheck(reg)
        self._extInterfaceCheck(reg)
        baseAddr = self._baseAddress(inst)

    def clear(self, inst, reg, mask):
        self._namecheck(reg)
        self._extInterfaceCheck(reg)
        baseAddr = self._baseAddress(inst)

    def toggle(self, inst, reg, mask):
        self._namecheck(reg)
        self._extInterfaceCheck(reg)
        baseAddr = self._baseAddress(inst)


class ModFlash(Module):
    NAME = "FLASHCALW"
    BASE_ADDRESS = 0x400A0000

    REGISTERS = {
        "FCR":      Register(0x00, "Flash Control Register", None),
        "FCMD":     Register(0x04, "Flash Command Register", None),
        "FSR":      Register(0x08, "Flash Status Register", None),
        "FPR":      Register(0x0C, "Flash Parameter Register", "flashParameters"),
        "FVR":      Register(0x10, "Flash Version Register", None),
        "FGPFRHI":  Register(0x14, "Flash General Purpose Fuse Register Hi", None),
        "FGPFRLO":  Register(0x18, "Flash General Purpose Fuse Register Lo", None),
        "CTRL":     Register(0x408, "PicoCache Control Register", None),
        "SR":       Register(0x40C, "PicoCache Status Register", None),
        "MAINT0":   Register(0x420, "PicoCache Maintenance Register 0", None),
        "MAINT1":   Register(0x424, "PicoCache Maintenance Register 1", None),
        "MCFG":     Register(0x428, "PicoCache Monitor Configuration Register", None),
        "MEN":      Register(0x42C, "PicoCache Monitor Enable Register", None),
        "MCTRL":    Register(0x430, "PicoCache Monitor Control Register", None),
        "MSR":      Register(0x434, "PicoCache Monitor Status Register", None),
        "PVR":      Register(0x4FC, "PicoCache Version Register", None),
    }

    def flashParameters(cls, value):
        PSZ = {
            0: "32 Byte",
            1: "64 Byte",
            2: "128 Byte",
            3: "256 Byte",
            4: "512 Byte",
            5: "1024 Byte",
            6: "2048 Byte",
            7: "4096 Byte",
        }
        FSZ = {
            0:  "4 Kbyte ",
            8:  "192 Kbyte",
            1:  "8 Kbyte",
            9:  "256 Kbyte",
            2:  "16 Kbyte",
            10: "384 Kbyte",
            3:  "32 Kbyte",
            11: "512 Kbyte",
            4:  "48 Kbyte",
            12: "768 Kbyte",
            5:  "64 Kbyte",
            13: "1024 Kbyte",
            6:  "96 Kbyte",
            14: "2048 Kbyte",
            7:  "128 Kbyte",
            15: "Reserved",
        }
        fsz = value & 0x000000ff
        psz = (value & 0x00000700) >> 8
        print "    Flash Size     :", FSZ.get(fsz, "Reserved")
        print "    Flash Page Size:", PSZ.get(psz, "*** UNKNOWN ***")
        print


def dumpModule(samba, mod):
    print "Module:", mod.NAME
    print
    print "=" * 60
    print "Addr     Name      Description"
    print "Val/Hex  Val/Bin"
    print "=" * 60
    for k, reg in sorted(mod.REGISTERS.items(), key = lambda x: x[1][0]):
        value = samba.readLong(mod.BASE_ADDRESS + reg.offset)
        print "{:08X} {:10s}{:s}".format(GPIO + reg.offset, k, reg.description)
        print "{:08X} {:032b}\n".format(value, value)
        if reg.decoder:
            getattr(mod, reg.decoder)(value)

def printHeader():
    print """\n  %s
  (C) 2015 by Christoph Schueler <https://github.com/christoph2,
                                       cpu12.gems@googlemail.com>
    """ % (__description__)

def main():
    usage = "usage: %prog [options] command"

    #printHeader()
    op = OptionParser(usage = usage, version = "%prog " +__version__)

    op.add_option("-p", "--port", action = "store", type = "string", dest = "comport",
        help = "Com-Port #. This depends on your operating system, e.g.: 1 ==> "
        "COM2 on Microsoft-Systems.", default = 0)
#    op.add_option("-s", "--speed", action = "store", type = "choice", dest = "speed",
#        choices = ('lo', 'med', 'hi'), default = "med", help = "Communication Speed. "
#        "Select one of the folowing: ['lo' | 'med' | 'hi'] (19200, 57600, 115200).")
    '''
    input_group = OptionGroup(op, 'Input')
    input_group.add_option('-I', '--include-path', dest = 'inc_path', action = 'append',
        metavar = 'dir',
        help = """Add directory to the list of directories to be searched for include files.
        Environment-Variable 'KOS_INCLUDE' is also used to locate Include-Files."""

    )
    op.add_option_group(input_group)

    group = OptionGroup(op, 'Output')
    group.add_option('-o', '--orti', help = 'generate orti-FILE', dest = 'orti', action = 'store_true', default = False)
    group.add_option('-r', '--resource-usage', help = 'generate resource statistics', dest = 'res_usage',
            action = 'store_true', default = False)
    group.add_option('-t', '--test', help = "verify only, don't generate anything", dest = 'test',
        action = 'store_true', default = False)
    group.add_option('-V', '--verbose', help = 'print Information messages', dest = 'verbose',
        action = 'store_true', default = False)
    group.add_option('-S', '--silent', help = "don't print any messages.", dest = 'silent', action = 'store_true',
        default = False
    '''
    (options, args) = op.parse_args()
    if len(args) != 1:
        op.print_help()
        exit(1)
    command = args[0].lower()

    if command not in COMMANDS:
        print
        print "'%s' not recognized.\nValid commands are: %s" % (command, sorted(COMMANDS.keys()))
        sys.exit(1)

    try:
        port = Port(options.comport)
    except serialutil.SerialException:
        sys.exit(1)
    except Exception as e:
        #logger.error("%s", e)
        print str(e)
        sys.exit(1)

    smb = Samba(port)
    print "ChipID       : 0x%08x" % smb.chipId()
    cinfo = smb.chipInfo()


    data = smb.receiveFile(APPLET_ADDR, 255)
    print data
    #smb.sendFile(APPLET_ADDR, [x for x in range(256)])
    smb.sendFile(APPLET_ADDR, data)
    data = smb.receiveFile(APPLET_ADDR, 255)
    print data


    """

        LocalBaud.BaudRate = lpDCB->BaudRate;
        Status = NtDeviceIoControlFile(
                     hFile,
                     SyncEvent,
                     NULL,
                     NULL,
                     &Iosb,
                     IOCTL_SERIAL_SET_BAUD_RATE,
                     &LocalBaud,
                     sizeof(LocalBaud),
                     NULL,
                     0
                     )
    """

##>>> import feedparser as fp
##>>> res=fp.parse("https://www.mikrocontroller.net/wikisoftware/api.php?hidebots=1&days=7&limit=50&action=feedrecentchanges&feedformat=atom")

    print "Requested command: ", command
    print cinfo

    data = smb.receiveFile(0x400E0740, 4)
    print [hex(x) for x in data]

    #sr = smb.readLong(SRAM + 0x6000)
    #print hex(sr)
    #smb.writeLong(SRAM + 0x6000, 0xdeadaffe)
    #sr = smb.readLong(SRAM + 0x6000)
    #print hex(sr)

    """
    sr = smb.readLong(GPIO + 0x040)
    print bin(sr)
    smb.writeLong(GPIO + 0x040, 0xffff)   # Changes from 0b00 ==> 0b10110
    smb.writeLong(GPIO + 0x050, 0x0000)   # Changes from 0b00 ==> 0b10110
    sr = smb.readLong(GPIO + 0x040)
    print bin(sr)
    sr = smb.readLong(GPIO + 0x060)
    print bin(sr)
    """

    gpio = ModGPIO(smb)
    flash = ModFlash(smb)
    dumpModule(smb, gpio)
    dumpModule(smb, flash)
    #print "GPRE?", hex(gpio.read(ModGPIO.PA, "GPER"))

    """
    Ich war natürlich auch erst einmal skeptisch, an der richtigen Addresse zu sein, aber
    bei wiederholten Aufrufen ändert sich z.B. stets PA00 (also XTAL), auch sonst sehen die
    Werte plausibel aus.
    """

    """Aber es ist ja nicht so als könnte man bei SAM-BA nicht ein paar Teile abmontieren :-)
    Flash-Loader.
    """

    """
                    NCN          SAM4
    UART_NCN_RX     28[TxD/out]  PA16[Tx/out]
    UART_NCN_TX     27[RxD/in]   PA15[Rx/in]
    """

    """




    """

    """
    try:
        prim = Primitives(port)
        print "ID\t:", prim.requestID()
        print "Version\t:", prim.requestVersion()
        print "Date\t:", prim.requestDate()

        speed = defs.SPEED_TAB[options.speed]

        if port.baudrate != speed[0]:
            print "\nSwitching baudrate to %d Bits/Sec." % (speed[0], )
            prim.SwitchBaudrate(speed)
            print "\tOK."

        print "\nErasing VMC."  # TODO: WEG HIER!!!
        prim.eraseVMC()
        print "\tOK."

        print "\nStart loading."    # dito.
        prim.startLoad(data.numberOfConstantBytes, data.numberOfCodeWords)
        print "\tOK."

        Loader(prim, data)()
        print "\n\tOK."
        #prim.LoadVMC(data)

        print "\nReseting Target.\n"
        prim.targetReset()
    except TimeoutError as e:
        print "\n\n", str(e)
    except Exception as e:
        raise
    finally:
        port.close()
    """


if __name__ == "__main__":
    main()

