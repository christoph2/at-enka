
rt = serial.Serial(port = 'COM19', baudrate = 115200 * 4, bytesize = 8, timeout = 0.0125, writeTimeout = 1.0)
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

    bulk = cmd.read(0x20000000, 64 * 1024)
    print "Länge", len(bulk)
    print bulk
    port.close()


if __name__ == '__main__':
    test()

