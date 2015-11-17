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
import datetime                                     # for generating a unique file name

ConfigName = 'rpicamera.config'
hasLISIPAROI = False
LISIPAROIPin = 4
streamer = None
camera = None

PreviewId = 1                                       # turn on/off preview on the stream server
RecordId = 2                                        # turn on/off recording on disk
StreamServerId = 3                                  # assign the destination to stream the video to.
ToggleLISIPAROIId = 4
PictureId = 5

_isPreview = False
_isRecording = False

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
    IOT.send(value, ToggleLISIPAROIId)                #provide feedback to the cloud that the operation was succesful


def setPreview(value):
    if _isRecording:
        print("recording not allowed during preview, shutting down recording.")
        setRecord(False)
    if value == "true":
        _isPreview = True
        streamer.start_preview()
    elif value == "false":
        _isPreview = False
        streamer.stop_preview()
    else:
        print("unknown value: " + value)
    IOT.send(value, PreviewId)                #provide feedback to the cloud that the operation was succesful

def setRecord(value):
    if _isPreview: 
        print("preview not allowed during recording, shutting down preview.")
        setPreview(False)
    if value == "true":
        camera.resolution = (1920, 1080)              #set to max resulotion for record
        camera.start_recording('video' + datetime.date.today().strftime("%d_%b_%Y_%H_%M%_S") + '.h264')
    elif value == "false":
        camera.stop_recording()
        camera.resolution = (640, 480)              #reset resulotion for preview
    else:
        print("unknown value: " + value)
    IOT.send(value, RecordId)                #provide feedback to the cloud that the operation was succesful

def takePicture():
    'take a single picture, max resoution'
    prevWasPreview = _isPreview
    prevWasRecording = _isRecording
    if _isRecording:
        print("record not allowed while taking picture.")
        setRecord(False)
    if not _isPreview: 
        print("preview required for taking picture.")
        setPreview(True)
        sleep(2)                                # if preview was not running yet, give it some time to startup
    
    camera.capture('picture' + datetime.date.today().strftime("%d_%b_%Y_%H_%M%_S") + '.jpg')

    if prevWasPreview:
        print("reactivating preview.")
        setPreview(True)
    elif prevWasRecording:
        print("reactivating record.")
        setRecord(True)

#callback: handles values sent from the cloudapp to the device
def on_message(id, value):
    if id.endswith(str(ToggleLISIPAROIId)) == True:
        value = value.lower()                        #make certain that the value is in lower case, for 'True' vs 'true'
        setBacklight(value)
    elif id.endswith(str(PreviewId)) == True:
        value = value.lower()                        #make certain that the value is in lower case, for 'True' vs 'true'
        setPreview(value)
    elif id.endswith(str(RecordId)) == True:
        value = value.lower()                        #make certain that the value is in lower case, for 'True' vs 'true'
        setRecord(value)
    elif id.endswith(str(StreamServerId)) == True:
        streamer.streamServerIp = value
        IOT.send(value, StreamServerId)                #provide feedback to the cloud that the operation was succesful
    elif id.endswith(str(PictureId)) == True:
        if value.lower() == "true":
            takePicture()
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
    IOT.addAsset(PictureId, "Picture", "take a picture (max resoution) and store on sd-card", True, "boolean")
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
        #GPIO.setmode(GPIO.BCM)
        GPIO.setmode(GPIO.BOARD)
        #set up the pins
        GPIO.setup(LISIPAROIPin, GPIO.OUT)
    except:
        logging.error(traceback.format_exc())

#main loop: run as long as the device is turned on
while True:
    #main thread doesn't have to do much, all is handled on the thread calling the message handler (for the actuators)
    sleep(5)
