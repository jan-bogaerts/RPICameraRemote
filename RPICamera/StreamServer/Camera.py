import thread
import threading
import io
import socket
import struct

class Camera(object):
    def __init__(self):
        self.clients = []                           # the list of clients currently monitoring this camera feed (a client is a user watching through a webpage)
        self.clientsLock = threading.Lock()         # so multiple threads can add a client to a root camera feed.
        thread.start_new_thread(someFunc, ())       # we need to receive input async, in the background.

    def add_client(self, client):
        'thread save manner for adding a client to the list of open data feeds'
        self.clientsLock.acquire()                  # thread save access to the list.
        try:
            self.clients.append(client)
        finally:
            self.clientsLock.release()

    def remove_client(self, client):
        'thread save manner for removing a client to the list of open data feeds'
        self.clientsLock.acquire()                  # thread save access to the list.
        try:
            self.clients.remove(client)
        finally:
            self.clientsLock.release()


    def _runInputServer(self):
        '''this function is run in a seperate thread and listens on a socket for a single connection
           Each frame that is received is stored in the 'curentFrame' field so that it can be sent out 
           over http by the streamServer.
        '''
        # Start a socket listening for connections on 0.0.0.0:8000 (0.0.0.0 means
        # all interfaces)
        server_socket = socket.socket()
        server_socket.bind(('0.0.0.0', 8000))
        server_socket.listen(0)

        # Accept a single connection and make a file-like object out of it
        connection = server_socket.accept()[0].makefile('rb')
        try:
            while True:
                # Read the length of the image as a 32-bit unsigned int. If the
                # length is zero, quit the loop
                image_len = struct.unpack('<L', connection.read(struct.calcsize('<L')))[0]
                if not image_len:
                    break
                # Construct a stream to hold the image data and read the image
                # data from the connection
                image_stream = io.BytesIO()
                image_stream.write(connection.read(image_len))
                # Rewind the stream and save it as the current frame
                # processing on it
                image_stream.seek(0)
                self.clientsLock.acquire()                  # thread save access to the list.
                try:
                    for client in self.clients:             # let all clients know that there is a new image available.
                        client.set_frame(image_stream)
                finally:
                    self.clientsLock.release()
        finally:
            connection.close()
            server_socket.close()