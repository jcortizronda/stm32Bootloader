#!/usr/bin/env python
# import pdb; pdb.set_trace()

import struct
import os
import sys
import glob
import tftpy
import socket
import time

os.system("mode con cols=70 lines=36")

#STM32 Flash Errors
Flash_HAL_OK                                        = 0x00
Flash_HAL_ERROR                                     = 0x01
Flash_HAL_BUSY                                      = 0x02
Flash_HAL_TIMEOUT                                   = 0x03
Flash_HAL_INV_ADDR                                  = 0x04

#BL Commands
COMMAND_BL_GET_VER                                  = 0x51
COMMAND_BL_GET_CID                                  = 0x52
COMMAND_BL_GET_RDP_STATUS                           = 0x53
COMMAND_BL_SET_RDP_STATUS                           = 0x59
COMMAND_BL_READ_ADDR_VALUE                          = 0x58
COMMAND_BL_GO_TO_ADDR                               = 0x54
COMMAND_BL_FLASH_ERASE                              = 0x55
COMMAND_BL_READ_SECTOR_P_STATUS                     = 0x56
COMMAND_BL_EN_RW_PROTECT                            = 0x57
COMMAND_BL_DIS_RW_PROTECT                           = 0x5C
COMMAND_BL_WRITE_OTP_AREA                           = 0x5B
COMMAND_BL_READ_OTP_AREA_STATUS	                    = 0x5D

#Length details of the command
COMMAND_BL_GET_VER_LEN                              = 6
COMMAND_BL_GET_CID_LEN                              = 6
COMMAND_BL_GET_RDP_STATUS_LEN                       = 6
COMMAND_BL_SET_RDP_STATUS_LEN                       = 7
COMMAND_BL_GO_TO_ADDR_LEN                           = 10
COMMAND_BL_FLASH_ERASE_LEN                          = 8
COMMAND_BL_READ_SECTOR_P_STATUS_LEN                 = 6
COMMAND_BL_EN_RW_PROTECT_LEN                        = 9
COMMAND_BL_DIS_RW_PROTECT_LEN                       = 9
COMMAND_BL_READ_ADDR_VALUE_LEN                      = 10
COMMAND_BL_WRITE_OTP_AREA_LEN                       = 14
COMMAND_BL_READ_OTP_AREA_STATUS_LEN                 = 6

#MICROCONTROLLERS DEFINE
STM32_TOTAL_SECTOR  = 11
OTP_BASE_ADDRESS = 0x1FFF7800

#ACK/NACK
ACK  = 0xA5
NACK = 0x7F

#Address Validation
ADDR_VALID   = 0x00
ADDR_INVALID = 0x01

ipAddress = 0
port = 0

#----------------------------- File Functions ----------------------------------------

def openFile(mode):
    global otp_file
    otp_file = open('otpArea.txt',mode)

def readFile():
    return otp_file.readlines()

def closeFile():
    otp_file.close()
    
def writeToFile(data):
    otp_file.write(data)


#----------------------------- Utilities ----------------------------------------

def wordToByte(addr, index , lowerfirst):
    value = (addr >> ( 8 * ( index -1)) & 0x000000FF )
    return value

def getCRC(buff, length):
    Crc = 0xFFFFFFFF
    for data in buff[0:length]:
        Crc = Crc ^ data
        for i in range(32):
            if(Crc & 0x80000000):
                Crc = (Crc << 1) ^ 0x04C11DB7
            else:
                Crc = (Crc << 1)
    return Crc


def progressBar(data):
    
    if (fileSize == 0):
        actualFileSize = 0
        percentage = 100
    else:
        actualFileSize = data.blocknumber*512/1024
        percentage = data.blocknumber*512/fileSize*100
    if (actualFileSize > (fileSize/1024)):
        actualFileSize = fileSize/1024
        percentage = 100
    print("   Flashing: ", "{:.2f}".format(percentage), "%   ", "{:.1f}".format(actualFileSize), "kB /", "{:.1f}".format(fileSize/1024), "kB", end='\r')
    return  
#----------------------------- Command Processing----------------------------------------

def process_COMMAND_BL_GET_VER( length, data ):
    print( "\n   Bootloader Version : ", data / 10 )

def process_COMMAND_BL_GET_CID( length, data ):
    ci  = ( data[2] << 8 ) + data[3]
    rev = ( data[4] << 8 ) + data[5]
    print( "\n   Chip Id.  : ", hex( ci ) )
    print( "\n   Chip Rev. : ", hex( rev) )

def process_COMMAND_BL_GET_RDP_STATUS( length, data ):
    if ( data == 0xAA):
        print("\n   RDP Status : Level 0")
    elif ( data == 0x55):    
        print("\n   RDP Status : Level 1")
    elif ( data == 0xCC):    
        print("\n   RDP Status : Level 2")         
    else:
        print("\n   Error")    

def process_COMMAND_BL_SET_RDP_STATUS( length, data ):
    if ( data == 0 ):
        print("\n   Success")
    else:
        print("\n   Error. Try again")

def process_COMMAND_BL_GO_TO_ADDR( length, data ):
    if ( data == 0 ):
        print( "\n   Valid Address. Successful! " )
    else:
        print( "\n   Invalid Address! " )

def process_COMMAND_BL_FLASH_ERASE( length, data ):
    eraseStatus = data
    if(eraseStatus == Flash_HAL_OK):
        print("\n   Erase Status: Success  Code: FLASH_HAL_OK")
    elif(eraseStatus == Flash_HAL_ERROR):
        print("\n   Erase Status: Fail  Code: FLASH_HAL_ERROR")
    elif(eraseStatus == Flash_HAL_BUSY):
        print("\n   Erase Status: Fail  Code: FLASH_HAL_BUSY")
    elif(eraseStatus == Flash_HAL_TIMEOUT):
        print("\n   Erase Status: Fail  Code: FLASH_HAL_TIMEOUT")
    elif(eraseStatus == Flash_HAL_INV_ADDR):
        print("\n   Erase Status: Fail  Code: FLASH_HAL_INV_SECTOR")
    else:
        print("\n   Erase Status: Fail  Code: UNKNOWN_ERROR_CODE")
  
