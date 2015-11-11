# RPICameraRemote
Provides remote viewing (and control) of a raspberry-pi camera on a web interface.

**supported features:**
 - Turn preview on/off from web interface
 - start/stop recording from web interface. Records to sd-card
 - Supports controlling the [LISIPAROI](http://www.lisiparoi.com/)
 - contains a webserver for streaming videos

**Usage**
- setup:
	- copy the content of RPICamera\RPICamera to the RPI
	- Create an account on [AllThingsTalk's smartliving platform](http://maker.smartliving.io), create an rpi device in your account and copy the credentials to the configuration file on your RPI.
	- start up the RPICameraRemote.py script. The device will connect to the cloud and set up the web interface so you can remotely control it.
	- On the website, in the field 'stream server', fill in the IP address of the system that will run the video streaming server. This lets the RPICamera application know where to stream the video to when 'preview is turned on.
	- Start the webserver: run \StreamServer\StreamServer.py
- Usage:
	- to view video, browse to the IP address where the StreamServer is running (port 5000). 
    Ex, if it's on your local pc, go to http://localhost:5000
	- on the smartliving website, turn preview on.
