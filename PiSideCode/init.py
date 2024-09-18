import sys

import eventlet

import logging
from logging.handlers import RotatingFileHandler
from directory import calibration_image_folder, calibration_path_by_cam, LOG

# Create and configure logger
LOG_FORMAT = "[%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(funcName)s()]  %(message)s"
logging.basicConfig(
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(LOG, maxBytes=1024 * 1024, backupCount=5),
    ],
    datefmt="%d-%b-%y %H:%M:%S",
    level=logging.INFO,
)

logging.getLogger("socketio").setLevel(logging.ERROR)
logging.getLogger("socketio.server").setLevel(logging.ERROR)
logging.getLogger("engineio").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)
logger.info("----------- Starting Up -----------")
# logger.info   (f"Running with niceness of {os.nice(-20)}")

from state import walleye_data, States, CALIBRATION_STATES
from processing.pose_processing import PoseProcessor
from processing.tag_processing import TagProcessor
from camera.camera import Cameras
from camera.camera_info import Modes
from calibration.calibration import Calibrator
import time

# Create and intialize cameras, save to local var
cameras = walleye_data.cameras = Cameras()
camera_infos = walleye_data.cameras.info

for i in camera_infos:
    if i not in walleye_data.cam_nicknames:
        walleye_data.cam_nicknames[i] = i

# Initialize web interface after walleye_data.cameras is set
from web_interface.web_interface import (
    cam_buffers,
    socketio,
    app,
    # visualization_buffers,
    display_info,
)

import threading
# import gc
# gc.disable()

def log_performance(walleye_data):
    """Logs loop time and individual camera read times every 30 seconds"""
    while True:
        logger.info(
            f"Loop time: {walleye_data.loop_time} | Cam delay: {walleye_data.cam_read_delay}"
        )
        eventlet.sleep(30)


# Initialize threads for performance logging and web interface
performence_logging = threading.Thread(
    target=log_performance, args=(walleye_data,), daemon=True
)
web_server = threading.Thread(
    target=lambda: socketio.run(
        app,
        host="0.0.0.0",
        port=5800,
        debug=False,
        use_reloader=False,
        log_output=False,
    ),
    daemon=True,
)