protection_mode= [ "Write Protection", "Read/Write Protection","No protection" ]
def protection_type(status,n):
    if( status & (1 << 15) ):
        #PCROP is active
        if(status & (1 << n) ):
            return protection_mode[1]
        else:
            return protection_mode[2]
    else:
        if(status & (1 << n)):
            return protection_mode[2]
        else:
            return protection_mode[0]
                               
def process_COMMAND_BL_READ_SECTOR_STATUS( length, data ):
    sectorStatus = ( ( data[2] & 0xF ) << 8 | data[3] )
    
    print( "\n   Sector Status : ", bin( sectorStatus ) )


    if( data[2] & ( 1 << 7 ) ):
        #PCROP is active
        print( "\n   Mode : Read/Write Protection(PCROP)\n" )
    else:
        print( "\n   Mode : Write Protection\n" )
        
    print( "   ====================================" )
    print( "   Sector     \tProtection" ) 
    print( "   ====================================" )
    for x in range( 12 ):
        print( "   Sector{0} => {1}".format( x, protection_type( sectorStatus, x ) ) )

def process_COMMAND_BL_READ_ADDR_VALUE( length, data ):
    if ( data[2] == 0):
        value = ( data[3] << 24 | data[4] << 16 | data[5] << 8 | data[6] )   
        print( "\n   Value : ", hex( value ) )
    else:
        print( "\n   Invalid address" )

def process_COMMAND_BL_WRITE_OTP_AREA( length, data ):
    if ( data[2] == ADDR_VALID):
        if(data[3] == Flash_HAL_OK):
            print("\n   Valid address and flash succeed")
        elif(data[3] == Flash_HAL_ERROR):
            print("\n   Valid address, but flash failed with code FLASH_HAL_ERROR")
        elif(data[3] == Flash_HAL_BUSY):
            print("\n   Valid address, but flash failed with code FLASH_HAL_BUSY")
        elif(data[3] == Flash_HAL_TIMEOUT):
            print("\n   Valid address, but flash failed with code FLASH_HAL_TIMEOUT")
        elif(data[3] == Flash_HAL_INV_ADDR):
            print("\n   Valid address, but flash failed with code FLASH_HAL_INV_SECTOR")
        else:
            print("\n   Valid address, but flash failed with code UNKNOWN_ERROR_CODE")
    else:
        print( "\n   Invalid address" )

otp_lock = [ "Locked", "Unlocked", "Lock" ]
def lock_otp(status,n):
    if(status & (1 << n) ):
        return otp_lock[0]
    else:
        return otp_lock[1]
            
def process_COMMAND_BL_READ_OTP_AREA_STATUS( length, data ):
    otpStatus = ( ( data[2] & 0xF ) << 8 | data[3] )

    print( "\n   OTP Blocks Status : ", bin( otpStatus ) )
     
    print( "   ====================================" )
    print( "   OTP Block     Status" ) 
    print( "   ====================================" )
    for x in range( 16 ):
        print( "   Block {0}  =>  {1}".format( x, lock_otp( otpStatus, x ) ) )  
               
def process_COMMAND_BL_DIS_RW_PROTECT( length, status ):
    if( status ):
        print( "\n   FAIL" )
    else:
        print( "\n   SUCCESS" )

def process_COMMAND_BL_EN_RW_PROTECT( length, status ):
    if( status ):
        print( "\n   Not supported option" )
    else:
        print( "\n   SUCCESS" )

