import cv2
from flask import Response, Flask, render_template, request, send_file
import state
import os
from flask_socketio import SocketIO, emit


class Buffer: 
    outputFrame = b""

    def update(self, img):
        self.outputFrame = cv2.imencode(".jpg", img)[1].tobytes()

    def output(self):
        while True:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + self.outputFrame + b"\r\n"
            )


app = Flask(__name__, static_folder="./walleye/build", static_url_path="/")
socketio = SocketIO(app, logger=True, cors_allowed_origins="*")

camBuffers = [Buffer() for i in range(len(state.cameraIDs))]


def updateAfter(action):
    def actionAndUpdate(*args, **kwargs):
        action(*args, **kwargs)
        sendStateUpdate()

    return actionAndUpdate


@socketio.on_error_default 
def default_error_handler(e):
    print(e)
    socketio.emit("error", "An error occured: " + str(e))

@socketio.on("connect")
@updateAfter
def connect():
    print("Client connected")


@socketio.on("disconnect")
def disconnect():
    print("Client disconnected")


@socketio.on("set_gain")
@updateAfter
def set_gain(camID, newValue):
    state.gain[int(camID)] = float(newValue)
    state.camNum = int(camID)


@socketio.on("set_exposure")
@updateAfter
def set_exposure(camID, newValue):
    state.exposure[int(camID)] = float(newValue)
    state.camNum = int(camID)


@socketio.on("set_resolution")
@updateAfter
def set_resolution(camID, newValue):
    w, h = map(int, newValue[1:-1].split(','))
    state.resolution[int(camID)] = (w, h)
    state.camNum = int(camID)


@socketio.on("toggle_calibration")
@updateAfter
def toggle_calibration(camID):
    state.camNum = int(camID)
    if state.currentState in (state.States.IDLE, state.States.PROCESSING):
        state.currentState = state.States.BEGIN_CALIBRATION
        state.cameraInCalibration = int(camID)
        state.reprojectionError = None
        state.calFilePath = None

    elif state.currentState == state.States.CALIBRATION_CAPTURE:
        state.currentState = state.States.IDLE


@socketio.on("generate_calibration")
@updateAfter
def generate_calibration(camID):
    state.currentState = state.States.GENERATE_CALIBRATION
    state.cameraInCalibration = int(camID)
    state.camNum = int(camID)


@socketio.on("set_table_name")
@updateAfter
def set_table_name(name):
    state.TABLENAME = name


@socketio.on("set_team_number")
@updateAfter
def set_team_number(number):
    state.TEAMNUMBER = int(number)


@socketio.on("shutdown")
@updateAfter
def shutdown():
    state.currentState = state.States.SHUTDOWN


@socketio.on("toggle_pnp")
@updateAfter
def generate_calibration():
    if state.currentState == state.States.PROCESSING:
        state.currentState = state.States.IDLE
    else:
        state.currentState = state.States.PROCESSING


@socketio.on("disconnect")
@updateAfter
def disconnect():
    print("Client disconnected")


def sendStateUpdate():
    print(f"Sending state update : {state.getState()}")
    socketio.emit("state_update", state.getState())


@app.route("/files/<path:path>")
def files(path):
    return send_file(os.path.join(os.getcwd(), path), as_attachment=True)


@app.route("/video_feed/<int:camID>")
def video_feed(camID):
    return Response(
        camBuffers[camID].output(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/", methods=["GET", "POST"])
def index():
    return app.send_static_file("index.html")
