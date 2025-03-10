from flask import Response, Flask, send_from_directory
import os
from flask_socketio import SocketIO
import json
from directory import (
    CONFIG_ZIP,
    calibration_path_by_cam,
    cam_config_path,
    CONFIG_DIRECTORY,
    CONFIG_DATA_PATH,
    TAG_LAYOUT_PATH
)
from state import walleye_data, States
import logging
import numpy as np
from web_interface.image_streams import Buffer
import zipfile
import pathlib
import io
import glob
from calibration.calibration import CalibType
from camera.camera_info import Modes

logger = logging.getLogger(__name__)


app = Flask(__name__, static_folder="./walleye/build", static_url_path="/")
socketio = SocketIO(
    app,
    logger=False,
    cors_allowed_origins="*",
    async_mode="eventlet",
)

cam_buffers = {identifier: Buffer() for identifier in walleye_data.cameras.info.keys()}
# visualization_buffers = {
#     identifier: LivePlotBuffer() for identifier in walleye_data.cameras.info.keys()
# }


# def iter_over_async(ait, loop):
#     ait = ait.__aiter__()

#     async def get_next():
#         try:
#             obj = await ait.__anext__()
#             return False, obj
#         except StopAsyncIteration:
#             return True, None

#     while True:
#         done, obj = loop.run_until_complete(get_next())
#         if done:
#             break
#         yield obj


def display_info(msg: str):
    walleye_data.status = msg

    socketio.emit("msg_update", walleye_data.status)
    socketio.sleep(0)


def update_after(action):
    def action_and_update(*args, **kwargs):
        action(*args, **kwargs)
        send_state_update()
        # logger.info(action.__name__)

    return action_and_update


# @socketio.on_error_default
# def default_error_handler(e):
#     logger.critical(e)
#     socketio.emit("error", "An error occured: " + str(e))


@socketio.on("connect")
@update_after
def connect():
    logger.info("Client connected")
    walleye_data.should_update_web_stream = True


@socketio.on("disconnect")
def disconnect():
    logger.warning("Client disconnected")
    walleye_data.should_update_web_stream = False


@socketio.on("set")
@update_after
def set(property: str, cam_id: str, new_value: float | str):
    camera_info = walleye_data.cameras.info[cam_id]

    if property == "resolution":
        w, h = map(int, new_value[1:-1].split(","))
        camera_info.set_resolution((w, h))
    elif property == "color_format":
        camera_info.set_color_format(new_value.strip('"'))
    elif property == "frame_rate":
        camera_info.set_frame_rate(int(new_value))
    else:
        camera_info.set(property, new_value)

    walleye_data.cameras.write_configs(cam_id)


@socketio.on("toggle_calibration")
@update_after
def toggle_calibration(cam_id: str):
    if walleye_data.current_state in (States.IDLE, States.PROCESSING):
        walleye_data.camera_in_calibration = cam_id
        walleye_data.reprojection_error = None
        walleye_data.current_state = States.BEGIN_CALIBRATION
        logger.info(f"Starting calibration capture for {cam_id}")
        display_info(f"Starting calibration capture for {cam_id}")

    elif walleye_data.current_state == States.CALIBRATION_CAPTURE:
        walleye_data.current_state = States.IDLE
        logger.info(f"Stopping calibration capture")
        display_info(f"Stopping calibration capture")


@socketio.on("generate_calibration")
@update_after
def generate_calibration(cam_id: str):
    walleye_data.current_state = States.GENERATE_CALIBRATION
    walleye_data.camera_in_calibration = cam_id
    walleye_data.cameras.info[cam_id].calibration_path = None
    display_info("Generating calibration parameters")


@socketio.on("import_calibration")
@update_after
def import_calibration(cam_id: str, file):
    with open(
        calibration_path_by_cam(cam_id, walleye_data.cameras.info[cam_id].resolution),
        "w",
    ) as outFile:
        # Save
        cal_data = json.loads(file.decode())
        cal_data["camPath"] = cam_id
        json.dump(cal_data, outFile)

        # Load
        cal_data["K"] = np.asarray(cal_data["K"])
        cal_data["dist"] = np.asarray(cal_data["dist"])
        walleye_data.cameras.set_calibration(cam_id, cal_data["K"], cal_data["dist"])
        walleye_data.cameras.info[cam_id].calibration_path = calibration_path_by_cam(
            cam_id, walleye_data.cameras.info[cam_id].resolution
        )

    logger.info(f"Calibration sucessfully imported for {cam_id}")
    display_info("Calibration loaded")


@socketio.on("import_config")
@update_after
def import_config(file):
    logger.info("Importing config")
    display_info("Importing config")
    with zipfile.ZipFile(io.BytesIO(file), "r") as config:
        for name in config.namelist():
            config.extract(name)
            logger.info(f"Extracted {name}")

        logger.info(f"Connected cams: {list(walleye_data.cameras.info)}")

        for cam_id in walleye_data.cameras.info.keys():
            walleye_data.cameras.import_config(cam_id)
            logger.info(f"Camera config imported for {cam_id}")

    logger.info(f"Configs sucessfully imported for {cam_id}")
    display_info("Configs/Cals loaded")

@socketio.on("import_tag_layout")
@update_after
def import_tag_layout(file):
    logger.info("Importing tag layout")
    display_info("Importing tag layout")
    with open(TAG_LAYOUT_PATH, "w") as f:
        f.write(file.decode("utf-8"))

