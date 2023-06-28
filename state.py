from enum import Enum


class States(Enum):
    IDLE = "IDLE"
    BEGIN_CALIBRATION = "BEGIN_CALIBRATION"
    CALIBRATION_CAPTURE = "CALIBRATION_CAPTURE"
    GENERATE_CALIBRATION = "GENERATE_CALIBRATION"
    PROCESSING = "PROCESSING"
    SHUTDOWN = "SHUTDOWN"

TEAMNUMBER = 2767
TABLENAME = 'Walleye'


CALIBRATION_STATES = (
    States.BEGIN_CALIBRATION,
    States.CALIBRATION_CAPTURE,
    States.GENERATE_CALIBRATION,
)

currentState = States.IDLE
cameraIDs = []

# Calibration 
cameraInCalibration = None
boardDims = (7, 7)
calDelay = 1
calImgPaths = []
reprojectionError = None
calFilePath = None

# Configs
resolution = []
gain = []
exposure = []
camNum = None
from enum import Enum


class States(Enum):
    IDLE = "IDLE"
    BEGIN_CALIBRATION = "BEGIN_CALIBRATION"
    CALIBRATION_CAPTURE = "CALIBRATION_CAPTURE"
    GENERATE_CALIBRATION = "GENERATE_CALIBRATION"
    PROCESSING = "PROCESSING"
    SHUTDOWN = "SHUTDOWN"

TEAMNUMBER = 2767
TABLENAME = 'Walleye'


CALIBRATION_STATES = (
    States.BEGIN_CALIBRATION,
    States.CALIBRATION_CAPTURE,
    States.GENERATE_CALIBRATION,
)

currentState = States.IDLE
cameraIDs = []

# Calibration 
cameraInCalibration = None
boardDims = (7, 7)
calDelay = 1
calImgPaths = []
reprojectionError = None
calFilePath = None

# Configs
resolution = []
gain = []
exposure = []
camNum = None

cameraResolutions = []

def getState(): 
    return {"TEAMNUMBER": TEAMNUMBER, "TABLENAME": TABLENAME, "currentState": currentState.value, "cameraIDs": cameraIDs, "cameraInCalibration": cameraInCalibration, "boardDims": boardDims, "calDelay": calDelay, "calImgPaths": calImgPaths, "reprojectionError": reprojectionError, "calFilePath": calFilePath, "resolution": resolution, "gain": gain, "exposure": exposure, "cameraResolutions": cameraResolutions}