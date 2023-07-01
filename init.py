from Calibration.calibration import Calibration
from Camera.camera import Cameras
import threading
from Processing.Processing import Processor
from Camera.camera import Cameras
from state import walleyeData, States, CALIBRATION_STATES

walleyeData.cameras = Cameras()

from WebInterface.InterfaceTest import (
    camBuffers,
    socketio,
    app,
)  # After walleyeData.cameras is set

webServer = threading.Thread(
    target=lambda: socketio.run(app, host="0.0.0.0", debug=True, use_reloader=False),
    daemon=True,
).start()

print("Web server ready")
print("Starting main loop")

walleyeData.makePublisher(2767, "Walleye")

images = {}
calibrators = {}

poseEstimator = Processor(0.157)
walleyeData.currentState = States.IDLE

while True:
    # State changes
    if walleyeData.currentState == States.IDLE:
        pass

    elif walleyeData.currentState == States.BEGIN_CALIBRATION:
        print("Beginning cal")
        calibrators[walleyeData.cameraInCalibration] = Calibration(
            walleyeData.calDelay,
            walleyeData.boardDims,
            walleyeData.cameraInCalibration,
            f"Calibration/Cam_{walleyeData.cameraInCalibration}CalImgs",
        )
        walleyeData.currentState = States.CALIBRATION_CAPTURE

    elif walleyeData.currentState == States.CALIBRATION_CAPTURE:
        _, img = walleyeData.cameras.info[walleyeData.cameraInCalibration].cam.read()

        returned, used, pathSaved = calibrators[
            walleyeData.cameraInCalibration
        ].processFrame(img)

        if used:
            walleyeData.calImgPaths.append(pathSaved)  # is saving this necessary?

        camBuffers[walleyeData.cameraInCalibration].update(returned)

    elif walleyeData.currentState == States.GENERATE_CALIBRATION:
        walleyeData.cameras.info[
            walleyeData.cameraInCalibration
        ].calibrationPath = Calibration.calibrationPathByCam(
            walleyeData.cameraInCalibration
        )

        calibrators[walleyeData.cameraInCalibration].generateCalibration(
            walleyeData.cameras.info[walleyeData.cameraInCalibration].calibrationPath
        )

        walleyeData.reprojectionError = calibrators[
            walleyeData.cameraInCalibration
        ].getReprojectionError()

        walleyeData.currentState = States.IDLE

    elif walleyeData.currentState == States.PROCESSING:
        images = walleyeData.cameras.getFrames()
        poses = poseEstimator.getPose(
            images.values(), walleyeData.cameras.listK(), walleyeData.cameras.listD()
        )
        print(poses)
        for i in range(len(poses)):
            walleyeData.robotPublisher.publish(
                i, walleyeData.robotPublisher.getTime(), poses[i]
            )
        for identifier, img in images.items():
            camBuffers[identifier].update(img)

    elif walleyeData.currentState == States.SHUTDOWN:
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
