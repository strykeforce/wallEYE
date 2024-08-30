import sys
import os

# import eventlet
# eventlet.monkey_patch()

import logging
from logging.handlers import RotatingFileHandler
from directory import calibration_image_folder, calibration_path_by_cam, LOG

# Create logger and set settings
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

logger = logging.getLogger(__name__)

logger.info("----------- Starting Up -----------")
# logger.info(f"Running with niceness of {os.nice(-20)}")

from state import walleye_data, States, CALIBRATION_STATES
from processing.pose_processing import PoseProcessor
from processing.tag_processing import TagProcessor
from camera.camera import Cameras
from camera.camera_info import Modes
from calibration.calibration import Calibrator
import time
import numpy as np

# Create and intialize cameras
walleye_data.cameras = Cameras()

from web_interface.web_interface import (
    cam_buffers,
    socketio,
    app,
    # visualization_buffers,
    display_info,
)  # After walleye_data.cameras is set

import threading

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
    # Start the web server
    web_server.start()

    logging.getLogger("socketio").setLevel(logging.ERROR)
    logging.getLogger("socketio.server").setLevel(logging.ERROR)
    logging.getLogger("engineio").setLevel(logging.ERROR)

    logger.info("Web server ready")

    images = {}
    calibrators = {}

    # Create network tables publisher and AprilTag Processor
    tag_processor = TagProcessor()
    pose_estimator = PoseProcessor(tag_processor, walleye_data.tag_size)
    # walleye_data.make_publisher(
    #     walleye_data.team_number, walleye_data.table_name, walleye_data.udp_port)
    walleye_data.current_state = States.PROCESSING

    logger.info("Starting main loop")

    last_loop_time = time.time()

    # Main loop (Runs everything)
    while True:
        # Calculate loop time
        curr_time = time.time()
        walleye_data.loop_time = round(curr_time - last_loop_time, 3)
        last_loop_time = curr_time

        curr_state = walleye_data.current_state

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
            calibrators[walleye_data.camera_in_calibration] = Calibrator(
                walleye_data.cal_delay,
                walleye_data.board_dims,
                walleye_data.camera_in_calibration,
                calibration_image_folder(walleye_data.camera_in_calibration),
                walleye_data.cameras.info[
                    walleye_data.camera_in_calibration
                ].resolution,
                walleye_data.calibration_type,
            )
            walleye_data.current_state = States.CALIBRATION_CAPTURE

        # Take calibration images
        elif curr_state == States.CALIBRATION_CAPTURE:
            # Read in frames
            ret, img = walleye_data.cameras.info[
                walleye_data.camera_in_calibration
            ].cam.read()

            if not ret:
                logger.error(
                    f"Failed to capture image: {walleye_data.camera_in_calibration}"
                )
            else:
                # Process frames with the calibration object created prior
                returned, used, path_saved = calibrators[
                    walleye_data.camera_in_calibration
                ].process_frame(img)

                # If the image is a part of the accepted images save it
                if used:
                    walleye_data.cal_img_paths.append(path_saved)

                # Update web stream
                if walleye_data.should_update_web_stream:
                    cam_buffers[walleye_data.camera_in_calibration].update(returned)

        # Finished Calibration, generate calibration
        elif curr_state == States.GENERATE_CALIBRATION:
            # Get file path for the calibration to be saved
            walleye_data.cameras.info[
                walleye_data.camera_in_calibration
            ].calibration_path = calibration_path_by_cam(
                walleye_data.camera_in_calibration,
                walleye_data.cameras.info[
                    walleye_data.camera_in_calibration
                ].resolution,
            )

            if (
                walleye_data.camera_in_calibration in calibrators
                and calibrators[walleye_data.camera_in_calibration] is not None
            ):
                # Generate a calibration file to the file path
                has_generated = calibrators[
                    walleye_data.camera_in_calibration
                ].generate_calibration(
                    walleye_data.cameras.info[
                        walleye_data.camera_in_calibration
                    ].calibration_path
                )

                if has_generated:
                    # Get reproj error
                    walleye_data.reprojection_error = calibrators[
                        walleye_data.camera_in_calibration
                    ].get_reprojection_error()

                    # Set the cameras calibration, save off the file path, and
                    # go to idle
                    walleye_data.cameras.set_calibration(
                        walleye_data.camera_in_calibration,
                        calibrators[
                            walleye_data.camera_in_calibration
                        ].calibration_data["K"],
                        calibrators[
                            walleye_data.camera_in_calibration
                        ].calibration_data["dist"],
                    )
                    walleye_data.cameras.info[
                        walleye_data.camera_in_calibration
                    ].calibration_path = calibration_path_by_cam(
                        walleye_data.camera_in_calibration,
                        walleye_data.cameras.info[
                            walleye_data.camera_in_calibration
                        ].resolution,
                    )
                    display_info("Calibration successful!")
                else:
                    display_info("Could not generate calibration")
                    walleye_data.cameras.info[
                        walleye_data.camera_in_calibration
                    ].calibration_path = None
            else:
                display_info("Calibrator for current calibration camera is None")
            walleye_data.current_state = States.IDLE
            calibrators[walleye_data.camera_in_calibration] = None

        # AprilTag processing state
        elif curr_state == States.PROCESSING:
            # Set tag size, grab camera frames, and grab image timestamp
            pose_estimator.set_tag_size(walleye_data.tag_size)

            image_time = walleye_data.robot_publisher.get_time()

            connections, images, img_time, walleye_data.cam_read_time = (
                walleye_data.cameras.get_frames_for_processing()
            )
            # list_img_time = list(img_time.values())

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
                curr_mode = walleye_data.cameras.info[identifier].mode
                if curr_mode == Modes.POSE_ESTIMATION:
                    img_pose, img_tags, img_ambig = pose_estimator.get_pose(
                        image,
                        walleye_data.cameras.info[identifier].K,
                        walleye_data.cameras.info[identifier].D,
                        walleye_data.should_update_web_stream,
                        walleye_data.valid_tags,
                    )

                    poses.append(img_pose)
                    tags.append(img_tags)
                    ambig.append(img_ambig)

                elif curr_mode == Modes.TAG_SERVOING:
                    img_ids, img_tag_centers = tag_processor.get_tag_centers(
                        image, walleye_data.valid_tags, walleye_data.should_update_web_stream
                    )
                    tags.append(img_ids)
                    tag_centers.append(img_tag_centers)

                else:
                    pass

            if curr_mode == Modes.POSE_ESTIMATION:
                # Publish camera number, timestamp, poses, tags, ambiguity and increase the update number
                # for i in range(len(poses)):
                #     if poses[i][0].X() < 2000: # TODO what is this doing here?
                walleye_data.robot_publisher.udp_pose_publish(
                    [pose[0] for pose in poses],
                    [pose[1] for pose in poses],
                    ambig,
                    [image_time] * len(poses),
                    tags,
                )  # TODO: is above loop needed?

            # Update video stream for web interface
            if walleye_data.should_update_web_stream:
                for i, (identifier, img) in enumerate(images.items()):
                    cam_buffers[identifier].update(img)
                    if walleye_data.cameras.info[identifier].mode == Modes.POSE_ESTIMATION and i < len(poses):
                        walleye_data.set_web_img_info(identifier, poses[i][0])
                    elif walleye_data.cameras.info[identifier].mode == Modes.TAG_SERVOING:
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
        if walleye_data.current_state != States.PROCESSING:
            for camera_info in walleye_data.cameras.info.values():
                if (
                    camera_info.identifier == walleye_data.camera_in_calibration
                    and walleye_data.current_state in CALIBRATION_STATES
                ):
                    continue

                ret, img = camera_info.cam.read()

                if walleye_data.should_update_web_stream:
                    cam_buffers[camera_info.identifier].update(img)

except Exception as e:
    # Something bad happened
    display_info(f"CRITICAL ERROR: {e}")
    logging.critical(e, exc_info=True)
    logger.info("Shutting down")
    socketio.stop()
    logging.shutdown()
