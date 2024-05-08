from flask import Response, Flask, send_from_directory
import os
from flask_socketio import SocketIO
import json
from directory import CONFIG_ZIP, calibrationPathByCam
from state import walleyeData, States
import logging
import numpy as np
from web_interface.image_streams import Buffer, LivePlotBuffer
import zipfile
import pathlib
import io

logger = logging.getLogger(__name__)


app = Flask(__name__, static_folder="./walleye/build", static_url_path="/")
socketio = SocketIO(
    app,
    logger=True,
    cors_allowed_origins="*",
    async_mode="gevent",
)

camBuffers = {identifier: Buffer() for identifier in walleyeData.cameras.info.keys()}
visualizationBuffers = {
    identifier: LivePlotBuffer() for identifier in walleyeData.cameras.info.keys()
}


def displayInfo(msg):
    logger.info(f"Sending message to web interface: {msg}")
    walleyeData.status = msg


def update_after(action):
    def action_and_update(*args, **kwargs):
        action(*args, **kwargs)
        send_state_update()
        logger.info(action.__name__)

    return action_and_update


# @socketio.on_error_default
# def default_error_handler(e):
#     logger.critical(e)
#     socketio.emit("error", "An error occured: " + str(e))


@socketio.on("connect")
@update_after
def connect():
    logger.info("Client connected")


@socketio.on("disconnect")
def disconnect():
    logger.warning("Client disconnected")


@socketio.on("set_brightness")
@update_after
def set_brightness(camID, newValue):
    walleyeData.cameras.setBrightness(camID, float(newValue))


@socketio.on("set_exposure")
@update_after
def set_exposure(camID, newValue):
    walleyeData.cameras.setExposure(camID, float(newValue))


@socketio.on("set_resolution")
@update_after
def set_resolution(camID, newValue):
    w, h = map(int, newValue[1:-1].split(","))
    if walleyeData.cameras.setResolution(camID, (w, h)):
        walleyeData.status = f"Resolution set to {newValue}"
    else:
        walleyeData.status = f"Could not set resolution: {newValue}"


@socketio.on("toggle_calibration")
@update_after
def toggle_calibration(camID):
    if walleyeData.currentState in (States.IDLE, States.PROCESSING):
        walleyeData.cameraInCalibration = camID
        walleyeData.reprojectionError = None
        walleyeData.currentState = States.BEGIN_CALIBRATION
        logger.info(f"Starting calibration capture for {camID}")
        walleyeData.status = f"Starting calibration capture for {camID}"

    elif walleyeData.currentState == States.CALIBRATION_CAPTURE:
        walleyeData.currentState = States.IDLE
        logger.info(f"Stopping calibration capture")
        walleyeData.status = f"Stopping calibration capture"


@socketio.on("generate_calibration")
@update_after
def generate_calibration(camID):
    walleyeData.currentState = States.GENERATE_CALIBRATION
    walleyeData.cameraInCalibration = camID
    walleyeData.cameras.info[camID].calibrationPath = None
    walleyeData.status = "Calibration generation"


@socketio.on("import_calibration")
@update_after
def import_calibration(camID, file):
    with open(
        calibrationPathByCam(camID, walleyeData.cameras.info[camID].resolution),
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
        walleyeData.cameras.info[camID].calibrationPath = calibrationPathByCam(
            camID, walleyeData.cameras.info[camID].resolution
        )

    logger.info(f"Calibration sucessfully imported for {camID}")
    walleyeData.status = "Calibration loaded"


@socketio.on("import_config")
@update_after
def import_config(file):
    logger.info("Importing config")
    walleyeData.status = "Importing config"
    with zipfile.ZipFile(io.BytesIO(file), "r") as config:
        for name in config.namelist():
            config.extract(name)
            logger.info(f"Extracted {name}")

        logger.info(f"Connected cams: {list(walleyeData.cameras.info)}")

        for camID in walleyeData.cameras.info.keys():
            walleyeData.cameras.importConfig(camID)
            logger.info(f"Camera config imported for {camID}")

    logger.info(f"Configs sucessfully imported for {camID}")
    walleyeData.status = "Configs/Cals loaded"


@socketio.on("export_config")
@update_after
def export_config():
    logger.info("Attempting to prepare config.zip")
    walleyeData.status = "Attempting to prepare config.zip"
    directory = pathlib.Path(".")

    with zipfile.ZipFile(CONFIG_ZIP, "w") as config:
        logger.info(f"Opening {CONFIG_ZIP} for writing")

        for f in directory.rglob("config_data/*"):
            config.write(f)
            logger.info(f"Zipping {f}")

        config.write(CONFIG_ZIP)
        logger.info(f"Zipping {CONFIG_ZIP}")

    logger.info(f"Config sucessfully zipped")
    walleyeData.status = "Config.zip ready"
    socketio.emit("config_ready")


@socketio.on("set_table_name")
@update_after
def set_table_name(name):
    walleyeData.makePublisher(walleyeData.teamNumber, name)


@socketio.on("set_team_number")
@update_after
def set_team_number(number):
    walleyeData.makePublisher(int(number), walleyeData.tableName)


@socketio.on("set_tag_size")
@update_after
def set_tag_size(size):
    walleyeData.setTagSize(float(size))


@socketio.on("set_board_dims")
@update_after
def set_board_dims(w, h):
    walleyeData.boardDims = (int(w), int(h))
    walleyeData.setBoardDim(walleyeData.boardDims)
    logger.info(f"Board dimensions set: {(w, h)}")


@socketio.on("set_static_ip")
@update_after
def set_static_ip(ip):
    walleyeData.setIP(str(ip))


@socketio.on("shutdown")
def shutdown():
    walleyeData.currentState = States.SHUTDOWN


@socketio.on("toggle_pnp")
@update_after
def toggle_pnp():
    if walleyeData.currentState == States.PROCESSING:
        walleyeData.currentState = States.IDLE
        logger.info("PnP stopped")
    else:
        walleyeData.currentState = States.PROCESSING
        logger.info("PnP started")


@socketio.on("toggle_pose_visualization")
@update_after
def toggle_pose_visualization():
    walleyeData.visualizingPoses = not walleyeData.visualizingPoses
    walleyeData.status = (
        "Visualizing poses"
        if walleyeData.visualizingPoses
        else "Not visualizating poses"
    )


@socketio.on("pose_update")
def pose_update():
    socketio.sleep(0)
    socketio.emit("pose_update", walleyeData.poses)


@socketio.on("performance_update")
def performance_update():
    socketio.sleep(0)
    socketio.emit("performance_update", walleyeData.loopTime)


@socketio.on("msg_update")
def msg_update():
    socketio.sleep(0)
    socketio.emit("msg_update", walleyeData.status)


def send_state_update():
    # logger.info(f"Sending state update : {walleyeData.getState()}")
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