try:
    # Start threads
    web_server.start()
    performence_logging.start()

    logger.info("Web server ready")

    images = {}
    calibrators = {}
    tag_processor = TagProcessor()
    pose_estimator = PoseProcessor(tag_processor, walleye_data.tag_size)
    # walleye_data.make_publisher(
    #     walleye_data.team_number, walleye_data.table_name, walleye_data.udp_port)
    walleye_data.current_state = States.PROCESSING  # Default state is PROCESSING

    logger.info("Starting main loop")

    # For computing loop time
    last_loop_time = time.perf_counter()

    # Main loop
    while True:
        # Calculate loop time
        curr_time = time.perf_counter()
        walleye_data.loop_time = round(curr_time - last_loop_time, 3)
        last_loop_time = curr_time

        # Use when reading for readability
        curr_state = walleye_data.current_state
        curr_calib_cam = walleye_data.camera_in_calibration

        # State changes
        # Pre-Calibration
        if curr_state == States.BEGIN_CALIBRATION:
            logger.info("Beginning calibration")

            # Prepare a calibration object for the camera that is being calibrated with pre-set data
            # # only if cal object does not exist yet
            # if (
            #     walleye_data.camera_in_calibration not in calibrators
            #     or calibrators[walleye_data.camera_in_calibration] is None
            # ):

            # Initialize calibrator for this camera
            calibrators[curr_calib_cam] = Calibrator(
                walleye_data.cal_delay,
                walleye_data.board_dims,
                curr_calib_cam,
                calibration_image_folder(curr_calib_cam),
                camera_infos[curr_calib_cam].resolution,
                walleye_data.calibration_type,
            )
            walleye_data.current_state = States.CALIBRATION_CAPTURE

        # Take calibration images
        elif curr_state == States.CALIBRATION_CAPTURE:
            # Read in frames

            img = cameras.get_frame(curr_calib_cam) # camera_infos[curr_calib_cam].cam.read()

            if img is None:
                logger.error(f"Failed to capture image: {curr_calib_cam}")
            else:
                # Process frames with the calibration object created prior
                returned, used, path_saved = calibrators[curr_calib_cam].process_frame(
                    img
                )

                # If the image is a part of the accepted images save it
                if used:
                    walleye_data.cal_img_paths.append(path_saved)

                # Update web stream
                if walleye_data.should_update_web_stream:
                    cam_buffers[curr_calib_cam].update(returned)

        # Finished Calibration, generate calibration
        elif curr_state == States.GENERATE_CALIBRATION:
            # Get file path for the calibration to be saved
            camera_infos[curr_calib_cam].calibration_path = calibration_path_by_cam(
                curr_calib_cam,
                camera_infos[curr_calib_cam].resolution,
            )

            if (
                curr_calib_cam in calibrators
                and calibrators[curr_calib_cam] is not None
            ):
                # Generate a calibration file to the file path
                has_generated = calibrators[curr_calib_cam].generate_calibration(
                    camera_infos[curr_calib_cam].calibration_path
                )

                if has_generated:
                    # Get reproj error
                    walleye_data.reprojection_error = calibrators[
                        curr_calib_cam
                    ].get_reprojection_error()

                    # Set the cameras calibration, save off the file path, and
                    # go to idle
                    cameras.set_calibration(
                        curr_calib_cam,
                        calibrators[curr_calib_cam].calibration_data["K"],
                        calibrators[curr_calib_cam].calibration_data["dist"],
                    )
                    camera_infos[curr_calib_cam].calibration_path = (
                        calibration_path_by_cam(
                            curr_calib_cam,
                            camera_infos[curr_calib_cam].resolution,
                        )
                    )
                    display_info("Calibration successful!")
                else:
                    display_info("Could not generate calibration")
                    camera_infos[curr_calib_cam].calibration_path = None
            else:
                display_info("Calibrator for current calibration camera is None")
            walleye_data.current_state = States.IDLE
            calibrators[curr_calib_cam] = None

        # AprilTag processing state
        elif curr_state == States.PROCESSING:
            # Set tag size, grab camera frames, and grab image timestamp
            pose_estimator.set_tag_size(walleye_data.tag_size)

            # image_time = walleye_data.robot_publisher.get_time()

            connections, images, img_time, walleye_data.cam_read_delay = (
                cameras.get_frames_for_processing()
            )

            for idx, val in enumerate(connections.values()):
                if not val and walleye_data.robot_publisher.get_connection_value(idx):
                    logger.info("Camera disconnected")

                walleye_data.robot_publisher.set_connection_value(idx, val)

            # Use the pose_estimator class to find the pose, tags, and ambiguity
            # poses, tags, ambig, tag_centers = pose_estimator.get_pose(
            #     images.values(),
            #     walleye_data.cameras.list_k(),
            #     walleye_data.cameras.list_d(),
            #     np.asarray([i.resolution for i in walleye_data.cameras.info.values()]),
            # )
            poses, tags, ambig, tag_centers = [], [], [], []

            for identifier, image in images.items():
                curr_mode = camera_infos[identifier].mode
                if curr_mode == Modes.POSE_ESTIMATION:
                    img_pose, img_tags, img_ambig = pose_estimator.get_pose(
                        image,
                        camera_infos[identifier].K,
                        camera_infos[identifier].D,
                        walleye_data.should_update_web_stream,
                        walleye_data.valid_tags,
                    )

                    poses.append(img_pose)
                    tags.append(img_tags)
                    ambig.append(img_ambig)

                elif curr_mode == Modes.TAG_SERVOING:
                    img_ids, img_tag_centers = tag_processor.get_tag_centers(
                        image,
                        walleye_data.valid_tags,
                        walleye_data.should_update_web_stream,
                    )
                    tags.append(img_ids)
                    tag_centers.append(img_tag_centers)

                else:
                    pass

            if len(poses) > 0:
                # Publish camera number, timestamp, poses, tags, ambiguity and increase the update number
                # for i in range(len(poses)):
                #     if poses[i][0].X() < 2000: # TODO what is this doing here?
                walleye_data.robot_publisher.udp_pose_publish(
                    [pose[0] for pose in poses],
                    [pose[1] for pose in poses],
                    ambig,
                    # [image_time] * len(poses),
                    list(img_time.values()),
                    tags,
                )  # TODO: is above loop needed?

            # Update video stream for web interface
            if walleye_data.should_update_web_stream:
                for i, (identifier, img) in enumerate(images.items()):
                    if curr_state != States.CALIBRATION_CAPTURE: 
                        cam_buffers[identifier].update(img)
                    if camera_infos[
                        identifier
                    ].mode == Modes.POSE_ESTIMATION and i < len(poses):
                        walleye_data.set_web_img_info(identifier, poses[i][0])
                    elif camera_infos[identifier].mode == Modes.TAG_SERVOING:
                        walleye_data.set_web_img_info(identifier, tag_centers)
                    # if walleye_data.visualizing_poses:
                    #     visualization_buffers[identifier].update(
                    #         (poses[i][0].X(), poses[i][0].Y(), poses[i][0].Z()),
                    #         tags[i][1:],
                    #     )

        # Ends the WallEye program through the web interface
        elif curr_state == States.SHUTDOWN:
            logger.info("Shutting down")
            socketio.stop()
            logging.shutdown()
            break

        # Update cameras no matter what state
        if curr_state != States.PROCESSING:
            for identifier, camera_info in camera_infos.items():
                if identifier == curr_calib_cam and curr_state in CALIBRATION_STATES:
                    continue

                if walleye_data.should_update_web_stream:
                    img = cameras.get_frame(identifier)  # camera_info.cam.read()
                    cam_buffers[identifier].update(img)

except Exception as e:
    # Something bad happened
    display_info(f"CRITICAL ERROR: {e}")
    logging.critical(e, exc_info=True)
    logger.info("Shutting down")
    socketio.stop()
    logging.shutdown()
