import sys

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

from state import walleye_data, States, CALIBRATION_STATES
from processing.processing import Processor
from camera.camera import Cameras
from calibration.calibration import Calibration
import time


# Create and intialize cameras
walleye_data.cameras = Cameras()

from web_interface.web_interface import (
    cam_buffers,
    socketio,
    app,
    visualization_buffers,
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
    pose_estimator = Processor(walleye_data.tag_size)
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

        # State changes
        # Pre-Calibration
        if walleye_data.current_state == States.BEGIN_CALIBRATION:
            logger.info("Beginning calibration")

            # Prepare a calibration object for the camera that is being calibrated with pre-set data
            # only if cal object does not exist yet
            if (
                walleye_data.camera_in_calibration not in calibrators
                or calibrators[walleye_data.camera_in_calibration] is None
            ):
                calibrators[walleye_data.camera_in_calibration] = Calibration(
                    walleye_data.cal_delay,
                    walleye_data.board_dims,
                    walleye_data.camera_in_calibration,
                    calibration_image_folder(
                        walleye_data.camera_in_calibration),
                    walleye_data.cameras.info[
                        walleye_data.camera_in_calibration
                    ].resolution,
                )
            walleye_data.current_state = States.CALIBRATION_CAPTURE

        # Take calibration images
        elif walleye_data.current_state == States.CALIBRATION_CAPTURE:
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

                # Keep a buffer with the images
                cam_buffers[walleye_data.camera_in_calibration].update(
                    returned)

        # Finished Calibration, generate calibration
        elif walleye_data.current_state == States.GENERATE_CALIBRATION:
            # Get file path for the calibration to be saved
            walleye_data.cameras.info[
                walleye_data.camera_in_calibration
            ].calibration_path = calibration_path_by_cam(
                walleye_data.camera_in_calibration,
                walleye_data.cameras.info[
                    walleye_data.camera_in_calibration
                ].resolution,
            )

            if calibrators[walleye_data.camera_in_calibration] is not None:
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
                else:
                    walleye_data.status = "Could not generate calibration"
            else:
                walleye_data.status = (
                    "Calibrator for current calibration camera is None"
                )
            walleye_data.current_state = States.IDLE
            calibrators[walleye_data.camera_in_calibration] = None

        # AprilTag processing state
        elif walleye_data.current_state == States.PROCESSING:
            # Set tag size, grab camera frames, and grab image timestamp
            pose_estimator.set_tag_size(walleye_data.tag_size)

            image_time = walleye_data.robot_publisher.get_time()

            connections, images, img_time = (
                walleye_data.cameras.get_frames_for_processing()
            )
            list_img_time = [i for i in img_time.values()] 

            for idx, val in enumerate(connections.values()):
                if not val and walleye_data.robot_publisher.getConnectionValue(idx):
                    logger.info("Camera disconnected")

                walleye_data.robot_publisher.setConnectionValue(idx, val)

            # Use the pose_estimator class to find the pose, tags, and ambiguity
            poses, tags, ambig = pose_estimator.get_pose(
                images.values(),
                walleye_data.cameras.list_k(),
                walleye_data.cameras.list_d(),
            )

            # Publish camera number, timestamp, poses, tags, ambiguity and increase the update number
            # logger.info(f"Poses at {image_time}: {poses}")

            for i in range(len(poses)):
                if poses[i][0].X() < 2000:
                    walleye_data.robot_publisher.udp_pose_publish([pose[0] for pose in poses], [
                                                           pose[1] for pose in poses], ambig, [image_time for pose in poses], tags)
                    # walleyeData.robotPublisher.publish(
                    #     i, imageTime, poses[i], tags[i], ambig[i]
                    # )

            # Update video stream for web interface
            for i, (identifier, img) in enumerate(images.items()):
                if i >= len(poses):
                    break
                cam_buffers[identifier].update(img)
                walleye_data.set_pose(identifier, poses[i][0])
                if walleye_data.visualizing_poses:
                    visualization_buffers[identifier].update(
                        (poses[i][0].X(), poses[i][0].Y(),
                         poses[i][0].Z()), tags[i][1:]
                    )

        # Ends the WallEye program through the web interface
        elif walleye_data.current_state == States.SHUTDOWN:
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

                cam_buffers[camera_info.identifier].update(img)

except Exception as e:
    # Something bad happened
    logging.critical(e, exc_info=True)
    logger.info("Shutting down")
    socketio.stop()
    logging.shutdown()
