#!/usr/bin/env python
# -*- coding: utf-8 -*-

#important: before running this demo, make certain that you import the library
#'paho.mqtt.client' into python (https://pypi.python.org/pypi/paho-mqtt)
#also make certain that ATT_IOT is in the same directory as this script.

import logging
logging.getLogger().setLevel(logging.INFO)                                                                          #before doing anything else, set the desired logging level, so all modules log correctly.

from ConfigParser import *

import RPi.GPIO as GPIO                            #provides pin support
import ATT_IOT as IOT                              #provide cloud support
from time import sleep                             #pause the app
import picamera

ConfigName = 'rpicamera.config'
hasLISIPAROI = False
LISIPAROIPin = 0

PreviewId = 1
RecordId = 2

def tryLoadConfig():
    'load the config from file'
    global hasLISIPAROI, LISIPAROIPin
    c = ConfigParser()
    if c.read(_configName):
        #set up the ATT internet of things platform
        IOT.DeviceId = c.get('cloud', 'deviceId')
        IOT.ClientId = c.get('cloud', 'clientId')
        IOT.ClientKey = c.get('cloud', 'clientKey')
        hasLISIPAROI = c.get('camera', 'has LISIPAROI')
        if hasLISIPAROI:
            LISIPAROIPin = int(c.get('camera', 'LISIPAROI pin'))
        return True
    else:
        return False


#callback: handles values sent from the cloudapp to the device
def on_message(id, value):
    if id.endswith(str(LISIPAROIPin)) == True:
        value = value.lower()                        #make certain that the value is in lower case, for 'True' vs 'true'
        if value == "true":
            GPIO.output(LISIPAROIPin, GPIO.HIGH)
            IOT.send("true", ActuatorPin)                #provide feedback to the cloud that the operation was succesful
        elif value == "false":
            GPIO.output(LISIPAROIPin, GPIO.LOW)
            IOT.send("false", LISIPAROIPin)                #provide feedback to the cloud that the operation was succesful
        else:
            print("unknown value: " + value)
    elif id.endswith(str(PreviewId)) == True:
        value = value.lower()                        #make certain that the value is in lower case, for 'True' vs 'true'
        if value == "true":
            camera.start_preview()
            IOT.send("true", PreviewId)                #provide feedback to the cloud that the operation was succesful
        elif value == "false":
            camera.stop_preview()
            IOT.send("false", PreviewId)                #provide feedback to the cloud that the operation was succesful
        else:
            print("unknown value: " + value)
    elif id.endswith(str(RecordId)) == True:
        value = value.lower()                        #make certain that the value is in lower case, for 'True' vs 'true'
        if value == "true":
            camera.start_recording('video.h264')
            IOT.send("true", RecordId)                #provide feedback to the cloud that the operation was succesful
        elif value == "false":
            camera.stop_recording()
            IOT.send("false", RecordId)                #provide feedback to the cloud that the operation was succesful
        else:
            print("unknown value: " + value)
    else:
        print("unknown actuator: " + id)

def setupCloud():
    IOT.on_message = on_message
    #make certain that the device & it's features are defined in the cloudapp
    IOT.connect()
    if hasLISIPAROI:
        IOT.addAsset(LISIPAROIPin, "LISIPAROI", "Control the light on the camera", False, "boolean")
    IOT.addAsset(PreviewId, "Preview", "Show/close a preview on the monitor that is connected to the RPI", True, "boolean")
    IOT.addAsset(RecordId, "Record", "Start/stop recording the video stream on sd-card", True, "boolean")
    IOT.subscribe()              							#starts the bi-directional communication

tryLoadConfig()
setupCloud()
if hasLISIPAROI:
    #setup GPIO using Board numbering
    #alternative:  GPIO.setmode(GPIO.BCM)
    GPIO.setmode(GPIO.BOARD)
    #set up the pins
    GPIO.setup(LISIPAROIPin, GPIO.OUT)


#main loop: run as long as the device is turned on
while True:
    #main thread doesn't have to do much, all is handled on the thread calling the message handler (for the actuators)
    sleep(5)