def decodeMenuCommandCode(command):
    retValue = 0
    dataBuf = []
    
    if( command  == 0 ):
        print("\n   Exiting...!")
        raise SystemExit
                
    elif( command == 1 ):
        print( "\n   Command == > BL_GET_VER" )

        dataBuf.append( COMMAND_BL_GET_VER_LEN - 1 ) 
        dataBuf.append( COMMAND_BL_GET_VER )
        
        crc32 = getCRC( dataBuf, COMMAND_BL_GET_VER_LEN - 4 )
        crc32 = crc32 & 0xffffffff
        
        dataBuf.append( wordToByte (crc32 ,1 ,1) )
        dataBuf.append( wordToByte (crc32 ,2 ,1) )
        dataBuf.append( wordToByte (crc32 ,3 ,1) )
        dataBuf.append( wordToByte (crc32 ,4 ,1) )
        
        sock.settimeout(1)
        sock.sendto( bytes( dataBuf ), ( ipAddress, port ) )

        try:
            receivedData, addr = sock.recvfrom(64)
        
        except socket.timeout:
            print( "\n   No response. Please, try again\n" )
            print( "   ------------------------------------------")
            return
            
        retValue = readBootloaderReply( bytearray( receivedData ) )
                   
    elif( command == 2 ):
        print( "\n   Command == > BL_GET_CID" )

        dataBuf.append( COMMAND_BL_GET_CID_LEN - 1 ) 
        dataBuf.append( COMMAND_BL_GET_CID )
        
        crc32 = getCRC( dataBuf, COMMAND_BL_GET_CID_LEN - 4 )
        crc32 = crc32 & 0xffffffff
        
        dataBuf.append( wordToByte (crc32 ,1 ,1) )
        dataBuf.append( wordToByte (crc32 ,2 ,1) )
        dataBuf.append( wordToByte (crc32 ,3 ,1) )
        dataBuf.append( wordToByte (crc32 ,4 ,1) )
        
        sock.settimeout(1)
        sock.sendto( bytes( dataBuf ), ( ipAddress, port ) )

        try:
            receivedData, addr = sock.recvfrom(64)
        
        except socket.timeout:
            print( "\n   No response. Please, try again\n" )
            print( "   ------------------------------------------")            
            return
        retValue = readBootloaderReply( bytearray( receivedData ) )

    elif( command == 3 ):
        print("\n   Command == > BL_GET_RDP_STATUS")

        dataBuf.append( COMMAND_BL_GET_RDP_STATUS_LEN - 1 ) 
        dataBuf.append( COMMAND_BL_GET_RDP_STATUS )
        
        crc32 = getCRC( dataBuf, COMMAND_BL_GET_RDP_STATUS_LEN - 4 )
        crc32 = crc32 & 0xffffffff
        
        dataBuf.append( wordToByte (crc32 ,1 ,1) )
        dataBuf.append( wordToByte (crc32 ,2 ,1) )
        dataBuf.append( wordToByte (crc32 ,3 ,1) )
        dataBuf.append( wordToByte (crc32 ,4 ,1) )
        
        sock.settimeout(1)
        sock.sendto( bytes( dataBuf ), ( ipAddress, port ) )

        try:
            receivedData, addr = sock.recvfrom(64)
        
        except socket.timeout:
            print( "\n   No response. Please, try again\n" )
            print( "   ------------------------------------------")
            return

        retValue = readBootloaderReply( bytearray( receivedData ) )        

    elif( command == 4 ):
        print("\n   Command == > BL_SECTOR_P_STATUS")

        dataBuf.append( COMMAND_BL_READ_SECTOR_P_STATUS_LEN - 1 ) 
        dataBuf.append( COMMAND_BL_READ_SECTOR_P_STATUS )
        
        crc32 = getCRC( dataBuf, COMMAND_BL_READ_SECTOR_P_STATUS_LEN - 4 )
        crc32 = crc32 & 0xffffffff
        
        dataBuf.append( wordToByte (crc32 ,1 ,1) )
        dataBuf.append( wordToByte (crc32 ,2 ,1) )
        dataBuf.append( wordToByte (crc32 ,3 ,1) )
        dataBuf.append( wordToByte (crc32 ,4 ,1) )
        
        sock.settimeout(1)
        sock.sendto( bytes( dataBuf ), ( ipAddress, port ) )

        try:
            receivedData, addr = sock.recvfrom(64)
        
        except socket.timeout:
            print( "\n   No response. Please, try again\n" )
            print( "   ------------------------------------------") 
            return
        
        retValue = readBootloaderReply( bytearray( receivedData ) )   

    elif( command == 5 ):
        print("\n   Command == > BL_READ_ADDR_VALUE")

        validOption = 0
        dataRxAck = 0
        
        dataBuf.append( COMMAND_BL_READ_ADDR_VALUE_LEN - 1 ) 
        dataBuf.append( COMMAND_BL_READ_ADDR_VALUE )
        
        while ( dataRxAck == 0):
            print( "\n   ###########################################" )
            print( "   #                                         #" )
            print( "   #  Name:           InitAddress     Size   #" )
            print( "   #                                         #" )
            print( "   #  Bootloader      0x08000000      64KB   #" )
            print( "   #  Application     0x08010000      960KB  #" )
            print( "   #  OTP Area        0x1FFF7800      528B   #" )
            print( "   #  Option Bytes    0x1FFFC000      16B    #" )
            print( "   #                                         #" )
            print( "   ###########################################" )
            
            while (validOption == 0):
                addressInput = input( "\n   Enter address to read (Word Hex) [0 to quit]: " )        
                
                if (addressInput == '0'):
                    return
                    
                try:
                    addressInput = int(addressInput, 16)
                    validOption = 1
                except ValueError:
                    print("\n   Invalid hex number. Please, try again.")
            
            dataBuf.append( wordToByte (addressInput ,1 ,1) )
            dataBuf.append( wordToByte (addressInput ,2 ,1) )
            dataBuf.append( wordToByte (addressInput ,3 ,1) )
            dataBuf.append( wordToByte (addressInput ,4 ,1) )
            
            crc32 = getCRC( dataBuf, COMMAND_BL_READ_ADDR_VALUE_LEN - 4 )
            crc32 = crc32 & 0xffffffff
            
            dataBuf.append( wordToByte (crc32 ,1 ,1) )
            dataBuf.append( wordToByte (crc32 ,2 ,1) )
            dataBuf.append( wordToByte (crc32 ,3 ,1) )
            dataBuf.append( wordToByte (crc32 ,4 ,1) )
            
            sock.settimeout(1)
            sock.sendto( bytes( dataBuf ), ( ipAddress, port ) )
            
            try:
                receivedData, addr = sock.recvfrom(64)               
                dataRxAck = 1
            
            except socket.timeout:
                validOption = 0
                print( "\n   No response. Please, try again.\n" )        
                print( "   ------------------------------------------")       
        retValue = readBootloaderReply( bytearray( receivedData ) )   

    elif( command == 6 ):
        print( "\n   Command == > BL_READ_OTP_AREA_STATE" )

        dataBuf.append( COMMAND_BL_READ_OTP_AREA_STATUS_LEN - 1 ) 
        dataBuf.append( COMMAND_BL_READ_OTP_AREA_STATUS )
        
        crc32 = getCRC( dataBuf, COMMAND_BL_READ_OTP_AREA_STATUS_LEN - 4 )
        crc32 = crc32 & 0xffffffff
        
        dataBuf.append( wordToByte (crc32 ,1 ,1) )
        dataBuf.append( wordToByte (crc32 ,2 ,1) )
        dataBuf.append( wordToByte (crc32 ,3 ,1) )
        dataBuf.append( wordToByte (crc32 ,4 ,1) )
        
        sock.settimeout(1)
        sock.sendto( bytes( dataBuf ), ( ipAddress, port ) )

        try:
            receivedData, addr = sock.recvfrom(64)
        
        except socket.timeout:
            print( "\n   No response. Please, try again\n" )
            print( "   ------------------------------------------")
            return
            
        retValue = readBootloaderReply( bytearray( receivedData ) )

    elif( command == 7 ):
        print("\n   Command == > BL_EXPORT_OTP")
       
        dataBuf = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        
        # OTP Area status. What blocks are locked?
        dataBuf[0] = COMMAND_BL_READ_OTP_AREA_STATUS_LEN - 1 
        dataBuf[1] = COMMAND_BL_READ_OTP_AREA_STATUS
        
        crc32 = getCRC( dataBuf, COMMAND_BL_READ_OTP_AREA_STATUS_LEN - 4 )
        crc32 = crc32 & 0xffffffff
        
        dataBuf[2] = wordToByte (crc32 ,1 ,1)
        dataBuf[3] = wordToByte (crc32 ,2 ,1)
        dataBuf[4] = wordToByte (crc32 ,3 ,1)
        dataBuf[5] = wordToByte (crc32 ,4 ,1)
        
        sock.settimeout(1)
        sock.sendto( bytes( dataBuf ), ( ipAddress, port ) )

        try:
            receivedData, addr = sock.recvfrom(64)
        
        except socket.timeout:
            print( "\n   No response. Please, try again\n" )
            print( "   ------------------------------------------")
            return
            
        otpStatus = ( ( receivedData[2] & 0xF ) << 8 | receivedData[3] )
            
        # Address and value of each OTP section
        dataBuf[0] = COMMAND_BL_READ_ADDR_VALUE_LEN - 1
        dataBuf[1] = COMMAND_BL_READ_ADDR_VALUE
        
        openFile('w')
        writeToFile("Block  Locked  Address     Value\n")
        for x in range( 16 ):
            for y in range( 8 ):
                addressInput = OTP_BASE_ADDRESS + x*0x20 + y*0x04  
                
                dataBuf[2] = wordToByte (addressInput ,1 ,1)
                dataBuf[3] = wordToByte (addressInput ,2 ,1)
                dataBuf[4] = wordToByte (addressInput ,3 ,1)
                dataBuf[5] = wordToByte (addressInput ,4 ,1)
                
                crc32 = getCRC( dataBuf, COMMAND_BL_READ_ADDR_VALUE_LEN - 4 )
                crc32 = crc32 & 0xffffffff
                
                dataBuf[6] = wordToByte (crc32 ,1 ,1)
                dataBuf[7] = wordToByte (crc32 ,2 ,1)
                dataBuf[8] = wordToByte (crc32 ,3 ,1)
                dataBuf[9] = wordToByte (crc32 ,4 ,1)
                
                sock.settimeout(2)
                sock.sendto( bytes( dataBuf ), ( ipAddress, port ) )
                    
                try:
                    data, addr = sock.recvfrom(64)               
                    value = hex(data[3] << 24 | data[4] << 16 | data[5] << 8 | data[6])                       
                    writeToFile("  {0}      {1}     {2}  {3}\n".format(x, otpStatus >> x & 1, hex(addressInput), value))
                except socket.timeout:
                    print( "\n   No response. Please, try again.\n" )        
                    print( "   ------------------------------------------")
                    return
                              
        print( "\n   otpArea.txt file created" )
        closeFile()    

    elif( command == 8 ):
        print("\n   Command == > BL_DOWNLOAD_FLASH ")
        fileName =  input( '\n   Enter file name (with bin extension): ' )
        
        conError = 0
        connection = []
        
        while (conError == 0):
            connection.append(1)
            connection.append(ACK)
            sock.sendto( bytes( connection ), ( ipAddress, port ) ) 
            sock.settimeout( 1 )    
            
            try:
                data, addr = sock.recvfrom(64) # buffer size is 1024 bytes
                conError = 1
            
            except socket.timeout:
                print( "\n   No response. Please, try again\n" )
                print( "   ------------------------------------------")
                return
            
        try:
            tftpClient = tftpy.TftpClient(ipAddress, 69)
            print("\n   Downloading. Please wait...")
            tftpClient.download('firmwareSTM32.bin', fileName, timeout = 10)
        
            retValue = 0
        except tftpClient.timeout:
            print( "\n   No response. Please, try again\n" )
            print( "   ------------------------------------------")
            return

    elif( command == 9 ):
        global fileSize
        print("\n   Command == > BL_UPDATE_FLASH ")
        fileName =  input( '\n   Enter file name (with bin extension): ' )
        
        conError = 0
        connection = []
        
        while (conError == 0):
            connection.append(1)
            connection.append(ACK)
            sock.sendto( bytes( connection ), ( ipAddress, port ) ) 
            sock.settimeout( 1 )    
            
            try:
                data, addr = sock.recvfrom(64) # buffer size is 1024 bytes
                conError = 1
            
            except socket.timeout:
                print( "\n   No response. Please, try again\n" )
                print( "   ------------------------------------------")
                return
                          
        try:
            fileSize = os.stat(fileName).st_size
            tftpClient = tftpy.TftpClient(ipAddress, 69, options={'blksize': 512})
            print("\n   Updating. Please wait...")
            print("   Erasing flash...")
            tftpClient.upload('firmwareSTM32.bin', fileName, packethook = progressBar, timeout = 20)

            retValue = 0
        except:
            print( "\   nNo response. Please, try again\n\n" )
            print( "   ------------------------------------------")            

    elif( command == 10 ):
        print("\n   Command == > BL_WRITE_OTP_AREA")

        validOption = 0
        dataRxAck = 0
        
        dataBuf.append( COMMAND_BL_WRITE_OTP_AREA_LEN - 1 ) 
        dataBuf.append( COMMAND_BL_WRITE_OTP_AREA )
        
        while ( dataRxAck == 0):
            print( "\n   #############################################" )
            print( "   #                                          #" )
            print( "   #  Name:       InitAddress     EndAddress  #" )
            print( "   #  Block 0     0x1FFF7800      0x1FFF781F  #" )
            print( "   #  Block 1     0x1FFF7820      0x1FFF783F  #" )
            print( "   #  Block 2     0x1FFF7840      0x1FFF785F  #" )
            print( "   #  Block 3     0x1FFF7860      0x1FFF787F  #" )
            print( "   #  Block 4     0x1FFF7880      0x1FFF789F  #" )
            print( "   #  Block 5     0x1FFF78A0      0x1FFF78BF  #" )
            print( "   #  Block 6     0x1FFF78C0      0x1FFF78DF  #" )
            print( "   #  Block 7     0x1FFF78E0      0x1FFF78FF  #" )
            print( "   #  Block 8     0x1FFF7900      0x1FFF791F  #" )
            print( "   #  Block 9     0x1FFF7920      0x1FFF793F  #" )
            print( "   #  Block 10    0x1FFF7940      0x1FFF795F  #" )
            print( "   #  Block 11    0x1FFF7960      0x1FFF797F  #" )
            print( "   #  Block 12    0x1FFF7980      0x1FFF799F  #" )
            print( "   #  Block 13    0x1FFF79A0      0x1FFF79BF  #" )
            print( "   #  Block 14    0x1FFF79C0      0x1FFF79DF  #" )
            print( "   #  Block 15    0x1FFF79E0      0x1FFF79FF  #" )            
            print( "   #                                          #" )
            print( "   ############################################" )
            
            while (validOption == 0):
                addressInput = input( "\n   Enter address to write (Word Hex) [0 to quit]: " )        
                
                if (addressInput == '0'):
                    return
                    
                try:
                    addressInput = int(addressInput, 16)
                    validOption = 1
                except ValueError:
                    print("\n   Invalid hex number. Please, try again.")
                    
            validOption = 0
            while (validOption == 0):
                dataInput = input( "\n   Enter data to write (Word Hex - LSB Right] [0 to quit]: " )        
                
                if (dataInput == '0'):
                    return
                    
                try:
                    dataInput = int(dataInput, 16)
                    validOption = 1
                except ValueError:
                    print("\n   Invalid hex number. Please, try again.")
      
            dataBuf.append( wordToByte (addressInput ,1 ,1) )
            dataBuf.append( wordToByte (addressInput ,2 ,1) )
            dataBuf.append( wordToByte (addressInput ,3 ,1) )
            dataBuf.append( wordToByte (addressInput ,4 ,1) )
            
            dataBuf.append( wordToByte (dataInput ,1 ,1) )
            dataBuf.append( wordToByte (dataInput ,2 ,1) )
            dataBuf.append( wordToByte (dataInput ,3 ,1) )
            dataBuf.append( wordToByte (dataInput ,4 ,1) )
            
            crc32 = getCRC( dataBuf, COMMAND_BL_WRITE_OTP_AREA_LEN - 4 )
            crc32 = crc32 & 0xffffffff

            dataBuf.append( wordToByte (crc32 ,1 ,1) )
            dataBuf.append( wordToByte (crc32 ,2 ,1) )
            dataBuf.append( wordToByte (crc32 ,3 ,1) )
            dataBuf.append( wordToByte (crc32 ,4 ,1) )

            sock.settimeout(1)
            sock.sendto( bytes( dataBuf ), ( ipAddress, port ) )

            try:
                
                receivedData, addr = sock.recvfrom(64)               
                dataRxAck = 1
            
            except socket.timeout:
                validOption = 0
                print( "\n   No response. Please, try again.\n" )        
                print( "   ------------------------------------------")
        
        retValue = readBootloaderReply( bytearray( receivedData ) )   

    elif( command == 11 ):
        print("\n   Command == > BL_WRITE_OTP_FILE")
        
        dataBuf = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]      
        openFile('r')
        lines = readFile()
        
        for x in range( 1, len(lines) ):
            lock = lines[x].split()[1]
            address = lines[x].split()[2]
            value = lines[x].split()[3]
            
            if (int(lock) != 1):
                address = int(address, 16)
                value = int(value, 16)  
                
                dataBuf[0] = COMMAND_BL_READ_ADDR_VALUE_LEN - 1
                dataBuf[1] = COMMAND_BL_READ_ADDR_VALUE                       
                dataBuf[2] = wordToByte (address ,1 ,1)
                dataBuf[3] = wordToByte (address ,2 ,1)
                dataBuf[4] = wordToByte (address ,3 ,1)
                dataBuf[5] = wordToByte (address ,4 ,1)
                
                crc32 = getCRC( dataBuf, COMMAND_BL_READ_ADDR_VALUE_LEN - 4 )
                crc32 = crc32 & 0xffffffff
                
                dataBuf[6] = wordToByte (crc32 ,1 ,1)
                dataBuf[7] = wordToByte (crc32 ,2 ,1)
                dataBuf[8] = wordToByte (crc32 ,3 ,1)
                dataBuf[9] = wordToByte (crc32 ,4 ,1)
                
                sock.settimeout(1)
                sock.sendto( bytes( dataBuf ), ( ipAddress, port ) )
                
                try:
                    receivedData, addr = sock.recvfrom(64)               
                
                except socket.timeout:
                    print( "\n   No response. Please, try again.\n" )        
                    print( "   ------------------------------------------")
                    return
                    
                recValue = ( receivedData[3] << 24 | receivedData[4] << 16 | receivedData[5] << 8 | receivedData[6] )
                
                if (recValue != value):
        
                    dataBuf[0] = COMMAND_BL_WRITE_OTP_AREA_LEN - 1
                    dataBuf[1] = COMMAND_BL_WRITE_OTP_AREA                        
                    dataBuf[2] = wordToByte (address ,1 ,1)
                    dataBuf[3] = wordToByte (address ,2 ,1)
                    dataBuf[4] = wordToByte (address ,3 ,1)
                    dataBuf[5] = wordToByte (address ,4 ,1)            
                    dataBuf[6] = wordToByte (value ,1 ,1)
                    dataBuf[7] = wordToByte (value ,2 ,1)
                    dataBuf[8] = wordToByte (value ,3 ,1)
                    dataBuf[9] = wordToByte (value ,4 ,1)
                
                    crc32 = getCRC( dataBuf, COMMAND_BL_WRITE_OTP_AREA_LEN - 4 )
                    crc32 = crc32 & 0xffffffff
    
                    dataBuf[10] = wordToByte (crc32 ,1 ,1)
                    dataBuf[11] = wordToByte (crc32 ,2 ,1)
                    dataBuf[12] = wordToByte (crc32 ,3 ,1)
                    dataBuf[13] = wordToByte (crc32 ,4 ,1)
    
                    sock.settimeout(1)
                    sock.sendto( bytes( dataBuf ), ( ipAddress, port ) )
                    print("HE ESCRITO")
    
                    try:               
                        receivedData, addr = sock.recvfrom(64)                         
                    except socket.timeout:
                        print( "\n   No response. Please, try again.\n" )        
                        print( "   ------------------------------------------")
                        return
                        
        print("\n   Values written to OTP Area")    
        closeFile()      
           
    elif( command == 12 ):
        
        dataRxAck = 0

        while ( dataRxAck == 0):
            validOption = 0
            print("\n   Command == > BL_SET_RDP_STATUS")
            print( "\n   #####################################" )
            print( "   #                                     #" )
            print( "   #  Select option:                     #" )
            print( "   #                                     #" )
            print( "   #  0) LEVEL 0: NO PROTECTION          #" )
            print( "   #  1) LEVEL 1: READ PROTECTION        #" )        
            print( "   #  2) LEVEL 2: CHIP PROTECTION        #" )        
            print( "   #  3) BACK TO MAIN MENU               #" )
            print( "   #                                     #" )
            print( "   #######################################" )
            while (validOption == 0):
                rdpLevel = input( "\n   Type option: " )
                if( rdpLevel.isdigit() ):
                    rdpLevel = int ( rdpLevel )
                if (rdpLevel == 1):        
                    contOpt = str( input( "\n   This option will disable debug and boot from RAM features. Continue? (y/n):" ))
                    validOption = 1 
                    if (contOpt == 'n'):
                        return
                elif (rdpLevel == 2):
        
                    continueOption = input( "\n   This option will protect the chip. This is irreversible. Are you sure? (y/n):" )
                    validOption = 1 
                    if (continueOption == 'n'):
                        return
                    reallyOption = input( "\n   Really? (y/n):" )
                    if (reallyOption == 'n'):
                        return    
                elif (rdpLevel == 0):
                    continueOption = input( "\n   If current level is Level 1, flash will be erased. Continue? (y/n):" )
                    validOption = 1 
                    if (continueOption == 'n'):
                        return
                elif (rdpLevel == 3):
                    return        
                else:
                    print( "\n   Please input valid option. Try again." )
                    print( "\n   ------------------------------------------")                
              
            dataBuf.append( COMMAND_BL_SET_RDP_STATUS_LEN - 1 ) 
            dataBuf.append( COMMAND_BL_SET_RDP_STATUS )
            
            dataBuf.append( wordToByte (rdpLevel ,1 ,1) )
                    
            crc32 = getCRC( dataBuf, COMMAND_BL_SET_RDP_STATUS_LEN - 4 )
            crc32 = crc32 & 0xffffffff
            
            dataBuf.append( wordToByte (crc32 ,1 ,1) )
            dataBuf.append( wordToByte (crc32 ,2 ,1) )
            dataBuf.append( wordToByte (crc32 ,3 ,1) )
            dataBuf.append( wordToByte (crc32 ,4 ,1) )
            
            sock.sendto( bytes( dataBuf ), ( ipAddress, port ) )
            sock.settimeout( 1 ) 
            
            try:
                receivedData, addr = sock.recvfrom(64)
                dataRxAck = 1
            
            except socket.timeout:
                print( "\n   No response. Please, try again\n" )        
                print( "   ------------------------------------------")
                
        retValue = readBootloaderReply( bytearray( receivedData ) )  

    elif( command == 13 ):
        
        dataRxAck = 0

        while ( dataRxAck == 0):
            validOption = 0
            while ( validOption == 0 ):
                print("\n   Command == > BL_CHANGE_RW_PROTECT")
                print( "\n   #####################################" )
                print( "   #                                     #" )
                print( "   #  Select option:                     #" )
                print( "   #                                     #" )
                print( "   #  1) ENABLE WRITE PROTECTION         #" )
                print( "   #  2) ENABLE READ/WRITE PROTECTION    #" )        
                print( "   #  3) DISABLE PROTECTION              #" )        
                print( "   #  4) BACK TO MAIN MENU               #" )
                print( "   #                                     #" )
                print( "   #######################################" )
                protectionCommand = input( "\n   Type option: " )
                
                if( protectionCommand.isdigit() ):
                    protectionCommand = int ( protectionCommand )
                if ( protectionCommand == 1 ):
                    totalSector =  input( "\n   How many sectors do you want to protect? [0-11]: " )
                    totalSector = int ( totalSector )
                    if ( totalSector == STM32_TOTAL_SECTOR ):
                        sectorDetails = 0xFFFF
                    else:
                        sectorNumbers = [0,0,0,0,0,0,0,0,0,0,0,0]
                        sectorDetails = 0
                        for x in range( totalSector ):
                            sectorNumbers[x] = int( input( "\n   Enter sector number[{0}]: ".format( x+1 ) ) )
                            sectorDetails = sectorDetails | ( 1 << sectorNumbers[x] )
                        
                    validOption = 1
    
                    dataBuf.append( COMMAND_BL_EN_RW_PROTECT_LEN - 1 )             
                    dataBuf.append( COMMAND_BL_EN_RW_PROTECT )
                    dataBuf.append( wordToByte (sectorDetails ,1 ,1) )
                    dataBuf.append( wordToByte (sectorDetails ,2 ,1) )
                    dataBuf.append( protectionCommand ) 
    
                    crc32 = getCRC( dataBuf, COMMAND_BL_EN_RW_PROTECT_LEN - 4 )
    
                
                elif ( protectionCommand == 2):
                    totalSector =  input( "\n   How many sectors do you want to protect? [0-11]: " )
                    totalSector = int ( totalSector )
                    if ( totalSector == STM32_TOTAL_SECTOR ):
                        sectorDetails = 0xFFFF
                    else:
                        sectorNumbers = [0,0,0,0,0,0,0,0,0,0,0,0]
                        sectorDetails = 0
                        for x in range( totalSector ):
                            sectorNumbers[x] = int( input( "\n   Enter sector number[{0}]: ".format( x+1 ) ) )
                            sectorDetails = sectorDetails | ( 1 << sectorNumbers[x] )            
                    validOption = 1
                    
                    dataBuf.append( COMMAND_BL_EN_RW_PROTECT_LEN - 1 )             
                    dataBuf.append( COMMAND_BL_EN_RW_PROTECT )
                    dataBuf.append( wordToByte (sectorDetails ,1 ,1) )
                    dataBuf.append( wordToByte (sectorDetails ,2 ,1) )
                    dataBuf.append( protectionCommand ) 
                                
                    crc32 = getCRC( dataBuf, COMMAND_BL_EN_RW_PROTECT_LEN - 4 )
                    
                elif ( protectionCommand == 3):    
                    totalSector =  input( "\n   How many sectors do you want to unprotect? [0-11]: " )
                    totalSector = int ( totalSector )
                    if ( totalSector == STM32_TOTAL_SECTOR ):
                        sectorDetails = 0xFFFF
                    else:
                        sectorNumbers = [0,0,0,0,0,0,0,0,0,0,0,0]
                        sectorDetails = 0
                        for x in range( totalSector ):
                            sectorNumbers[x] = int( input( "\n   Enter sector number[{0}]: ".format( x+1 ) ) )
                            sectorDetails = sectorDetails | ( 1 << sectorNumbers[x] )
                            
                    validOption = 1
    
                    dataBuf.append( COMMAND_BL_DIS_RW_PROTECT_LEN - 1 )             
                    dataBuf.append( COMMAND_BL_DIS_RW_PROTECT )
                    dataBuf.append( wordToByte (sectorDetails ,1 ,1) )
                    dataBuf.append( wordToByte (sectorDetails ,2 ,1) )
                    dataBuf.append( protectionCommand ) 
    
                    crc32       = getCRC(dataBuf,COMMAND_BL_DIS_RW_PROTECT_LEN-4)
                    
                elif ( protectionCommand == 4): 
                    return        
                    
                else :
                    print( "\n   Please input valid option. Try again." )
                    print( "\n   ------------------------------------------")
            
            if (validOption == 1):    
                crc32 = crc32 & 0xffffffff
    
                dataBuf.append( wordToByte (crc32 ,1 ,1) )
                dataBuf.append( wordToByte (crc32 ,2 ,1) )
                dataBuf.append( wordToByte (crc32 ,3 ,1) )
                dataBuf.append( wordToByte (crc32 ,4 ,1) )
                        
                sock.sendto( bytes( dataBuf ), ( ipAddress, port ) )
                sock.settimeout( 1 ) 

                try:
                    receivedData, addr = sock.recvfrom(64)
                    dataRxAck = 1
     
                except socket.timeout:
                    print( "\n   No response. Please, try again\n" )
                    print( "   ------------------------------------------")
            
        retValue = readBootloaderReply( bytearray( receivedData ) )    

    elif( command == 14 ):
    
        dataRxAck = 0

        while ( dataRxAck == 0):

            print("\n   Command == > BL_FLASH_ERASE")
        
            nSec = 0
            validOption = 0
    
            dataBuf.append( COMMAND_BL_FLASH_ERASE_LEN - 1 ) 
            dataBuf.append( COMMAND_BL_FLASH_ERASE )
    
            while ( validOption == 0 ):
                print( "\n   ##########################" )
                print( "   #                        #" )
                print( "   #  Select option:        #" )
                print( "   #                        #" )
                print( "   #  1) SPECIFIC SECTORS   #" )
                print( "   #  2) FULL ERASE         #" )
                print( "   #  3) BACK TO MAIN MENU  #" )
                print( "   #                        #" )
                print( "   ##########################" )
                eraseOption = input( "\n   Type erase option: " )
                if( eraseOption.isdigit() ):
                    eraseOption = int(eraseOption)
                if ( eraseOption == 1 ):
                    sectorNum = int( input( "\n   Enter sector number(0-11) here :" ) )
                    nSec=int( input( "\n   Enter number of sectors to erase(max 12) here :" ) )
                    validOption = 1
                
                elif ( eraseOption == 2):
                    eraseVerification = input( "\n   Are you sure you want to erase ALL FLASH SECTORS? Press (y/n): " )
                    if (eraseVerification == "y"):
                        sectorNum = 0xff
                        validOption = 1
                    else:
                        print ( "\n   Operation cancelled " )
                        time.sleep(1)
                elif ( eraseOption == 3): 
                    return         
                else :
                    print( "\n   Please input valid option. Try again." )
                    print( "\n   ------------------------------------------")
            
            if (validOption == 1):    
                dataBuf.append( sectorNum )
                dataBuf.append( nSec ) 
            
                crc32 = getCRC( dataBuf, COMMAND_BL_FLASH_ERASE - 4 )
                crc32 = crc32 & 0xffffffff
            
                dataBuf.append( wordToByte (crc32 ,1 ,1) )
                dataBuf.append( wordToByte (crc32 ,2 ,1) )
                dataBuf.append( wordToByte (crc32 ,3 ,1) )
                dataBuf.append( wordToByte (crc32 ,4 ,1) )
                
                sock.settimeout(10)
                sock.sendto( bytes( dataBuf ), ( ipAddress, port ) )
                
                try:
                    receivedData, addr = sock.recvfrom(64)
                    dataRxAck = 1
            
                except socket.timeout:
                    print( "\n   No response. Please, try again\n" )
                    print( "   ------------------------------------------")                    

        retValue = readBootloaderReply( bytearray( receivedData ) ) 

    elif( command == 15 ):
        print( "\n   Command == > BL_GO_TO_ADDR" )
   
        dataRxAck = 0
        while ( dataRxAck == 0):
            validOption = 0
            while (validOption == 0):
                goAddress  = input( "\n   Please enter Word Address in hex [0 to quit]: " )
                if ( goAddress == '0'):
                    return    
                    
                try:
                    goAddress = int(goAddress, 16)
                    validOption = 1
                except ValueError:
                        print("\n   Invalid hex number. Please, try again.")
                      
            dataBuf.append( COMMAND_BL_GO_TO_ADDR_LEN - 1 ) 
            dataBuf.append( COMMAND_BL_GO_TO_ADDR )
            
            dataBuf.append( wordToByte( goAddress, 1, 1 ) )
            dataBuf.append( wordToByte( goAddress, 2, 1 ) )
            dataBuf.append( wordToByte( goAddress, 3, 1 ) )
            dataBuf.append( wordToByte( goAddress, 4, 1 ) )
            
            crc32 = getCRC( dataBuf, COMMAND_BL_GO_TO_ADDR_LEN - 4 )
            crc32 = crc32 & 0xffffffff
            
            dataBuf.append( wordToByte (crc32 ,1 ,1) )
            dataBuf.append( wordToByte (crc32 ,2 ,1) )
            dataBuf.append( wordToByte (crc32 ,3 ,1) )
            dataBuf.append( wordToByte (crc32 ,4 ,1) )
            
            sock.sendto( bytes( dataBuf ), ( ipAddress, port ) )
    
            try:
                receivedData, addr = sock.recvfrom(64)
            
            except socket.timeout:
                print( "\n   No response. Please, try again\n" )
                print( "   ------------------------------------------")                   

        retValue = readBootloaderReply( bytearray( receivedData ) )                
       

       