@socketio.on("export_config")
@update_after
def export_config():
    logger.info("Attempting to prepare config.zip")
    display_info("Attempting to prepare config.zip")
    directory = pathlib.Path(".")

    with zipfile.ZipFile(CONFIG_ZIP, "w") as config:
        logger.info(f"Opening {CONFIG_ZIP} for writing")

        for f in glob.iglob(f"{CONFIG_DIRECTORY}/**/*", recursive=True):
            if f == CONFIG_ZIP:
                continue
            
            logger.info(f"Zipping {f}")
            config.write(f)

        logger.info(f"Zipping {CONFIG_ZIP}")
        config.write(CONFIG_ZIP)

    logger.info(f"Config sucessfully zipped")
    display_info("Config.zip ready")
    socketio.emit("config_ready")
    socketio.sleep(0)


@socketio.on("set_table_name")
@update_after
def set_table_name(name: str):
    walleye_data.make_publisher(walleye_data.team_number, name, walleye_data.udp_port)
    display_info(f"Table Name set: {walleye_data.table_name}")


@socketio.on("set_team_number")
@update_after
def set_team_number(number: int):
    walleye_data.make_publisher(
        int(number), walleye_data.table_name, walleye_data.udp_port
    )
    display_info(f"Team number set: {walleye_data.team_number}")


@socketio.on("set_tag_size")
@update_after
def set_tag_size(size: float):
    walleye_data.set_tag_size(float(size))
    display_info(f"Tag Size set: {walleye_data.tag_size}")


@socketio.on("set_board_dims")
@update_after
def set_board_dims(w: int, h: int):
    walleye_data.board_dims = (int(w), int(h))
    walleye_data.set_board_dim(walleye_data.board_dims)
    logger.info(f"Board dimensions set: {(w, h)}")
    display_info(f"Board dimensions set: {(w, h)}")


@socketio.on("set_calibration_type")
@update_after
def set_calibration_type(cal_type: str):
    if cal_type == "Chessboard":
        walleye_data.calibration_type = CalibType.CHESSBOARD
    elif cal_type == "Circle Grid":
        walleye_data.calibration_type = CalibType.CIRCLE_GRID
    else:
        logger.error(f"Unrecognized calibration type: {cal_type}")

    display_info(f"Calibration type set: {walleye_data.calibration_type}")


@socketio.on("set_udp_port")
@update_after
def set_udp_port(port):
    walleye_data.udp_port = port
    logger.info(f"Attempting to set UDP port to {port}")
    walleye_data.set_udp_port(port)
    display_info(f"UDP Port set: {walleye_data.udp_port}")


@socketio.on("set_static_ip")
@update_after
def set_static_ip(ip: str):
    walleye_data.set_ip(str(ip))


@socketio.on("set_tag_allowed")
@update_after
def set_tag_allowed(tag_id: int, allowed: bool):
    valid = walleye_data.valid_tags.tolist()

    if tag_id in valid and not allowed:
        valid.remove(tag_id)
    elif tag_id not in valid and allowed:
        valid.append(tag_id)

    walleye_data.set_valid_tags(valid)


@socketio.on("set_cam_nickname")
@update_after
def set_cam_nickname(cam_id: str, nickname: str):
    if len(nickname) == 0:
        nickname = cam_id
    
    walleye_data.set_nickname(cam_id, nickname)

    display_info(f"{cam_id} is now named {nickname}")

@socketio.on("set_mode")
@update_after
def set_mode(mode: str, cam_id: str):
    if mode in (
        Modes.POSE_ESTIMATION.value,
        Modes.TAG_SERVOING.value,
        Modes.DISABLED.value,
    ):
        walleye_data.cameras.info[cam_id].mode = Modes(mode)
        walleye_data.cameras.write_configs(cam_id)

        display_info(f"Mode set to {mode} for {cam_id}")

        if mode == Modes.DISABLED.value:
            display_info("Disabled upon next wallEYE boot")


@socketio.on("shutdown")
@update_after
def shutdown():
    walleye_data.current_state = States.SHUTDOWN
    socketio.stop()


@socketio.on("toggle_pnp")
@update_after
def toggle_pnp():
    if walleye_data.current_state == States.PROCESSING:
        walleye_data.current_state = States.IDLE
        logger.info("PnP stopped")
        display_info("PnP Stopped")
    else:
        walleye_data.current_state = States.PROCESSING
        logger.info("PnP started")
        display_info("PnP Started")


@socketio.on("toggle_pose_visualization")
@update_after
def toggle_pose_visualization():
    walleye_data.visualizing_poses = not walleye_data.visualizing_poses
    display_info(
        "Visualizing poses"
        if walleye_data.visualizing_poses
        else "Not visualizating poses"
    )


@socketio.on("img_info_update")
def img_info_update():
    socketio.emit("img_info_update", walleye_data.img_info)
    socketio.sleep(0)


@socketio.on("performance_update")
def performance_update():
    socketio.emit(
        "performance_update",
        {"loopTime": walleye_data.loop_time, "camReadTime": walleye_data.cam_read_delay},
    )
    socketio.sleep(0)


def send_state_update():
    # logger.info(f"Sending state update : {walleye_data.get_state()}")
    socketio.emit("state_update", walleye_data.get_state())
    socketio.sleep(0)


@app.route("/files/<path:path>")
def files(path):
    return send_from_directory(os.getcwd(), path, as_attachment=True)


@app.route("/video_feed/<cam_id>")
def video_feed(cam_id):
    if cam_id not in cam_buffers:
        logger.error(f"Bad cam id recieved: {cam_id}")
        return

    return Response(
        cam_buffers[cam_id].output(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


# @app.route("/pose_visualization/<cam_id>")
# def pose_visualization(cam_id):
#     if cam_id not in cam_buffers:
#         logger.error(f"Bad cam id recieved: {cam_id}")
#         return

#     return Response(
#         visualization_buffers[cam_id].output(),
#         mimetype="multipart/x-mixed-replace; boundary=frame",
#     )


@app.route("/", methods=["GET", "POST"])
def index():
    return app.send_static_file("index.html")
