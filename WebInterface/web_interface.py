import cv2
from flask import Response, Flask, send_from_directory
import os
from flask_socketio import SocketIO
import json
from Calibration.calibration import Calibration
from state import walleyeData, States, Config
import logging
import numpy as np
from WebInterface.image_streams import Buffer, LivePlotBuffer

logger = logging.getLogger(__name__)


app = Flask(__name__, static_folder="./walleye/build", static_url_path="/")
socketio = SocketIO(app, logger=True, cors_allowed_origins="*")

camBuffers = {identifier: Buffer() for identifier in walleyeData.cameras.info.keys()}
visualizationBuffers = {
    identifier: LivePlotBuffer() for identifier in walleyeData.cameras.info.keys()
}


def updateAfter(action):
    def actionAndUpdate(*args, **kwargs):
        action(*args, **kwargs)
        sendStateUpdate()

    return actionAndUpdate


# @socketio.on_error_default
# def default_error_handler(e):
#     logger.critical(e)
#     socketio.emit("error", "An error occured: " + str(e))


@socketio.on("connect")
@updateAfter
def connect():
    logger.info("Client connected")


@socketio.on("disconnect")
def disconnect():
    logger.warning("Client disconnected")


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
    #     socketio.emit("info", f"Resolution set to {newValue}")
    # else:
    #     socketio.emit("info", f"Could not set resolution: {newValue}")


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
        Calibration.calibrationPathByCam(
            camID, walleyeData.cameras.info[camID].resolution
        ),
        "w",
    ) as outFile:
        # Save
        calData = json.loads(file.decode())
        calData["camPath"] = camID
        json.dump(calData, outFile)

        # Load
        calData["K"] = np.asarray(calData["K"])
        calData["dist"] = np.asarray(calData["dist"])
        walleyeData.cameras.setCalibration(camID, calData["K"], calData["dist"])
        walleyeData.cameras.info[camID].calibrationPath = file

    logger.info(f"Calibration sucessfully imported for {camID}")
    socketio.emit("info", "Calibration loaded")


@socketio.on("set_table_name")
@updateAfter
def set_table_name(name):
    walleyeData.makePublisher(walleyeData.teamNumber, name)


@socketio.on("set_team_number")
@updateAfter
def set_team_number(number):
    walleyeData.makePublisher(int(number), walleyeData.tableName)


@socketio.on("set_tag_size")
@updateAfter
def set_tag_size(size):
    walleyeData.setTagSize(float(size))


@socketio.on("set_board_dims")
@updateAfter
def set_board_dims(w, h):
    walleyeData.boardDims = (int(w), int(h))
    walleyeData.setBoardDim(walleyeData.boardDims)
    logger.info(f"Board dimensions set: {(w, h)}")
    socketio.info(f"Board dimentions updated: {(w, h)}")


@socketio.on("set_static_ip")
@updateAfter
def set_static_ip(ip):
    walleyeData.setIP(str(ip))


@socketio.on("reset_networking")
@updateAfter
def reset_networking():
    walleyeData.resetNetworking()


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


@socketio.on("toggle_pose_visualization")
@updateAfter
def toggle_pose_visualization(isVisualizing):
    walleyeData.visualizingPoses = isVisualizing
    socketio.emit("info", f"Pose visualizing: {isVisualizing}")


@socketio.on("pose_update")
def pose_update():
    socketio.sleep(0)
    socketio.emit("pose_update", walleyeData.poses)


@socketio.on("performance_update")
def pose_update():
    socketio.sleep(0)
    socketio.emit("performance_update", walleyeData.loopTime)


def sendStateUpdate():
    logger.debug(f"Sending state update : {walleyeData.getState()}")
    socketio.sleep(0)
    socketio.emit("state_update", walleyeData.getState())


@app.route("/files/<path:path>")
def files(path):
    return send_from_directory(os.getcwd(), path, as_attachment=True)


@app.route("/video_feed/<camID>")
def video_feed(camID):
    if camID not in camBuffers:
        logger.error(f"Bad cam id recieved: {camID}")
        return

    return Response(
        camBuffers[camID].output(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/pose_visualization/<camID>")
def pose_visualization(camID):
    if camID not in camBuffers:
        logger.error(f"Bad cam id recieved: {camID}")
        return

    return Response(
        visualizationBuffers[camID].output(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/", methods=["GET", "POST"])
def index():
    return app.send_static_file("index.html")