def readBootloaderReply(receivedData):
    lenToFollow = 0 
    ret         = -2 
    if( len( receivedData ) ):
        if ( receivedData[1] != 0xA5 ):

            #CRC of last command was good .. received data and "len to follow"
            commandCode = receivedData[1]
            lenToFollow = receivedData[0]
            
            if ( commandCode ) == COMMAND_BL_GET_VER :
                process_COMMAND_BL_GET_VER( lenToFollow, receivedData[2] )
                
            elif ( commandCode ) == COMMAND_BL_GET_CID:
                process_COMMAND_BL_GET_CID( lenToFollow, receivedData )
                
            elif ( commandCode ) == COMMAND_BL_GET_RDP_STATUS:
                process_COMMAND_BL_GET_RDP_STATUS( lenToFollow, receivedData[2] )

            elif ( commandCode ) == COMMAND_BL_SET_RDP_STATUS:
                process_COMMAND_BL_SET_RDP_STATUS( lenToFollow, receivedData[2] ) 

            elif ( commandCode ) == COMMAND_BL_READ_ADDR_VALUE:
                process_COMMAND_BL_READ_ADDR_VALUE( lenToFollow, receivedData )
                
            elif ( commandCode ) == COMMAND_BL_WRITE_OTP_AREA:
                process_COMMAND_BL_WRITE_OTP_AREA( lenToFollow, receivedData )

            elif ( commandCode) == COMMAND_BL_GO_TO_ADDR:        
                process_COMMAND_BL_GO_TO_ADDR( lenToFollow, receivedData[2] )                 
                
            elif ( commandCode) == COMMAND_BL_READ_OTP_AREA_STATUS:        
                process_COMMAND_BL_READ_OTP_AREA_STATUS( lenToFollow, receivedData )                
                
            elif ( commandCode ) == COMMAND_BL_FLASH_ERASE:
                process_COMMAND_BL_FLASH_ERASE( lenToFollow, receivedData[2] ) 
                
            elif ( commandCode ) == COMMAND_BL_READ_SECTOR_P_STATUS:
                process_COMMAND_BL_READ_SECTOR_STATUS( lenToFollow, receivedData ) 
                
            elif ( commandCode ) == COMMAND_BL_EN_RW_PROTECT:
                process_COMMAND_BL_EN_RW_PROTECT( lenToFollow, receivedData[2] )
                
            elif ( commandCode ) == COMMAND_BL_DIS_RW_PROTECT:
                process_COMMAND_BL_DIS_RW_PROTECT( lenToFollow, receivedData[2] )                
                
            else:
                print("\n   Invalid command code\n")
                
            ret = 0
         
        elif ( receivedData[1] == NACK ):
            #CRC of last command was bad .. received NACK
            print("\n   CRC: FAIL \n")
            ret= -1
    else:
        print("\n   Timeout : Bootloader not responding")
        
    return ret
   
