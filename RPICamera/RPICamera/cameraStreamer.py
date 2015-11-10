
import logging
logging.getLogger().setLevel(logging.INFO)                                                                          #before doing anything else, set the desired logging level, so all modules log correctly.

import io
import socket
import struct
import time
import threading

class OutputStreamer(threading.Thread):
    'thread that writes the images to the output connection'
    def __init__(self, cameraStreamer):
        super(OutputStreamer, self).__init__()
        self._cameraStreamer = cameraStreamer
        self.stream = io.BytesIO()
        self.event = threading.Event()
        self.terminated = False
        self.start()

    def run(self):
        # This method runs in a background thread
        while not self.terminated:
            # Wait for the image to be written to the stream
            if self.event.wait(1):
                try:
                    with self._cameraStreamer._connection_lock:
                        self._cameraStreamer._connection.write(struct.pack('<L', self.stream.tell()))
                        self._cameraStreamer._connection.flush()
                        self.stream.seek(0)
                        print 'start write'
                        self._cameraStreamer._connection.write(self.stream.read())
                        self._cameraStreamer._connection.flush()
                        print 'end write'
                finally:
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()
                    with self._cameraStreamer._pool_lock:
                        self._cameraStreamer._pool.append(self)


class InputStreamer(threading.Thread):
    'thread that reads the images from the camera and stores them in the threads that will send them to the output connections'
    def __init__(self, cameraStreamer):
        super(InputStreamer, self).__init__()
        self._cameraStreamer = cameraStreamer
        self.start()

    def run(self):
        # This method runs in a background thread
        self._cameraStreamer._connect()
        self._cameraStreamer._pool = [OutputStreamer(self._cameraStreamer) for i in range(4)]
        self._cameraStreamer._camera.capture_sequence(self._cameraStreamer.streams(), 'jpeg', use_video_port=True)


class CameraStreamer(object):
    'managment object that reads from the camera and manages the output connections. Provides functionality to start and stop the process'
    def __init__(self, camera):
        'init the object'
        self._camera = camera       # ref to the camera object that should be used.
        self._client_socket = None
        self._connection = None
        self._connection_lock = threading.Lock()
        self._pool = []             # thread pool that will poll
        self._pool_lock = threading.Lock()
        self._InputStreamer = None
        self._isRunning = False     # keep track of wether the camera is running or not
        self.streamServerIp = None                                 # the ip address to send the video to.


    def start_preview(self):
        'start sending data to the cloud'
        if not self.streamServerIp:
            raise Exception("need ip address of server to start preview")
        logging.info("start preview")
        self._isRunning = True
        self._InputStreamer = InputStreamer(self)

    def stop_preview(self):
        'stop sending data to the cloud'
        logging.info("stop preview")
        self._isRunning = False
        # Shut down the streamers in an orderly fashion
        while self._pool:
            streamer = self._pool.pop()
            streamer.join()
        self._InputStreamer.join()

        # Write the terminating 0-length to the connection to let the server
        # know we're done
        with connection_lock:
            connection.write(struct.pack('<L', 0))
        self._disconnect()

    def _connect(self):
        logging.info("connecting to: " + self.streamServerIp)
        self._client_socket = socket.socket()
        self._client_socket.connect((self.streamServerIp, 8000))
        self._connection = self._client_socket.makefile('wb')

    def _disconnect(self):
        self._connection.close()
        self._client_socket.close()

    def streams(self):
        while self._isRunning:
            with self._pool_lock:
                if self._pool:
                    streamer = self._pool.pop()
                else:
                    streamer = None
            if streamer:
                yield streamer.stream
                streamer.event.set()
            else:
                # When the pool is starved, wait a while for it to refill
                time.sleep(0.1)
