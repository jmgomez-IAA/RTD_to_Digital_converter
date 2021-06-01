#!/usr/bin/python3.6
"""! @brief Basic example of PT1000 adquisition with RPI3 and ADS1248."""

##
# @file test_idac-mux_ads1248
#
# @brief Define the ADC class and test idac-mux
# @author Juan Manuel Gómez
#
# @Copyright (c) IAA-CSIC. All rights reserved.


# Imports
import sys
import spidev
import time
import RPi.GPIO as GPIO
import datetime
# use UliEngineering to accurate calculate the Temperature from  Resistance.
from UliEngineering.Physics.RTD import pt1000_temperature

from enum import IntEnum

# --- Global variables ---
spi = 0
PGA = 4
Vref = 1.560
r_ref =  15000

# --- ASSIGNMENTS ---
#Define GPIO Pins (using board numbering)
START = 11
RESET = 16
DRDY = 18

# --- VALUES ---

class RTD_IF(IntEnum):
    J1 = 0
    J2 = 1
    J3 = 2
    J4 = 3

class ADS1248:
    """ ADS1248 class manages the ADC ADS1248, it configures the ADC to excite an
    RTD PT1000 with .100uA and uses AN2-AN3 inputs to read the sensor.
    """

    # Addresses of the configuration registers
    MUX0 = 0x00
    MUX1 = 0x02
    VBIAS = 0x01
    SYS0 = 0x03
    OFC0 = 0x04
    OFC1 = 0x05
    OFC2 = 0x06
    FSC0 = 0x07
    FSC1 = 0x08
    FSC2 = 0x09
    IDAC0 = 0x0a
    IDAC1 = 0x0b
    GPIOCFG = 0x0c
    GPIODIR = 0x0d
    GPIODAT = 0x0e

    #ADS1248 commands
    WREG = 0x40     #Write to register (0100xxxx)
    RREG = 0x20     #Read from register (0010xxxx)
    NOP = 0xff      #No operation
    RDATA = 0x12    #Read conversion result
    RDATAC = 0x14   #Read conversion continuously

def resetADS1248():
    """ Resets the ADS1248 by pulsing RESET pin LOW and back to HIGH.

    Returns nothing."""

    #Reset the ADS1248 and re-read register
    GPIO.output(RESET, False)       #RESET pin low -> reset
    time.sleep(0.025)
    GPIO.output(RESET, True)        #RESET pin high -> run
    time.sleep(0.025)

    return

def writeReg(reg,data):
    """ Writes one byte to the given register.

    Accepts two integer bytes: register and data."""

    r = spi.xfer2([ADS1248.WREG+reg,0x00,data])
    return r

def readReg(reg):
    """ Reads one byte from the given register.

    Accepts one integer byte: register."""

    spi.xfer2([ADS1248.RREG+reg,0x00])
    r = spi.xfer2([ADS1248.NOP])
    return r

def convert():
    """ Returns ADC conversion from ADS1248. """

    spi.writebytes([ADS1248.RDATA])              #Issue read data once command
    raw = spi.readbytes(3)                       #Read bytes
    spi.writebytes([ADS1248.NOP])                #Send no operation
    #print(raw)
    adc = (raw[0]<<16) + (raw[1]<<8) + raw[2]
    #print(adc)
    return adc

def initGPIO():
    """ Initializes RPi GPIO settings for ADS1248 interface.

    Accepts no arguments, returns nothing."""

    #Use board pin numbering (as on RPi)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)

    #Setup pins as output
    GPIO.setup(START, GPIO.OUT)
    GPIO.setup(RESET, GPIO.OUT)
    GPIO.setup(DRDY, GPIO.IN)

    #Set and hold reset pin high
    GPIO.output(RESET, True)
    #Set start pin high to allow communicating with registers
    GPIO.output(START, True)

def printRegs():
    """ Reads and prints all registers of ADS1248.""" 

    s = ""
    regs = {'   MUX0' : ADS1248.MUX0,
            '   MUX1' : ADS1248.MUX1,
            '  VBIAS' : ADS1248.VBIAS,
            '   SYS0' : ADS1248.SYS0,
            '   OFC0' : ADS1248.OFC0,
            '   OFC1' : ADS1248.OFC1,
            '   OFC2' : ADS1248.OFC2,
            '  IDAC0' : ADS1248.IDAC0,
            '  IDAC1' : ADS1248.IDAC1,
            'FSC0-RO' : ADS1248.FSC0,
            'FSC1-RO' : ADS1248.FSC1,
            'FSC2-RO' : ADS1248.FSC2,
            'GPIOCFG' : ADS1248.GPIOCFG,
            'GPIODIR' : ADS1248.GPIODIR,
            'GPIODAT' : ADS1248.GPIODAT}

    s += "\n--- ADS1248 Register Values: ---"
    s += "\n         dec    binary     hex"

    for key, value in regs.items():
        r = readReg(value)
        s += "\n" + key + ": " + str(r[0]).zfill(3) + "  0b" + str(bin(r[0])[2:]).zfill(8) + "  0x" + str(hex(r[0])[2:]).zfill(2)

    return s