#----------------------------- Ask Menu implementation----------------------------------------
print( "\n +==============================================================+" )
print( " |                         Software                             |" )
print( " |                   STM32F4 BootLoader v1.0                    |" )
print( " +==============================================================+" )

conEstablished = 0
while ( conEstablished == 0 ):
    ipAddress = str( input( "   Enter IP of your device: " ) )
    #ipAddress = "192.168.1.10"
    port = 7
    #port      = int( input( "   Enter UDP port of your device: " ) )
    ack       = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP

    ack.append(1)
    ack.append(ACK)
    sock.sendto( bytes( ack ), ( ipAddress, port ) ) 
    sock.settimeout( 1 )
    try:
        data, addr = sock.recvfrom(64) # buffer size is 1024 bytes
        print( "\n   Connection established\n\n" )
        time.sleep(1)
        conEstablished = 1
        os.system('cls')
        
    except socket.timeout:
        print( "\n   Connection couldn't be established. Please, try again\n\n" )
    
      
while True:
    print( "\n +==============================================================+" )
    print( " |                           Menu                               |" )
    print( " |                   STM32F4 BootLoader v1.0                    |" )
    print( " +==============================================================+" )
    
    print( "\n   ------------------- INFORMATION COMMANDS -------------------\n" )
    print( "   1)  BL_GET_VER            Get version of STM32FX Bootloader" )
    print( "   2)  BL_GET_CID:           Get Device ID and Rev Identifier" )
    print( "   3)  BL_GET_RDP_STATUS:    Read Protection Byte status" )
    print( "   4)  BL_SECTOR_P_STATUS:   Read sectors status protection" )
    print( "   5)  BL_READ_ADDR_VALUE:   Read the value of specified address" )
    print( "   6)  BL_READ_OTP_STATE:    Read the state (if lock) of otp area" )    
    print( "   7)  BL_EXPORT_OTP:        Export values from otp area to a file" )        
    
    print( "\n   --------------------- UPDATE COMMANDS ----------------------\n" )
    print( "   8)  BL_DOWNLOAD_FLASH:    Download actual software from FLASH" )
    print( "   9)  BL_UPDATE_FLASH:      Update FLASH with a new software" )
    
    print( "\n   -------------------- ADVANCED COMMANDS --------------------" )
    print( "   /!\ ONLY AUTHORIZED PERSONAL SHOULD USE THESE COMMANDS /!\ \n" )
    print( "   10) BL_WRITE_OTP_AREA:    Write value to a specific OTP address" )
    print( "   11) BL_WRITE_OTP_FILE:    Write OTP file with new values" )
    print( "   12) BL_SET_RDP_STATUS:    Set Protection Byte status" )
    print( "   13) BL_CHANGE_RW_PROTECT: Change R/W sectors protection" )
    print( "   14) BL_FLASH_ERASE:       Erase flash specified N sectors" )
    print( "   15) BL_GO_TO_ADDR:        Go to specified address" )
      
    commandCode = input( "\n   Type the command code here (0 to quit): " )

    if(not commandCode.isdigit()):
        print( "\n   Please input valid code shown above" )
    else:
        decodeMenuCommandCode( int( commandCode ) )

    input( "\n   Press any key to continue  :" )
    os.system('cls')

def protection_type():
    pass

