import threading

class CameraClient(object):
    'represents a single user watching a camera feed through the website (multiple users can watch the same feed)'
    def __init__(self):
        self.currentFrame = None
        self.lock = threading.Event()
        self.lock.set()                                         # we set the lock as signaled for the initial state, this will result in the getter, initially returning with a None and then wait until a value comes in.

    def set_frame(self, newFrame):
        'assign a new frame to this client. When set, the getter will be signaled that a new value is present.'
        self.currentFrame = newFrame
        self.lock.set()

    def get_NextFrame(self):
        'for every call, returns with the next image/frame to show'
        self.lock.wait()                                        # wait until a new picture is available
        result = self.currentFrame
        self.lock.clear()
        return result
