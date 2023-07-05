from enum import Enum
from Publisher.NetworkTablePublisher import NetworkIO
import logging

class States(Enum):
    IDLE = "IDLE"
    BEGIN_CALIBRATION = "BEGIN_CALIBRATION"
    CALIBRATION_CAPTURE = "CALIBRATION_CAPTURE"
    GENERATE_CALIBRATION = "GENERATE_CALIBRATION"
    PROCESSING = "PROCESSING"
    SHUTDOWN = "SHUTDOWN"


CALIBRATION_STATES = (
    States.BEGIN_CALIBRATION,
    States.CALIBRATION_CAPTURE,
    States.GENERATE_CALIBRATION,
)


class Config:
    logger = logging.getLogger(__name__)

    def __init__(self) -> None:
        self.teamNumber = 2767
        self.tableName = "Walleye"

        self.currentState = States.PROCESSING

        # Calibration
        self.cameraInCalibration = None
        self.boardDims = (7, 7)
        self.calDelay = 1
        self.calImgPaths = []
        self.reprojectionError = None

        # Cams
        self.cameras = None

        self.robotPublisher = None

    def makePublisher(self, teamNumber, tableName):
        self.teamNumber = teamNumber
        self.tableName = tableName

        if self.robotPublisher is not None:
            self.robotPublisher.destroy()
            Config.logger.info("Existing publisher destroyed")

        self.robotPublisher = NetworkIO(
            True, walleyeData.teamNumber, walleyeData.tableName
        )

        Config.logger.info(f"Robot publisher created: {teamNumber} - {tableName}")

    def getCalFilePaths(self):
        return {i.identifier: i.calibrationPath for i in self.cameras.info.values()}

    def getState(self):
        return {
            "teamNumber": self.teamNumber,
            "tableName": self.tableName,
            "currentState": self.currentState.value,
            "cameraIDs": list(self.cameras.info.keys()),
            "cameraInCalibration": self.cameraInCalibration,
            "boardDims": self.boardDims,
            "calDelay": self.calDelay,
            "calImgPaths": self.calImgPaths,
            "reprojectionError": self.reprojectionError,
            "calFilePaths": self.getCalFilePaths(),
            "resolution": self.cameras.getResolutions(),
            "gain": self.cameras.getGains(),
            "exposure": self.cameras.getExposures(),
            "supportedResolutions": {
                k: v.supportedResolutions for k, v in self.cameras.info.items()
            },
        }


walleyeData = Config()