def configureADS1248():
    """ Configures ADS1248 for four-three wire RTDs.

    Accepts nothing, returns nothing."""

    #writeReg(ADS1248.OFC0, 0b00000000);             #Offset calibration reset (pg 45)
    #writeReg(ADS1248.OFC1, 0b00000000);             #Offset calibration reset (pg 45)
    #writeReg(ADS1248.OFC2, 0b00000000);             #Offset calibration reset (pg 45)
    #writeReg(ADS1248.GPIODIR, 0b00000000);          #N/A - GPIO disabled in GPIOCFG
    #writeReg(ADS1248.GPIODAT, 0b00000000);          #N/A - GPIO disabled in GPIOCFG

    writeReg(ADS1248.MUX0,0b00000001)               #Burnout OFF,VREF On, AIN0 & AIN1 selected (pg 43)
    writeReg(ADS1248.VBIAS, 0b00000000);            #VBIAS off (pg 43)
    writeReg(ADS1248.MUX1,0b00101000)               #Internal oscillator, VREF on, REF1, normal operations (pg 44)
    writeReg(ADS1248.SYS0,0b00100000)               #PGA=4, ADC data rate = 20 SPS (pg 45)
    writeReg(ADS1248.IDAC0, 0b10000010);            #DRDY only, IDAC I=1mA (pg 46)
    writeReg(ADS1248.IDAC1, 0b10001100);            #IDAC1 -> IEXC1, IDAC2 -> Disconnected (pg 63)

    writeReg(ADS1248.GPIOCFG, 0b00000011);          #GPIO[0,1] pins are analog outputs (others GPIO disabled) (pg 48)
    writeReg(ADS1248.GPIODIR, 0b00000000);          # GPIO[0,1] pins are output
    writeReg(ADS1248.GPIODAT, 0b00000000);          # Value is low.

def  select_mux(interface):
    """ Configures ADS1248 GPIO to select on the MUX
    to read from rtd_if interface.
    Accepts if: interface to read, returns nothing."""

    if interface == 0:
        writeReg(ADS1248.MUX0,0b00110111)               #Burnout OFF,VREF On, AIN6 & AIN7 selected (pg 43)
        writeReg(ADS1248.GPIODAT, 0b00000000);          # Value is 00.

    elif interface == 1:
        writeReg(ADS1248.MUX0,0b00100101)               #Burnout OFF,VREF On, AIN4 & AIN5 selected (pg 43)
        writeReg(ADS1248.GPIODAT, 0b00000001);          # Value is 01.

    elif interface == 2:
        writeReg(ADS1248.MUX0,0b00010011)               #Burnout OFF,VREF On, AIN3 & AIN2 selected (pg 43)
        writeReg(ADS1248.GPIODAT, 0b00000010);          # Value is 10.

    elif interface == 3:
        writeReg(ADS1248.MUX0,0b00000001)               #Burnout OFF,VREF On, AIN0 & AIN1 selected (pg 43)
        writeReg(ADS1248.GPIODAT, 0b00000011);          # Value is 11.
    
    else:
        writeReg(ADS1248.MUX0,0b00000001)               #Burnout OFF,VREF On, AIN0 & AIN1 selected (pg 43)
        writeReg(ADS1248.GPIODAT, 0b00000000);          # def is 00.
        print ("Unknown Inteface. Default 00")


def adquire_rtd(rtd_number):
    """ Configure the MUX to adquire the RTD rtd_number 
    and returns the value of the Code, Resistence and Temperature.
    Accepts rtd_number, J1 to J4 rtd interface connectors, 
    returns, list with ADC-Code, Resistance-RTD and Temperature."""

    select_mux(rtd_number)
    time.sleep(1)

    code = convert();
    v_rtd = (code/8388608.0)*Vref/PGA
    # The resistance of the RTD
    r_rtd =  r_ref*(code / 8388608.0)/PGA
    # Convert to temperature using UliEngineering libary
    temp_C = pt1000_temperature(r_rtd)

    return code, v_rtd, r_rtd, temp_C

#Begin the main program
def main():

    initGPIO()

    #Initialize SPI
    global spi
    spi = spidev.SpiDev()
    spi.open(0,0)
    spi.cshigh=False
    spi.bits_per_word=8
    spi.mode=1              #For ADS1248 clock dwells low (CPOL=0) and data clocked on falling edge (CPHA=1)
    spi.max_speed_hz = 1000

    resetADS1248()
    #print (printRegs())
    time.sleep(0.050)

    configureADS1248()
    #print (printRegs())
    time.sleep(0.050)

    print ("-- MUX to J1 ---")
    select_mux(1)
    time.sleep(1)

    rtd_if = 0
    # Header of the psudotable
    print ("timeStamp\t      RTD_IF\tCODE\tVrtd\t     Rrtd\t    T ºC")
    while True:
        #    GPIO.wait_for_edge(DRDY, GPIO.FALLING)      #Wait for DRDY
        time.sleep(0.050)
        #code = convert();

        #v_rtd = (code/8388608.0)*Vref/PGA
        # The resistance of the RTD 
        #r_rtd =  r_ref*(code / 8388608.0)/PGA
        # Convert to temperature using UliEngineering libary
        #temp_C = pt1000_temperature(r_rtd)

        code, v_rtd, r_rtd, temp_C = adquire_rtd(rtd_if)
        #Outputs the results of the conversion.
        print ("%s\t%d\t%d\t%.3fV\t%.3fOhms\t2:+%.3fC" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), rtd_if, code, v_rtd, r_rtd,temp_C) )

        time.sleep(2)
        rtd_if = rtd_if +1
        if rtd_if > 3: rtd_if = 0

if __name__ == "__main__":
   main()
