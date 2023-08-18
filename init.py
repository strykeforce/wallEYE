import logging
import sys
import time

LOG_FORMAT = "[%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(funcName)s()]  %(message)s"
logging.basicConfig(
    format=LOG_FORMAT,
    handlers=[logging.FileHandler("walleye.log"), logging.StreamHandler(sys.stdout)],
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

walleyeData.cameras = Cameras()

from WebInterface.web_interface import (
    camBuffers,
    socketio,
    app,
    visualizationBuffers,
)  # After walleyeData.cameras is set

try:
    webServer = threading.Thread(
        target=lambda: socketio.run(
            app, host="0.0.0.0", debug=True, use_reloader=False, log_output=False
        ),
        daemon=True,
    ).start()

    logging.getLogger("socketio").setLevel(logging.ERROR)
    logging.getLogger("socketio.server").setLevel(logging.ERROR)
    logging.getLogger("engineio").setLevel(logging.ERROR)

    logger.info("Web server ready")

    images = {}
    calibrators = {}

    poseEstimator = Processor(walleyeData.tagSize)
    walleyeData.makePublisher(walleyeData.teamNumber, walleyeData.tableName)
    walleyeData.currentState = States.PROCESSING

    logger.info("Starting main loop")

    lastLoopTime = time.time()
    while True:
        currTime = time.time()
        walleyeData.loopTime = round(currTime - lastLoopTime, 3)
        lastLoopTime = currTime

        # State changes
        if walleyeData.currentState == States.IDLE:
            pass

        elif walleyeData.currentState == States.BEGIN_CALIBRATION:
            logger.info("Beginning calibration")

            calibrators[walleyeData.cameraInCalibration] = Calibration(
                walleyeData.calDelay,
                walleyeData.boardDims,
                walleyeData.cameraInCalibration,
                f"Calibration/Cam_{Cameras.cleanIdentifier(walleyeData.cameraInCalibration)}CalImgs",
                walleyeData.cameras.info[walleyeData.cameraInCalibration].resolution,
            )
            walleyeData.currentState = States.CALIBRATION_CAPTURE

        elif walleyeData.currentState == States.CALIBRATION_CAPTURE:
            _, img = walleyeData.cameras.info[
                walleyeData.cameraInCalibration
            ].cam.read()

            returned, used, pathSaved = calibrators[
                walleyeData.cameraInCalibration
            ].processFrame(img)

            if used:
                walleyeData.calImgPaths.append(pathSaved)

            camBuffers[walleyeData.cameraInCalibration].update(returned)

        elif walleyeData.currentState == States.GENERATE_CALIBRATION:
            walleyeData.cameras.info[
                walleyeData.cameraInCalibration
            ].calibrationPath = Calibration.calibrationPathByCam(
                walleyeData.cameraInCalibration,
                walleyeData.cameras.info[walleyeData.cameraInCalibration].resolution,
            )

            calibrators[walleyeData.cameraInCalibration].generateCalibration(
                walleyeData.cameras.info[
                    walleyeData.cameraInCalibration
                ].calibrationPath
            )

            walleyeData.reprojectionError = calibrators[
                walleyeData.cameraInCalibration
            ].getReprojectionError()

            walleyeData.cameras.setCalibration(
                walleyeData.cameraInCalibration,
                calibrators[walleyeData.cameraInCalibration].calibrationData["K"],
                calibrators[walleyeData.cameraInCalibration].calibrationData["dist"],
            )

            walleyeData.currentState = States.IDLE

        elif walleyeData.currentState == States.PROCESSING:
            poseEstimator.setTagSize(walleyeData.tagSize)
            images = walleyeData.cameras.getFrames()
            imageTime = walleyeData.robotPublisher.getTime()
            poses, tags, ambig = poseEstimator.getPose(
                images.values(), walleyeData.cameras.listK(), walleyeData.cameras.listD()
            )
            logger.debug(f"Poses at {imageTime}: {poses}")

            for i in range(len(poses)):
                walleyeData.robotPublisher.publish(i, imageTime, poses[i], tags[i], ambig[i])
                
            for i, (identifier, img) in enumerate(images.items()):
                if i >= len(poses):
                    break
                camBuffers[identifier].update(img)
                walleyeData.setPose(identifier, poses[i])
                if walleyeData.visualizingPoses:
                    visualizationBuffers[identifier].update(
                        (poses[i].X(), poses[i].Y(), poses[i].Z()),
                        tags
                    )

        elif walleyeData.currentState == States.SHUTDOWN:
            logger.info("Shutting down")
            logging.shutdown()
            socketio.stop()
            break

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
    logging.critical(e, exc_info=True)
    logger.info("Shutting down")
    logging.shutdown()
    socketio.stop()
