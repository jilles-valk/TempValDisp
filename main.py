# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from luma.core.interface.serial import i2c, spi
from luma.core.render import canvas
from luma.oled.device import ssd1306, ssd1309, ssd1325, ssd1331, sh1106
from time import sleep
from datetime import datetime
import Adafruit_GPIO.SPI as SPI
import Adafruit_MAX31855.MAX31855 as MAX31855
from sys import argv
import serial
import pynmea2
from threading import Thread
import os
import sys
from PIL import ImageFont
from dateutil import tz

gpsDateTime = None
gpsData = None
gpsTime = None
gpsDate = datetime(2000, 1, 1)
gpsSpeed = None
trueCourse = None
gpsAltitude = None
tEngHist = []
#tIntHist = []
tEngine = 0
tInternal = 0
counter = 0
t = 0


def updateDisplay():
	dispSerial = spi(device=0, port=0)
	device = ssd1306(dispSerial)
	fontLarge = make_font("FreePixel.ttf", 18)
	fontSmall = make_font("C&C Red Alert [INET].ttf", 13)
	headings = ["N", "NO", "O", "ZO", "Z", "ZW", "W", "NW"]
	speedString = ""
	timeString = ""
	altitudeString = ""
	trueCourseString = "" 
	compassString = ""

	while True:
		if (gpsDateTime):
			gpsString = gpsDateTime.strftime("%d-%m-%y")
			timeString = gpsDateTime.strftime("%H:%M:%S")
		else:
			gpsString = "Zoekt GPS"
			timeString = "--:--"
		if (gpsSpeed):
			speedString = "{0:0.1F}".format(gpsSpeed)
		else:
			speedString = "-.-"
		if (gpsAltitude):
			altitudeString = "{0:0.0F}".format(gpsAltitude) + " m"
		else:
			altitudeString = "- m"
		tExhaustString = "{0:0.1F}".format(tEngine)+u'\N{DEGREE SIGN}'+"C"
		if (trueCourse):
			trueCourseString = str(trueCourse)+u'\N{DEGREE SIGN}'
			compassString = headings[int(round(8*(trueCourse/360.0))%8)]

		with canvas(device) as draw:
			wspeed, h = draw.textsize(text=speedString, font=fontLarge)
			wtime, h = draw.textsize(text=timeString, font=fontSmall)
			wcompass, h = draw.textsize(text=compassString, font=fontSmall)
			wcourse, h = draw.textsize(text=trueCourseString, font=fontSmall)
			walt, h = draw.textsize(text=altitudeString, font=fontSmall)
			draw.rectangle(device.bounding_box, outline="white", fill="black")
			draw.text((3, 0), gpsString, font = fontSmall, fill = "white")
			draw.text((127 - wtime, 0), timeString, font = fontSmall, fill = "white")
			draw.text((3, 15), speedString, font = fontLarge, fill = "white")
			draw.text((6 + wspeed, 19), "km/u", font = fontSmall, fill="white")
			draw.text((124 - walt, 19), altitudeString, font = fontSmall, fill= "white")
			draw.text((3, 52), tExhaustString, font = fontSmall, fill="white")
			draw.text((127 - wcourse - wcompass - 5, 52), compassString, font=fontSmall, fill="white")
			draw.text((127 - wcourse, 52), trueCourseString, font=fontSmall, fill="white")
			draw.rectangle([2, 33, 125, 53], outline = "white", fill = "black") 
#			draw.rectangle([64, 33, 125, 53], outline = "white", fill = "black")
			draw.line((tEngHist), fill = "white")
#			draw.line((tIntHist), fill = "white")
		sleep(1)	

def setArrayTime(startTime, arr):
	newArr = []
	for i in range(0, len(arr)):
		newArr.append((i + startTime, arr[i][1]))
	return newArr

def readGPS():
	global gpsData
	global gpsTime
	global gpsDate
	global gpsSpeed
	global trueCourse
	global gpsAltitude
	global gpsDateTime
	from_zone = tz.gettz('UTC')
	to_zone = tz.gettz('Europe/Amsterdam')
	gpsSerialPort = None

	while True:
		try:
			gpsSerialPort = serial.Serial("/dev/ttyAMA0", 9600, timeout=0.5)
			break
		except SerialException:
			sleep(1)

	while True:
		newData = gpsSerialPort.readline()
		if newData[0:6] == "$GPRMC":
			gpsData = pynmea2.parse(newData)
			gpsTime = gpsData.timestamp
			gpsDate = gpsData.datestamp
			temp = str(gpsDate)
			if (gpsDate and gpsTime and not isinstance(gpsDate, basestring) and not isinstance(gpsTime, basestring)):
				gpsDateTime = datetime.combine(gpsDate, gpsTime)
				gpsDateTime = gpsDateTime.replace(tzinfo = from_zone)
				gpsDateTime = gpsDateTime.astimezone(to_zone)
			if (gpsData.spd_over_grnd):
				gpsSpeed = 1.852*float(gpsData.spd_over_grnd)
			if (gpsData.true_course):
				trueCourse = int(gpsData.true_course)
		if newData[0:6] == "$GPGGA":
			gpsData = pynmea2.parse(newData)
			if (gpsData.altitude):
				gpsAltitude = gpsData.altitude


def readTemp():
	global tEngHist
#	global tIntHist
	global tEngine
	global tInternal
	tEngArr = []
	tIntArr = []
	counter = 0
	engCounter = 0
	intCounter = 0
	t = 0
	CLK = 5
	CS  = 23
	DO  = 18
	tempSensor = MAX31855.MAX31855(CLK, CS, DO)
	while True:
		tEngineNow = tempSensor.readTempC()
		if (tEngineNow == tEngineNow):
			tEngArr.append(tEngineNow)
			engCounter += 1
		tInternalNow = tempSensor.readInternalC()
		if (tInternalNow == tInternalNow):
			tIntArr.append(tInternalNow)
			intCounter += 1
		counter += 1
		if (tEngineNow == tEngineNow):
			tEngine = tEngineNow
		if (counter == 60):
			if (engCounter > 0):
				tEngine = sum(tEngArr)/engCounter
			if (intCounter > 0):
				tInternal = sum(tIntArr)/intCounter
			if (tEngine < 0):
				tEngHist.append((t + 2, 53))
			elif (tEngine > 800):
				tEngHist.append((t + 2, 53 - 20))
			else:
				tEngHist.append((t + 2, 53 - 20*(tEngine/800)))
#			if (tInternal < 0):
#				tIntHist.append((t + 65, 53))
#			elif (tInternal > 50):
#				tIntHist.append((t + 65, 53 - 20))
#			else:
#				tIntHist.append((t + 65, 53 - 20*(tInternal/50)))
			t += 1
			tEngArr = []
			tIntArr = []
			engCounter = 0
			intCounter = 0
			counter = 0
			if (len(tEngHist) > 124):
				del tEngHist[0]
				tEngHist = setArrayTime(2, tEngHist)
#			if (len(tIntHist) > 60):
#				del tIntHist[0]
#				tIntHist = setArrayTime(65, tIntHist)
		sleep(0.5)

def make_font(name, size):
    font_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'fonts', name))
    return ImageFont.truetype(font_path, size)

if __name__ == "__main__":
	gpsThread = Thread(target = readGPS, args = ( ))
	displayThread = Thread(target = updateDisplay, args = ( ))
	tempThread = Thread(target = readTemp, args = ( ))
	gpsThread.start()
	displayThread.start()
	tempThread.start()
	gpsThread.join()
	displayThread.join()
	tempThread.join()
