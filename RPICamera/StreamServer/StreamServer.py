#!/usr/bin/env python
from flask import Flask, render_template, Response
from camera import Camera
from cameraClient import CameraClient

app = Flask(__name__)
dataFeed = None

@app.route('/')
def index():
    return render_template('index.html')

def gen(camera):
    #try:
    #finally:
    #    print('removing client')
    #    dataFeed.remove_client(camera)
    print(dataFeed.clients)
    while True:
        frame = camera.get_frame()
        if not frame:
            frame = open('templates/noCamera.jpg', 'rb').read()
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    global dataFeed
    if not dataFeed:                                            # we have to create it during the call, otherwise the list that syncs between threads (cients) doesn't get synced correctly between threads (bummer).
        dataFeed = Camera()
    client = CameraClient()
    dataFeed.add_client(client)
    return Response(gen(client),                  # all video streams use the same camera object -> the same input stream.
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)