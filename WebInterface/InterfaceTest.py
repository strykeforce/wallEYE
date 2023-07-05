import cv2
from flask import Response, Flask, send_file
import os
from flask_socketio import SocketIO, emit
import json
from Calibration.calibration import Calibration
from state import walleyeData, States
import logging

logger = logging.getLogger(__name__)

class Buffer:
    outputFrame = b""

    def update(self, img):
        if img is None:
            logger.error("Updated image is None - Skipping")
            return

        self.outputFrame = cv2.imencode(".jpg", img)[1].tobytes()

    def output(self):
        while True:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + self.outputFrame + b"\r\n"
            )


app = Flask(__name__, static_folder="./walleye/build", static_url_path="/")
socketio = SocketIO(app, logger=True, cors_allowed_origins="*")

camBuffers = {identifier: Buffer() for identifier in walleyeData.cameras.info.keys()}


def updateAfter(action):
    def actionAndUpdate(*args, **kwargs):
        action(*args, **kwargs)
        sendStateUpdate()

    return actionAndUpdate

# Commented out for easier debugging
# @socketio.on_error_default
# def default_error_handler(e):
#     print(e)
#     socketio.emit("error", "An error occured: " + str(e))


@socketio.on("connect")
@updateAfter
def connect(test=None):
    logger.info("Client connected", test)


@socketio.on("disconnect")
def disconnect():
    logger.info("Client disconnected")


@socketio.on("set_gain")
@updateAfter
def set_gain(camID, newValue):
    walleyeData.cameras.setGain(camID, float(newValue))


@socketio.on("set_exposure")
@updateAfter
def set_exposure(camID, newValue):
    walleyeData.cameras.setExposure(camID, float(newValue))


@socketio.on("set_resolution")
@updateAfter
def set_resolution(camID, newValue):
    w, h = map(int, newValue[1:-1].split(","))
    walleyeData.cameras.setResolution(camID, (w, h))


@socketio.on("toggle_calibration")
@updateAfter
def toggle_calibration(camID):
    if walleyeData.currentState in (States.IDLE, States.PROCESSING):
        walleyeData.cameraInCalibration = camID
        walleyeData.reprojectionError = None
        walleyeData.currentState = States.BEGIN_CALIBRATION
        logger.info(f"Starting calibration capture for {camID}")
        

    elif walleyeData.currentState == States.CALIBRATION_CAPTURE:
        walleyeData.currentState = States.IDLE
        logger.info(f"Stopping calibration capture")


@socketio.on("generate_calibration")
@updateAfter
def generate_calibration(camID):
    walleyeData.currentState = States.GENERATE_CALIBRATION
    walleyeData.cameraInCalibration = camID


@socketio.on("import_calibration")
@updateAfter
def import_calibration(camID, file):
    with open(
        Calibration.calibrationPathByCam(camID),
        "w",
    ) as outFile:
        # Save
        calData = json.loads(file.decode())
        calData["camPath"] = camID
        json.dump(calData, outFile)

        # Load
        walleyeData.cameras.setCalibration(camID, calData["K"], calData["dist"])

    logger.info(f"Calibration sucessfully imported for {camID}")


@socketio.on("set_table_name")
@updateAfter
def set_table_name(name):
    walleyeData.makePublisher(walleyeData.teamNumber, name)


@socketio.on("set_team_number")
@updateAfter
def set_team_number(number):
    walleyeData.makePublisher(int(number), walleyeData.tableName)


@socketio.on("set_board_dims")
@updateAfter
def set_team_number(w, h):
    walleyeData.boardDims = (int(w), int(h))
    logger.info("Board dimensions set: {(w, h)}")


@socketio.on("shutdown")
@updateAfter
def shutdown():
    walleyeData.currentState = States.SHUTDOWN


@socketio.on("toggle_pnp")
@updateAfter
def toggle_pnp():
    if walleyeData.currentState == States.PROCESSING:
        walleyeData.currentState = States.IDLE
        logger.info("PnP stopped")
    else:
        walleyeData.currentState = States.PROCESSING
        logger.info("PnP started")


@socketio.on("disconnect")
@updateAfter
def disconnect():
    logger.info("Client disconnected")

def sendStateUpdate():
    logger.debug(f"Sending state update : {walleyeData.getState()}")
    socketio.emit("state_update", walleyeData.getState())


@app.route("/files/<path:path>")
def files(path):
    return send_file(os.path.join(os.getcwd(), path), as_attachment=True)


@app.route("/video_feed/<camID>")
def video_feed(camID):
    if camID not in camBuffers:
        logger.error(f"Bad cam id recieved: {camID}")
        return
     
    return Response(
        camBuffers[camID].output(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/", methods=["GET", "POST"])
def index():
    return app.send_static_file("index.html")
