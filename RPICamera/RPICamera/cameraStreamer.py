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
                        self._cameraStreamer._connection.write(self.stream.read())
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
        self._cameraStreamer._pool = [OutputStreamer() for i in range(4)]
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

    def start_preview(self):
        'start sending data to the cloud'
        self._isRunning = True
        self._InputStreamer = InputStreamer(self)

    def stop_preview(self):
        'stop sending data to the cloud'
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
        self.client_socket = socket.socket()
        self.client_socket.connect(('spider', 8000))
        self.connection = client_socket.makefile('wb')

    def _disconnect(self):
        self.connection.close()
        self.client_socket.close()

    def streams(self):
        while self._isRunning:
            with self.pool_lock:
                if self.pool:
                    streamer = self.pool.pop()
                else:
                    streamer = None
            if streamer:
                yield streamer.stream
                streamer.event.set()
            else:
                # When the pool is starved, wait a while for it to refill
                time.sleep(0.1)
