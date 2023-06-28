from Calibration.calibration import Calibration
from Camera.camera import Camera
import threading
import state
from Publisher.NetworkTablePublisher import NetworkIO
from Processing.Processing import Processor
from Camera.camera import Camera

# cams = Camera()
# cals = [None] * len(cams.cameras)  # Better init in the future
# state.cameraIDs = [i for i in range(len(cams.cameras))]  # Before server start

# Work around due to windows only dep
cams = Camera()
cals = [None] * cams.index
state.cameraIDs = list(range(cams.index))
state.resolution = cams.getResolution()
state.gain = cams.getGain()
state.exposure = cams.getExposure()
state.cameraResolutions = cams.supportedResolutions
state.camPaths = cams.cameraPaths

from WebInterface.InterfaceTest import camBuffers, socketio, app # After state.cameraIDs is set

webServer = threading.Thread(
    target=lambda: socketio.run(app, host="0.0.0.0", debug=True, use_reloader=False), daemon=True
).start()

print("Web server ready")
print("Starting main loop")

robotPublisher = NetworkIO(False, 2767, 'Walleye')
lastTeamNum = 2767
lastTableName = 'Walleye'
images = []

poseEstimator = Processor(0.157)
state.currentState = state.States.PROCESSING

while True:
    if state.camNum is not None:
        if state.gain[state.camNum] is not None and state.gain[state.camNum] != cams.getGain()[state.camNum]:
            cams.setGain(state.camNum, float(state.gain[state.camNum]))

        if state.exposure[state.camNum] is not None and state.exposure[state.camNum] != cams.getExposure()[state.camNum]:
            cams.setExposure(state.camNum, float(state.exposure[state.camNum]))

        if state.resolution[state.camNum] is not None and state.resolution[state.camNum] != cams.getResolution()[state.camNum]:
            cams.setResolution(state.camNum, state.resolution[state.camNum])

        state.camNum = None

    if lastTeamNum != state.TEAMNUMBER and state.TEAMNUMBER is not None:
        lastTeamNum = state.TEAMNUMBER
        print('\n\n\n\n',lastTeamNum)
        robotPublisher.destroy()
        robotPublisher = NetworkIO(True, lastTeamNum, lastTableName)

    if lastTableName != state.TABLENAME and state.TABLENAME is not None:
        lastTableName = state.TABLENAME
        print('\n\n\n\n',lastTableName)
        robotPublisher.destroy()
        robotPublisher = NetworkIO(True, lastTeamNum, lastTableName)

    if state.currentState == state.States.IDLE:
        pass

    elif state.currentState == state.States.BEGIN_CALIBRATION:
        print("Beginning cal")
        cals[state.cameraInCalibration] = Calibration(
            state.calDelay,
            state.boardDims,
            cams.cameraPaths[state.cameraInCalibration],
            f"Calibration/Cam_{state.cameraInCalibration}CalImgs",
        ) 
        state.currentState = state.States.CALIBRATION_CAPTURE

    elif state.currentState == state.States.CALIBRATION_CAPTURE:
        _, img = cams.cameras[state.cameraInCalibration].read()

        returned, used, pathSaved = cals[state.cameraInCalibration].processFrame(img)

        if used:
            state.calImgPaths.append(pathSaved)

        camBuffers[state.cameraInCalibration].update(returned)

    elif state.currentState == state.States.GENERATE_CALIBRATION:
        state.calFilePath = f"Calibration/Cam_{cams.cameraPaths[state.cameraInCalibration].replace('.', '-').replace(':', '-')}CalData.json"

        cals[state.cameraInCalibration].generateCalibration(
            state.calFilePath
        ) 

        state.reprojectionError = cals[state.cameraInCalibration].getReprojectionError()

        state.currentState = state.States.IDLE

    elif state.currentState == state.States.PROCESSING:
        images = cams.getFrames()
        poses = poseEstimator.getPose(images, cams.K, cams.D)   
        print(poses)
        for i in range(len(poses)):
            robotPublisher.publish(i, robotPublisher.getTime(), poses[i])
        for i in range(len(images)):
            camBuffers[i].update(images[i])

    elif state.currentState == state.States.SHUTDOWN:
        break
    
    if state.currentState != state.States.PROCESSING:
        for i in range(len(cams.cameras)):
            if (
                i == state.cameraInCalibration
                and state.currentState in state.CALIBRATION_STATES
            ): continue

            _, img = cams.cameras[i].read()
            
            camBuffers[i].update(img)