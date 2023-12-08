import logging
import sys
import time
from logging.handlers import RotatingFileHandler

# Create logger and set settings
LOG_FORMAT = "[%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(funcName)s()]  %(message)s"
logging.basicConfig(
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler("walleye.log", maxBytes=5 * 1024 * 1024, backupCount=5),
    ],
    datefmt="%d-%b-%y %H:%M:%S",
    level=logging.INFO,  # Set to DEBUG for pose printouts
)

logger = logging.getLogger(__name__)
logger.info("----------- Starting Up -----------")

from Calibration.calibration import Calibration
from Camera.camera import Cameras
import threading
from Processing.Processing import Processor
from Camera.camera import Cameras
from state import walleyeData, States, CALIBRATION_STATES

# Create and intialize cameras
walleyeData.cameras = Cameras()

from WebInterface.web_interface import (
    camBuffers,
    socketio,
    app,
    visualizationBuffers,
    displayInfo,
    sendStateUpdate,
)  # After walleyeData.cameras is set

try:
    # Start the web server
    webServer = threading.Thread(
        target=lambda: socketio.run(
            app,
            host="0.0.0.0",
            port=5800,
            debug=True,
            use_reloader=False,
            log_output=False,
        ),
        daemon=True,
    ).start()

    logging.getLogger("socketio").setLevel(logging.ERROR)
    logging.getLogger("socketio.server").setLevel(logging.ERROR)
    logging.getLogger("engineio").setLevel(logging.ERROR)

    logger.info("Web server ready")

    images = {}
    calibrators = {}

    # Create network tables publisher and AprilTag Processor
    poseEstimator = Processor(walleyeData.tagSize)
    walleyeData.makePublisher(walleyeData.teamNumber, walleyeData.tableName)
    walleyeData.currentState = States.PROCESSING

    logger.info("Starting main loop")

    lastLoopTime = time.time()

    # Main loop (Runs everything)
    while True:
        # Calculate loop time
        currTime = time.time()
        walleyeData.loopTime = round(currTime - lastLoopTime, 3)
        lastLoopTime = currTime

        # State changes
        # Pre-Calibration
        if walleyeData.currentState == States.BEGIN_CALIBRATION:
            logger.info("Beginning calibration")

            # Prepare a calibration object for the camera that is being calibrated with pre-set data
            # only if cal object does not exist yet
            if (
                walleyeData.cameraInCalibration not in calibrators
                or calibrators[walleyeData.cameraInCalibration] is None
            ):
                calibrators[walleyeData.cameraInCalibration] = Calibration(
                    walleyeData.calDelay,
                    walleyeData.boardDims,
                    walleyeData.cameraInCalibration,
                    f"Calibration/Cam_{Cameras.cleanIdentifier(walleyeData.cameraInCalibration)}CalImgs",
                    walleyeData.cameras.info[
                        walleyeData.cameraInCalibration
                    ].resolution,
                )
            walleyeData.currentState = States.CALIBRATION_CAPTURE

        # Take calibration images
        elif walleyeData.currentState == States.CALIBRATION_CAPTURE:
            # Read in frames
            _, img = walleyeData.cameras.info[
                walleyeData.cameraInCalibration
            ].cam.read()

            # Process frames with the calibration object created prior
            returned, used, pathSaved = calibrators[
                walleyeData.cameraInCalibration
            ].processFrame(img)

            # If the image is a part of the accepted images save it
            if used:
                walleyeData.calImgPaths.append(pathSaved)

            # Keep a buffer with the images
            camBuffers[walleyeData.cameraInCalibration].update(returned)

        # Finished Calibration, generate calibration
        elif walleyeData.currentState == States.GENERATE_CALIBRATION:
            # Get file path for the calibration to be saved
            walleyeData.cameras.info[
                walleyeData.cameraInCalibration
            ].calibrationPath = Calibration.calibrationPathByCam(
                walleyeData.cameraInCalibration,
                walleyeData.cameras.info[walleyeData.cameraInCalibration].resolution,
            )

            if calibrators[walleyeData.cameraInCalibration] is not None:
                # Generate a calibration file to the file path
                hasGenerated = calibrators[
                    walleyeData.cameraInCalibration
                ].generateCalibration(
                    walleyeData.cameras.info[
                        walleyeData.cameraInCalibration
                    ].calibrationPath
                )

                if hasGenerated:
                    # Get reproj error
                    walleyeData.reprojectionError = calibrators[
                        walleyeData.cameraInCalibration
                    ].getReprojectionError()

                    # Set the cameras calibration, save off the file path, and go to idle
                    walleyeData.cameras.setCalibration(
                        walleyeData.cameraInCalibration,
                        calibrators[walleyeData.cameraInCalibration].calibrationData[
                            "K"
                        ],
                        calibrators[walleyeData.cameraInCalibration].calibrationData[
                            "dist"
                        ],
                    )
                    walleyeData.cameras.info[
                        walleyeData.cameraInCalibration
                    ].calibrationPath = Calibration.calibrationPathByCam(
                        walleyeData.cameraInCalibration,
                        walleyeData.cameras.info[
                            walleyeData.cameraInCalibration
                        ].resolution,
                    )
                else:
                    walleyeData.status = "Could not generate calibration"
            else:
                walleyeData.status = "Calibrator for current calibration camera is None"
            walleyeData.currentState = States.IDLE
            calibrators[walleyeData.cameraInCalibration] = None

        # AprilTag processing state
        elif walleyeData.currentState == States.PROCESSING:
            # Set tag size, grab camera frames, and grab image timestamp
            poseEstimator.setTagSize(walleyeData.tagSize)
            connections, images = walleyeData.cameras.getFramesForProcessing()

            for idx, val in enumerate(connections.values()):
                if not val and walleyeData.robotPublisher.getConnectionValue(idx):
                    logger.info("Camera disconnected")
                walleyeData.robotPublisher.setConnectionValue(idx, val)

            imageTime = walleyeData.robotPublisher.getTime()

            # Use the poseEstimator class to find the pose, tags, and ambiguity
            poses, tags, ambig = poseEstimator.getPose(
                images.values(),
                walleyeData.cameras.listK(),
                walleyeData.cameras.listD(),
            )

            # Publish camera number, timestamp, poses, tags, ambiguity and increase the update number
            # logger.info(f"Poses at {imageTime}: {poses}")

            for i in range(len(poses)):
                if poses[i].X() < 2000:
                    walleyeData.robotPublisher.publish(
                        i, imageTime, poses[i], tags[i], ambig[i]
                    )

            # Update the pose visualization
            for i, (identifier, img) in enumerate(images.items()):
                if i >= len(poses):
                    break
                camBuffers[identifier].update(img)
                walleyeData.setPose(identifier, poses[i])
                if walleyeData.visualizingPoses:
                    visualizationBuffers[identifier].update(
                        (poses[i].X(), poses[i].Y(), poses[i].Z()), tags[i][1:]
                    )

        # Ends the WallEye program through the web interface
        elif walleyeData.currentState == States.SHUTDOWN:
            logger.info("Shutting down")
            logging.shutdown()
            socketio.stop()
            break

        # Update cameras no matter what state
        if walleyeData.currentState != States.PROCESSING:
            for cameraInfo in walleyeData.cameras.info.values():
                if (
                    cameraInfo.identifier == walleyeData.cameraInCalibration
                    and walleyeData.currentState in CALIBRATION_STATES
                ):
                    continue

                _, img = cameraInfo.cam.read()

                camBuffers[cameraInfo.identifier].update(img)

except Exception as e:
    # Something bad happened
    logging.critical(e, exc_info=True)
    logger.info("Shutting down")
    logging.shutdown()
    socketio.stop()
