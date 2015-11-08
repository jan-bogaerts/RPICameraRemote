#!/usr/bin/env python
# -*- coding: utf-8 -*-

#important: before running this demo, make certain that you import the library
#'paho.mqtt.client' into python (https://pypi.python.org/pypi/paho-mqtt)
#also make certain that ATT_IOT is in the same directory as this script.

import traceback                                                                                                    # for logging exceptions
import logging
logging.getLogger().setLevel(logging.INFO)                                                                          #before doing anything else, set the desired logging level, so all modules log correctly.

from ConfigParser import *

import RPi.GPIO as GPIO                            #provides pin support
import ATT_IOT as IOT                              #provide cloud support
from time import sleep                             #pause the app
import picamera
import cameraStreamer
import sys

ConfigName = 'rpicamera.config'
hasLISIPAROI = False
LISIPAROIPin = 0
streamer = None
camera = None

PreviewId = 1                                       # turn on/off preview on the stream server
RecordId = 2                                        # turn on/off recording on disk
StreamServerId = 3                                  # assign the destination to stream the video to.
ToggleLISIPAROIId = 4

def tryLoadConfig():
    'load the config from file'
    global hasLISIPAROI, LISIPAROIPin
    c = ConfigParser()
    if c.read(ConfigName):
        #set up the ATT internet of things platform
        IOT.DeviceId = c.get('cloud', 'deviceId')
        IOT.ClientId = c.get('cloud', 'clientId')
        IOT.ClientKey = c.get('cloud', 'clientKey')
        hasLISIPAROI = bool(c.get('camera', 'has LISIPAROI'))
        logging.info("has LISIPAROI:" + str(hasLISIPAROI) )
        if hasLISIPAROI:
            LISIPAROIPin = int(c.get('camera', 'LISIPAROI pin'))
            logging.info("LISIPAROI pin:" + str(LISIPAROIPin) )
        return True
    else:
        return False

def setupCamera():
    'create the camera responsible for recording video and streaming object responsible for sending it to the server.'
    global streamer, camera
    camera = picamera.PiCamera()
    camera.resolution = (640, 480)
    camera.framerate = 30
    streamer = cameraStreamer.CameraStreamer(camera)

def setBacklight(value):
    '''turn on/off the backlight
       value: string ('true' or 'false')
       returns: true when input was succesfully processed, otherwise false
    '''
    if value == "true":
        GPIO.output(LISIPAROIPin, GPIO.HIGH)
    elif value == "false":
        GPIO.output(LISIPAROIPin, GPIO.LOW)
    else:
        print("unknown value: " + value)
        return False
    return True

def setPreview(value):
    if value == "true":
        streamer.start_preview()
    elif value == "false":
        streamer.stop_preview()
    else:
        print("unknown value: " + value)
        return False
    return True

def setRecord(value):
    if value == "true":
        camera.start_recording('video.h264')
    elif value == "false":
        camera.stop_recording()
    else:
        print("unknown value: " + value)
        return False
    return True

#callback: handles values sent from the cloudapp to the device
def on_message(id, value):
    if id.endswith(str(ToggleLISIPAROIId)) == True:
        value = value.lower()                        #make certain that the value is in lower case, for 'True' vs 'true'
        if setBacklight(value):
            IOT.send(value, ToggleLISIPAROIId)                #provide feedback to the cloud that the operation was succesful
    elif id.endswith(str(PreviewId)) == True:
        value = value.lower()                        #make certain that the value is in lower case, for 'True' vs 'true'
        if setPreview(value):
            IOT.send(value, PreviewId)                #provide feedback to the cloud that the operation was succesful
    elif id.endswith(str(RecordId)) == True:
        value = value.lower()                        #make certain that the value is in lower case, for 'True' vs 'true'
        if setRecord(value):
            IOT.send(value, RecordId)                #provide feedback to the cloud that the operation was succesful
    elif id.endswith(str(StreamServerId)) == True:
        streamer.streamServerIp = value
        IOT.send(value, StreamServerId)                #provide feedback to the cloud that the operation was succesful
    else:
        print("unknown actuator: " + id)

def setupCloud():
    IOT.on_message = on_message
    #make certain that the device & it's features are defined in the cloudapp
    IOT.connect()
    if hasLISIPAROI:
        IOT.addAsset(ToggleLISIPAROIId, "LISIPAROI", "Control the light on the camera", False, "boolean")
    IOT.addAsset(PreviewId, "Preview", "Show/close a preview on the monitor that is connected to the RPI", True, "boolean")
    IOT.addAsset(RecordId, "Record", "Start/stop recording the video stream on sd-card", True, "boolean")
    IOT.addAsset(StreamServerId, "Stream server", "set the ip address of the server that manages the video", True, "string")

    # get any previously defined settings
    streamer.streamServerIp = IOT.getAssetState(StreamServerId)
    if streamer.streamServerIp:
        streamer.streamServerIp = streamer.streamServerIp['state']['value']
        logging.info("sending stream to: " + streamer.streamServerIp)
    else:
        logging.info("no stream endpoint defined")

    IOT.subscribe()              							#starts the bi-directional communication
    # set current state of the device
    IOT.send("false", ToggleLISIPAROIId)
    IOT.send("false", PreviewId)
    IOT.send("false", RecordId)


tryLoadConfig()
setupCamera()                   # needs to be done before setting up the cloud, cause we will get the settings from the cloud and assign them to the camera.
setupCloud()
if hasLISIPAROI:
    try:
        #setup GPIO using Board numbering
        GPIO.setmode(GPIO.BCM)
        #GPIO.setmode(GPIO.BOARD)
        #set up the pins
        GPIO.setup(LISIPAROIPin, GPIO.OUT)
    except:
        logging.error(traceback.format_exc())

#main loop: run as long as the device is turned on
while True:
    #main thread doesn't have to do much, all is handled on the thread calling the message handler (for the actuators)
    sleep(5)
