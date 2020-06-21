# -*- coding: utf-8 -*-
import binascii
import sys
import json
import struct
import functools
from collections import OrderedDict


hexFile = b''
rebuildFileTemp = b''
exportDict = OrderedDict()
stringOffsetTable = []
stringTable = []



def readFromPosition (offset, size, value_type):
    valueToRead=(binascii.unhexlify(hexFile[offset*2:(offset+size)*2]))
    valueToRead=struct.unpack(value_type,valueToRead)
    valueToRead=functools.reduce(lambda rst, d: rst * 10 + d, (valueToRead))
    if type(valueToRead) is bytes: #String gets unpacked as bytes, we want to convert it to a regular string
        valueToRead = valueToRead.decode()
    return valueToRead



def calculateSeparator(end): #Calculates the amount of null bytes that need to be added
    last_part_offset = int(hex(int(end))[-1],16) #This is retarded

	#Check the last digit of the hex value to calculate the amount that needs to be filled for the next table to start
    if (last_part_offset<0x4): 
        return 0x4-last_part_offset
    elif (last_part_offset>=0x4 and last_part_offset<0x8):
        return 0x8-last_part_offset
    elif (last_part_offset>=0x8 and last_part_offset<0xC):
        return 0xC-last_part_offset
    elif (last_part_offset>=0xC and last_part_offset<0x10):
        return 0x10-last_part_offset
    else:
        return 1



def storeTable (startOffset, tableSize, tableContainer): #Stores every entry of the table into the selected variable
    byteGroup = ""
    table = hexFile[(startOffset*2) : (startOffset*2)+(tableSize*4)*2].decode('utf-8')

    for nibble in table:
        if (len(byteGroup) <8):
            byteGroup += nibble
			
        if (len(byteGroup) == 8):
            tableContainer.append(byteGroup)
            byteGroup= ""
            #byteGroup += byte



def iterateStringTable ():
    for offset in stringOffsetTable:
        table = hexFile[(int(offset,16)*2):] #A bit of a dirty approach but it will do for now
        string_end = table.find(b'00') 
        if (string_end % 2 != 0): #If the last hex digit ends with 0, the pointer will be odd, so we compensate adding 1
            string_end += 1
        string = binascii.unhexlify (table[:string_end]).decode()
        stringTable.append(string)
        
        





def exportFile ():
    with open(file_path, "rb") as f:
        file=f.read()
    global hexFile
    hexFile=(binascii.hexlify(file))



    numberOfElements = readFromPosition (0x10, 0x4, ">i")
    pointerToStringOffsetTable = readFromPosition (0x14, 0x4, ">i")
    pointerToUnknownDataTable = readFromPosition (0x18, 0x4, ">i")
    pointerToUnknownData1OffsetTable = readFromPosition (0x1C, 0x4, ">i")
    pointerToUnknownData2OffsetTable = readFromPosition (0x20, 0x4, ">i")
    pointerToUnknownData3OffsetTable = readFromPosition (0x24, 0x4, ">i")
    pointerToUnknownData4OffsetTable = readFromPosition (0x28, 0x4, ">i")

    # DEBUG
    print ("Number of Elements: " + str(numberOfElements))
    print ("Pointer to String Offset Table: " + str(pointerToStringOffsetTable))
    print ("Pointer to Unknown Data Table: " + str(pointerToUnknownDataTable))
    print ("Pointer to Unknown Data 1 Offset Table: " + str(pointerToUnknownData1OffsetTable))
    print ("Pointer to Unknown Data 2 Offset Table: " + str(pointerToUnknownData2OffsetTable))
    print ("Pointer to Unknown Data 3 Offset Table: " + str(pointerToUnknownData3OffsetTable))
    print ("Pointer to Unknown Data 4 Offset Table: " + str(pointerToUnknownData4OffsetTable))



    storeTable(pointerToStringOffsetTable, numberOfElements, stringOffsetTable)
    iterateStringTable()

    # PREPARE THE EXPORT DICTIONARY AND SAVE AS JSON
    exportDict["MAGIC"] = readFromPosition (0x0, 0x4, ">4s")
    exportDict["ENDIANNESS_FLAG"] = hexFile[0x4*2:(0x4+0x4)*2].decode()
    exportDict["NUMBER_ELEMENTS"] = numberOfElements
    for element in stringTable:
        element_index = stringTable.index(element)
        elementDict = OrderedDict()
        elementDict["NAME"] = element #Strings
        exportDict[element_index] = elementDict


    with open(file_name +'.json', 'w') as file:
        json.dump(exportDict, file, indent=2)
        
    




def rebuildFile ():
    with open(file_path, 'r') as file:
        data = json.load(file)
        print(data)
        global rebuildFileTemp
        stringOffsetTableTemp = []
        rebuildFileTemp += binascii.hexlify(data["MAGIC"].encode()) #Add magic
        rebuildFileTemp += data["ENDIANNESS_FLAG"].encode() #Add endianness identifier
        rebuildFileTemp += b'00000000'*2 #Fill the empty values
        rebuildFileTemp += b'00000000'*16 #Set the main table to all zeros for now

        for x in range(data["NUMBER_ELEMENTS"]): #Write String table and store offsets for the String offset table
            stringOffsetTableTemp.append(len(rebuildFileTemp)/2)
            rebuildFileTemp += binascii.hexlify(data[str(x)]["NAME"].encode())
            rebuildFileTemp += b'00' #Null byte
        rebuildFileTemp += b'00' * calculateSeparator(len(rebuildFileTemp)/2) #Add null bytes at the end of the String table

        stringOffsetTableOffset = len(rebuildFileTemp)/2
        for x in range(data["NUMBER_ELEMENTS"]): #Write String Offset table
            rebuildFileTemp += hex(int(stringOffsetTableTemp[x]))[2:].zfill(8).encode() 
        

        rebuildFileTemp = rebuildFileTemp[:0x10*2] + hex(data["NUMBER_ELEMENTS"])[2:].zfill(8).encode() + rebuildFileTemp[0x14*2:] #Add the number of elements to the main table
        rebuildFileTemp = rebuildFileTemp[:0x14*2] + hex(int(stringOffsetTableOffset))[2:].zfill(8).encode() + rebuildFileTemp[0x18*2:] #Add the pointer to the String Offset table to the main table
        


        with open(file_name +'.bin', 'wb') as file:
            file.write(binascii.unhexlify(rebuildFileTemp))




file_path = sys.argv[1:][0]
file_name = file_path.split("\\")[-1]
file_extension = file_name.split(".")[-1]


def determineFileExtension(file_extension): #Switch case based on the file extension
    switch = {
        "bin" : exportFile,
        "json" : rebuildFile
    }
    func = switch.get(file_extension.lower(), lambda: "Extension not supported")
    return func()


determineFileExtension(file_extension)





