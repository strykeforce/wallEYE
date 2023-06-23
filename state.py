from enum import Enum


class States(Enum):
    IDLE = 1
    BEGIN_CALIBRATION = 2
    CALIBRATION_CAPTURE = 3
    GENERATE_CALIBRATION = 4
    PROCESSING = 5
    SHUTDOWN = 6
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